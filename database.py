import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from config import Config

logger = logging.getLogger(__name__)

# Global database client and db placeholder
client = None
db = None

def get_db():
    global client, db
    if db is None:
        client = AsyncIOMotorClient(Config.MONGO_URI)
        # Extract db name from URI or default to 'akhbarbot'
        db_name = Config.MONGO_URI.split("/")[-1].split("?")[0]
        if not db_name:
            db_name = "akhbarbot"
        db = client[db_name]
    return db

async def init_indexes():
    """Initializes MongoDB indexes for reliability and idempotency."""
    database = get_db()
    
    # Compound unique index for webhook deduplication
    try:
        await database.voice_notes.create_index(
            [("telegram_message_id", 1), ("chat_id", 1)],
            unique=True
        )
        logger.info("Successfully created unique compound index on voice_notes (telegram_message_id, chat_id)")
    except Exception as e:
        logger.error(f"Error creating voice_notes unique index: {e}")
        
    # Index for fast status checks and sorting
    try:
        await database.voice_notes.create_index([("chat_id", 1), ("status", 1), ("received_at", 1)])
        logger.info("Successfully created status indexing on voice_notes")
    except Exception as e:
        logger.error(f"Error creating status index: {e}")

    # Unique index for chat settings
    try:
        await database.settings.create_index("chat_id", unique=True)
        logger.info("Successfully created unique index on settings (chat_id)")
    except Exception as e:
        logger.error(f"Error creating settings index: {e}")

async def get_pending_voice_notes(chat_id: int):
    """Fetches all pending voice notes sorted chronologically."""
    database = get_db()
    cursor = database.voice_notes.find({"chat_id": chat_id, "status": "pending"}).sort("received_at", 1)
    return await cursor.to_list(length=100)

async def lock_voice_notes(note_ids: list):
    """Atomically sets status from 'pending' to 'processing' to prevent race conditions."""
    database = get_db()
    result = await database.voice_notes.update_many(
        {"_id": {"$in": note_ids}, "status": "pending"},
        {"$set": {"status": "processing"}}
    )
    return result.modified_count

async def processed_voice_notes(note_ids: list):
    """Sets status to 'processed' once synthesis completes."""
    database = get_db()
    await database.voice_notes.update_many(
        {"_id": {"$in": note_ids}},
        {"$set": {"status": "processed"}}
    )

async def rollback_voice_notes(note_ids: list):
    """Rolls back status from 'processing' to 'pending' in case of synthesis failure."""
    database = get_db()
    await database.voice_notes.update_many(
        {"_id": {"$in": note_ids}},
        {"$set": {"status": "pending"}}
    )

async def get_pending_count(chat_id: int) -> int:
    """Gets the current number of pending voice notes for the chat."""
    database = get_db()
    return await database.voice_notes.count_documents({"chat_id": chat_id, "status": "pending"})

async def save_voice_note(note_doc: dict) -> bool:
    """
    Saves a voice note to MongoDB.
    Returns True if successfully inserted, or False if it was a duplicate message ID.
    """
    database = get_db()
    try:
        await database.voice_notes.insert_one(note_doc)
        return True
    except DuplicateKeyError:
        logger.info(f"Duplicate Telegram message ID {note_doc['telegram_message_id']} for chat {note_doc['chat_id']}. Ignoring.")
        return False

async def save_article(article_doc: dict):
    """Saves a successfully generated news article to the database."""
    database = get_db()
    result = await database.articles.insert_one(article_doc)
    return result.inserted_id

async def get_recent_articles(limit: int = 20) -> list[dict]:
    """Fetches recently generated articles for Streamlit history views."""
    database = get_db()
    safe_limit = max(1, min(limit, 50))
    cursor = database.articles.find({}).sort("created_at", -1).limit(safe_limit)
    articles = await cursor.to_list(length=safe_limit)
    for article in articles:
        article["_id"] = str(article["_id"])
        if article.get("created_at"):
            article["created_at"] = article["created_at"].isoformat()
    return articles

async def get_chat_settings(chat_id: int) -> dict:
    """Fetches chat configurations/preferences (e.g. location, department). Defaults if none exist."""
    database = get_db()
    settings = await database.settings.find_one({"chat_id": chat_id})
    if not settings:
        settings = {
            "chat_id": chat_id,
            "location": "Prayagraj, India",
            "department": "General",
            "language": "Hindi"
        }
    return settings

async def get_chat_mode(chat_id: int) -> str | None:
    """Returns the current Telegram input mode for a chat, or None."""
    settings = await get_chat_settings(chat_id)
    return settings.get("mode")

async def set_chat_mode(chat_id: int, mode: str | None) -> None:
    """Sets the Telegram input mode for a chat. Pass None to clear."""
    await update_chat_settings(chat_id, {"mode": mode})

async def get_pending_stories(chat_id: int) -> list[dict] | None:
    """Returns pending stories awaiting selection, or None."""
    settings = await get_chat_settings(chat_id)
    stories = settings.get("pending_stories")
    if isinstance(stories, list):
        return stories
    return None

async def set_pending_stories(chat_id: int, stories: list[dict] | None) -> None:
    """Stores pending stories awaiting selection."""
    await update_chat_settings(chat_id, {"pending_stories": stories})

async def update_chat_settings(chat_id: int, updates: dict):
    """Updates settings for a specific chat ID."""
    database = get_db()
    await database.settings.update_one(
        {"chat_id": chat_id},
        {"$set": updates},
        upsert=True
    )

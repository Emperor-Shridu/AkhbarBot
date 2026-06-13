import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from config import Config
from database import (
    init_indexes,
    save_voice_note,
    get_pending_voice_notes,
    lock_voice_notes,
    processed_voice_notes,
    rollback_voice_notes,
    get_pending_count,
    save_article,
    get_chat_settings,
    update_chat_settings
)
from utils.telegram import (
    send_message,
    edit_message_text,
    answer_callback_query
)
from agents.supervisor import SupervisorAgent

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the supervisor agent
supervisor = SupervisorAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database connections and indexes...")
    await init_indexes()
    yield
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(lifespan=lifespan)

# Helper functions for the Dashboard UI
async def get_dashboard_markup(chat_id: int) -> dict:
    pending_count = await get_pending_count(chat_id)
    return {
        "inline_keyboard": [
            [
                {"text": f"🎙️ Voice Notes ({pending_count} Pending)", "callback_data": "compile_voice"},
                {"text": "📸 Image / Document", "callback_data": "ocr_info"}
            ],
            [
                {"text": "✏️ Enter Text Topic", "callback_data": "topic_info"},
                {"text": "🌍 Top Local Trends", "callback_data": "run_trends"}
            ]
        ]
    }

async def get_dashboard_text(chat_id: int, settings: dict) -> str:
    location = settings.get("location", "Delhi")
    department = settings.get("department", "General")
    language = settings.get("language", "Hindi")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return (
        f"📰 *AkhbarBot Command Center*\n\n"
        f"📍 *Location Preference:* {location}\n"
        f"🏢 *Department Focus:* {department}\n"
        f"🌐 *Language:* {language}\n"
        f"📅 *Active Timestamp:* {now_str}\n\n"
        f"Select an ingestion source to compile your report:"
    )

async def refresh_dashboard(chat_id: int):
    """Refreshes the dynamic inline dashboard keyboard labels."""
    settings = await get_chat_settings(chat_id)
    msg_id = settings.get("dashboard_message_id")
    if msg_id:
        text = await get_dashboard_text(chat_id, settings)
        markup = await get_dashboard_markup(chat_id)
        try:
            await edit_message_text(chat_id, msg_id, text, reply_markup=markup)
        except Exception as e:
            logger.warning(f"Failed to edit dashboard message {msg_id}: {e}. Sending new dashboard.")
            # If editing fails, reset dashboard message ID to force resending on next request
            await update_chat_settings(chat_id, {"dashboard_message_id": None})

async def send_new_dashboard(chat_id: int):
    """Sends a new Command Center dashboard and saves its message ID."""
    settings = await get_chat_settings(chat_id)
    text = await get_dashboard_text(chat_id, settings)
    markup = await get_dashboard_markup(chat_id)
    
    res = await send_message(chat_id, text, reply_markup=markup)
    if res.get("ok"):
        msg_id = res["result"]["message_id"]
        await update_chat_settings(chat_id, {"dashboard_message_id": msg_id})


# Background processing tasks
async def task_compile_voice_notes(chat_id: int, note_ids: list, settings: dict):
    """Background task to run audio segmentation, parallel concepts extraction and synthesis."""
    try:
        # Fetch actual notes from database to pass records
        notes = []
        from database import get_db
        db_conn = get_db()
        notes = await db_conn.voice_notes.find({"_id": {"$in": note_ids}}).to_list(length=100)
        
        # Call supervisor
        article = await supervisor.compile_voice_notes(notes, settings)
        
        # Save generated article
        article_doc = {
            "associated_voice_note_ids": [n.get("telegram_message_id") for n in notes],
            "generated_article_hindi": article,
            "created_at": datetime.now(),
            "chat_id": chat_id
        }
        await save_article(article_doc)
        
        # Update status to processed
        await processed_voice_notes(note_ids)
        
        # Send synthesized article
        await send_message(chat_id, article)
        
    except Exception as e:
        logger.error(f"Error compiling voice notes: {e}")
        # Rollback status to pending on error
        await rollback_voice_notes(note_ids)
        await send_message(chat_id, f"❌ समाचार संश्लेषण प्रक्रिया विफल रही: {str(e)}")
    finally:
        # Refresh dashboard layout
        await refresh_dashboard(chat_id)

async def task_compile_image(chat_id: int, file_id: str, mime_type: str, settings: dict):
    """Background task to extract document text via OCR and synthesize news."""
    try:
        article = await supervisor.compile_image_document(file_id, mime_type, settings)
        
        # Save article
        article_doc = {
            "source_type": "image_ocr",
            "telegram_file_id": file_id,
            "generated_article_hindi": article,
            "created_at": datetime.now(),
            "chat_id": chat_id
        }
        await save_article(article_doc)
        await send_message(chat_id, article)
    except Exception as e:
        logger.error(f"Error compiling image OCR: {e}")
        await send_message(chat_id, f"❌ दस्तावेज़ विश्लेषण विफल रहा: {str(e)}")

async def task_compile_topic(chat_id: int, topic: str, settings: dict):
    """Background task to search real-time verified data and compile news."""
    try:
        article = await supervisor.compile_topic_search(topic, settings)
        
        # Save article
        article_doc = {
            "source_type": "topic_search",
            "topic": topic,
            "generated_article_hindi": article,
            "created_at": datetime.now(),
            "chat_id": chat_id
        }
        await save_article(article_doc)
        await send_message(chat_id, article)
    except Exception as e:
        logger.error(f"Error compiling topic news: {e}")
        await send_message(chat_id, f"❌ विषय विश्लेषण विफल रहा: {str(e)}")

async def task_compile_trends(chat_id: int, settings: dict):
    """Background task to fetch top trends and synthesize news."""
    try:
        article = await supervisor.compile_top_trends(settings)
        
        # Save article
        article_doc = {
            "source_type": "top_trends",
            "generated_article_hindi": article,
            "created_at": datetime.now(),
            "chat_id": chat_id
        }
        await save_article(article_doc)
        await send_message(chat_id, article)
    except Exception as e:
        logger.error(f"Error compiling top trends: {e}")
        await send_message(chat_id, f"❌ स्थानीय समाचार रुझान विश्लेषण विफल रहा: {str(e)}")


@app.post("/api/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Main Telegram Bot API Webhook router."""
    try:
        body = await request.json()
        logger.info(f"Received update: {body}")
        
        # Handle Callback Queries (Inline keyboard clicks)
        if "callback_query" in body:
            callback = body["callback_query"]
            callback_id = callback["id"]
            chat_id = callback["message"]["chat"]["id"]
            data = callback["data"]
            
            # Security verification
            if Config.ALLOWED_CHAT_ID and str(chat_id) != str(Config.ALLOWED_CHAT_ID):
                logger.warn(f"Ignored callback from unauthorized chat ID: {chat_id}")
                await answer_callback_query(callback_id, "Unauthorized chat", show_alert=True)
                return {"ok": True}
                
            settings = await get_chat_settings(chat_id)
            
            if data == "compile_voice":
                pending_notes = await get_pending_voice_notes(chat_id)
                if not pending_notes:
                    await answer_callback_query(callback_id, "कोई भी लंबित वॉयस नोट नहीं मिला। कृपया पहले वॉयस नोट भेजें।", show_alert=True)
                    return {"ok": True}
                
                note_ids = [n["_id"] for n in pending_notes]
                # Lock notes synchronously
                locked_count = await lock_voice_notes(note_ids)
                if locked_count == 0:
                    await answer_callback_query(callback_id, "संश्लेषण पहले से ही प्रगति पर है।", show_alert=True)
                    return {"ok": True}
                
                await answer_callback_query(callback_id, "समाचार रिपोर्ट संकलन शुरू हो रहा है...")
                
                # Update dashboard to show busy/processing status
                msg_id = callback["message"]["message_id"]
                await edit_message_text(
                    chat_id, 
                    msg_id, 
                    "⏳ *वॉयस नोट्स का विश्लेषण (synthesis) शुरू हो रहा है...*\n\nसक्रिय संकलन प्रगति पर है। कृपया प्रतीक्षा करें।"
                )
                
                # Add background job
                background_tasks.add_task(task_compile_voice_notes, chat_id, note_ids, settings)
                
            elif data == "ocr_info":
                await answer_callback_query(callback_id)
                await send_message(chat_id, "📸 **दस्तावेज़ से समाचार:**\n\nसमाचार विश्लेषण करने के लिए किसी दस्तावेज़ की फ़ोटो, समाचार पत्र का पृष्ठ या स्क्रीनशॉट भेजें।")
                
            elif data == "topic_info":
                await answer_callback_query(callback_id)
                await send_message(chat_id, "✏️ **विषय पर समाचार:**\n\nसर्च और विश्लेषण के लिए चैट में `/topic <आपका विषय>` लिखकर भेजें।\n\nउदाहरण:\n`/topic स्थानीय कृषि विकास`")
                
            elif data == "run_trends":
                await answer_callback_query(callback_id, "स्थानीय समाचार रुझानों का विश्लेषण शुरू हो रहा है...")
                await send_message(chat_id, f"🌍 **सक्रिय रुझान:**\n\nस्थान: `{settings['location']}`\nश्रेणी: `{settings['department']}`\nके लिए नवीनतम समाचारों की खोज की जा रही है...")
                background_tasks.add_task(task_compile_trends, chat_id, settings)
                
            return {"ok": True}

        # Handle Standard Messages
        message = body.get("message")
        if not message:
            return {"ok": True}
            
        chat_id = message["chat"]["id"]
        
        # Whitelist filtering
        if Config.ALLOWED_CHAT_ID and str(chat_id) != str(Config.ALLOWED_CHAT_ID):
            logger.warn(f"Ignored message from unauthorized chat ID: {chat_id}")
            return {"ok": True}
            
        settings = await get_chat_settings(chat_id)
        
        # 1. Handle Voice Notes / Audio Files
        file_id = None
        mime_type = "audio/ogg" # Default
        
        if "voice" in message:
            file_id = message["voice"]["file_id"]
            mime_type = message["voice"].get("mime_type", "audio/ogg")
        elif "audio" in message:
            file_id = message["audio"]["file_id"]
            mime_type = message["audio"].get("mime_type", "audio/mpeg")
        elif "document" in message and message["document"].get("mime_type", "").startswith("audio/"):
            file_id = message["document"]["file_id"]
            mime_type = message["document"]["mime_type"]
            
        if file_id:
            note_doc = {
                "telegram_message_id": message["message_id"],
                "chat_id": chat_id,
                "telegram_file_id": file_id,
                "mime_type": mime_type,
                "received_at": datetime.fromtimestamp(message["date"]),
                "status": "pending"
            }
            # Attempt to save. If it is a duplicate message, it returns False
            saved = await save_voice_note(note_doc)
            if saved:
                await send_message(
                    chat_id,
                    "🎙️ **ऑडियो/वॉयस नोट सुरक्षित कर लिया गया है!**\n\nसमाचार रिपोर्ट संकलित करने के लिए नीचे दिए गए 'Voice Notes' बटन पर क्लिक करें।",
                    reply_to_message_id=message["message_id"]
                )
                # Refresh dashboard to show updated pending counts
                await refresh_dashboard(chat_id)
            return {"ok": True}

        # 2. Handle Photos / Images
        if "photo" in message:
            # Get the highest resolution photo (last element in array)
            photo = message["photo"][-1]
            file_id = photo["file_id"]
            
            await send_message(chat_id, "📸 **दस्तावेज़ की फ़ोटो प्राप्त हुई!**\n\nOCR और समाचार विश्लेषण प्रारंभ हो रहा है... कृपया प्रतीक्षा करें।")
            background_tasks.add_task(task_compile_image, chat_id, file_id, "image/jpeg", settings)
            return {"ok": True}
        
        elif "document" in message and message["document"].get("mime_type", "").startswith("image/"):
            file_id = message["document"]["file_id"]
            mime_type = message["document"]["mime_type"]
            
            await send_message(chat_id, "📸 **दस्तावेज़ प्राप्त हुआ!**\n\nOCR और समाचार विश्लेषण प्रारंभ हो रहा है... कृपया प्रतीक्षा करें।")
            background_tasks.add_task(task_compile_image, chat_id, file_id, mime_type, settings)
            return {"ok": True}

        # 3. Handle Commands and Text Messages
        text = message.get("text", "").strip()
        if not text:
            return {"ok": True}
            
        if text.startswith("/start"):
            await send_message(chat_id, "👋 **AkhbarBot v2 (Python Multi-Agent Edition) में आपका स्वागत है!**")
            await send_new_dashboard(chat_id)
            
        elif text.startswith("/compile"):
            # Programmatic compile command
            pending_notes = await get_pending_voice_notes(chat_id)
            if not pending_notes:
                await send_message(chat_id, "❌ कोई भी लंबित (pending) वॉयस नोट नहीं मिला।")
                return {"ok": True}
                
            note_ids = [n["_id"] for n in pending_notes]
            locked_count = await lock_voice_notes(note_ids)
            if locked_count == 0:
                await send_message(chat_id, "❌ समाचार संश्लेषण पहले से ही प्रगति पर है।")
                return {"ok": True}
                
            await send_message(chat_id, f"⏳ *{len(pending_notes)}* वॉयस नोट्स का विश्लेषण शुरू हो रहा है...")
            background_tasks.add_task(task_compile_voice_notes, chat_id, note_ids, settings)
            
        elif text.startswith("/topic"):
            # Command syntax: /topic <topic string>
            topic_query = text[len("/topic"):].strip()
            if not topic_query:
                await send_message(chat_id, "❌ कृपया /topic के साथ अपना खोज विषय लिखें।\n\nउदाहरण: `/topic भारत की डिजिटल अर्थव्यवस्था`")
                return {"ok": True}
                
            await send_message(chat_id, f"🔍 **'{topic_query}'** पर समाचार और तथ्य संकलित किए जा रहे हैं...")
            background_tasks.add_task(task_compile_topic, chat_id, topic_query, settings)
            
        elif text.startswith("/location"):
            loc = text[len("/location"):].strip()
            if not loc:
                await send_message(chat_id, f"❌ स्थान बदलने के लिए लिखें: `/location <स्थान का नाम>`\n\nवर्तमान स्थान: `{settings.get('location')}`")
                return {"ok": True}
            await update_chat_settings(chat_id, {"location": loc})
            await send_message(chat_id, f"✅ स्थान बदलकर `{loc}` कर दिया गया है।")
            await refresh_dashboard(chat_id)
            
        elif text.startswith("/dept"):
            dept = text[len("/dept"):].strip()
            if not dept:
                await send_message(chat_id, f"❌ विभाग बदलने के लिए लिखें: `/dept <विभाग का नाम>`\n\nवर्तमान विभाग: `{settings.get('department')}`")
                return {"ok": True}
            await update_chat_settings(chat_id, {"department": dept})
            await send_message(chat_id, f"✅ विभाग बदलकर `{dept}` कर दिया गया है।")
            await refresh_dashboard(chat_id)

        elif text.startswith("/lang"):
            lang = text[len("/lang"):].strip()
            if not lang:
                await send_message(chat_id, f"❌ भाषा बदलने के लिए लिखें: `/lang <भाषा का नाम>`\n\nवर्तमान भाषा: `{settings.get('language')}`")
                return {"ok": True}
            await update_chat_settings(chat_id, {"language": lang})
            await send_message(chat_id, f"✅ भाषा बदलकर `{lang}` कर दिया गया है।")
            await refresh_dashboard(chat_id)
            
        elif text.startswith("/dashboard"):
            await send_new_dashboard(chat_id)
            
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        # Always return 200 to Telegram to avoid webhook retry loops
        return JSONResponse(status_code=200, content={"ok": True})

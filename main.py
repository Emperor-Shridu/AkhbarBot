"""FastAPI backend for Telegram webhooks and Streamlit article APIs."""

import logging
import re
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import Config
from database import get_chat_settings, get_chat_mode, get_pending_stories, get_recent_articles, init_indexes, set_chat_mode, set_pending_stories, update_chat_settings
from services.news_service import NewsService, NewsSettings
from user_interactions import (
    VIDEO_RECEIVED,
    AUDIO_RECEIVED,
    DASHBOARD_BODY,
    ERROR_AUDIO,
    ERROR_IMAGE,
    ERROR_SOCIAL,
    ERROR_TEXT,
    IMAGE_RECEIVED,
    MODE_CLEARED,
    MODE_PROMPT_AUDIO,
    MODE_PROMPT_IMAGE,
    MODE_PROMPT_LINK,
    MODE_PROMPT_PROFESSIONALIZE,
    MODE_PROMPT_TEXT,
    MODE_PROMPT_TOPIC,
    MODE_PROMPT_TOPIC_SELECTION,
    SETTINGS_HELP,
    SOCIAL_LINK_RECEIVED,
    TEXT_RECEIVED,
    WELCOME_TEXT,
    ERROR_VIDEO,
)
from utils.telegram import answer_callback_query as tg_answer_callback_query
from utils.telegram import download_file as tg_download_file
from utils.telegram import get_file as tg_get_file
from utils.telegram import send_message as tg_send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

NOISE_TEXTS = {"hi", "hello", "hey", "ok", "okay", "hmm", "yes", "no", "test", "testing"}

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
Config.validate()
news_service = NewsService()


class ArticleRequest(BaseModel):
    """Request body for text-based article generation paths."""

    text: str = Field(..., min_length=1)
    location: str = "Delhi"
    department: str = "General"


class SocialLinkRequest(BaseModel):
    """Request body for public social media URL processing."""

    url: str = Field(..., min_length=1)
    location: str = "Delhi"
    department: str = "General"


class ArticleResponse(BaseModel):
    """Response body returned by article-generation endpoints."""

    article: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes shared backend resources when the web service starts."""
    logger.info("Initializing database connections and indexes...")
    await init_indexes()
    yield
    logger.info("Shutting down application...")


app = FastAPI(title="AkhbarBot Telegram + Streamlit Backend", lifespan=lifespan)


def _settings(location: str = "Delhi", department: str = "General") -> NewsSettings:
    """Builds normalized Hindi-only article settings."""
    return NewsSettings(location=location, department=department, language="Hindi")


def _is_public_url(text: str) -> bool:
    """Returns whether a message contains a public-looking HTTP URL."""
    match = URL_PATTERN.search(text or "")
    if not match:
        return False
    host = urlparse(match.group(0)).netloc.lower()
    return bool(host and "." in host)


def _first_url(text: str) -> str:
    """Extracts the first URL from a user message."""
    match = URL_PATTERN.search(text or "")
    return match.group(0).rstrip(").,") if match else ""


async def require_streamlit_user(
    x_user_id: str = Header(default=""),
    x_api_secret: str = Header(default=""),
) -> str:
    """Protects frontend APIs with an allowed user id and optional shared secret."""
    if Config.API_SHARED_SECRET and x_api_secret != Config.API_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API secret")
    if not Config.is_streamlit_user_allowed(x_user_id):
        raise HTTPException(status_code=403, detail="User id is not allowed")
    return x_user_id


@app.get("/health")
async def health() -> dict[str, bool]:
    """Lightweight health check for Render and uptime checks."""
    return {"ok": True}


@app.post("/api/articles/text", response_model=ArticleResponse)
async def create_text_article(request: ArticleRequest, user_id: str = Depends(require_streamlit_user)):
    """Creates a Hindi article from pasted text or a topic brief."""
    article = await news_service.from_text(
        request.text,
        _settings(request.location, request.department),
        {"channel": "streamlit", "user_id": user_id},
    )
    return ArticleResponse(article=article)


@app.post("/api/articles/latest-topic", response_model=ArticleResponse)
async def create_latest_topic_article(request: ArticleRequest, user_id: str = Depends(require_streamlit_user)):
    """Creates a Hindi article from the latest verified updates around a topic."""
    article = await news_service.from_latest_topic_article(
        request.text,
        _settings(request.location, request.department),
        {"channel": "streamlit", "user_id": user_id},
    )
    return ArticleResponse(article=article)


@app.post("/api/articles/professionalize", response_model=ArticleResponse)
async def professionalize_article(request: ArticleRequest, user_id: str = Depends(require_streamlit_user)):
    """Rewrites a draft article into polished Hindi newsroom copy."""
    article = await news_service.professionalize(
        request.text,
        _settings(request.location, request.department),
        {"channel": "streamlit", "user_id": user_id},
    )
    return ArticleResponse(article=article)


@app.post("/api/articles/social-link", response_model=ArticleResponse)
async def create_social_link_article(request: SocialLinkRequest, user_id: str = Depends(require_streamlit_user)):
    """Creates a Hindi article from a public media URL."""
    article = await news_service.from_social_link(
        request.url,
        _settings(request.location, request.department),
        {"channel": "streamlit", "user_id": user_id},
    )
    return ArticleResponse(article=article)


@app.post("/api/articles/audio", response_model=ArticleResponse)
async def create_audio_article(
    location: str = "Delhi",
    department: str = "General",
    file: UploadFile = File(...),
    user_id: str = Depends(require_streamlit_user),
):
    """Creates a Hindi article from uploaded audio bytes."""
    audio_bytes = await file.read()
    article = await news_service.from_audio(
        audio_bytes,
        file.content_type or "audio/ogg",
        _settings(location, department),
        file.filename or "streamlit_audio",
        {"channel": "streamlit", "user_id": user_id, "filename": file.filename},
    )
    return ArticleResponse(article=article)


@app.post("/api/articles/image", response_model=ArticleResponse)
async def create_image_article(
    location: str = "Delhi",
    department: str = "General",
    file: UploadFile = File(...),
    user_id: str = Depends(require_streamlit_user),
):
    """Creates a Hindi article from an uploaded image or scanned document."""
    image_bytes = await file.read()
    article = await news_service.from_image(
        image_bytes,
        file.content_type or "image/jpeg",
        _settings(location, department),
        {"channel": "streamlit", "user_id": user_id, "filename": file.filename},
    )
    return ArticleResponse(article=article)


@app.get("/api/articles/history")
async def article_history(limit: int = 20, user_id: str = Depends(require_streamlit_user)):
    """Returns recent generated articles for the Streamlit history tab."""
    return {"articles": await get_recent_articles(limit)}


async def _send_telegram_dashboard(chat_id: int) -> None:
    """Sends Telegram users the compact command menu."""
    settings = await get_chat_settings(chat_id)
    body = DASHBOARD_BODY.format(
        location=settings.get("location", "Delhi"),
        department=settings.get("department", "General"),
        language=settings.get("language", "Hindi"),
    )
    markup = {
        "inline_keyboard": [
            [{"text": "Audio to news", "callback_data": "audio_to_news"}],
            [{"text": "Social link to news", "callback_data": "social_link_to_news"}],
            [{"text": "OCR to news", "callback_data": "ocr_to_news"}],
            [{"text": "Text to news", "callback_data": "text_to_news"}],
            [{"text": "Latest topic", "callback_data": "latest_topic"}],
            [{"text": "Professionalize article", "callback_data": "professionalize"}],
        ]
    }
    await tg_send_message(chat_id, f"{WELCOME_TEXT}\n\n{body}", reply_markup=markup)


async def task_compile_telegram_audio(chat_id: int, file_id: str, mime_type: str, settings: dict, sender: dict):
    """Downloads Telegram audio, generates an article, and sends the result."""
    try:
        file_info = await tg_get_file(file_id)
        audio_bytes = await tg_download_file(file_info["file_path"])
        article = await news_service.from_audio(
            audio_bytes,
            mime_type,
            _settings(settings.get("location", "Delhi"), settings.get("department", "General")),
            file_id,
            {"channel": "telegram", "chat_id": chat_id, "sender": sender},
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram audio compilation failed")
        await tg_send_message(chat_id, ERROR_AUDIO.format(error=str(exc)))


async def task_compile_telegram_image(chat_id: int, file_id: str, mime_type: str, settings: dict, sender: dict):
    """Downloads Telegram image media, generates an article, and sends it."""
    try:
        file_info = await tg_get_file(file_id)
        image_bytes = await tg_download_file(file_info["file_path"])
        article = await news_service.from_image(
            image_bytes,
            mime_type,
            _settings(settings.get("location", "Delhi"), settings.get("department", "General")),
            {"channel": "telegram", "chat_id": chat_id, "sender": sender},
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram image compilation failed")
        await tg_send_message(chat_id, ERROR_IMAGE.format(error=str(exc)))


async def task_compile_telegram_video(chat_id: int, file_id: str, mime_type: str, settings: dict, sender: dict):
    """Downloads Telegram video media, generates an article, and sends it."""
    try:
        file_info = await tg_get_file(file_id)
        video_bytes = await tg_download_file(file_info["file_path"])
        article = await news_service.from_audio(
            video_bytes,
            mime_type,
            _settings(settings.get("location", "Delhi"), settings.get("department", "General")),
            file_id,
            {"channel": "telegram", "chat_id": chat_id, "sender": sender},
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram video compilation failed")
        await tg_send_message(chat_id, ERROR_VIDEO.format(error=str(exc)))


async def task_compile_telegram_social_link(chat_id: int, url: str, settings: dict, sender: dict):
    """Generates an article from a public URL received on Telegram."""
    try:
        article = await news_service.from_social_link(
            url,
            _settings(settings.get("location", "Delhi"), settings.get("department", "General")),
            {"channel": "telegram", "chat_id": chat_id, "sender": sender},
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram social link compilation failed")
        await tg_send_message(chat_id, ERROR_SOCIAL.format(error=str(exc)))


async def task_compile_telegram_text(chat_id: int, text: str, settings: dict, sender: dict):
    """Generates an article from Telegram text and sends it back."""
    try:
        article = await news_service.from_text(
            text,
            _settings(settings.get("location", "Delhi"), settings.get("department", "General")),
            {"channel": "telegram", "chat_id": chat_id, "sender": sender},
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram text compilation failed")
        await tg_send_message(chat_id, ERROR_TEXT.format(error=str(exc)))


async def task_compile_telegram_latest_topic(chat_id: int, topic: str, settings: dict, sender: dict):
    """Generates multiple latest topic story options for selection."""
    try:
        formatted_text, story_list = await news_service.from_latest_topic(
            topic,
            _settings(settings.get("location", "Delhi"), settings.get("department", "General")),
            {"channel": "telegram", "chat_id": chat_id, "sender": sender},
        )
        
        if not story_list:
            # Fallback: no stories found, return formatted text as-is
            await tg_send_message(chat_id, formatted_text)
            return
        
        await set_pending_stories(chat_id, story_list)
        
        lines = [f"Topic: {topic}", "Choose a story by replying with its number:"]
        for idx, story in enumerate(story_list[:5], 1):
            lines.append(f"\n{idx}. {story.get('title', 'Untitled')}")
            lines.append(f"   {story.get('summary', '')[:200]}...")
        
        await tg_send_message(chat_id, "\n".join(lines))
        await set_chat_mode(chat_id, "latest_topic_selection")
        await tg_send_message(chat_id, MODE_PROMPT_TOPIC_SELECTION)
    except Exception as exc:
        logger.exception("Telegram latest topic compilation failed")
        await tg_send_message(chat_id, ERROR_TEXT.format(error=str(exc)))


async def task_expand_telegram_story(chat_id: int, story_index: int, settings: dict, sender: dict):
    """Expands a user-selected story into a full article."""
    try:
        stories = await get_pending_stories(chat_id)
        if not stories or story_index < 0 or story_index >= len(stories):
            await tg_send_message(chat_id, "Invalid selection. Please try again.")
            return
        
        story = stories[story_index]
        await tg_send_message(chat_id, f"Expanding: {story.get('title', 'Story')}...")
        
        article = await news_service.expand_story(
            story,
            _settings(settings.get("location", "Delhi"), settings.get("department", "General")),
            {"channel": "telegram", "chat_id": chat_id, "sender": sender},
        )
        await tg_send_message(chat_id, article)
        await set_pending_stories(chat_id, None)
    except Exception as exc:
        logger.exception("Telegram story expansion failed")
        await tg_send_message(chat_id, ERROR_TEXT.format(error=str(exc)))


async def task_compile_telegram_professionalize(chat_id: int, draft: str, settings: dict, sender: dict):
    """Rewrites a draft into a polished Hindi news article."""
    try:
        article = await news_service.professionalize(
            draft,
            _settings(settings.get("location", "Delhi"), settings.get("department", "General")),
            {"channel": "telegram", "chat_id": chat_id, "sender": sender},
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram professionalize compilation failed")
        await tg_send_message(chat_id, ERROR_TEXT.format(error=str(exc)))


@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives Telegram updates and routes them into the shared article service."""
    try:
        body = await request.json()

        if "callback_query" in body:
            callback = body["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            await tg_answer_callback_query(callback["id"])
            if Config.is_chat_allowed(chat_id):
                data = callback.get("data", "")
                mode_map = {
                    "audio_to_news": ("audio", MODE_PROMPT_AUDIO),
                    "social_link_to_news": ("social_link", MODE_PROMPT_LINK),
                    "ocr_to_news": ("image", MODE_PROMPT_IMAGE),
                    "text_to_news": ("text", MODE_PROMPT_TEXT),
                    "latest_topic": ("latest_topic", MODE_PROMPT_TOPIC),
                    "professionalize": ("professionalize", MODE_PROMPT_PROFESSIONALIZE),
                }
                if data in mode_map:
                    mode, prompt = mode_map[data]
                    await set_chat_mode(chat_id, mode)
                    await tg_send_message(chat_id, prompt)
                else:
                    await tg_send_message(chat_id, SETTINGS_HELP)
            return {"ok": True}

        message = body.get("message")
        if not message:
            return {"ok": True}

        chat_id = message["chat"]["id"]
        if not Config.is_chat_allowed(chat_id):
            return {"ok": True}

        settings = await get_chat_settings(chat_id)
        from_user = message.get("from", {})
        sender = {
            "user_id": from_user.get("id"),
            "username": from_user.get("username"),
            "first_name": from_user.get("first_name"),
            "last_name": from_user.get("last_name"),
        }

        if "voice" in message:
            file_id = message["voice"]["file_id"]
            mime_type = message["voice"].get("mime_type", "audio/ogg")
            await tg_send_message(chat_id, AUDIO_RECEIVED)
            background_tasks.add_task(task_compile_telegram_audio, chat_id, file_id, mime_type, settings, sender)
            return {"ok": True}

        if "audio" in message:
            file_id = message["audio"]["file_id"]
            mime_type = message["audio"].get("mime_type", "audio/mpeg")
            await tg_send_message(chat_id, AUDIO_RECEIVED)
            background_tasks.add_task(task_compile_telegram_audio, chat_id, file_id, mime_type, settings, sender)
            return {"ok": True}

        if "video" in message:
            file_id = message["video"]["file_id"]
            mime_type = message["video"].get("mime_type", "video/mp4")
            await tg_send_message(chat_id, VIDEO_RECEIVED)
            background_tasks.add_task(task_compile_telegram_video, chat_id, file_id, mime_type, settings, sender)
            return {"ok": True}

        if "photo" in message:
            file_id = message["photo"][-1]["file_id"]
            await tg_send_message(chat_id, IMAGE_RECEIVED)
            background_tasks.add_task(task_compile_telegram_image, chat_id, file_id, "image/jpeg", settings, sender)
            return {"ok": True}

        if "document" in message:
            doc = message["document"]
            mime_type = doc.get("mime_type", "")
            if mime_type.startswith("image/"):
                await tg_send_message(chat_id, IMAGE_RECEIVED)
                background_tasks.add_task(task_compile_telegram_image, chat_id, doc["file_id"], mime_type, settings, sender)
                return {"ok": True}
            if mime_type.startswith("audio/"):
                await tg_send_message(chat_id, AUDIO_RECEIVED)
                background_tasks.add_task(task_compile_telegram_audio, chat_id, doc["file_id"], mime_type, settings, sender)
                return {"ok": True}
            if mime_type.startswith("video/"):
                await tg_send_message(chat_id, VIDEO_RECEIVED)
                background_tasks.add_task(task_compile_telegram_video, chat_id, doc["file_id"], mime_type, settings, sender)
                return {"ok": True}

        text = message.get("text", "").strip()
        if not text:
            return {"ok": True}

        if text.lower() in NOISE_TEXTS:
            return {"ok": True}

        mode = await get_chat_mode(chat_id)

        if text.lower() in {"/start", "start", "menu", "/menu"}:
            await _send_telegram_dashboard(chat_id)
            await set_chat_mode(chat_id, None)
        elif text.startswith("/cancel"):
            await set_chat_mode(chat_id, None)
            await tg_send_message(chat_id, MODE_CLEARED)
        elif text.startswith("/location"):
            value = text[len("/location"):].strip()
            if value:
                await update_chat_settings(chat_id, {"location": value})
                await tg_send_message(chat_id, f"Location updated to {value}.")
        elif text.startswith("/dept"):
            value = text[len("/dept"):].strip()
            if value:
                await update_chat_settings(chat_id, {"department": value})
                await tg_send_message(chat_id, f"Department updated to {value}.")
        elif text.startswith("/lang"):
            await tg_send_message(chat_id, "Language is fixed to Hindi for publish-ready output.")
        elif mode == "text":
            await tg_send_message(chat_id, TEXT_RECEIVED)
            background_tasks.add_task(task_compile_telegram_text, chat_id, text, settings, sender)
            await set_chat_mode(chat_id, None)
        elif mode == "latest_topic":
            await tg_send_message(chat_id, TEXT_RECEIVED)
            background_tasks.add_task(task_compile_telegram_latest_topic, chat_id, text, settings, sender)
        elif mode == "latest_topic_selection":
            if text.isdigit():
                idx = int(text) - 1
                background_tasks.add_task(task_expand_telegram_story, chat_id, idx, settings, sender)
                await set_chat_mode(chat_id, None)
            else:
                await tg_send_message(chat_id, "Please send a number to select a story (e.g., send '1', '2', etc.).")
        elif mode == "professionalize":
            await tg_send_message(chat_id, TEXT_RECEIVED)
            background_tasks.add_task(task_compile_telegram_professionalize, chat_id, text, settings, sender)
            await set_chat_mode(chat_id, None)
        elif mode == "social_link":
            if _is_public_url(text):
                url = _first_url(text)
                await tg_send_message(chat_id, SOCIAL_LINK_RECEIVED)
                background_tasks.add_task(task_compile_telegram_social_link, chat_id, url, settings, sender)
            else:
                await tg_send_message(chat_id, "Please send a valid public URL.")
        elif mode == "image":
            await tg_send_message(chat_id, "Please send a photo or document.")
        elif mode == "audio":
            await tg_send_message(chat_id, "Please send a voice message or audio file.")
        elif _is_public_url(text):
            url = _first_url(text)
            await tg_send_message(chat_id, SOCIAL_LINK_RECEIVED)
            background_tasks.add_task(task_compile_telegram_social_link, chat_id, url, settings, sender)
        else:
            await tg_send_message(chat_id, TEXT_RECEIVED)
            background_tasks.add_task(task_compile_telegram_text, chat_id, text, settings, sender)

        return {"ok": True}
    except Exception as exc:
        logger.exception("Telegram webhook processing error: %s", exc)
        return JSONResponse(status_code=200, content={"ok": True})

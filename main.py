import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import urlparse

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from agents.supervisor import SupervisorAgent
from config import Config
from database import get_chat_settings, init_indexes, save_article, update_chat_settings
from user_interactions import (
    AUDIO_RECEIVED,
    DASHBOARD_BODY,
    ERROR_AUDIO,
    ERROR_IMAGE,
    ERROR_SOCIAL,
    ERROR_TEXT,
    IMAGE_RECEIVED,
    SETTINGS_HELP,
    SOCIAL_LINK_RECEIVED,
    TEXT_RECEIVED,
    WELCOME_TEXT,
)
from utils.whatsapp import download_media, send_flow, send_text
from utils.telegram import download_file as tg_download_file
from utils.telegram import get_file as tg_get_file
from utils.telegram import send_message as tg_send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

supervisor = SupervisorAgent()
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database connections and indexes...")
    await init_indexes()
    yield
    logger.info("Shutting down application...")


app = FastAPI(lifespan=lifespan)


def _extract_messages(payload: dict) -> list[dict]:
    messages = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages.extend(value.get("messages", []))
    return messages


def _is_public_url(text: str) -> bool:
    match = URL_PATTERN.search(text or "")
    if not match:
        return False
    host = urlparse(match.group(0)).netloc.lower()
    return bool(host and "." in host)


def _first_url(text: str) -> str:
    match = URL_PATTERN.search(text or "")
    return match.group(0).rstrip(").,") if match else ""


async def _send_dashboard(contact_id: str):
    settings = await get_chat_settings(contact_id)
    body = DASHBOARD_BODY.format(
        location=settings.get("location", "Delhi"),
        department=settings.get("department", "General"),
        language=settings.get("language", "Hindi"),
    )
    await send_text(contact_id, WELCOME_TEXT)
    await send_text(contact_id, body)
    await send_flow(contact_id)


async def _save_and_send(contact_id: str, source_type: str, article: str, sender: dict):
    await save_article(
        {
            "source_type": source_type,
            "generated_article_hindi": article,
            "created_at": datetime.now(),
            "contact_id": contact_id,
            "sender": sender,
        }
    )
    await send_text(contact_id, article)


async def task_compile_audio(contact_id: str, media_id: str, settings: dict, sender: dict):
    try:
        audio_bytes, mime_type = await download_media(media_id)
        article = await supervisor.compile_audio_bytes(audio_bytes, mime_type, settings, media_id)
        await _save_and_send(contact_id, "audio_to_news", article, sender)
    except Exception as exc:
        logger.exception("Audio compilation failed")
        await send_text(contact_id, ERROR_AUDIO.format(error=str(exc)))


async def task_compile_telegram_audio(chat_id: int, file_id: str, mime_type: str, settings: dict, sender: dict):
    try:
        file_info = await tg_get_file(file_id)
        audio_bytes = await tg_download_file(file_info["file_path"])
        article = await supervisor.compile_audio_bytes(audio_bytes, mime_type, settings, file_id)
        await save_article(
            {
                "source_type": "telegram_audio_to_news",
                "generated_article_hindi": article,
                "created_at": datetime.now(),
                "chat_id": chat_id,
                "sender": sender,
            }
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram audio compilation failed")
        await tg_send_message(chat_id, ERROR_AUDIO.format(error=str(exc)))


async def task_compile_image(contact_id: str, media_id: str, settings: dict, sender: dict):
    try:
        image_bytes, mime_type = await download_media(media_id)
        article = await supervisor.compile_image_bytes(image_bytes, mime_type, settings)
        await _save_and_send(contact_id, "ocr_to_news", article, sender)
    except Exception as exc:
        logger.exception("Image/OCR compilation failed")
        await send_text(contact_id, ERROR_IMAGE.format(error=str(exc)))


async def task_compile_telegram_image(chat_id: int, file_id: str, mime_type: str, settings: dict, sender: dict):
    try:
        file_info = await tg_get_file(file_id)
        image_bytes = await tg_download_file(file_info["file_path"])
        article = await supervisor.compile_image_bytes(image_bytes, mime_type, settings)
        await save_article(
            {
                "source_type": "telegram_ocr_to_news",
                "generated_article_hindi": article,
                "created_at": datetime.now(),
                "chat_id": chat_id,
                "sender": sender,
            }
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram image compilation failed")
        await tg_send_message(chat_id, ERROR_IMAGE.format(error=str(exc)))


async def task_compile_social_link(contact_id: str, url: str, settings: dict, sender: dict):
    try:
        article = await supervisor.compile_social_link(url, settings)
        await _save_and_send(contact_id, "social_link_to_news", article, sender)
    except Exception as exc:
        logger.exception("Social link compilation failed")
        await send_text(contact_id, ERROR_SOCIAL.format(error=str(exc)))


async def task_compile_telegram_social_link(chat_id: int, url: str, settings: dict, sender: dict):
    try:
        article = await supervisor.compile_social_link(url, settings)
        await save_article(
            {
                "source_type": "telegram_social_link_to_news",
                "generated_article_hindi": article,
                "created_at": datetime.now(),
                "chat_id": chat_id,
                "sender": sender,
            }
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram social link compilation failed")
        await tg_send_message(chat_id, ERROR_SOCIAL.format(error=str(exc)))


async def task_compile_text(contact_id: str, text: str, settings: dict, sender: dict):
    try:
        article = await supervisor.compile_topic_search(text, settings)
        await _save_and_send(contact_id, "text_to_news", article, sender)
    except Exception as exc:
        logger.exception("Text compilation failed")
        await send_text(contact_id, ERROR_TEXT.format(error=str(exc)))


async def task_compile_telegram_text(chat_id: int, text: str, settings: dict, sender: dict):
    try:
        article = await supervisor.compile_topic_search(text, settings)
        await save_article(
            {
                "source_type": "telegram_text_to_news",
                "generated_article_hindi": article,
                "created_at": datetime.now(),
                "chat_id": chat_id,
                "sender": sender,
            }
        )
        await tg_send_message(chat_id, article)
    except Exception as exc:
        logger.exception("Telegram text compilation failed")
        await tg_send_message(chat_id, ERROR_TEXT.format(error=str(exc)))


async def _send_telegram_dashboard(chat_id: int):
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
        ]
    }
    await tg_send_message(chat_id, f"{WELCOME_TEXT}\n\n{body}", reply_markup=markup)


@app.get("/api/webhook")
async def verify_whatsapp_webhook(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == Config.WHATSAPP_VERIFY_TOKEN
    ):
        return PlainTextResponse(params.get("hub.challenge", ""))
    return JSONResponse(status_code=403, content={"ok": False})


@app.post("/api/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        messages = _extract_messages(payload)
        for message in messages:
            contact_id = message.get("from")
            if not contact_id or not Config.is_contact_allowed(contact_id):
                continue

            settings = await get_chat_settings(contact_id)
            sender = {"contact_id": contact_id, "whatsapp_message_id": message.get("id")}
            message_type = message.get("type")

            if message_type == "interactive":
                interactive = message.get("interactive", {})
                selected = (
                    interactive.get("list_reply", {}).get("id")
                    or interactive.get("button_reply", {}).get("id")
                    or interactive.get("nfm_reply", {}).get("response_json")
                )
                await send_text(contact_id, f"Selected: {selected}\n\n{SETTINGS_HELP}")
                continue

            if message_type == "audio":
                media_id = message["audio"]["id"]
                await send_text(contact_id, AUDIO_RECEIVED)
                background_tasks.add_task(task_compile_audio, contact_id, media_id, settings, sender)
                continue

            if message_type == "image":
                media_id = message["image"]["id"]
                await send_text(contact_id, IMAGE_RECEIVED)
                background_tasks.add_task(task_compile_image, contact_id, media_id, settings, sender)
                continue

            if message_type == "document" and message.get("document", {}).get("mime_type", "").startswith("image/"):
                media_id = message["document"]["id"]
                await send_text(contact_id, IMAGE_RECEIVED)
                background_tasks.add_task(task_compile_image, contact_id, media_id, settings, sender)
                continue

            text = message.get("text", {}).get("body", "").strip() if message_type == "text" else ""
            if not text:
                continue

            if text.lower() in {"/start", "start", "menu", "/menu"}:
                await _send_dashboard(contact_id)
            elif text.startswith("/location"):
                value = text[len("/location"):].strip()
                if value:
                    await update_chat_settings(contact_id, {"location": value})
                    await send_text(contact_id, f"Location updated to {value}.")
            elif text.startswith("/dept"):
                value = text[len("/dept"):].strip()
                if value:
                    await update_chat_settings(contact_id, {"department": value})
                    await send_text(contact_id, f"Department updated to {value}.")
            elif text.startswith("/lang"):
                value = text[len("/lang"):].strip()
                if value:
                    await update_chat_settings(contact_id, {"language": value})
                    await send_text(contact_id, f"Language updated to {value}.")
            elif _is_public_url(text):
                url = _first_url(text)
                await send_text(contact_id, SOCIAL_LINK_RECEIVED)
                background_tasks.add_task(task_compile_social_link, contact_id, url, settings, sender)
            else:
                await send_text(contact_id, TEXT_RECEIVED)
                background_tasks.add_task(task_compile_text, contact_id, text, settings, sender)

        return {"ok": True}
    except Exception as exc:
        logger.exception("Webhook processing error: %s", exc)
        return JSONResponse(status_code=200, content={"ok": True})


@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()

        if "callback_query" in body:
            callback = body["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            if Config.is_chat_allowed(chat_id):
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

        text = message.get("text", "").strip()
        if not text:
            return {"ok": True}

        if text.lower() in {"/start", "start", "menu", "/menu"}:
            await _send_telegram_dashboard(chat_id)
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
            value = text[len("/lang"):].strip()
            if value:
                await update_chat_settings(chat_id, {"language": value})
                await tg_send_message(chat_id, f"Language updated to {value}.")
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

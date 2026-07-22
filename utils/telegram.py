import logging
import httpx
from config import Config

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"
FILE_DOWNLOAD_URL = f"https://api.telegram.org/file/bot{Config.TELEGRAM_BOT_TOKEN}"

async def _telegram_post(url: str, payload: dict, timeout: float = 15.0) -> dict:
    """Sends a POST to the Telegram API, falling back to plain text on parse errors."""
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=timeout)
        res_json = response.json()
        if not res_json.get("ok"):
            error_msg = res_json.get("description", "Unknown error")
            if "can't parse entities" in error_msg.lower() or "bad request" in error_msg.lower():
                payload.pop("parse_mode", None)
                fallback_response = await client.post(url, json=payload, timeout=timeout)
                return fallback_response.json()
            logger.error(f"Telegram Error: {res_json}")
        return res_json


async def send_message(chat_id: int, text: str, reply_markup: dict = None, reply_to_message_id: int = None, parse_mode: str = "Markdown") -> dict:
    """
    Sends a message to the specified Telegram chat.
    If the formatting parser fails, falls back to plain text to ensure delivery.
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        return await _telegram_post(url, payload, timeout=15.0)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise e


async def edit_message_text(chat_id: int, message_id: int, text: str, reply_markup: dict = None, parse_mode: str = "Markdown") -> dict:
    """
    Edits an existing Telegram message's text and inline keyboard markup.
    """
    url = f"{TELEGRAM_API_URL}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        return await _telegram_post(url, payload, timeout=15.0)
    except Exception as e:
        logger.error(f"Failed to edit message {message_id}: {e}")
        raise e


async def answer_callback_query(callback_query_id: str, text: str = None, show_alert: bool = False) -> dict:
    """
    Acknowledges a callback query from inline buttons.
    """
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id
    }
    if text:
        payload["text"] = text
        payload["show_alert"] = show_alert

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}")
            return {"ok": False, "description": str(e)}


async def get_file(file_id: str) -> dict:
    """
    Retrieves file information (specifically file_path) from Telegram.
    """
    url = f"{TELEGRAM_API_URL}/getFile"
    payload = {"file_id": file_id}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10.0)
        res_json = response.json()
        if not res_json.get("ok"):
            raise Exception(f"Failed to get file: {res_json.get('description', 'Unknown error')}")
        return res_json["result"]


async def download_file(file_path: str) -> bytes:
    """
    Downloads the raw bytes of a file from Telegram.
    """
    url = f"{FILE_DOWNLOAD_URL}/{file_path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        if response.status_code != 200:
            raise Exception(f"Failed to download file from {url}: HTTP {response.status_code}")
        return response.content

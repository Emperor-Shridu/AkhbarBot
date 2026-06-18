import logging
import httpx
from config import Config

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = f"https://graph.facebook.com/{Config.WHATSAPP_API_VERSION}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {Config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


async def send_text(to: str, text: str) -> dict:
    url = f"{GRAPH_BASE_URL}/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text[:4096]},
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=_headers(), json=payload, timeout=20.0)
        data = response.json()
        if response.status_code >= 400:
            logger.error("WhatsApp send_text failed: %s", data)
        return data


async def send_menu(to: str) -> dict:
    url = f"{GRAPH_BASE_URL}/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Select a news creation path."},
            "action": {
                "button": "Choose path",
                "sections": [
                    {
                        "title": "News inputs",
                        "rows": [
                            {"id": "audio_to_news", "title": "Audio to news"},
                            {"id": "social_link_to_news", "title": "Social link to news"},
                            {"id": "ocr_to_news", "title": "OCR to news"},
                            {"id": "text_to_news", "title": "Text to news"},
                        ],
                    }
                ],
            },
        },
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=_headers(), json=payload, timeout=20.0)
        return response.json()


async def send_flow(to: str) -> dict:
    if not Config.WHATSAPP_FLOW_ID:
        return await send_menu(to)

    url = f"{GRAPH_BASE_URL}/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "body": {"text": "Open the AkhbarBot intake flow."},
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_id": Config.WHATSAPP_FLOW_ID,
                    "flow_cta": "Start",
                    "flow_action": "navigate",
                    "flow_action_payload": {"screen": "NEWS_INTAKE"},
                },
            },
        },
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=_headers(), json=payload, timeout=20.0)
        data = response.json()
        if response.status_code >= 400:
            logger.error("WhatsApp send_flow failed: %s", data)
        return data


async def get_media_url(media_id: str) -> str:
    url = f"{GRAPH_BASE_URL}/{media_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_headers(), timeout=20.0)
        data = response.json()
        if response.status_code >= 400 or "url" not in data:
            raise RuntimeError(f"Unable to get WhatsApp media URL: {data}")
        return data["url"]


async def download_media(media_id: str) -> tuple[bytes, str]:
    media_url = await get_media_url(media_id)
    async with httpx.AsyncClient() as client:
        response = await client.get(media_url, headers=_headers(), timeout=60.0)
        if response.status_code >= 400:
            raise RuntimeError(f"Unable to download WhatsApp media: HTTP {response.status_code}")
        return response.content, response.headers.get("content-type", "application/octet-stream")

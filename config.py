import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/akhbarbot")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ALLOWED_CONTACTS = os.getenv("ALLOWED_CONTACTS")
    ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID")
    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
    WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0")
    WHATSAPP_FLOW_ID = os.getenv("WHATSAPP_FLOW_ID")

    @classmethod
    def is_contact_allowed(cls, contact_id: str) -> bool:
        if not cls.ALLOWED_CONTACTS:
            return True
        allowed_ids = [x.strip() for x in cls.ALLOWED_CONTACTS.replace(";", ",").split(",") if x.strip()]
        return str(contact_id) in allowed_ids

    @classmethod
    def is_chat_allowed(cls, chat_id: int) -> bool:
        if not cls.ALLOWED_CHAT_ID:
            return True
        allowed_ids = [x.strip() for x in cls.ALLOWED_CHAT_ID.replace(";", ",").split(",") if x.strip()]
        return str(chat_id) in allowed_ids

    @classmethod
    def validate(cls):
        missing = []
        has_whatsapp = cls.WHATSAPP_ACCESS_TOKEN and cls.WHATSAPP_PHONE_NUMBER_ID and cls.WHATSAPP_VERIFY_TOKEN
        has_telegram = cls.TELEGRAM_BOT_TOKEN
        if not has_whatsapp and not has_telegram:
            missing.append("WHATSAPP_* or TELEGRAM_BOT_TOKEN")
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

Config.validate()


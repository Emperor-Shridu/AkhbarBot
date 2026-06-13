import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/akhbarbot")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID")

    @classmethod
    def is_chat_allowed(cls, chat_id: int) -> bool:
        if not cls.ALLOWED_CHAT_ID:
            return True
        # Support both comma and semicolon separation
        allowed_ids = [x.strip() for x in cls.ALLOWED_CHAT_ID.replace(";", ",").split(",") if x.strip()]
        return str(chat_id) in allowed_ids

    @classmethod
    def validate(cls):
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

Config.validate()


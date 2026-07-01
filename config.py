import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/akhbarbot")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID")
    STREAMLIT_USER_IDS = os.getenv("STREAMLIT_USER_IDS", "demo")
    API_SHARED_SECRET = os.getenv("API_SHARED_SECRET")
    BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "https://akhbar-bot.onrender.com")

    @classmethod
    def is_chat_allowed(cls, chat_id: int) -> bool:
        if not cls.ALLOWED_CHAT_ID:
            return True
        allowed_ids = [x.strip() for x in cls.ALLOWED_CHAT_ID.replace(";", ",").split(",") if x.strip()]
        return str(chat_id) in allowed_ids

    @classmethod
    def is_streamlit_user_allowed(cls, user_id: str) -> bool:
        """Returns whether a Streamlit user id can access protected article APIs."""
        allowed_ids = [x.strip() for x in cls.STREAMLIT_USER_IDS.replace(";", ",").split(",") if x.strip()]
        return str(user_id).strip() in allowed_ids

    @classmethod
    def validate(cls):
        missing = []
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


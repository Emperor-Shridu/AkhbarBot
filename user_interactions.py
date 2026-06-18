WELCOME_TEXT = (
    "AkhbarBot is ready on WhatsApp.\n\n"
    "Choose one of four news creation paths:\n"
    "1. Audio to news\n"
    "2. Social video/audio link to news\n"
    "3. Document/photo OCR to news\n"
    "4. Text to news article"
)

DASHBOARD_BODY = (
    "Current settings:\n"
    "Location: {location}\n"
    "Department: {department}\n"
    "Language: {language}\n\n"
    "Send audio, image/document, a social media URL, or text."
)

AUDIO_RECEIVED = "Audio received. I am extracting facts and preparing the news article."
IMAGE_RECEIVED = "Document/photo received. I am running OCR and preparing the news article."
SOCIAL_LINK_RECEIVED = "Social media link received. I am extracting audio with yt-dlp and verifying facts."
TEXT_RECEIVED = "Text received. I am verifying the facts and preparing the news article."

SETTINGS_HELP = (
    "To update preferences, send:\n"
    "/location <place>\n"
    "/dept <department>\n"
    "/lang <language>"
)

ERROR_AUDIO = "Audio analysis failed: {error}"
ERROR_IMAGE = "Document/photo analysis failed: {error}"
ERROR_SOCIAL = "Social link analysis failed: {error}"
ERROR_TEXT = "Text analysis failed: {error}"

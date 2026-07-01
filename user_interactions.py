WELCOME_TEXT = (
    "AkhbarBot is ready.\n\n"
    "Choose a news creation path:\n"
    "1. Audio to news\n"
    "2. Social video/audio link to news\n"
    "3. Document/photo OCR to news\n"
    "4. Text to news article\n"
    "5. Latest topic article\n"
    "6. Professionalize an article"
)

DASHBOARD_BODY = (
    "Current settings:\n"
    "Location: {location}\n"
    "Department: {department}\n"
    "Language: {language}\n\n"
    "Send audio, image/document, a social media URL, or text."
)

MODE_PROMPT_TEXT = (
    "Text mode active.\n"
    "Send any topic, brief, or pasted facts and I will prepare the news article."
)

MODE_PROMPT_TOPIC = (
    "Latest topic mode active.\n"
    "Send the topic you want the latest verified updates for."
)
MODE_PROMPT_TOPIC_SELECTION = (
    "Select a story by replying with its number (e.g., send '1', '2', etc.)."
)

MODE_PROMPT_LINK = (
    "Social link mode active.\n"
    "Send a public media URL (YouTube, Instagram, etc.) and I will prepare the news article."
)

MODE_PROMPT_IMAGE = (
    "OCR mode active.\n"
    "Send a photo or scanned document and I will extract the text and prepare the article."
)

MODE_PROMPT_AUDIO = (
    "Audio mode active.\n"
    "Send a voice message or audio file and I will prepare the news article."
)

MODE_PROMPT_PROFESSIONALIZE = (
    "Professionalize mode active.\n"
    "Paste a draft article and I will rewrite it into publish-ready Hindi newsroom copy."
)

MODE_CLEARED = (
    "Mode cleared.\n"
    "Send /start to see the menu again, or just send content and I will pick the right path."
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

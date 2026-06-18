# AkhbarBot v3 (Dual WhatsApp + Telegram Backend)

An asynchronous FastAPI news assistant that runs the same news-generation backend for both WhatsApp Business API and Telegram. WhatsApp support was added because Telegram access can be banned or restricted for Indian users, while the already functional Telegram bot remains supported on a separate webhook.

## Four News Creation Paths

1. **Audio to news**: User sends WhatsApp or Telegram audio/voice. The app downloads media from the channel API, chunks audio when useful, transcribes facts with Gemini, and writes a Hindi news article.
2. **Social video/audio link to news**: User sends a Facebook, Instagram, YouTube, or other public media URL. The app extracts audio with `yt-dlp`, verifies context with Gemini Search Grounding, and writes the article.
3. **Document/photo OCR to news**: User sends an image/photo/document. Gemini Vision extracts text/entities and the editor turns verified material into a news article.
4. **Text to news article**: User sends a topic, rough brief, or pasted text. Gemini Search Grounding verifies facts before final writing.

There are intentionally no extra modes such as trend feeds or multi-button compile queues.

## Project Structure

```text
E:/autoPapaPython/
|-- agents/
|   |-- audio.py        # Audio transcription and factual extraction
|   |-- ocr.py          # OCR and image/document extraction
|   |-- trend.py        # Search-grounded verification for text and links
|   |-- editor.py       # Final news article synthesis
|   `-- supervisor.py   # Four-path orchestration
|-- utils/
|   |-- whatsapp.py     # WhatsApp Cloud API media and message helpers
|   |-- social_audio.py # yt-dlp audio extraction from public media URLs
|   |-- ogg_splitter.py # Pure-python Ogg page segmenter
|   `-- telegram.py     # Telegram media and message helpers
|-- prompts.py          # All LLM prompts/gems in one editable file
|-- user_interactions.py # All user-facing channel text in one editable file
|-- config.py           # Environment parsing and validation
|-- database.py         # MongoDB connection, settings, and article storage
|-- main.py             # FastAPI WhatsApp and Telegram webhook entrypoints
|-- IMPLEMENTATION.md   # Technical decisions and prompt locations
|-- VERSIONS.md         # Short interview problem/solution log
`-- requirements.txt
```

## Environment

Create `.env` with:

```env
WHATSAPP_ACCESS_TOKEN=your_meta_cloud_api_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_API_VERSION=v20.0
WHATSAPP_FLOW_ID=optional_published_flow_id
ALLOWED_CONTACTS=optional_comma_separated_whatsapp_numbers
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_CHAT_ID=optional_comma_separated_telegram_chat_ids
MONGO_URI=your_mongodb_uri
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Run locally:

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Register Meta WhatsApp at `/api/webhook`. Register Telegram at `/api/telegram-webhook`. Both channels use the same agents, prompts, user text files, MongoDB article storage, and four-path methodology.

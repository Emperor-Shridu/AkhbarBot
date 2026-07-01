# AkhbarBot

AkhbarBot is a Hindi news article generator with a Telegram bot backend and a Streamlit web frontend. The old WhatsApp Business API layer has been removed. Telegram and Streamlit now share one modular article-generation service, so every input path produces the same publish-ready newsroom output.

## News Creation Paths

1. Audio upload or Telegram voice/audio to news.
2. Image or scanned document OCR to news.
3. Public social media URL to news through `yt-dlp` audio extraction plus search-grounded verification.
4. Text, topic, or pasted facts to news.
5. Latest topic research to a newly worded article.
6. Professional rewrite of an existing article draft.

All final output is Hindi only and formatted as a publish-ready article with a headline and body. The editor prompt explicitly avoids mentioning the source format, recording, OCR, bot, or internal workflow.

## Recommended Free Deployment

Use two free-friendly surfaces:

- **Render Free Web Service** for FastAPI and the Telegram webhook.
- **Streamlit Community Cloud** for the website frontend.

This split is intentional. Telegram needs a public webhook URL, while Streamlit needs its own interactive app server. Render web services expose one public HTTP port, and free services spin down after idle time. Keeping Streamlit on Streamlit Cloud avoids fighting that port model and leaves the Render service focused on backend work.

## Project Structure

```text
E:/autoPapaPython/
|-- agents/
|   |-- audio.py
|   |-- ocr.py
|   |-- trend.py
|   |-- editor.py
|   `-- supervisor.py
|-- services/
|   `-- news_service.py      # Shared article service for Telegram and Streamlit
|-- utils/
|   |-- social_audio.py
|   |-- ogg_splitter.py
|   `-- telegram.py
|-- docs/
|   |-- DEPLOYMENT.md
|   `-- interview_portfolio_log.md
|-- main.py                  # FastAPI backend and Telegram webhook
|-- streamlit_app.py          # Streamlit frontend
|-- prompts.py
|-- user_interactions.py
|-- config.py
|-- database.py
|-- render.yaml
|-- .env.example
`-- requirements.txt
```

## Environment

Create `.env` locally from `.env.example`:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash-lite
MONGO_URI=your_mongodb_uri
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_CHAT_ID=optional_comma_separated_telegram_chat_ids
STREAMLIT_USER_IDS=demo,father
API_SHARED_SECRET=choose_a_long_random_secret
BACKEND_BASE_URL=http://localhost:8000
```

`demo` is included for interview showcase access. Replace or supplement it with your father's user id for real use.

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
python -m uvicorn main:app --reload
```

Start the website:

```bash
streamlit run streamlit_app.py
```

Register Telegram webhook after the Render backend is live:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<your-render-service>.onrender.com/api/telegram-webhook"
```

The Streamlit app includes a WhatsApp share button. It opens a prefilled WhatsApp message so the final article can be sent to the office group from the user's device.


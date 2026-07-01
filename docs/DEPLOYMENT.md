# Deployment Guide

## Recommended Free Setup

Use Render for the FastAPI backend and Streamlit Community Cloud for the frontend.

Render's free web services are useful for hobby or demo deployments, but they have limits: they spin down after 15 minutes without inbound traffic, start back up on the next request, and use an ephemeral filesystem. Render also documents 750 free instance hours per workspace per month. Background workers are not part of the free service types, so this repo keeps Telegram work inside the FastAPI web service.

## Backend on Render

1. Push the repo to GitHub.
2. In Render, create a new Blueprint or Web Service from the repo.
3. Use `render.yaml` or set these manually:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
4. Add environment variables:
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL`
   - `MONGO_URI`
   - `TELEGRAM_BOT_TOKEN`
   - `ALLOWED_CHAT_ID`
   - `STREAMLIT_USER_IDS`
   - `API_SHARED_SECRET`
5. Deploy and confirm `https://<service>.onrender.com/health` returns `{"ok": true}`.

## Telegram Webhook

After the backend URL is live, register the Telegram webhook:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<service>.onrender.com/api/telegram-webhook"
```

Check the current webhook:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

## Streamlit Community Cloud

1. Create a new Streamlit app from the same GitHub repo.
2. Set main file path to `streamlit_app.py`.
3. Add secrets:

```toml
BACKEND_BASE_URL = "https://<service>.onrender.com"
STREAMLIT_USER_IDS = "demo,father"
API_SHARED_SECRET = "same-secret-as-render"
```

The frontend does not need `GEMINI_API_KEY` because it calls the FastAPI backend.

## Local Development

Run the backend:

```bash
python -m uvicorn main:app --reload
```

Run the frontend:

```bash
streamlit run streamlit_app.py
```

Use `demo` as the user id unless you changed `STREAMLIT_USER_IDS`.

## Long Audio Notes

Render free is a better fit than Vercel serverless for long audio because the FastAPI process can keep running as a web service. Very long audio can still be slow, and free services may restart or spin down. For production reliability, move the backend to a paid Render instance or add a real queue and worker on paid infrastructure.

## WhatsApp Share Button

The Streamlit app uses `https://wa.me/?text=<article>` to open WhatsApp with the article prefilled. WhatsApp does not provide a reliable public web link that directly targets a specific group for arbitrary apps, so the sender chooses the office group inside WhatsApp before sending.


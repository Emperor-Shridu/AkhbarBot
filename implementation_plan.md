# Implementation Plan: Shared Backend for WhatsApp Business API + Telegram

## Scope

Use one backend for WhatsApp and Telegram. WhatsApp is required for India reach and uses Business API/Flows. Telegram remains available through the same backend. Keep only four creation paths:

1. Audio to news.
2. Social media video/audio link to news using `yt-dlp` audio extraction.
3. Document/photo OCR to news article.
4. Text to news article.

## Required Credentials

1. `WHATSAPP_ACCESS_TOKEN`
2. `WHATSAPP_PHONE_NUMBER_ID`
3. `WHATSAPP_VERIFY_TOKEN`
4. Optional `WHATSAPP_FLOW_ID`
5. `TELEGRAM_BOT_TOKEN`
6. Optional `ALLOWED_CONTACTS`
7. Optional `ALLOWED_CHAT_ID`
8. `MONGO_URI`
9. `GEMINI_API_KEY`

## Build Steps

1. Configure `.env` with WhatsApp, Telegram, MongoDB, and Gemini values.
2. Deploy FastAPI to Vercel or another HTTPS host.
3. In Meta Developer Console, set the webhook callback URL to `https://<host>/api/webhook`.
4. Subscribe the app to WhatsApp message events.
5. Publish a WhatsApp Flow for the four intake paths, or let the app use its list fallback.
6. Register Telegram webhook to `https://<host>/api/telegram-webhook`.
7. Test all four paths from a WhatsApp test number and Telegram chat.

## Verification

- `GET /api/webhook` returns the Meta challenge when the verify token matches.
- `/start` or `menu` sends the WhatsApp Flow/list on WhatsApp and an inline menu on Telegram.
- Audio messages return a generated news article.
- Social links trigger `yt-dlp` extraction and search-grounded verification.
- Image/photo messages trigger OCR and article synthesis.
- Plain text triggers fact-checked article synthesis.

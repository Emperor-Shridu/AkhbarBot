# AkhbarBot v3: Dual-Channel Implementation Guide

## Core Methodology

The product is constrained to four user paths only:

1. Audio to news.
2. Facebook/other social media video or audio link to news through `yt-dlp` audio extraction.
3. Document/photo OCR to news article.
4. Text to news article.

The old pending voice-note compile queue and top-local-trends mode are no longer part of the primary methodology. WhatsApp Business API and Telegram are both channel layers; WhatsApp Flow/list UI and Telegram inline buttons are intake helpers; Gemini agents remain the shared content intelligence layer.

## Architecture Decisions

### Same backend for WhatsApp and Telegram

WhatsApp support was added for the Indian deployment context because Telegram access can be banned or restricted, but the existing functional Telegram bot remains useful where available. The app exposes Meta webhook verification through `GET /api/webhook`, receives WhatsApp message events through `POST /api/webhook`, and receives Telegram updates through `POST /api/telegram-webhook`. Both channels route into the same `SupervisorAgent`.

### WhatsApp Flows and list fallback

`utils/whatsapp.py` sends a WhatsApp Flow when `WHATSAPP_FLOW_ID` is configured. If no Flow is configured, it sends a WhatsApp interactive list with the same four paths. This keeps local development and production setup practical while preserving the WhatsApp-native intake design.

### Telegram support without extra methodology

Telegram support uses the same four paths as WhatsApp. Audio/photo/text/link messages are processed immediately; no separate pending queue or trends mode is reintroduced.

### Prompt and text separation

All LLM prompts/gems are centralized in `prompts.py`. All user-facing interaction text is centralized in `user_interactions.py`. This makes editorial tuning and WhatsApp copy changes possible without hunting through webhook logic.

### Social link extraction

`utils/social_audio.py` uses `yt-dlp` to download the best available public audio for social-media URLs. The extracted audio is passed through the same audio factual extraction agent, then combined with search-grounded URL verification before final article writing.

### Serverless-friendly agent core

The existing custom async engine remains. It avoids heavy orchestration frameworks, uses Gemini directly, keeps MongoDB async through Motor, and preserves pure-python Ogg splitting for WhatsApp voice/audio files.

## Prompt/Gem Locations

- `prompts.py::AUDIO_ANALYSIS_PROMPT`
- `prompts.py::OCR_ANALYSIS_PROMPT`
- `prompts.py::SOCIAL_LINK_RESEARCH_PROMPT`
- `prompts.py::TEXT_RESEARCH_PROMPT`
- `prompts.py::EDITOR_SYSTEM_PROMPT`

## User Interaction Text Locations

- `user_interactions.py::WELCOME_TEXT`
- `user_interactions.py::DASHBOARD_BODY`
- `user_interactions.py::AUDIO_RECEIVED`
- `user_interactions.py::IMAGE_RECEIVED`
- `user_interactions.py::SOCIAL_LINK_RECEIVED`
- `user_interactions.py::TEXT_RECEIVED`
- `user_interactions.py::SETTINGS_HELP`
- `user_interactions.py::ERROR_*`

## Runtime Flow

1. Meta calls `GET /api/webhook` with `hub.challenge`; the app validates `WHATSAPP_VERIFY_TOKEN`.
2. Meta posts WhatsApp messages to `POST /api/webhook`; Telegram posts updates to `POST /api/telegram-webhook`.
3. `main.py` routes channel messages by type:
   - `audio` -> audio-to-news background task.
   - `image` or image document -> OCR-to-news background task.
   - public URL text -> social-link-to-news background task.
   - any other text -> text-to-news background task.
4. `SupervisorAgent` calls the specific extraction/research agent and then `EditorAgent`.
5. The article is saved to MongoDB and sent back through the originating channel.

## Operational Notes

- The WhatsApp Cloud API requires a Meta app, configured phone number, permanent or system-user access token, webhook callback URL, and matching verify token.
- Telegram requires `TELEGRAM_BOT_TOKEN` and a webhook pointing to `/api/telegram-webhook`.
- `yt-dlp` can fail when a platform blocks unauthenticated downloads, private links, age gates, or region-restricted media. In that case the user should send the audio directly to WhatsApp.
- For Meta WhatsApp Flows, publish a Flow with one intake screen named `NEWS_INTAKE` or update `utils/whatsapp.py` to match the published screen name.

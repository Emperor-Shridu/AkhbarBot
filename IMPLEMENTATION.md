# AkhbarBot Implementation Notes

## Current Architecture

AkhbarBot now has three clear layers:

1. **Channel adapters:** Telegram webhook in `main.py` and Streamlit frontend in `streamlit_app.py`.
2. **Service layer:** `services/news_service.py` exposes the article-generation methods used by every channel.
3. **Agent layer:** `agents/` performs audio analysis, OCR, search-grounded research, and final editorial synthesis.

WhatsApp-specific endpoints, configuration, and helper utilities were removed. There is no `/api/webhook` Meta endpoint and no `WHATSAPP_*` environment requirement.

## Why FastAPI Backend Plus Streamlit Frontend

FastAPI remains the backend because Telegram needs a reliable webhook endpoint and upload APIs. Streamlit is best kept as a separate frontend because it provides the fastest usable web interface for your father and for interview demonstrations.

For free hosting, the recommended split is:

- Render Free Web Service: `main.py` with `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- Streamlit Community Cloud: `streamlit_app.py`, configured with `BACKEND_BASE_URL`, `STREAMLIT_USER_IDS`, and `API_SHARED_SECRET`.

This avoids Vercel's serverless timeout pattern for long audio work. A 10-minute audio file can still be slow because Gemini processing and social extraction take time, but it is no longer bound to Vercel-style short serverless execution.

## Article Modes

### Audio to News

Telegram or Streamlit sends raw audio bytes. `NewsService.from_audio()` calls `SupervisorAgent.compile_audio_bytes()`, which chunks Ogg/Opus audio where possible, extracts facts through Gemini, and synthesizes a Hindi article.

### Image/OCR to News

Uploaded image bytes go to `NewsService.from_image()`, then `OCRAgent`, then the editor. The final output avoids saying that the source was an image or scan.

### Social Link to News

`NewsService.from_social_link()` uses `yt-dlp` via `utils/social_audio.py` to extract public audio from supported URLs. `TrendAgent` performs search-grounded context verification before the editor writes the final article.

### Text to News

`NewsService.from_text()` treats pasted facts or a topic brief as a fact-checking task. Search grounding verifies dates, names, entities, and claims before final writing.

### Latest Topic

`NewsService.from_latest_topic()` uses the new latest-topic prompt to find recent, credible developments about a topic and write a newly worded Hindi article.

### Professionalize Article

`NewsService.professionalize()` rewrites a submitted Hindi draft into polished newsroom copy without inventing facts.

## API Endpoints

- `GET /health`
- `POST /api/telegram-webhook`
- `POST /api/articles/text`
- `POST /api/articles/latest-topic`
- `POST /api/articles/professionalize`
- `POST /api/articles/social-link`
- `POST /api/articles/audio`
- `POST /api/articles/image`
- `GET /api/articles/history`

All Streamlit article endpoints require `X-User-Id`. If `API_SHARED_SECRET` is set, they also require `X-Api-Secret`.

## Prompt Locations

- `prompts.py::AUDIO_ANALYSIS_PROMPT`
- `prompts.py::OCR_ANALYSIS_PROMPT`
- `prompts.py::SOCIAL_LINK_RESEARCH_PROMPT`
- `prompts.py::TEXT_RESEARCH_PROMPT`
- `prompts.py::LATEST_TOPIC_RESEARCH_PROMPT`
- `prompts.py::EDITOR_SYSTEM_PROMPT`
- `prompts.py::PROFESSIONALIZE_ARTICLE_PROMPT`

## Storage

MongoDB remains the persistent store. Generated articles are saved with `source_type`, `generated_article_hindi`, `created_at`, and actor metadata. Streamlit history reads from the same `articles` collection.

On Render Free, local filesystem changes are ephemeral, so MongoDB Atlas or another external MongoDB service is preferred for history. Do not rely on local files for durable article history.


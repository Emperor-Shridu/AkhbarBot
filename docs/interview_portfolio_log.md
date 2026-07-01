# Interview Portfolio Log

## Entry #2 | 2026-06-24 | Focus: WhatsApp Removal and Streamlit + Telegram Modularization

### 1. Situation & Engineering Challenge (S-T)

**Context:** The project needed to drop WhatsApp Business API functionality while keeping Telegram delivery and adding a Streamlit website for Hindi article generation. The app also needed long-audio friendliness after Vercel-style serverless timeout issues, plus professional publish-ready output that does not mention source formats such as audio recordings or OCR.

**The Bottleneck:** The previous `main.py` mixed WhatsApp webhook verification, WhatsApp media handling, Telegram routing, article saving, and channel-specific user copy. This made the app harder to deploy on free hosting and harder to extend with Streamlit without duplicating business logic.

**Impact:** Channel adapters needed to become thin entrypoints while article generation moved behind a reusable service layer. The deployment model also needed to account for Render Free limitations: idle spin-down, one public web port per service, ephemeral local files, and no free background worker service type.

### 2. Architectural Trade-offs & Choices (The "Why")

**Option A (Implemented):** Remove WhatsApp endpoints and helpers, keep FastAPI for Telegram/web APIs, add `services/news_service.py`, and add `streamlit_app.py` as a separate frontend that calls protected backend endpoints.

**Pros:** Removes dead channel complexity, keeps Telegram webhook support, lets Streamlit and Telegram share one tested article pipeline, supports MongoDB-backed history, and avoids binding the whole product to Vercel serverless request limits.

**Cons:** Free hosting now uses two surfaces, Render for backend and Streamlit Cloud for frontend, and long audio can still be slow without a paid queue or worker.

**Option B (Rejected):** Run Telegram, Streamlit, and long-running article work inside one hosted process.

**Why Rejected:** Render web services publicly expose one HTTP port, Streamlit expects its own app server, and combining both would make deployment brittle. A single-process design would also blur channel/UI concerns with backend workflow concerns.

### 3. Action Taken & Technical Implementation (A)

**Execution Layer (`execution/`):** No `execution/` folder exists in this repo. The deterministic shared workflow was implemented in `services/news_service.py`, which exposes audio, image, social link, text, latest topic, and professional rewrite methods with docstrings and consistent MongoDB persistence.

**Directive Layer (`directives/`):** No `directives/` folder exists. Durable operating guidance was updated in `README.md`, `IMPLEMENTATION.md`, and `docs/DEPLOYMENT.md`.

**State & Security:** Removed `WHATSAPP_*` config and `utils/whatsapp.py`; deleted `vercel.json`; added `render.yaml`, `.env.example`, `STREAMLIT_USER_IDS`, `API_SHARED_SECRET`, and `BACKEND_BASE_URL`. Streamlit article APIs require an allowed user id, with `demo` available for interview showcasing. MongoDB remains the durable history store because Render Free local files are ephemeral.

### 4. Result & Resume Bullet Point (R)

**System Impact:** Converted a dual-channel webhook backend into a modular Telegram + Streamlit product with six article workflows, protected frontend APIs, shared service orchestration, and clearer free-hosting deployment docs.

**Resume Formatting (Action + Context + Quantifiable Result):**
> "Refactored a Hindi news-generation bot from a mixed WhatsApp/Telegram webhook service into a modular Telegram + Streamlit architecture, expanding from 4 to 6 article workflows while isolating channel adapters behind one reusable service layer and documenting a free Render deployment path."

## Entry #1 | 2026-06-18 | Focus: Dual WhatsApp + Telegram News Backend

### 1. Situation & Engineering Challenge (S-T)

**Context:** The project was a Telegram-first FastAPI news bot. The deployment requirement changed because Telegram can be banned or restricted for Indian users, but Telegram support still needed to remain available because the previous multi-user bot was already functional.

**The Bottleneck:** The old methodology coupled channel behavior, prompts, user-facing text, and extra modes such as local trends. This made it hard to support WhatsApp Business API and Telegram from the same backend without feature drift.

**Impact:** Layer 2 orchestration needed a cleaner channel boundary. Channel webhooks had to become thin intake adapters, while the Gemini agent layer stayed shared and deterministic.

### 2. Architectural Trade-offs & Choices (The "Why")

**Option A (Implemented):** Keep one FastAPI backend with separate webhooks: `/api/webhook` for WhatsApp and `/api/telegram-webhook` for Telegram. Both route into the same four-path `SupervisorAgent`.

**Pros:** Removes duplicated agent logic, preserves Telegram users, adds India-ready WhatsApp delivery, and keeps prompts/user copy centralized for fast tuning.

**Cons:** Requires maintaining two channel API adapters and separate webhook registration steps.

**Option B (Rejected):** Fork into separate WhatsApp and Telegram services.

**Why Rejected:** Separate services would duplicate prompt logic, increase deployment overhead, and make behavior drift likely across channels.

### 3. Action Taken & Technical Implementation (A)

**Execution Layer (`execution/`):** No `execution/` folder exists in this repo. The reusable logic was added in `utils/whatsapp.py` for Meta media/messages and `utils/social_audio.py` for `yt-dlp` extraction.

**Directive Layer (`directives/`):** No `directives/` folder exists. Methodology was documented in `README.md`, `IMPLEMENTATION.md`, `implementation_plan.md`, and `VERSIONS.md`.

**State & Security:** Updated `config.py` to support `WHATSAPP_*`, `TELEGRAM_BOT_TOKEN`, `ALLOWED_CONTACTS`, and `ALLOWED_CHAT_ID`. Prompt templates moved to `prompts.py`; user-facing channel text moved to `user_interactions.py`.

### 4. Result & Resume Bullet Point (R)

**System Impact:** Reduced the product to four clear paths across two chat platforms while sharing one agent core. This removes the old top-trends and pending-queue complexity from the primary flow.

**Resume Formatting (Action + Context + Quantifiable Result):**
> "Added WhatsApp Business API support to a functional Telegram Hindi news bot for India-restricted Telegram access, consolidating four intake workflows into one shared agent core while limiting channel-specific business logic to two webhook adapters."

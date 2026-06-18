# Interview Portfolio Log

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

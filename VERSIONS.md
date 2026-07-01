# AkhbarBot v3: Engineering Challenges & Interview Reference Sheet

Short interview-ready notes for the dual WhatsApp + Telegram backend.

### Challenge 1: India channel reliability
* **Problem:** Telegram access can be banned or restricted for Indian users, but removing Telegram would break the already functional bot.
* **Resolution:** Added WhatsApp Business Cloud API support while keeping Telegram on `/api/telegram-webhook`. Both channels route into the same `SupervisorAgent`.

### Challenge 2: Methodology sprawl
* **Problem:** The older bot mixed voice queues, OCR, topics, and top-local-trends, making the product harder to explain and maintain.
* **Resolution:** Reduced the product to four paths only: audio, social link, OCR, and text. Removed top-trends from the primary methodology.

### Challenge 3: Prompt and copy tuning
* **Problem:** Prompts and user-facing messages were embedded inside agents and webhook handlers, making editorial tuning slow.
* **Resolution:** Moved all prompts/gems into `prompts.py` and all user interaction text into `user_interactions.py`.

### Challenge 4: Social media source handling
* **Problem:** Users often share Facebook/YouTube/social links instead of raw audio.
* **Resolution:** Added `yt-dlp` extraction through `utils/social_audio.py`, then combined extracted audio facts with search-grounded URL verification before article writing.

### Challenge 5: Serverless dependency control
* **Problem:** FFmpeg-heavy media stacks can exceed serverless package limits.
* **Resolution:** Preserved the pure-python Ogg splitter for voice/audio chunking and used `yt-dlp` only for public social link downloads.

### Challenge 6: Same behavior across two chat platforms
* **Problem:** Maintaining separate WhatsApp and Telegram logic would cause drift.
* **Resolution:** Kept channel-specific code only at the webhook/media-send layer. Agents, prompts, settings, article storage, and four-path routing are shared.

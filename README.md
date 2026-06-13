# AkhbarBot v2 (Python Multi-Agent Edition)

An asynchronous, serverless-optimized Telegram bot that compiles multi-modal inputs (voice notes, images/documents, topics, trends) into professional Hindi news reports.

---

## 🚀 Key Features

*   **Custom Async Engine:** Fast, lightweight multi-agent coordination using `asyncio` and the native `google-genai` SDK.
*   **Parallelized Audio Chunking:** Pure-python Ogg page segmenter that splits long audios into 60s segments to run transcriptions in parallel.
*   **Search Grounding:** Ingests live Google search results using Gemini's native Search Grounding tool for topic verification and local trends lookup.
*   **Dynamic Telegram UI:** Control center dashboard using Inline Keyboard buttons with real-time pending counts.
*   **State Locking & Deduplication:** Compound unique constraints and atomic transitions prevent race conditions and duplicate executions.

---

## 📁 Project Structure

```text
e:/autoPapaPython/
├── agents/
│   ├── __init__.py
│   ├── audio.py        # Audio Chunk Agent (Map-Reduce transcription)
│   ├── ocr.py          # OCR Agent (Vision context extraction)
│   ├── trend.py        # Trend Agent (Search Grounding factual checks)
│   ├── editor.py       # Final Editorial Agent (Hindi news synthesis)
│   └── supervisor.py   # Supervisor orchestrator
├── utils/
│   ├── __init__.py
│   ├── ogg_splitter.py # Pure-python binary Ogg page segmenter
│   └── telegram.py     # Telegram HTTP Client wrappers
├── config.py           # Configuration parsing & validation
├── database.py         # Motor connection pooling and index setup
├── main.py             # FastAPI entrypoint and webhook routes
├── requirements.txt    # Project dependencies
├── IMPLEMENTATION.md   # System design and AI prompts reference
├── VERSIONS.md         # Interview QA sheet and challenges log
└── README.md           # Project documentation
```

---

## 🛠️ Setup & Local Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
MONGO_URI=your_mongodb_atlas_uri
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
ALLOWED_CHAT_ID=your_chat_id
```

### 3. Run FastAPI Application
```bash
python -m uvicorn main:app --reload
```

The application runs on `http://127.0.0.1:8000`. You can configure a webhook URL via Telegram pointing to `/api/webhook`.

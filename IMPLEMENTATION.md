# AkhbarBot v2: Technical Implementation & System Design Guide

This guide details the architectural decisions, database modeling, concurrency controls, and AI prompt engineering implemented in **AkhbarBot v2 (Python Multi-Agent Edition)**.

---

## 1. Architectural Decisions & Tradeoffs

### A. Custom Async Engine vs. CrewAI / LangGraph
* **Decision:** Built a custom asynchronous engine using Python's native `asyncio` and the raw `google-genai` SDK, bypassing heavy agentic frameworks.
* **Reasoning:** 
  * Frameworks like CrewAI or LangGraph add substantial package overhead, pushing the deployment bundle size close to or beyond serverless execution limits (e.g., Vercel's 500 MB limit).
  * Standard agent frameworks introduce considerable bootstrap time and internal routing layers. In serverless environments, this overhead directly causes longer cold starts and increased execution time (higher costs).
  * Direct asynchronous calls via `client.aio` combined with explicit supervisor orchestration provide absolute control over concurrency, latency, and error boundaries.

### B. Pure-Python Ogg Segmenter vs. Pydub/FFmpeg
* **Decision:** Implemented a binary search parser for Ogg container files directly in Python (`utils/ogg_splitter.py`), segmenting streams by page boundaries.
* **Reasoning:**
  * Segmenting files longer than 3 minutes (up to 10 minutes) into 60-second chunks is critical to parallelize Gemini transcription requests and fit within serverless execution windows.
  * Standard audio libraries like Pydub require an underlying `ffmpeg` binary. Packaging and running `ffmpeg` in a Vercel serverless environment is highly complex and easily balloons the package size.
  * By reading Ogg page boundaries directly (detecting the `OggS` sync markers, extracting header pages, and grouping stream pages), we segment files natively in under 10 milliseconds with zero external binaries.

### C. Native Google Search Grounding vs. Third-Party Search APIs
* **Decision:** Configured the Trend Agent using Gemini's native Search Grounding tool (`tools=[{"google_search": {}}]`).
* **Reasoning:**
  * Avoids managing API key credentials, rate limits, and billing setups for external search engines like Tavily or Serper.
  * Google Search grounding returns factual references integrated directly into the LLM prompt context, reducing system complexity and improving verification speed.

### D. Async MongoDB Driver (Motor) vs. PyMongo
* **Decision:** Motor (`motor.motor_asyncio`) for connection pooling and non-blocking queries.
* **Reasoning:**
  * PyMongo blocks the executing thread during database requests, which severely hurts FastAPI concurrency under load.
  * Motor enables complete non-blocking operations, utilizing a shared connection pool cached inside FastAPI's event loop.

---

## 2. Concurrency & Reliability Design Patterns

### A. Webhook Deduplication (At-Least-Once Delivery Guard)
* **Problem:** Telegram webhooks guarantee at-least-once delivery. In case of transient network issues, Telegram will retry sending identical message payloads, leading to double-synthesis API charges.
* **Solution:** A database-level compound unique index on `{ "telegram_message_id": 1, "chat_id": 1 }` in the `voice_notes` collection. Duplicate webhook payloads automatically trigger a MongoDB `DuplicateKeyError` (code `11000`), which FastAPI catches and discards, returning `200 OK` instantly.

### B. State-Locking Pattern (Double Compilation Prevention)
* **Problem:** If a user clicks the "Voice Notes" compile button multiple times in rapid succession, parallel webhook invocations would retrieve the same pending records, running redundant Gemini tasks.
* **Solution:**
  1. When a compilation request starts, the system synchronously queries and updates the target notes to `status: "processing"` using an atomic MongoDB update query.
  2. If the modified document count is `0` (due to another thread already processing them), the request exits immediately.
  3. The request spawns a FastAPI background task to download, segment, and synthesize.
  4. On success: Notes are updated to `status: "processed"`.
  5. On exception: A rollback block restores the status to `status: "pending"`, ensuring the user can retry compilation.

---

## 3. Dedicated Prompts Section

Below are the exact prompt templates utilized by the specialized agents for further tweaking and refinement.

### A. Audio Ingestion / Chunk Agent Prompt
* **Location:** `agents/audio.py`
```text
You are an expert audio transcription and factual analysis agent.
Analyze this audio clip (Segment #{chunk_index}, recorded at: {timestamp.isoformat()}).
Your tasks are:
1. Transcribe the audio clearly and accurately in Hindi.
2. Extract all key facts, including entity names (people, organizations), locations, dates/times, and core events mentioned.
3. Highlight any legal allegations, quotes, or numbers.
Strictly adhere ONLY to the facts present in the audio. Do not summarize outside this audio fragment.
```

### B. OCR / Document Agent Prompt
* **Location:** `agents/ocr.py`
```text
You are an expert Document OCR and entity extraction agent.
Analyze the uploaded document image.
Your tasks are:
1. Perform OCR and extract all readable text. Maintain original layout or flow where possible.
2. Extract key entities: Person names, organizations, departments, locations, dates/times, and numbers.
3. Draft a clean, structured factual summary in Hindi outlining the core matter of the document.
Do not hallucinate or add any details not explicitly visible in the document.
```

### C. Trend Agent - Local Trends Prompt
* **Location:** `agents/trend.py`
```text
You are a professional local news investigator.
Using Google Search, fetch the top 5 current, active local news trends/events for the location: '{location}'.
Focus on the department/domain: '{department}'.
Active Timestamp: {timestamp_str}.
Output a fact-verified summary of exactly 5 distinct news entries. For each entry, specify the key event, names, dates, and verified facts.
Provide the response in {language}.
```

### D. Trend Agent - Custom Topic Research Prompt
* **Location:** `agents/trend.py`
```text
You are a dedicated Research and Fact Verification Agent.
Research the following user topic: '{topic}'.
Filter information relevant to the location: '{location}' and department: '{department}'.
Active Reference Timestamp: {timestamp_str}.
Execute Google Searches to verify the facts, dates, legal status, and entity names associated with this topic.
Summarize the findings in a structured, fact-checked report in {language}.
Do not include rumors, unverified claims, or hallucinations.
```

### E. Final Editorial Agent Prompt (System Instruction)
* **Location:** `agents/editor.py`
```text
You are a professional Hindi news editor.
Below is the consolidated factual information compiled by our multi-agent system.
Your task is to synthesize this data into a single, cohesive, professional Hindi news report.
Strictly follow these guidelines:
1. Adhere ONLY to the provided facts. DO NOT introduce or hallucinate names, locations, numbers, dates, or legal allegations.
2. Adapt the report for the location: '{location}' and domain focus: '{department}'.
3. Formatting Rules (CRITICAL for Telegram compatibility):
   - Use clean markdown headings (e.g., #, ##, ###) for structure.
   - Use simple bold formatting (**word**) for key metrics or names.
   - Use standard bullet points (-) for listing details.
   - Strictly avoid using underscores (_) or standalone/unmatched asterisks (*) anywhere in the text.
   - Do not nest formatting styles (e.g., do not place bold text inside italicized blocks).
   - Do not add any emojis.
   - Do not add conversational intro/outro text. Output only the finished news report.
```

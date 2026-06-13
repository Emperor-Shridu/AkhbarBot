import asyncio
import logging
from datetime import datetime
from google import genai
from google.genai import types
from config import Config
from utils.ogg_splitter import split_ogg

logger = logging.getLogger(__name__)

class AudioChunkAgent:
    def __init__(self):
        # Initialize Google GenAI client
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.semaphore = asyncio.Semaphore(5) # Concurrency guardrail

    async def _process_chunk(self, chunk_bytes: bytes, mime_type: str, chunk_index: int, note_id: str, timestamp: datetime) -> str:
        """Processes a single audio chunk in parallel with Gemini."""
        async with self.semaphore:
            logger.info(f"Processing chunk {chunk_index} for audio note {note_id}...")
            
            # Prepare contents with inline audio data
            part = types.Part.from_bytes(
                data=chunk_bytes,
                mime_type=mime_type
            )
            
            prompt = (
                f"You are an expert audio transcription and factual analysis agent.\n"
                f"Analyze this audio clip (Segment #{chunk_index}, recorded at: {timestamp.isoformat()}).\n"
                f"Your tasks are:\n"
                f"1. Transcribe the audio clearly and accurately in Hindi.\n"
                f"2. Extract all key facts, including entity names (people, organizations), locations, dates/times, and core events mentioned.\n"
                f"3. Highlight any legal allegations, quotes, or numbers.\n"
                f"Strictly adhere ONLY to the facts present in the audio. Do not summarize outside this audio fragment."
            )
            
            try:
                response = await self.client.aio.models.generate_content(
                    model=Config.GEMINI_MODEL,
                    contents=[part, prompt]
                )
                if not response.text:
                    raise ValueError(f"Empty response from Gemini for chunk {chunk_index}")
                return response.text
            except Exception as e:
                logger.error(f"Error processing audio chunk {chunk_index}: {e}")
                return f"[Error processing chunk {chunk_index}: {str(e)}]"

    async def analyze_audios(self, voice_notes: list) -> list:
        """
        Takes a list of voice note dictionaries from the database, downloads them, 
        chunks them if necessary, and extracts key concepts in parallel.
        """
        # Download and chunk tasks preparation
        from utils.telegram import get_file, download_file
        
        all_chunks_tasks = []
        
        for idx, note in enumerate(voice_notes):
            note_id = str(note["_id"])
            file_id = note["telegram_file_id"]
            mime_type = note.get("mime_type", "audio/ogg")
            received_at = note["received_at"]
            
            logger.info(f"Downloading audio note {idx + 1}/{len(voice_notes)} (ID: {note_id})...")
            try:
                file_info = await get_file(file_id)
                file_path = file_info.get("file_path")
                if not file_path:
                    raise ValueError(f"No file path retrieved for file ID {file_id}")
                
                audio_bytes = await download_file(file_path)
                
                # Check if it needs chunking
                # If Ogg and duration > 3 mins, split_ogg will return multiple chunks.
                # If not Ogg or short, it returns a single item [audio_bytes].
                chunks = split_ogg(audio_bytes)
                
                for c_idx, chunk_data in enumerate(chunks):
                    # We pass the index (1-based)
                    task = self._process_chunk(
                        chunk_bytes=chunk_data,
                        mime_type=mime_type,
                        chunk_index=c_idx + 1,
                        note_id=note_id,
                        timestamp=received_at
                    )
                    all_chunks_tasks.append(task)
                    
            except Exception as e:
                logger.error(f"Failed to prepare audio note {note_id} for analysis: {e}")
                # Append a mock task returning error text
                async def mock_err_task(msg=str(e)):
                    return f"[Ingestion error for voice note {note_id}: {msg}]"
                all_chunks_tasks.append(mock_err_task())
                
        # Gather all chunk analyses in parallel
        if not all_chunks_tasks:
            return []
            
        logger.info(f"Fanning out {len(all_chunks_tasks)} audio chunk Gemini requests...")
        results = await asyncio.gather(*all_chunks_tasks)
        return results

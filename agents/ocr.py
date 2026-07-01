import logging
from google import genai
from google.genai import types
from config import Config
from prompts import OCR_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

class OCRAgent:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    async def extract_text(self, file_id: str, mime_type: str) -> str:
        """
        Downloads an image from Telegram and uses Gemini's multimodal vision 
        capability to extract structured text and key facts.
        """
        from utils.telegram import get_file, download_file
        
        logger.info(f"OCRAgent starting download of file: {file_id}")
        try:
            file_info = await get_file(file_id)
            file_path = file_info.get("file_path")
            if not file_path:
                raise ValueError(f"No file path retrieved for photo file ID {file_id}")
            
            image_bytes = await download_file(file_path)
            
            # Prepare image part
            part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
            
            prompt = OCR_ANALYSIS_PROMPT
            
            logger.info("Sending image to Gemini for OCR and entity extraction...")
            response = await self.client.aio.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[part, prompt]
            )
            
            if not response.text:
                raise ValueError("Gemini returned an empty response for OCR")
                
            return response.text
            
        except Exception as e:
            logger.error(f"OCR Agent failed: {e}")
            return f"[OCR Ingestion Error: {str(e)}]"

    async def extract_text_from_bytes(self, image_bytes: bytes, mime_type: str) -> str:
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        response = await self.client.aio.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=[part, OCR_ANALYSIS_PROMPT],
        )
        if not response.text:
            raise ValueError("Gemini returned an empty response for OCR")
        return response.text

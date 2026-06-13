import logging
from google import genai
from google.genai import types
from config import Config

logger = logging.getLogger(__name__)

class EditorAgent:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    async def synthesize(self, source_type: str, consolidated_context: str, settings: dict) -> str:
        """
        Synthesizes the consolidated facts into a cohesive news report in Hindi.
        Applies strict Telegram formatting rules to ensure delivery uptime.
        """
        location = settings.get("location", "Delhi")
        department = settings.get("department", "General")
        
        system_prompt = (
            "You are a professional Hindi news editor.\n"
            "Below is the consolidated factual information compiled by our multi-agent system.\n"
            "Your task is to synthesize this data into a single, cohesive, professional Hindi news report.\n"
            "Strictly follow these guidelines:\n"
            "1. Adhere ONLY to the provided facts. DO NOT introduce or hallucinate names, locations, numbers, dates, or legal allegations.\n"
            "2. Adapt the report for the location: '" + location + "' and domain focus: '" + department + "'.\n"
            "3. Formatting Rules (CRITICAL for Telegram compatibility):\n"
            "   - Use clean markdown headings (e.g., #, ##, ###) for structure.\n"
            "   - Use simple bold formatting (**word**) for key metrics or names.\n"
            "   - Use standard bullet points (-) for listing details.\n"
            "   - Strictly avoid using underscores (_) or standalone/unmatched asterisks (*) anywhere in the text.\n"
            "   - Do not nest formatting styles (e.g., do not place bold text inside italicized blocks).\n"
            "   - Do not add any emojis.\n"
            "   - Do not add conversational intro/outro text. Output only the finished news report."
        )

        user_content = (
            f"Source Pipeline: {source_type}\n"
            f"--- Consolidated Facts & Context ---\n"
            f"{consolidated_context}\n"
            f"------------------------------------"
        )

        logger.info("EditorAgent: Synthesizing final news article in Hindi...")
        try:
            response = await self.client.aio.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt
                )
            )
            
            if not response.text:
                raise ValueError("Gemini returned empty text for synthesis")
                
            return response.text
        except Exception as e:
            logger.error(f"EditorAgent synthesis failed: {e}")
            raise e

import logging
from google import genai
from google.genai import types
from config import Config
from prompts import EDITOR_SYSTEM_PROMPT, PROFESSIONALIZE_ARTICLE_PROMPT

logger = logging.getLogger(__name__)

class EditorAgent:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    async def synthesize(self, source_type: str, consolidated_context: str, settings: dict) -> str:
        """
        Synthesizes the consolidated facts into a cohesive news report in Hindi.
        Applies strict Telegram formatting rules to ensure delivery uptime.
        """
        if not consolidated_context or not consolidated_context.strip():
            raise ValueError("No factual content available to generate an article.")
        
        location = settings.get("location", "Delhi")
        department = settings.get("department", "General")
        
        system_prompt = EDITOR_SYSTEM_PROMPT.substitute(location=location, department=department)

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

    async def professionalize(self, article: str, settings: dict) -> str:
        """Rewrites a draft into a polished, publish-ready Hindi news article."""
        location = settings.get("location", "Delhi")
        department = settings.get("department", "General")
        prompt = PROFESSIONALIZE_ARTICLE_PROMPT.substitute(
            article=article,
            location=location,
            department=department,
        )

        logger.info("EditorAgent: Professionalizing submitted Hindi article...")
        response = await self.client.aio.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
        )
        if not response.text:
            raise ValueError("Gemini returned empty text for professional rewrite")
        return response.text

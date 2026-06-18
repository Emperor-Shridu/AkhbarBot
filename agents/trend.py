import logging
from datetime import datetime
from google import genai
from google.genai import types
from config import Config
from prompts import SOCIAL_LINK_RESEARCH_PROMPT, TEXT_RESEARCH_PROMPT

logger = logging.getLogger(__name__)

class TrendAgent:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        # Configure search grounding tool
        self.search_tool_config = types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )

    async def search_topic(self, topic: str, location: str, department: str, language: str, timestamp: datetime) -> str:
        """
        Performs deep research on a specific user-submitted topic, applying search grounding and filters.
        """
        timestamp_str = timestamp.isoformat()
        prompt = (
            TEXT_RESEARCH_PROMPT.substitute(
                topic=topic,
                location=location,
                department=department,
                language=language,
                timestamp=timestamp_str,
            )
        )

        logger.info(f"TrendAgent: Researching topic '{topic}' in {location} using Search Grounding...")
        try:
            response = await self.client.aio.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=self.search_tool_config
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini Search Grounding")
                
            return response.text
        except Exception as e:
            logger.error(f"TrendAgent failed to research topic: {e}")
            return f"[Topic Research Error: {str(e)}]"

    async def research_social_link(self, url: str, location: str, department: str, language: str, timestamp: datetime) -> str:
        prompt = SOCIAL_LINK_RESEARCH_PROMPT.substitute(
            url=url,
            location=location,
            department=department,
            language=language,
            timestamp=timestamp.isoformat(),
        )
        try:
            response = await self.client.aio.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=self.search_tool_config,
            )
            if not response.text:
                raise ValueError("Empty response from Gemini Search Grounding")
            return response.text
        except Exception as e:
            logger.error(f"TrendAgent failed to research social link: {e}")
            return f"[Social Link Research Error: {str(e)}]"

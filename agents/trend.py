import logging
from datetime import datetime
from googlesearch import search as google_search
from google import genai
from google.genai import types
from config import Config
from prompts import LATEST_TOPIC_RESEARCH_PROMPT, TEXT_RESEARCH_PROMPT

logger = logging.getLogger(__name__)


def _web_search_context(query: str, max_results: int = 5) -> str:
    """Fetches top Google search results and returns title+URL snippets."""
    try:
        results = list(google_search(query, max_results=max_results, advanced=True))
        if not results:
            return ""
        lines = ["--- Google Search Results ---"]
        for r in results:
            lines.append(f"Title: {r.title}\nURL: {r.url}\nSnippet: {r.description}")
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
        return ""


class TrendAgent:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    async def search_topic(self, topic: str, location: str, department: str, language: str, timestamp: datetime) -> str:
        """
        Generates a researched brief using both web search results and model knowledge.
        """
        timestamp_str = timestamp.isoformat()
        web_context = ""
        try:
            web_context = _web_search_context(f"{topic} {location} {department}", max_results=6)
        except Exception as exc:
            logger.warning("Skipping web search for topic: %s", exc)

        base_prompt = TEXT_RESEARCH_PROMPT.substitute(
            topic=topic,
            location=location,
            department=department,
            language=language,
            timestamp=timestamp_str,
        )
        prompt = base_prompt
        if web_context:
            prompt = f"{web_context}\n\nAbove are recent web search results for reference.\n\n{prompt}"

        logger.info(f"TrendAgent: Researching topic '{topic}' in {location}...")
        try:
            response = await self.client.aio.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini")
                
            return response.text
        except Exception as e:
            logger.error(f"TrendAgent failed to research topic: {e}")
            raise e

    async def search_latest_topic(self, topic: str, location: str, department: str, language: str, timestamp: datetime) -> str:
        """Researches recent developments for a topic using web search and Gemini."""
        web_context = ""
        try:
            web_context = _web_search_context(f"{topic} latest news {location} {department}", max_results=6)
        except Exception as exc:
            logger.warning("Skipping web search for latest topic: %s", exc)

        prompt = LATEST_TOPIC_RESEARCH_PROMPT.substitute(
            topic=topic,
            location=location,
            department=department,
            language=language,
            timestamp=timestamp.isoformat(),
        )
        if web_context:
            prompt = f"{web_context}\n\nAbove are recent web search results for reference.\n\n{prompt}"

        logger.info("TrendAgent: Researching latest developments for '%s'...", topic)
        try:
            response = await self.client.aio.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
            )
            if not response.text:
                raise ValueError("Empty response from Gemini")
            return response.text
        except Exception as e:
            logger.error(f"TrendAgent failed to research latest topic: {e}")
            raise e

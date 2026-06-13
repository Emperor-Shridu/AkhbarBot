import logging
from datetime import datetime
from google import genai
from google.genai import types
from config import Config

logger = logging.getLogger(__name__)

class TrendAgent:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        # Configure search grounding tool
        self.search_tool_config = types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )

    async def fetch_local_trends(self, location: str, department: str, language: str, timestamp: datetime) -> str:
        """
        Fetches the top 5 local trends using Gemini's native Google Search Grounding.
        Injects location preferences, active timestamp, and department filters.
        """
        timestamp_str = timestamp.isoformat()
        prompt = (
            f"You are a professional local news investigator.\n"
            f"Using Google Search, fetch the top 5 current, active local news trends/events for the location: '{location}'.\n"
            f"Focus on the department/domain: '{department}'.\n"
            f"Active Timestamp: {timestamp_str}.\n"
            f"Output a fact-verified summary of exactly 5 distinct news entries. For each entry, specify the key event, names, dates, and verified facts.\n"
            f"Provide the response in {language}."
        )

        logger.info(f"TrendAgent: Fetching top trends for {location} ({department}) using Search Grounding...")
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
            logger.error(f"TrendAgent failed to fetch trends: {e}")
            return f"[Trend Ingestion Error: {str(e)}]"

    async def search_topic(self, topic: str, location: str, department: str, language: str, timestamp: datetime) -> str:
        """
        Performs deep research on a specific user-submitted topic, applying search grounding and filters.
        """
        timestamp_str = timestamp.isoformat()
        prompt = (
            f"You are a dedicated Research and Fact Verification Agent.\n"
            f"Research the following user topic: '{topic}'.\n"
            f"Filter information relevant to the location: '{location}' and department: '{department}'.\n"
            f"Active Reference Timestamp: {timestamp_str}.\n"
            f"Execute Google Searches to verify the facts, dates, legal status, and entity names associated with this topic.\n"
            f"Summarize the findings in a structured, fact-checked report in {language}.\n"
            f"Do not include rumors, unverified claims, or hallucinations."
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

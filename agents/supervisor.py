import logging
from datetime import datetime
from agents.audio import AudioChunkAgent
from agents.ocr import OCRAgent
from agents.trend import TrendAgent
from agents.editor import EditorAgent

logger = logging.getLogger(__name__)

class SupervisorAgent:
    def __init__(self):
        self.audio_agent = AudioChunkAgent()
        self.ocr_agent = OCRAgent()
        self.trend_agent = TrendAgent()
        self.editor_agent = EditorAgent()

    async def compile_voice_notes(self, voice_notes: list, settings: dict) -> str:
        """
        Coordinates the Audio-to-News pipeline:
        1. Invokes AudioChunkAgent to process and transcribe all note fragments.
        2. Consolidates the results.
        3. Invokes EditorAgent to synthesize the Hindi news report.
        """
        logger.info(f"Supervisor: Initiating voice note compilation for {len(voice_notes)} notes...")
        
        # Step 1: Run map-reduce audio chunk analyses
        chunk_summaries = await self.audio_agent.analyze_audios(voice_notes)
        
        # Step 2: Consolidate summaries
        consolidated = ""
        for idx, summary in enumerate(chunk_summaries):
            consolidated += f"\n--- Audio Segment Analysis #{idx + 1} ---\n{summary}\n"
            
        # Step 3: Run final editorial synthesis
        article = await self.editor_agent.synthesize(
            source_type="Voice Notes Ingestion (Multi-Chunk)",
            consolidated_context=consolidated,
            settings=settings
        )
        return article

    async def compile_image_document(self, file_id: str, mime_type: str, settings: dict) -> str:
        """
        Coordinates the Image/Doc-to-News pipeline:
        1. Invokes OCRAgent to extract text and details from the image.
        2. Invokes EditorAgent to synthesize the Hindi news report.
        """
        logger.info(f"Supervisor: Initiating image OCR compilation for file {file_id}...")
        
        # Step 1: OCR Extraction
        ocr_result = await self.ocr_agent.extract_text(file_id, mime_type)
        
        # Step 2: Editorial Synthesis
        article = await self.editor_agent.synthesize(
            source_type="Document OCR Ingestion",
            consolidated_context=ocr_result,
            settings=settings
        )
        return article

    async def compile_topic_search(self, topic: str, settings: dict) -> str:
        """
        Coordinates the Topic-to-News pipeline:
        1. Invokes TrendAgent to run fact verification searches for the topic.
        2. Invokes EditorAgent to synthesize the Hindi news report.
        """
        logger.info(f"Supervisor: Initiating topic research compilation for: {topic}...")
        
        location = settings.get("location", "Delhi")
        department = settings.get("department", "General")
        language = settings.get("language", "Hindi")
        now = datetime.now()
        
        # Step 1: Fact Verification & Search Grounding
        research_result = await self.trend_agent.search_topic(
            topic=topic,
            location=location,
            department=department,
            language=language,
            timestamp=now
        )
        
        # Step 2: Editorial Synthesis
        article = await self.editor_agent.synthesize(
            source_type=f"Topic Research: {topic}",
            consolidated_context=research_result,
            settings=settings
        )
        return article

    async def compile_top_trends(self, settings: dict) -> str:
        """
        Coordinates the Local Trends-to-News pipeline:
        1. Invokes TrendAgent to fetch the top 5 location trends with search grounding.
        2. Invokes EditorAgent to synthesize the Hindi news report.
        """
        location = settings.get("location", "Delhi")
        department = settings.get("department", "General")
        language = settings.get("language", "Hindi")
        now = datetime.now()
        
        logger.info(f"Supervisor: Initiating local trends compilation for {location} ({department})...")
        
        # Step 1: Fetch Trends
        trends_result = await self.trend_agent.fetch_local_trends(
            location=location,
            department=department,
            language=language,
            timestamp=now
        )
        
        # Step 2: Editorial Synthesis
        article = await self.editor_agent.synthesize(
            source_type=f"Top Local Trends for {location}",
            consolidated_context=trends_result,
            settings=settings
        )
        return article

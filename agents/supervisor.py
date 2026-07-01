import logging
from datetime import datetime
from agents.audio import AudioChunkAgent
from agents.ocr import OCRAgent
from agents.trend import TrendAgent
from agents.editor import EditorAgent
from utils.social_audio import extract_audio_from_url

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

    async def compile_audio_bytes(self, audio_bytes: bytes, mime_type: str, settings: dict, source_id: str = "audio") -> str:
        """Builds a Hindi news article from raw audio bytes."""
        logger.info("Supervisor: Initiating audio compilation...")
        chunk_summaries = await self.audio_agent.analyze_audio_bytes(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            timestamp=datetime.now(),
            source_id=source_id,
        )
        consolidated = ""
        for idx, summary in enumerate(chunk_summaries):
            consolidated += f"\n--- Audio Segment Analysis #{idx + 1} ---\n{summary}\n"
        return await self.editor_agent.synthesize(
            source_type="Audio to News",
            consolidated_context=consolidated,
            settings=settings,
        )

    async def compile_image_bytes(self, image_bytes: bytes, mime_type: str, settings: dict) -> str:
        """Builds a Hindi news article from raw image/document bytes."""
        logger.info("Supervisor: Initiating OCR compilation...")
        ocr_result = await self.ocr_agent.extract_text_from_bytes(image_bytes, mime_type)
        return await self.editor_agent.synthesize(
            source_type="Document or Photo OCR to News",
            consolidated_context=ocr_result,
            settings=settings,
        )

    async def compile_social_link(self, url: str, settings: dict) -> str:
        logger.info("Supervisor: Initiating social media link compilation for %s", url)
        audio_bytes, mime_type = await extract_audio_from_url(url)
        audio_summaries = await self.audio_agent.analyze_audio_bytes(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            timestamp=datetime.now(),
            source_id=url,
        )

        consolidated = ""
        for idx, summary in enumerate(audio_summaries):
            consolidated += f"\n--- Extracted Audio Analysis #{idx + 1} ---\n{summary}\n"

        return await self.editor_agent.synthesize(
            source_type=f"Social Media Audio Link: {url}",
            consolidated_context=consolidated,
            settings=settings,
        )

    async def compile_topic_search(self, topic: str, settings: dict) -> str:
        """
        Coordinates the Topic-to-News pipeline:
        1. Invokes TrendAgent to run fact verification searches for the topic.
        2. Formats multiple story options for user selection.
        3. Invokes EditorAgent to synthesize the chosen Hindi news report.
        """
        logger.info(f"Supervisor: Initiating topic research compilation for: {topic}...")
        
        location = settings.get("location", "Delhi")
        department = settings.get("department", "General")
        language = settings.get("language", "Hindi")
        now = datetime.now()
        
        stories = await self.trend_agent.search_topic(
            topic=topic,
            location=location,
            department=department,
            language=language,
            timestamp=now
        )
        
        if not stories:
            raise ValueError("No stories found for this topic.")
        
        # Step 2: Format stories for selection
        stories_context = self._format_stories_for_selection(stories)
        
        # Step 3: Editorial Synthesis - present options and let editor create final article
        article = await self.editor_agent.synthesize(
            source_type=f"Topic Research: {topic}",
            consolidated_context=stories_context,
            settings=settings
        )
        return article

    def _format_stories_for_selection(self, stories: list[dict]) -> str:
        """Formats multiple story options for user selection."""
        if not stories:
            return "No story options found."
        
        formatted = []
        for idx, story in enumerate(stories, 1):
            formatted.append(f"Option {idx}: {story.get('title', 'Untitled')}")
            formatted.append(f"  {story.get('summary', '')}")
            if story.get('why_it_matters'):
                formatted.append(f"  Why it matters: {story['why_it_matters']}")
            formatted.append("")
        return "\n".join(formatted)

    async def compile_latest_topic(self, topic: str, settings: dict) -> list[dict]:
        """Builds a Hindi news article from the latest verified updates for a topic."""
        logger.info("Supervisor: Initiating latest topic compilation for: %s", topic)
        location = settings.get("location", "Delhi")
        department = settings.get("department", "General")
        language = settings.get("language", "Hindi")
        stories = await self.trend_agent.search_latest_topic(
            topic=topic,
            location=location,
            department=department,
            language=language,
            timestamp=datetime.now(),
        )
        if not stories:
            raise ValueError("No latest stories found for this topic.")
        return stories

    async def expand_story(self, story: dict, settings: dict) -> str:
        """Expands a single selected story into a full Hindi news article."""
        title = story.get("title", "")
        summary = story.get("summary", "")
        why = story.get("why_it_matters", "")
        
        context = f"Selected Story:\nTitle: {title}\n\nSummary:\n{summary}\n\nNews Value:\n{why}\n\nExpand this into a full publish-ready Hindi news article following the editorial guidelines."
        
        return await self.editor_agent.synthesize(
            source_type="Selected Story Expansion",
            consolidated_context=context,
            settings=settings,
        )

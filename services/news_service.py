"""Reusable article generation service shared by Telegram and Streamlit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents.supervisor import SupervisorAgent
from database import save_article


@dataclass(frozen=True)
class NewsSettings:
    """Editorial preferences that shape every generated Hindi article."""

    location: str = "Delhi"
    department: str = "General"
    language: str = "Hindi"

    def as_dict(self) -> dict[str, str]:
        """Converts settings into the dictionary format expected by agents."""
        return {
            "location": self.location.strip() or "Delhi",
            "department": self.department.strip() or "General",
            "language": "Hindi",
        }


class NewsService:
    """Coordinates article generation and persistence for every channel."""

    def __init__(self, supervisor: SupervisorAgent | None = None) -> None:
        self.supervisor = supervisor or SupervisorAgent()

    async def from_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        settings: NewsSettings,
        source_id: str,
        actor: dict[str, Any],
    ) -> str:
        """Generates and stores a publish-ready article from an audio file."""
        article = await self.supervisor.compile_audio_bytes(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            settings=settings.as_dict(),
            source_id=source_id,
        )
        await self._save("audio_to_news", article, actor)
        return article

    async def from_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        settings: NewsSettings,
        actor: dict[str, Any],
    ) -> str:
        """Generates and stores a publish-ready article from an image document."""
        article = await self.supervisor.compile_image_bytes(image_bytes, mime_type, settings.as_dict())
        await self._save("ocr_to_news", article, actor)
        return article

    async def from_social_link(
        self,
        url: str,
        settings: NewsSettings,
        actor: dict[str, Any],
    ) -> str:
        """Generates and stores a publish-ready article from a public media URL."""
        article = await self.supervisor.compile_social_link(url, settings.as_dict())
        await self._save("social_link_to_news", article, actor)
        return article

    async def from_text(
        self,
        text: str,
        settings: NewsSettings,
        actor: dict[str, Any],
    ) -> str:
        """Generates and stores a publish-ready article from a topic or brief."""
        article = await self.supervisor.compile_topic_search(text, settings.as_dict())
        await self._save("text_to_news", article, actor)
        return article

    async def from_latest_topic(
        self,
        topic: str,
        settings: NewsSettings,
        actor: dict[str, Any],
    ) -> tuple[str, list[dict]]:
        """Generates multiple short listed story options for a topic, returns (formatted_options_text, stories_list)."""
        stories = await self.supervisor.compile_latest_topic(topic, settings.as_dict())
        formatted = self.supervisor._format_stories_for_selection(stories)
        await self._save("latest_topic_to_news", formatted, actor)
        return formatted, stories

    async def from_latest_topic_article(
        self,
        topic: str,
        settings: NewsSettings,
        actor: dict[str, Any],
    ) -> str:
        """Generates a full Hindi article from the latest verified updates around a topic."""
        try:
            stories = await self.supervisor.compile_latest_topic(topic, settings.as_dict())
        except Exception as exc:
            raise ValueError(f"Could not find stories for topic '{topic}': {exc}") from exc

        if not stories:
            article = "No recent stories found for this topic."
        else:
            article = await self.supervisor.expand_story(stories[0], settings.as_dict())
        await self._save("latest_topic_to_news", article, actor)
        return article

    async def expand_story(
        self,
        story: dict[str, Any],
        settings: NewsSettings,
        actor: dict[str, Any],
    ) -> str:
        """Expands a single selected story into a full Hindi news article."""
        article = await self.supervisor.expand_story(story, settings.as_dict())
        await self._save("expanded_story_to_news", article, actor)
        return article

    async def professionalize(
        self,
        article: str,
        settings: NewsSettings,
        actor: dict[str, Any],
    ) -> str:
        """Stores a polished rewrite of an existing Hindi news draft."""
        rewritten = await self.supervisor.professionalize_article(article, settings.as_dict())
        await self._save("professionalized_article", rewritten, actor)
        return rewritten

    async def _save(self, source_type: str, article: str, actor: dict[str, Any]) -> None:
        """Persists an article with consistent metadata for history views."""
        await save_article(
            {
                "source_type": source_type,
                "generated_article_hindi": article,
                "created_at": datetime.now(),
                "actor": actor,
            }
        )


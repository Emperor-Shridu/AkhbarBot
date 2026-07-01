import asyncio
import os
import tempfile


async def extract_audio_from_url(url: str) -> tuple[bytes, str]:
    """Download best available audio from a public social/video URL using yt-dlp."""
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("yt-dlp is required for social link audio extraction") from exc

    def _download() -> tuple[bytes, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_template = os.path.join(tmpdir, "source.%(ext)s")
            options = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "quiet": True,
                "noplaylist": True,
            }
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    matches = [os.path.join(tmpdir, name) for name in os.listdir(tmpdir)]
                    if not matches:
                        raise RuntimeError("yt-dlp did not produce a media file")
                    filename = matches[0]
                with open(filename, "rb") as handle:
                    data = handle.read()
                ext = os.path.splitext(filename)[1].lower()
                mime_type = "audio/webm" if ext == ".webm" else "audio/mpeg"
                return data, mime_type

    return await asyncio.to_thread(_download)

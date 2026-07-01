import io
import logging
import subprocess

logger = logging.getLogger(__name__)


def extract_audio_from_video(video_bytes: bytes) -> bytes | None:
    """Extract audio from video bytes if an audio stream is present."""
    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        logger.warning("FFmpeg is unavailable: %s", exc)
        return None

    try:
        process = subprocess.Popen(
            [
                ffmpeg_exe,
                "-hide_banner",
                "-i",
                "pipe:0",
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=video_bytes, timeout=60)

        if process.returncode == 0 and stdout:
            return stdout

        logger.warning("Audio extraction failed: %s", stderr.decode("utf-8", errors="replace")[:500])
        return None
    except Exception as exc:
        logger.warning("Audio extraction error: %s", exc)
        return None

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
            try:
                from curl_cffi import impersonate as _curl_impersonate
            except ImportError:
                _curl_impersonate = None
            options = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "quiet": True,
                "noplaylist": True,
                "geo_bypass": True,
                "geo_bypass_country": "US",
                "nocheckcertificate": True,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                },
                "extractor_args": {
                    "instagram": {
                        "api_host": "www.instagram.com",
                        **({"impersonate": ["chrome120"]} if _curl_impersonate else {}),
                    },
                    "facebook": {
                        "api_host": "www.facebook.com",
                        **({"impersonate": ["chrome120"]} if _curl_impersonate else {}),
                    },
                },
            }
            cookie_file = os.environ.get("YOUTUBE_COOKIES") or os.environ.get("YTDL_COOKIES")
            if cookie_file and os.path.isfile(cookie_file):
                options["cookiefile"] = cookie_file
            else:
                cookie_content = os.environ.get("YOUTUBE_COOKIES_CONTENT") or os.environ.get("YTDL_COOKIES_CONTENT")
                if cookie_content:
                    cookie_path = os.path.join(tmpdir, "cookies.txt")
                    with open(cookie_path, "w", encoding="utf-8") as handle:
                        handle.write(cookie_content)
                    options["cookiefile"] = cookie_path
            try:
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
            except yt_dlp.utils.DownloadError as exc:
                if "Cannot parse data" in str(exc):
                    raise RuntimeError(
                        "yt-dlp could not extract this social media video. "
                        "For Facebook/Instagram videos this may be because the page requires browser impersonation. "
                        "Set the YOUTUBE_COOKIES environment variable to a Netscape-format cookies.txt file."
                    ) from exc
                raise

    return await asyncio.to_thread(_download)

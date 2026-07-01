"""Streamlit frontend for generating and sharing Hindi news articles."""

from __future__ import annotations

from urllib.parse import quote

import httpx
import streamlit as st

from config import Config

st.set_page_config(page_title="AkhbarBot", page_icon="A", layout="wide")


def secret_value(key: str, default: str = "") -> str:
    """Reads a value from Streamlit secrets first and environment config second."""
    try:
        value = st.secrets.get(key)
    except Exception:
        value = None
    return str(value or getattr(Config, key, default) or default)


def backend_base_url() -> str:
    """Returns the configured FastAPI backend URL."""
    return secret_value("BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")


def allowed_user_ids() -> set[str]:
    """Returns allowed Streamlit user ids, including the interview demo id."""
    raw_ids = secret_value("STREAMLIT_USER_IDS", "demo")
    return {item.strip() for item in raw_ids.replace(";", ",").split(",") if item.strip()}


def headers(user_id: str) -> dict[str, str]:
    """Builds authentication headers for backend requests."""
    request_headers = {"X-User-Id": user_id}
    api_secret = secret_value("API_SHARED_SECRET", "")
    if api_secret:
        request_headers["X-Api-Secret"] = api_secret
    return request_headers


def post_json(path: str, payload: dict, user_id: str) -> str:
    """Calls a JSON article endpoint and returns the generated article."""
    with httpx.Client(timeout=600.0) as client:
        response = client.post(
            f"{backend_base_url()}{path}",
            json=payload,
            headers=headers(user_id),
        )
        response.raise_for_status()
        return response.json()["article"]


def post_file(path: str, file, location: str, department: str, user_id: str) -> str:
    """Uploads a file to an article endpoint and returns the generated article."""
    files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
    params = {"location": location, "department": department}
    with httpx.Client(timeout=900.0) as client:
        response = client.post(
            f"{backend_base_url()}{path}",
            params=params,
            files=files,
            headers=headers(user_id),
        )
        response.raise_for_status()
        return response.json()["article"]


def show_article(article: str, key: str = "article") -> None:
    """Displays the final article and a WhatsApp share action."""
    if not article:
        return
    st.subheader("Final Article")
    st.text_area("Publish-ready Hindi copy", article, height=420, key=key)
    whatsapp_url = f"https://wa.me/?text={quote(article)}"
    st.link_button("Send to WhatsApp", whatsapp_url, use_container_width=True)


def guarded_user_id() -> str | None:
    """Collects and validates the Streamlit user id locally before API calls."""
    st.sidebar.title("Access")
    user_id = st.sidebar.text_input("User ID", value="demo")
    if user_id.strip() not in allowed_user_ids():
        st.warning("This user id is not allowed.")
        return None
    return user_id


def render_generator(user_id: str) -> None:
    """Renders all article creation modes."""
    st.title("AkhbarBot")

    location = st.sidebar.text_input("Location", value="Delhi")
    department = st.sidebar.text_input("Department", value="General")
    base_payload = {"location": location, "department": department}

    tabs = st.tabs(
        [
            "Text",
            "Latest Topic",
            "Professionalize",
            "Audio",
            "Image/OCR",
            "Social Link",
            "History",
        ]
    )

    with tabs[0]:
        text = st.text_area("Topic, brief, or pasted facts", height=220)
        if st.button("Generate Article", type="primary", disabled=not text.strip()):
            with st.spinner("Generating article..."):
                st.session_state.article = post_json("/api/articles/text", {"text": text, **base_payload}, user_id)
        show_article(st.session_state.get("article", ""), key="text_article")

    with tabs[1]:
        topic = st.text_input("Topic to fetch latest verified updates")
        if st.button("Fetch Latest Article", type="primary", disabled=not topic.strip()):
            with st.spinner("Researching latest updates..."):
                st.session_state.latest_article = post_json(
                    "/api/articles/latest-topic",
                    {"text": topic, **base_payload},
                    user_id,
                )
        show_article(st.session_state.get("latest_article", ""), key="latest_article")

    with tabs[2]:
        draft = st.text_area("Paste article draft", height=260)
        if st.button("Professionalize", type="primary", disabled=not draft.strip()):
            with st.spinner("Polishing article..."):
                st.session_state.polished_article = post_json(
                    "/api/articles/professionalize",
                    {"text": draft, **base_payload},
                    user_id,
                )
        show_article(st.session_state.get("polished_article", ""), key="polished_article")

    with tabs[3]:
        audio_file = st.file_uploader("Upload audio", type=["ogg", "opus", "mp3", "m4a", "wav", "webm"])
        if st.button("Generate from Audio", type="primary", disabled=audio_file is None):
            with st.spinner("Processing audio..."):
                st.session_state.audio_article = post_file(
                    "/api/articles/audio",
                    audio_file,
                    location,
                    department,
                    user_id,
                )
        show_article(st.session_state.get("audio_article", ""), key="audio_article")

    with tabs[4]:
        image_file = st.file_uploader("Upload image or scanned document", type=["jpg", "jpeg", "png", "webp"])
        if st.button("Generate from Image", type="primary", disabled=image_file is None):
            with st.spinner("Reading document..."):
                st.session_state.image_article = post_file(
                    "/api/articles/image",
                    image_file,
                    location,
                    department,
                    user_id,
                )
        show_article(st.session_state.get("image_article", ""), key="image_article")

    with tabs[5]:
        url = st.text_input("Public social media URL")
        if st.button("Generate from Link", type="primary", disabled=not url.strip()):
            with st.spinner("Extracting and verifying link..."):
                st.session_state.link_article = post_json(
                    "/api/articles/social-link",
                    {"url": url, **base_payload},
                    user_id,
                )
        show_article(st.session_state.get("link_article", ""), key="link_article")

    with tabs[6]:
        st.caption("History is password protected.")
        if "history_auth" not in st.session_state:
            pw = st.text_input("Enter history password", type="password")
            if st.button("Unlock History", disabled=not pw):
                if pw == "shridhu74":
                    st.session_state["history_auth"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            st.stop()
        if st.button("Refresh History"):
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{backend_base_url()}/api/articles/history",
                    headers=headers(user_id),
                )
                response.raise_for_status()
                st.session_state.history = response.json()["articles"]
        for idx, item in enumerate(st.session_state.get("history", [])):
            with st.expander(f"{item.get('created_at', '')} | {item.get('source_type', '')}"):
                show_article(item.get("generated_article_hindi", ""), key=f"history_{idx}")


def main() -> None:
    """Runs the Streamlit app."""
    user_id = guarded_user_id()
    if user_id:
        render_generator(user_id)


if __name__ == "__main__":
    main()

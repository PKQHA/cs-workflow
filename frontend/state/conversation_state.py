from __future__ import annotations

from uuid import uuid4

import streamlit as st


def ensure_conversation_state() -> str:
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"web_{uuid4().hex[:12]}"
    if "last_analysis" not in st.session_state:
        st.session_state.last_analysis = None
    return st.session_state.session_id


def save_analysis(data: dict) -> None:
    st.session_state.last_analysis = data


def get_last_recommendations() -> list[dict]:
    data = st.session_state.get("last_analysis") or {}
    return data.get("recommendations") or []


def reset_local_conversation() -> None:
    st.session_state.session_id = f"web_{uuid4().hex[:12]}"
    st.session_state.last_analysis = None

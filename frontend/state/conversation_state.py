from __future__ import annotations

from uuid import uuid4

import streamlit as st


def sync_workspace_state() -> str | None:
    workspace_id = _normalize_query_param(st.query_params.get("workspace_id"))
    if workspace_id:
        st.session_state.workspace_id = workspace_id
        return workspace_id
    session_workspace_id = _normalize_query_param(st.session_state.get("workspace_id"))
    if session_workspace_id:
        st.query_params["workspace_id"] = session_workspace_id
        return session_workspace_id
    st.session_state.workspace_id = None
    return None


def set_workspace_id(workspace_id: str) -> None:
    normalized = _normalize_query_param(workspace_id)
    st.session_state.workspace_id = normalized
    if normalized:
        st.query_params["workspace_id"] = normalized
    else:
        st.query_params.pop("workspace_id", None)


def get_workspace_id() -> str | None:
    return _normalize_query_param(st.session_state.get("workspace_id"))


def ensure_conversation_state() -> str:
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"web_{uuid4().hex[:12]}"
    if "last_analysis" not in st.session_state:
        st.session_state.last_analysis = None
    if "analysis_progress" not in st.session_state:
        st.session_state.analysis_progress = []
    return st.session_state.session_id


def save_analysis(data: dict) -> None:
    st.session_state.last_analysis = data


def save_analysis_progress(steps: list[str]) -> None:
    st.session_state.analysis_progress = steps


def get_analysis_progress() -> list[str]:
    return st.session_state.get("analysis_progress") or []


def get_last_recommendations() -> list[dict]:
    data = st.session_state.get("last_analysis") or {}
    return data.get("recommendations") or []


def reset_local_conversation() -> None:
    st.session_state.session_id = f"web_{uuid4().hex[:12]}"
    st.session_state.last_analysis = None
    st.session_state.analysis_progress = []


def _normalize_query_param(value) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    normalized = str(value or "").strip()
    return normalized or None

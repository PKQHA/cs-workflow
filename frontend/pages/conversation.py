from __future__ import annotations

import streamlit as st

from frontend.components.recommendation_panel import render_recommendations
from frontend.services.api_client import ApiClientError, BackendApiClient
from frontend.state.conversation_state import ensure_conversation_state, reset_local_conversation, save_analysis


def render_conversation_page(api_client: BackendApiClient) -> None:
    session_id = ensure_conversation_state()
    st.header("对话分析")
    st.caption(f"当前会话：{session_id}")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("新对话"):
            try:
                api_client.post("/api/conversation/reset", {"session_id": session_id})
                reset_local_conversation()
                st.success("新对话已开始")
                st.rerun()
            except ApiClientError as exc:
                st.error(exc.message)

    text = st.text_area("客户话语", height=150, placeholder="例如：我们3个人，开2个房间，预算1000元，住2天")
    if st.button("发送 / 分析", type="primary"):
        try:
            data = api_client.post("/api/conversation/analyze", {"session_id": session_id, "text": text})
            save_analysis(data)
            _render_analysis(data, api_client, session_id)
        except ApiClientError as exc:
            st.error(exc.message)

    if st.session_state.get("last_analysis"):
        st.divider()
        _render_analysis(st.session_state.last_analysis, api_client, session_id)


def _render_analysis(data: dict, api_client: BackendApiClient, session_id: str) -> None:
    if data.get("intent") == "qa":
        st.success("普通答疑")
        st.write(data.get("reply", ""))
        return

    if data.get("intent") == "unknown":
        st.info(data.get("reply", "我可以帮您查询酒店信息，也可以帮您订房，请问您现在需要哪一种？"))
        return

    if data.get("status") == "missing_info":
        st.warning(data.get("reply", "订房信息不足，请继续补充。"))
        missing = data.get("missing_fields") or []
        if missing:
            st.write("缺失信息：" + "、".join(missing))
        return

    if data.get("status") == "recommendations_ready":
        render_recommendations(data.get("recommendations") or [], api_client, session_id)

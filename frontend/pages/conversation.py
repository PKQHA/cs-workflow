from __future__ import annotations

import streamlit as st

from frontend.components.recommendation_panel import render_recommendations
from frontend.services.api_client import ApiClientError, BackendApiClient
from frontend.state.conversation_state import (
    ensure_conversation_state,
    get_analysis_progress,
    reset_local_conversation,
    save_analysis,
    save_analysis_progress,
)


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

    text = st.text_area("客户话语", height=150, placeholder="例如：我们3个人，开2个房间，预算1000元，住2晚")
    if st.button("发送 / 分析", type="primary"):
        cleaned_text = text.strip()
        if not cleaned_text:
            st.warning("请先输入客户问题或需求。")
        else:
            progress_steps = [
                "已接收客户输入",
                "正在分析意图并选择处理路径",
                "正在调用本地规则、知识库或推荐逻辑",
            ]
            try:
                with st.status("正在处理客户消息…", expanded=True) as status:
                    for step in progress_steps:
                        status.write(step)
                    data = api_client.post("/api/conversation/analyze", {"session_id": session_id, "text": cleaned_text})
                    final_step = _finalize_progress_step(data)
                    status.write(final_step)
                    status.update(label="处理完成", state="complete")
                save_analysis_progress(progress_steps + [final_step])
                save_analysis(data)
                _render_analysis(data, api_client, session_id)
            except ApiClientError as exc:
                save_analysis_progress(progress_steps + [f"处理终止：{exc.message}"])
                st.error(exc.message)

    progress_steps = get_analysis_progress()
    if progress_steps:
        with st.expander("最近一次处理过程", expanded=False):
            for index, step in enumerate(progress_steps, start=1):
                st.write(f"{index}. {step}")

    if st.session_state.get("last_analysis"):
        st.divider()
        _render_analysis(st.session_state.last_analysis, api_client, session_id)


def _render_analysis(data: dict, api_client: BackendApiClient, session_id: str) -> None:
    if data.get("intent") == "qa":
        st.success("已完成答疑")
        st.write(data.get("reply", ""))
        return

    if data.get("intent") == "unknown":
        st.info(data.get("reply", "我可以协助您查询酒店信息，也可以帮您安排订房。请问您现在是想咨询问题，还是需要预订房间？"))
        return

    if data.get("status") == "missing_info":
        st.warning(data.get("reply", "订房信息不足，请继续补充。"))
        missing = data.get("missing_fields") or []
        if missing:
            st.write("缺失信息：" + "、".join(missing))
        return

    if data.get("status") == "recommendations_ready":
        render_recommendations(data.get("recommendations") or [], api_client, session_id)


def _finalize_progress_step(data: dict) -> str:
    if data.get("intent") == "qa":
        qa_type = (data.get("slots") or {}).get("qa_type")
        if qa_type in {"room_status", "room_availability"}:
            return "已完成房态查询并生成回复"
        return "已完成知识查询并生成回复"
    if data.get("intent") == "unknown":
        return "已完成初步判断，等待进一步澄清"
    if data.get("status") == "missing_info":
        return "已识别为订房需求，正在等待补充关键信息"
    if data.get("status") == "recommendations_ready":
        return "已完成房型推荐整理"
    return "已完成处理"

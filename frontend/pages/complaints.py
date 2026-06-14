from __future__ import annotations

import streamlit as st

from frontend.services.api_client import ApiClientError, BackendApiClient


def render_complaints_page(api_client: BackendApiClient) -> None:
    st.header("投诉处理")
    text = st.text_area("投诉内容", height=150, placeholder="例如：房间床单有污渍，卫生不好")
    if st.button("分析投诉", type="primary"):
        cleaned_text = text.strip()
        if not cleaned_text:
            st.warning("请先输入投诉内容。")
            return

        try:
            with st.status("正在分析投诉…", expanded=True) as status:
                status.write("已接收投诉内容")
                status.write("正在使用现有规则识别投诉类型与严重程度")
                status.write("正在整理客服处理建议")
                data = api_client.post("/api/complaints/analyze", {"text": cleaned_text})
                status.update(label="投诉分析完成", state="complete")
        except ApiClientError as exc:
            st.error(exc.message)
            return

        st.success("投诉分析完成")
        st.write(f"投诉类型：{data.get('complaint_type')}")
        st.write(f"严重程度：{data.get('severity')}")
        st.write("安抚文案：")
        st.info(data.get("comfort_reply", ""))
        if data.get("severity") == "轻度":
            st.write(f"解决方式：{data.get('solution')}")
            st.write(f"补偿建议：{data.get('compensation')}")
        else:
            st.write(f"上报提示：{data.get('escalation_note')}")
            st.write(f"上报摘要：{data.get('escalation_summary')}")

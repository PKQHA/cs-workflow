from __future__ import annotations

import streamlit as st

from frontend.services.api_client import ApiClientError, BackendApiClient
from frontend.state.conversation_state import get_workspace_id, set_workspace_id


def render_files_page(api_client: BackendApiClient) -> None:
    st.header("Excel 上传")
    workspace_id = get_workspace_id()
    if workspace_id:
        st.caption(f"当前工作区：{workspace_id}")
    try:
        status = api_client.get("/api/files/status")
        if status.get("uploaded"):
            st.success("当前工作区已上传 Excel，可执行保存类操作。")
            try:
                file_bytes = api_client.download_file("/api/files/download")
                st.download_button(
                    "下载当前 Excel",
                    data=file_bytes,
                    file_name="data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=False,
                )
            except ApiClientError as exc:
                st.error(exc.message)
        else:
            st.warning("当前工作区未上传 Excel，新增表单、修改表单、修改房态会被后端拦截。")
    except ApiClientError as exc:
        st.error(exc.message)

    uploaded_file = st.file_uploader("选择 .xlsx 文件", type=["xlsx"])
    if uploaded_file and st.button("上传 Excel", type="primary"):
        try:
            with st.spinner("正在上传 Excel…"):
                result = api_client.upload_file(
                    "/api/files/upload-excel",
                    uploaded_file.name,
                    uploaded_file,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    include_workspace=False,
                )
            if result.get("workspace_id"):
                set_workspace_id(str(result["workspace_id"]))
            st.success(f"上传成功：{result.get('file_name')}")
            st.rerun()
        except ApiClientError as exc:
            st.error(exc.message)

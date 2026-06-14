from __future__ import annotations

import streamlit as st

from frontend.services.api_client import ApiClientError, BackendApiClient


def render_files_page(api_client: BackendApiClient) -> None:
    st.header("Excel 上传")
    try:
        status = api_client.get("/api/files/status")
        if status.get("uploaded"):
            st.success("当前已上传 Excel，可执行保存类操作。")
        else:
            st.warning("当前未上传 Excel，新增表单、修改表单、修改房态会被后端拦截。")
    except ApiClientError as exc:
        st.error(exc.message)

    uploaded_file = st.file_uploader("选择 .xlsx 文件", type=["xlsx"])
    if uploaded_file and st.button("上传 Excel", type="primary"):
        try:
            result = api_client.upload_file(
                "/api/files/upload-excel",
                uploaded_file.name,
                uploaded_file,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.success(f"上传成功：{result.get('file_name')}")
        except ApiClientError as exc:
            st.error(exc.message)

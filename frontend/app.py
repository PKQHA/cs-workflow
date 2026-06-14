from __future__ import annotations

import streamlit as st

from frontend.pages.complaints import render_complaints_page
from frontend.pages.conversation import render_conversation_page
from frontend.pages.files import render_files_page
from frontend.pages.forms import render_forms_page
from frontend.pages.rooms import render_rooms_page
from frontend.services.api_client import ApiClientError, get_api_client, get_backend_base_url


def hide_streamlit_default_navigation() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="酒店客服自动化系统", layout="wide")
    hide_streamlit_default_navigation()
    st.title("酒店客服自动化系统")

    try:
        get_backend_base_url()
        api_client = get_api_client()
    except ApiClientError as exc:
        st.error(exc.message)
        st.stop()

    page = st.sidebar.radio(
        "功能导航",
        ["对话页", "表单管理", "房间查询", "投诉处理", "Excel 上传"],
    )

    if page == "对话页":
        render_conversation_page(api_client)
    elif page == "表单管理":
        render_forms_page(api_client)
    elif page == "房间查询":
        render_rooms_page(api_client)
    elif page == "投诉处理":
        render_complaints_page(api_client)
    elif page == "Excel 上传":
        render_files_page(api_client)


if __name__ == "__main__":
    main()

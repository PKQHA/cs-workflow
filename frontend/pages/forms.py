from __future__ import annotations

import re

import streamlit as st

from frontend.services.api_client import ApiClientError, BackendApiClient


def render_forms_page(api_client: BackendApiClient) -> None:
    st.header("表单管理")
    tab_create, tab_pending = st.tabs(["手动新增表单", "待完成表单"])

    with tab_create:
        with st.form("manual_create_form"):
            contact_name = st.text_input("联系人")
            gender = st.selectbox("性别", ["男", "女", "其他"])
            phone = st.text_input("手机号")
            total_amount = st.number_input("总金额", min_value=0.0, step=1.0)
            guest_count = st.number_input("人数", min_value=1, step=1)
            guest_type = st.selectbox("人数类型", ["个人", "多人", "企业团建", "情侣"])
            stay_days = st.number_input("居住天数", min_value=1, step=1)
            room_numbers_text = st.text_input("房间号，多个用英文逗号分隔", placeholder="201,202")
            order_status = st.selectbox("订单状态", ["已完成", "待完成"])
            submitted = st.form_submit_button("创建表单")
            if submitted:
                contact_name = contact_name.strip()
                phone = phone.strip()
                room_numbers = [item.strip() for item in room_numbers_text.split(",") if item.strip()]
                if not contact_name:
                    st.error("联系人不能为空。")
                elif not re.fullmatch(r"^1[3-9]\d{9}$", phone):
                    st.error("请输入有效的 11 位手机号。")
                elif total_amount <= 0:
                    st.error("总金额必须大于 0。")
                elif not room_numbers:
                    st.error("请至少填写一个房间号。")
                else:
                    try:
                        with st.spinner("正在创建表单…"):
                            result = api_client.post(
                                "/api/forms/create",
                                {
                                    "contact_name": contact_name,
                                    "gender": gender,
                                    "phone": phone,
                                    "total_amount": total_amount,
                                    "guest_count": guest_count,
                                    "guest_type": guest_type,
                                    "stay_days": stay_days,
                                    "room_numbers": room_numbers,
                                    "order_status": order_status,
                                },
                            )
                        st.success(f"表单创建成功：{result.get('form_id')}")
                    except ApiClientError as exc:
                        st.error(exc.message)
                    except Exception:
                        st.error("创建表单时出现异常，请稍后重试。")

    with tab_pending:
        if "pending_forms_data" not in st.session_state:
            st.session_state.pending_forms_data = None

        if st.button("加载/刷新待完成表单"):
            st.session_state.pending_forms_data = _load_pending_forms(api_client)

        pending_forms = st.session_state.pending_forms_data
        if pending_forms is None:
            st.info("点击“加载/刷新待完成表单”后查看当前待完成记录。")
        else:
            _render_pending_forms(api_client, pending_forms)


def _load_pending_forms(api_client: BackendApiClient) -> list[dict] | None:
    try:
        return api_client.get("/api/forms/pending") or []
    except ApiClientError as exc:
        st.error(exc.message)
        return None


def _render_pending_forms(api_client: BackendApiClient, pending_forms: list[dict]) -> None:
    if not pending_forms:
        st.info("所有表单已完成，或当前没有待完成表单。")
        return

    for form in pending_forms:
        form_id = form.get("表单唯一标识") or form.get("form_id")
        with st.expander(f"待完成表单：{form_id}", expanded=False):
            st.json(form)
            if st.button("改为已完成", key=f"complete_{form_id}"):
                try:
                    with st.spinner("正在更新表单状态…"):
                        api_client.post("/api/forms/complete", {"form_id": form_id})
                    st.session_state.pending_forms_data = _load_pending_forms(api_client)
                    st.success("已更新为已完成")
                    st.rerun()
                except ApiClientError as exc:
                    st.error(exc.message)
                except Exception:
                    st.error("更新表单状态时出现异常，请稍后重试。")

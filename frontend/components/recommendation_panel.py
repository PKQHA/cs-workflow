from __future__ import annotations

import re

import streamlit as st

from frontend.services.api_client import ApiClientError, BackendApiClient


def render_recommendations(recommendations: list[dict], api_client: BackendApiClient, session_id: str) -> None:
    if not recommendations:
        st.info("暂无推荐方案。")
        return

    st.subheader("推荐结果")
    for index, item in enumerate(recommendations):
        recommendation_id = item.get("recommendation_id", "unknown")
        widget_prefix = f"{recommendation_id}_{index}"
        sample_room_numbers = item.get("room_numbers") or []
        selectable_room_numbers = item.get("selectable_room_numbers") or sample_room_numbers
        selectable_text = "，".join(selectable_room_numbers)
        with st.expander(f"方案 {item.get('recommendation_id')} | 示例房间：{', '.join(sample_room_numbers)}", expanded=True):
            st.write(f"总金额：{item.get('total_amount')}")
            st.write(f"入住人数：{item.get('guest_count')}，房间数：{item.get('room_count')}，居住天数：{item.get('stay_days')}")
            st.write(f"推荐理由：{item.get('reason_text')}")
            st.write(f"当前方案可选空房号：{selectable_text}")
            st.text_area("客服可复制文案", value=item.get("reply_text", ""), height=90, key=f"reply_{widget_prefix}")

            with st.form(f"recommendation_form_{widget_prefix}"):
                contact_name = st.text_input("联系人", key=f"contact_name_{widget_prefix}")
                gender = st.selectbox("性别", ["男", "女", "其他"], key=f"gender_{widget_prefix}")
                phone = st.text_input("手机号", key=f"phone_{widget_prefix}")
                selected_room_numbers_text = st.text_input(
                    "最终房间号（多个用英文逗号分隔）",
                    value=",".join(sample_room_numbers),
                    key=f"selected_room_numbers_{widget_prefix}",
                )
                order_status = st.selectbox("订单状态", ["已完成", "待完成"], key=f"status_{widget_prefix}")
                submitted = st.form_submit_button("将此方案转为表单")
                if submitted:
                    contact_name = contact_name.strip()
                    phone = phone.strip()
                    selected_room_numbers = [room.strip() for room in selected_room_numbers_text.split(",") if room.strip()]
                    if not contact_name:
                        st.error("联系人不能为空。")
                        continue
                    if not re.fullmatch(r"^1[3-9]\d{9}$", phone):
                        st.error("请输入有效的 11 位手机号。")
                        continue
                    try:
                        with st.spinner("正在生成表单…"):
                            result = api_client.post(
                                "/api/forms/from-recommendation",
                                {
                                    "session_id": session_id,
                                    "recommendation_id": item.get("recommendation_id"),
                                    "contact_name": contact_name,
                                    "gender": gender,
                                    "phone": phone,
                                    "selected_room_numbers": selected_room_numbers,
                                    "order_status": order_status,
                                },
                            )
                        st.success(f"表单创建成功：{result.get('form_id')}")
                    except ApiClientError as exc:
                        st.error(exc.message)

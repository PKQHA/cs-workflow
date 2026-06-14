from __future__ import annotations

import streamlit as st

from frontend.services.api_client import ApiClientError, BackendApiClient


def render_recommendations(recommendations: list[dict], api_client: BackendApiClient, session_id: str) -> None:
    if not recommendations:
        st.info("暂无推荐方案。")
        return

    st.subheader("推荐结果")
    for item in recommendations:
        with st.expander(f"方案 {item.get('recommendation_id')} | 房间：{', '.join(item.get('room_numbers', []))}", expanded=True):
            st.write(f"总金额：{item.get('total_amount')}")
            st.write(f"入住人数：{item.get('guest_count')}，房间数：{item.get('room_count')}，居住天数：{item.get('stay_days')}")
            st.write(f"推荐理由：{item.get('reason_text')}")
            st.text_area("客服可复制文案", value=item.get("reply_text", ""), height=90, key=f"reply_{item.get('recommendation_id')}")

            with st.form(f"recommendation_form_{item.get('recommendation_id')}"):
                contact_name = st.text_input("联系人")
                gender = st.selectbox("性别", ["男", "女", "其他"], key=f"gender_{item.get('recommendation_id')}")
                phone = st.text_input("手机号")
                order_status = st.selectbox("订单状态", ["已完成", "待完成"], key=f"status_{item.get('recommendation_id')}")
                submitted = st.form_submit_button("将此方案转为表单")
                if submitted:
                    try:
                        result = api_client.post(
                            "/api/forms/from-recommendation",
                            {
                                "session_id": session_id,
                                "recommendation_id": item.get("recommendation_id"),
                                "contact_name": contact_name,
                                "gender": gender,
                                "phone": phone,
                                "order_status": order_status,
                            },
                        )
                        st.success(f"表单创建成功：{result.get('form_id')}")
                    except ApiClientError as exc:
                        st.error(exc.message)

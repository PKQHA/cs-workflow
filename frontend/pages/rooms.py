from __future__ import annotations

import streamlit as st

from frontend.services.api_client import ApiClientError, BackendApiClient


def render_rooms_page(api_client: BackendApiClient) -> None:
    st.header("房间查询")
    col1, col2, col3 = st.columns(3)
    capacity_type = col1.selectbox("容量维度", ["全部", "单人间", "多人间"])
    room_status = col2.selectbox("房态", ["全部", "空房", "已住", "已预订"])
    room_category = col3.selectbox("房型层级", ["全部", "普通房", "特殊房"])

    try:
        rooms = api_client.get(
            "/api/rooms",
            {
                "capacity_type": None if capacity_type == "全部" else capacity_type,
                "room_status": None if room_status == "全部" else room_status,
                "room_category": None if room_category == "全部" else room_category,
            },
        )
    except ApiClientError as exc:
        st.error(exc.message)
        return

    st.write(f"共 {len(rooms or [])} 间房")
    for room in rooms or []:
        with st.container(border=True):
            st.write(
                f"房号：{room.get('room_number')} | 房型：{room.get('room_name')} | "
                f"价格：{room.get('price_per_day')} | 房态：{room.get('status')}"
            )
            st.caption(f"图片资源：{room.get('image_url')}")
            if room.get("status") in {"已住", "已预订"}:
                if st.button("改为空房", key=f"release_{room.get('room_number')}"):
                    try:
                        api_client.post(
                            "/api/rooms/update-status",
                            {"room_number": room.get("room_number"), "target_status": "空房"},
                        )
                        st.success("房态修改成功")
                        st.rerun()
                    except ApiClientError as exc:
                        st.error(exc.message)

def classify_complaint_type(text: str) -> str:
    if any(word in text for word in ("脏", "卫生", "床单", "异味")):
        return "卫生"
    if any(word in text for word in ("态度", "前台", "客服", "骂", "冷漠")):
        return "服务态度"
    if any(word in text for word in ("坏", "空调", "热水", "电梯", "设施")):
        return "设施故障"
    if any(word in text for word in ("吵", "噪音", "施工", "隔音")):
        return "噪音"
    if any(word in text for word in ("退款", "退钱", "赔", "扣款")):
        return "退款"
    return "服务态度"


def judge_severity(text: str, complaint_type: str) -> str:
    severe_words = ("受伤", "报警", "媒体", "曝光", "全部退款", "严重", "无法入住")
    medium_words = ("很差", "多次", "整晚", "拒绝", "投诉", "退款")
    if any(word in text for word in severe_words):
        return "重度"
    if complaint_type == "退款" or any(word in text for word in medium_words):
        return "中度"
    return "轻度"

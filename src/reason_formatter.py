from __future__ import annotations

from typing import Any


REASON_TRANSLATIONS = {
    "support proximity not confirmed": "ราคาใกล้แนวรับยังไม่ชัด",
    "volume confirmation missing": "ปริมาณซื้อยังไม่ยืนยัน",
    "BTC Guard WARNING": "BTC ตลาดใหญ่ยังไม่แข็งแรง",
    "BTC Guard DANGER": "BTC ตลาดใหญ่มีความเสี่ยงสูง",
    "RSI not in entry zone": "RSI ยังไม่อยู่ในโซนเข้า",
    "RSI still weak": "RSI ยังเสียทรง",
    "price below trend": "ราคายังต่ำกว่าแนวโน้มหลัก",
    "data error": "ข้อมูลไม่ครบหรือดึงข้อมูลไม่สำเร็จ",
    "no confirmed bounce": "ยังไม่มีสัญญาณเด้งกลับที่ชัดเจน",
    "sell volume still strong": "แรงขายยังมาก",
}

BTC_GUARD_TRANSLATIONS = {
    "SAFE": "BTC ตลาดใหญ่ยังปลอดภัย",
    "WARNING": "BTC ตลาดใหญ่เริ่มอ่อนแรง",
    "DANGER": "BTC ตลาดใหญ่มีความเสี่ยงสูง",
}

ACTION_TRANSLATIONS = {
    "WAIT / NO TRADE": "รอดูต่อ ยังไม่ควรเข้า",
    "BUY LEG1": "เปิดไม้แรก",
    "STRONG BUY": "จังหวะเข้าที่หาได้ยาก",
    "TAKE PROFIT 50": "ทยอยปิดกำไร 50%",
    "TAKE PROFIT ALL": "ปิดกำไรทั้งหมด",
}


def translate_reason(reason: Any) -> str:
    text = str(reason)
    if text in REASON_TRANSLATIONS:
        return REASON_TRANSLATIONS[text]
    if text.startswith("BTC Guard "):
        return BTC_GUARD_TRANSLATIONS.get(text.replace("BTC Guard ", ""), "สถานะ BTC ยังไม่สนับสนุนการเข้า")
    return "เงื่อนไขนี้ยังไม่ผ่าน"


def format_reason_lines(reasons: list[Any] | tuple[Any, ...] | None) -> list[str]:
    if not reasons:
        return ["-"]
    lines: list[str] = []
    for reason in reasons:
        lines.append(f"• {reason}")
        lines.append(translate_reason(reason))
    return lines


def format_action_lines(action: Any) -> list[str]:
    action_text = str(action or "-")
    thai = ACTION_TRANSLATIONS.get(action_text)
    if thai:
        return [f"Action: {action_text}", thai]
    return [f"Action: {action_text}"]


def format_btc_guard(status: Any) -> str:
    status_text = str(status or "-")
    thai = BTC_GUARD_TRANSLATIONS.get(status_text)
    if thai:
        return f"{status_text}\n({thai})"
    return status_text


def rolling_drop_translation(event_type: Any) -> str:
    text = str(event_type or "")
    try:
        threshold = text.rsplit("_", 1)[1]
    except IndexError:
        return "ราคาลงสะสมในรอบ 24 ชั่วโมง"
    return f"ลงมากกว่า {threshold}%"


def confidence_text(confidence: Any) -> str:
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return "ความมั่นใจ"
    if value >= 97:
        return "ความมั่นใจสูงมาก"
    if value >= 80:
        return "ความมั่นใจสูง"
    return "ความมั่นใจปานกลาง"

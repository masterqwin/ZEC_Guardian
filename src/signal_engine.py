from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Signal:
    grade: str
    score: int
    confidence: int
    action: str
    reasons: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)


REQUIRED_KEYS = ["rsi14", "ema20", "ema50", "atr14", "volume_average20", "price_change_24h_percent"]


def _missing(indicators: dict[str, Any]) -> list[str]:
    return [key for key in REQUIRED_KEYS if indicators.get(key) is None]


def evaluate_signal(
    zec_price: float,
    zec_volume: float,
    zec_indicators: dict[str, Any],
    btc_indicators: dict[str, Any],
    data_error: str | None = None,
) -> Signal:
    if data_error:
        return Signal("C", 0, 0, "ห้ามเข้า", [data_error], ["data_error"])

    missing = _missing(zec_indicators) + [f"btc_{key}" for key in _missing(btc_indicators)]
    if missing:
        return Signal("C", 0, 0, "ห้ามเข้า", [f"ข้อมูลไม่ครบ: {', '.join(missing)}"], ["incomplete_data"])

    score = 50
    reasons: list[str] = []
    risk_flags: list[str] = []

    rsi14 = float(zec_indicators["rsi14"])
    ema20 = float(zec_indicators["ema20"])
    ema50 = float(zec_indicators["ema50"])
    atr14 = float(zec_indicators["atr14"])
    avg_volume = float(zec_indicators["volume_average20"])
    change_24h = float(zec_indicators["price_change_24h_percent"])
    btc_change_24h = float(btc_indicators["price_change_24h_percent"])
    btc_rsi = float(btc_indicators["rsi14"])

    near_ema = abs(zec_price - ema20) / zec_price <= 0.035 or abs(zec_price - ema50) / zec_price <= 0.045
    if rsi14 <= 35:
        score += 18
        reasons.append("RSI ต่ำ มีโซนช้อน")
    elif 35 < rsi14 <= 45 and change_24h > -8:
        score += 10
        reasons.append("RSI เริ่มฟื้น")
    elif rsi14 >= 68:
        score -= 12
        risk_flags.append("RSI ร้อนเกินไป")

    if near_ema:
        score += 14
        reasons.append("ราคาอยู่ใกล้ EMA สำคัญ")
    elif zec_price < ema50 - (1.5 * atr14):
        score -= 18
        risk_flags.append("ZEC หลุดแรงจาก EMA50")

    if zec_volume <= avg_volume * 0.9 and change_24h <= 0:
        score += 10
        reasons.append("volume ขายอ่อนลง")
    elif zec_volume >= avg_volume * 1.5 and change_24h < -4:
        score -= 22
        risk_flags.append("volume ขายแรง")

    if btc_change_24h <= -4 or btc_rsi < 30:
        score -= 35
        risk_flags.append("BTC Guard เสีย")
    else:
        score += 10
        reasons.append("BTC Guard ยังไม่พัง")

    if change_24h <= -9:
        score -= 18
        risk_flags.append("ZEC ย่อลึกใน 24 ชั่วโมง")
    elif -6 <= change_24h <= 1:
        score += 8
        reasons.append("ราคาอยู่ในโซนย่อที่ยังควบคุมได้")

    score = max(0, min(100, int(round(score))))

    hard_c = any(flag in risk_flags for flag in ["BTC Guard เสีย", "volume ขายแรง", "ZEC หลุดแรงจาก EMA50"])
    if hard_c or score < 45:
        grade = "C"
        action = "ห้ามเข้า"
    elif score >= 70 and (rsi14 <= 45) and near_ema and not risk_flags:
        grade = "A"
        action = "เข้าได้ / ช้อนคุ้ม"
    else:
        grade = "B"
        action = "รอ"

    confidence = score if grade != "C" else min(score, 45)
    return Signal(grade, score, confidence, action, reasons or ["ยังไม่มี edge ชัด"], risk_flags)


from __future__ import annotations

from typing import Any


def label_from_score(score: int, btc_status: str = "SAFE") -> str:
    if btc_status == "DANGER":
        return "DANGER"
    if score >= 97:
        return "SS_PLUS"
    if score >= 95:
        return "STRONG_ENTRY"
    if score >= 85:
        return "ENTRY"
    if score >= 70:
        return "NEAR_ENTRY"
    return "WAIT"


def evaluate_entry_score(price_thb: float, indicators: dict[str, Any], btc_guard: dict[str, Any], data_ok: bool = True) -> dict[str, Any]:
    score = 50
    reasons: list[str] = []
    blockers: list[str] = []
    components: dict[str, int] = {}

    if not data_ok:
        return {"entry_score": 0, "components": {}, "reasons": [], "blockers": ["data quality incomplete"], "label": "DANGER"}

    rsi = indicators.get("rsi14")
    if rsi is not None and rsi <= 35:
        components["rsi_recovery"] = 18
        reasons.append("RSI low/recovery zone")
    elif rsi is not None and rsi <= 45:
        components["rsi_recovery"] = 12
        reasons.append("RSI starts recovering")
    else:
        components["rsi_recovery"] = -5
        blockers.append("RSI not in entry zone")

    ema20 = indicators.get("ema20")
    ema50 = indicators.get("ema50")
    near_ema = bool(price_thb and ((ema20 and abs(price_thb - ema20) / price_thb <= 0.04) or (ema50 and abs(price_thb - ema50) / price_thb <= 0.06)))
    components["support_proximity"] = 12 if near_ema else -4
    (reasons if near_ema else blockers).append("price near EMA/support" if near_ema else "support proximity not confirmed")

    volume_avg = indicators.get("volume_average20")
    current_volume = indicators.get("current_volume", volume_avg)
    sell_exhaustion = volume_avg and current_volume and current_volume <= volume_avg * 1.05
    components["volume_exhaustion"] = 10 if sell_exhaustion else -4
    (reasons if sell_exhaustion else blockers).append("selling volume exhausted" if sell_exhaustion else "volume confirmation missing")

    drawdown = indicators.get("price_change_24h_percent")
    good_drawdown = drawdown is not None and -10 <= drawdown <= -1
    components["drawdown_quality"] = 10 if good_drawdown else 0
    if good_drawdown:
        reasons.append("recent pullback is tradable")

    btc_status = btc_guard.get("status", "SAFE")
    if btc_status == "SAFE":
        components["btc_guard"] = 10
        reasons.append("BTC Guard SAFE")
    elif btc_status == "WARNING":
        components["btc_guard"] = -8
        blockers.append("BTC Guard WARNING")
    else:
        components["btc_guard"] = -40
        blockers.append("BTC Guard DANGER")

    score += sum(components.values())
    score = max(0, min(100, int(round(score))))
    label = label_from_score(score, btc_status)
    if label == "WAIT" and not blockers:
        blockers.append("entry score below threshold")
    return {"entry_score": score, "components": components, "reasons": reasons, "blockers": blockers, "label": label}

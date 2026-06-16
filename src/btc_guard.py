from __future__ import annotations

from typing import Any


def evaluate_btc_guard(btc_snapshot: Any, btc_indicators: dict[str, Any] | None = None) -> dict[str, Any]:
    btc_indicators = btc_indicators or {}
    change_24h = btc_snapshot.get("change_24h_percent") if isinstance(btc_snapshot, dict) else getattr(btc_snapshot, "change_24h_percent", None)
    change_7d = btc_snapshot.get("change_7d_percent") if isinstance(btc_snapshot, dict) else getattr(btc_snapshot, "change_7d_percent", None)
    price = btc_snapshot.get("price_usdt") if isinstance(btc_snapshot, dict) else getattr(btc_snapshot, "price_usdt", None)
    ema50 = btc_indicators.get("ema50")
    ema200 = btc_indicators.get("ema200")
    reasons: list[str] = []
    status = "SAFE"

    if change_24h is not None and change_24h <= -5:
        status = "DANGER"
        reasons.append("BTC 24h <= -5%")
    elif change_24h is not None and change_24h <= -3:
        status = "WARNING"
        reasons.append("BTC 24h <= -3%")

    if change_7d is not None and change_7d <= -8:
        status = "DANGER"
        reasons.append("BTC 7d <= -8%")

    if price and ema200 and price < ema200:
        status = "DANGER"
        reasons.append("BTC below EMA200")
    elif price and ema50 and price < ema50 and (change_24h or 0) < 0 and status == "SAFE":
        status = "WARNING"
        reasons.append("BTC below EMA50 with negative momentum")

    if not reasons:
        reasons.append("BTC market guard is stable")
    return {"status": status, "change_24h": change_24h, "change_7d": change_7d, "reason": "; ".join(reasons)}

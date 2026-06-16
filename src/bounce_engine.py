from __future__ import annotations

from typing import Any


def estimate_bounce_probability(entry_result: dict[str, Any], btc_guard: dict[str, Any]) -> dict[str, Any]:
    probability = int(entry_result.get("entry_score", 0))
    blockers = list(entry_result.get("blockers", []))
    if btc_guard.get("status") == "WARNING":
        probability -= 8
        blockers.append("BTC warning reduces bounce quality")
    elif btc_guard.get("status") == "DANGER":
        probability -= 30
        blockers.append("BTC danger blocks bounce setup")
    probability = max(0, min(100, probability))
    return {"bounce_probability": probability, "model": "model_estimate", "bounce_reason": list(entry_result.get("reasons", [])), "bounce_blockers": blockers}

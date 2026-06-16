from __future__ import annotations

from typing import Any


def estimate_recovery(position: dict[str, Any], profit_state: dict[str, Any] | None, recent_high_thb: float | None = None) -> dict[str, Any]:
    if position.get("total_zec", 0) and profit_state:
        target = profit_state.get("tp50_price") or position.get("average_cost_thb")
        reference = "TP50"
    else:
        target = recent_high_thb
        reference = "recent_high"
    return {
        "recovery_3d": 55,
        "recovery_7d": 65,
        "recovery_14d": 72,
        "target_reference": reference,
        "target_price_thb": target,
        "reason": "Rule-based recovery estimate until enough outcome memory exists",
    }

from __future__ import annotations

from typing import Any

from position_manager import holding_days, recalculate_position


def calculate_profit_state(state: dict[str, Any], current_price_thb: float) -> dict[str, Any]:
    state = recalculate_position(state)
    position = state["position"]
    total_zec = float(position["total_zec"])
    average_cost = float(position["average_cost_thb"])
    total_cost = float(position["total_cost_thb"])
    market_value = round(total_zec * current_price_thb, 2)
    unrealized = round(market_value - total_cost, 2)
    pnl_percent = round((unrealized / total_cost) * 100, 2) if total_cost > 0 else 0
    targets = state.get("targets", {})

    return {
        "current_price_thb": round(float(current_price_thb), 2),
        "total_zec": round(total_zec, 8),
        "total_cost_thb": round(total_cost, 2),
        "market_value_thb": market_value,
        "unrealized_pnl_thb": unrealized,
        "unrealized_pnl_percent": pnl_percent,
        "average_cost_thb": round(average_cost, 2),
        "tp50_price": round(average_cost * (1 + float(targets.get("tp50_percent", 5)) / 100), 2) if total_zec > 0 else 0,
        "tp100_price": round(average_cost * (1 + float(targets.get("tp100_percent", 10)) / 100), 2) if total_zec > 0 else 0,
        "tp3_price": round(average_cost * (1 + float(targets.get("tp3_percent", 15)) / 100), 2) if total_zec > 0 else 0,
        "amount_to_sell_50_percent": round(total_zec * 0.5, 8),
        "remaining_after_tp50": round(total_zec * 0.5, 8),
        "holding_days": holding_days(state),
    }


def action_from_profit(profit_state: dict[str, Any], signal_grade: str) -> str:
    if profit_state["total_zec"] <= 0:
        return "WAIT"
    if signal_grade == "C":
        return "RISK HOLD"
    current = float(profit_state["current_price_thb"])
    if current >= float(profit_state["tp100_price"]):
        return "TAKE PROFIT ALL"
    if current >= float(profit_state["tp50_price"]):
        return "TAKE PROFIT 50%"
    return "HOLD"

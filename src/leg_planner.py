from __future__ import annotations

from typing import Any

from position_manager import recalculate_position


def plan_next_leg(state: dict[str, Any], signal_grade: str, suggested_buy_price_thb: float, suggested_buy_price_usdt: float | None = None) -> dict[str, Any]:
    state = recalculate_position(state)
    position = state["position"]
    risk = state.get("risk", {})
    lots = position.get("lots", [])
    open_lots = [lot for lot in lots if lot.get("status") == "OPEN" and float(lot.get("remaining_zec", 0)) > 0]
    next_leg_number = len(lots) + 1
    max_legs = int(risk.get("max_legs", 4))
    suggested_zec = float(risk.get("zec_per_leg", 1))
    cash_required = round(suggested_zec * suggested_buy_price_thb, 2)
    starting_capital = float(state.get("cash_thb", 0)) + float(position.get("total_cost_thb", 0))
    reserve = round(starting_capital * (float(risk.get("reserve_percent", 25)) / 100), 2)
    spendable_cash = round(float(state.get("cash_thb", 0)) - reserve, 2)
    can_buy = True
    reason = "OK"

    if signal_grade != "A":
        can_buy = False
        reason = "NO_SIGNAL_A"
    elif not open_lots:
        can_buy = False
        reason = "NO_POSITION"
    elif next_leg_number > max_legs:
        can_buy = False
        reason = "MAX_LEGS_REACHED"
    elif cash_required > spendable_cash:
        can_buy = False
        reason = "INSUFFICIENT CASH"

    new_total_zec = round(float(position["total_zec"]) + suggested_zec, 8)
    new_total_cost = round(float(position["total_cost_thb"]) + cash_required, 2)
    new_average = round(new_total_cost / new_total_zec, 2) if new_total_zec > 0 else 0

    return {
        "next_leg_id": f"L{next_leg_number}",
        "suggested_buy_price_thb": round(float(suggested_buy_price_thb), 2),
        "suggested_buy_price_usdt": round(float(suggested_buy_price_usdt or 0), 4),
        "suggested_zec": suggested_zec,
        "new_total_zec": new_total_zec,
        "new_total_cost_thb": new_total_cost,
        "new_average_cost_thb": new_average,
        "new_tp50": round(new_average * 1.05, 2),
        "new_tp100": round(new_average * 1.10, 2),
        "cash_required": cash_required,
        "cash_after_buy": round(float(state.get("cash_thb", 0)) - cash_required, 2),
        "reserve_thb": reserve,
        "spendable_cash_thb": spendable_cash,
        "can_buy": can_buy,
        "reason": reason,
    }

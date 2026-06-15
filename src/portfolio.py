from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _leg_tp_percent(config: Any, next_leg: int) -> tuple[float, float]:
    table = {
        1: (config.first_leg_tp50_percent, config.first_leg_tp100_percent),
        2: (config.second_leg_tp50_percent, config.second_leg_tp100_percent),
        3: (config.third_leg_tp50_percent, config.third_leg_tp100_percent),
    }
    return table.get(next_leg, table[3])


def _open_legs(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        leg
        for leg in state.get("position", {}).get("legs", [])
        if leg.get("status", "open") == "open" and float(leg.get("quantity_zec", 0)) > 0
    ]


def average_cost_usdt(legs: list[dict[str, Any]]) -> float:
    total_qty = sum(float(leg["quantity_zec"]) for leg in legs)
    if total_qty <= 0:
        return 0.0
    total_cost = sum(float(leg["quantity_zec"]) * float(leg["entry_price_usdt"]) for leg in legs)
    return total_cost / total_qty


def holding_days(legs: list[dict[str, Any]], now: datetime | None = None) -> int:
    if not legs:
        return 0
    now = now or datetime.now(timezone.utc)
    opened_times = []
    for leg in legs:
        raw = leg.get("opened_at")
        if raw:
            opened_times.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    if not opened_times:
        return 0
    return max(0, (now - min(opened_times)).days)


def build_trade_plan(state: dict[str, Any], signal_grade: str, price_usdt: float, config: Any) -> dict[str, Any]:
    price_thb = price_usdt * config.usd_thb_rate
    open_legs = _open_legs(state)
    next_leg = len(open_legs) + 1
    tp50_percent, tp100_percent = _leg_tp_percent(config, next_leg)

    if not open_legs:
        return {
            "mode": "no_position",
            "action": "เข้าไม้ 1" if signal_grade == "A" else "รอ",
            "buy_zone_usdt": round(price_usdt, 4),
            "buy_zone_thb": round(price_thb, 2),
            "quantity_zec": config.zec_per_leg,
            "tp50_usdt": round(price_usdt * (1 + tp50_percent / 100), 4),
            "tp100_usdt": round(price_usdt * (1 + tp100_percent / 100), 4),
            "tp50_thb": round(price_thb * (1 + tp50_percent / 100), 2),
            "tp100_thb": round(price_thb * (1 + tp100_percent / 100), 2),
            "reserved_capital_thb": round(config.capital_thb * config.reserve_percent / 100, 2),
        }

    avg_cost = average_cost_usdt(open_legs)
    total_qty = sum(float(leg["quantity_zec"]) for leg in open_legs)
    unrealized_pnl_usdt = (price_usdt - avg_cost) * total_qty
    unrealized_pnl_percent = ((price_usdt - avg_cost) / avg_cost) * 100 if avg_cost else 0
    held_days = holding_days(open_legs)

    plan: dict[str, Any] = {
        "mode": "has_position",
        "action": "ถือเฉย ๆ" if signal_grade == "B" else "ห้ามเพิ่มไม้" if signal_grade == "C" else "พิจารณาไม้ถัดไป",
        "average_cost_usdt": round(avg_cost, 4),
        "average_cost_thb": round(avg_cost * config.usd_thb_rate, 2),
        "quantity_zec": round(total_qty, 8),
        "unrealized_pnl_usdt": round(unrealized_pnl_usdt, 4),
        "unrealized_pnl_thb": round(unrealized_pnl_usdt * config.usd_thb_rate, 2),
        "unrealized_pnl_percent": round(unrealized_pnl_percent, 2),
        "holding_days": held_days,
        "tp50_usdt": round(avg_cost * (1 + tp50_percent / 100), 4),
        "tp100_usdt": round(avg_cost * (1 + tp100_percent / 100), 4),
        "tp50_thb": round(avg_cost * config.usd_thb_rate * (1 + tp50_percent / 100), 2),
        "tp100_thb": round(avg_cost * config.usd_thb_rate * (1 + tp100_percent / 100), 2),
    }

    if signal_grade == "A" and price_usdt < avg_cost and next_leg <= 3:
        new_qty = total_qty + config.zec_per_leg
        new_avg = ((avg_cost * total_qty) + (price_usdt * config.zec_per_leg)) / new_qty
        plan.update(
            {
                "action": f"แนะนำไม้ {next_leg}",
                "next_average_cost_usdt": round(new_avg, 4),
                "next_average_cost_thb": round(new_avg * config.usd_thb_rate, 2),
                "next_tp50_usdt": round(new_avg * (1 + tp50_percent / 100), 4),
                "next_tp100_usdt": round(new_avg * (1 + tp100_percent / 100), 4),
            }
        )
    return plan


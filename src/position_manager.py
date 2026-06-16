from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


DEFAULT_STATE_V2: dict[str, Any] = {
    "schema_version": 2,
    "mode": "WAIT",
    "cash_thb": 50000,
    "realized_profit_thb": 0,
    "position": {
        "total_zec": 0,
        "total_cost_thb": 0,
        "average_cost_thb": 0,
        "lots": [],
    },
    "targets": {
        "tp50_percent": 5,
        "tp100_percent": 10,
        "tp3_percent": 15,
    },
    "risk": {
        "reserve_percent": 25,
        "max_legs": 4,
        "zec_per_leg": 1,
    },
    "last_action": None,
    "updated_at": None,
    "alerts": {},
    "daily_summary": {},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state(capital_thb: float = 50000, reserve_percent: float = 25, zec_per_leg: float = 1) -> dict[str, Any]:
    state = deepcopy(DEFAULT_STATE_V2)
    state["cash_thb"] = float(capital_thb)
    state["risk"]["reserve_percent"] = float(reserve_percent)
    state["risk"]["zec_per_leg"] = float(zec_per_leg)
    return state


def migrate_state(raw_state: dict[str, Any] | None, capital_thb: float = 50000, reserve_percent: float = 25, zec_per_leg: float = 1) -> dict[str, Any]:
    if not raw_state:
        return default_state(capital_thb, reserve_percent, zec_per_leg)

    if "cash_thb" in raw_state and "lots" in raw_state.get("position", {}):
        state = deepcopy(DEFAULT_STATE_V2)
        state.update(raw_state)
        state["position"] = {**DEFAULT_STATE_V2["position"], **raw_state.get("position", {})}
        state["targets"] = {**DEFAULT_STATE_V2["targets"], **raw_state.get("targets", {})}
        state["risk"] = {**DEFAULT_STATE_V2["risk"], **raw_state.get("risk", {})}
        state["alerts"] = raw_state.get("alerts", {})
        state["daily_summary"] = raw_state.get("daily_summary", {})
        return recalculate_position(state)

    state = default_state(capital_thb, reserve_percent, zec_per_leg)
    state["alerts"] = raw_state.get("alerts", {})
    state["daily_summary"] = raw_state.get("daily_summary", {})
    legacy_legs = raw_state.get("position", {}).get("legs", [])
    lots = []
    for index, leg in enumerate(legacy_legs, start=1):
        if leg.get("status", "open").upper() != "OPEN" and leg.get("status", "open") != "open":
            continue
        quantity = float(leg.get("quantity_zec", 0))
        if quantity <= 0:
            continue
        entry_price_thb = float(leg.get("entry_price_thb") or (float(leg.get("entry_price_usdt", 0)) * 32.5))
        lots.append(
            {
                "lot_id": f"L{index}",
                "entry_price_thb": entry_price_thb,
                "entry_price_usdt": float(leg.get("entry_price_usdt", 0)),
                "initial_zec": quantity,
                "remaining_zec": quantity,
                "cost_thb": round(quantity * entry_price_thb, 2),
                "opened_at": leg.get("opened_at") or now_iso(),
                "status": "OPEN",
            }
        )
    state["position"]["lots"] = lots
    return recalculate_position(state)


def recalculate_position(state: dict[str, Any]) -> dict[str, Any]:
    lots = state.setdefault("position", {}).setdefault("lots", [])
    open_lots = []
    for lot in lots:
        remaining = round(float(lot.get("remaining_zec", 0)), 8)
        lot["remaining_zec"] = remaining
        lot["cost_thb"] = round(remaining * float(lot.get("entry_price_thb", 0)), 2)
        lot["status"] = "OPEN" if remaining > 0 else "CLOSED"
        if remaining > 0:
            open_lots.append(lot)

    total_zec = round(sum(float(lot["remaining_zec"]) for lot in open_lots), 8)
    total_cost = round(sum(float(lot["remaining_zec"]) * float(lot["entry_price_thb"]) for lot in open_lots), 2)
    average = round(total_cost / total_zec, 2) if total_zec > 0 else 0

    state["position"]["total_zec"] = total_zec
    state["position"]["total_cost_thb"] = total_cost
    state["position"]["average_cost_thb"] = average
    state["mode"] = "POSITION" if total_zec > 0 else "WAIT"
    state["updated_at"] = now_iso()
    return state


def next_lot_id(state: dict[str, Any]) -> str:
    lots = state.get("position", {}).get("lots", [])
    return f"L{len(lots) + 1}"


def buy_lot(state: dict[str, Any], zec: float, price_thb: float, price_usdt: float, timestamp: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if zec <= 0 or price_thb <= 0:
        raise ValueError("Buy quantity and price must be positive")
    state = recalculate_position(state)
    lot_id = next_lot_id(state)
    cost = round(zec * price_thb, 2)
    lot = {
        "lot_id": lot_id,
        "entry_price_thb": float(price_thb),
        "entry_price_usdt": float(price_usdt),
        "initial_zec": float(zec),
        "remaining_zec": float(zec),
        "cost_thb": cost,
        "opened_at": timestamp or now_iso(),
        "status": "OPEN",
    }
    state["position"]["lots"].append(lot)
    state["cash_thb"] = round(float(state.get("cash_thb", 0)) - cost, 2)
    state["last_action"] = {"type": "BUY", "lot_id": lot_id, "zec": float(zec), "price_thb": float(price_thb), "timestamp": timestamp or now_iso()}
    return recalculate_position(state), lot


def sell_zec(state: dict[str, Any], zec_to_sell: float, price_thb: float, price_usdt: float, sell_percent: float | None = None, timestamp: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if zec_to_sell <= 0 or price_thb <= 0:
        raise ValueError("Sell quantity and price must be positive")
    state = recalculate_position(state)
    available = float(state["position"]["total_zec"])
    if zec_to_sell > available + 1e-8:
        raise ValueError("Cannot sell more ZEC than the current position")

    remaining_to_sell = zec_to_sell
    cost_basis = 0.0
    reductions = []
    for lot in state["position"]["lots"]:
        remaining = float(lot.get("remaining_zec", 0))
        if remaining <= 0 or remaining_to_sell <= 0:
            continue
        sold_from_lot = min(remaining, remaining_to_sell)
        lot["remaining_zec"] = round(remaining - sold_from_lot, 8)
        cost_piece = sold_from_lot * float(lot["entry_price_thb"])
        cost_basis += cost_piece
        remaining_to_sell = round(remaining_to_sell - sold_from_lot, 8)
        reductions.append({"lot_id": lot["lot_id"], "zec_sold": round(sold_from_lot, 8), "cost_basis_thb": round(cost_piece, 2)})

    proceeds = round(zec_to_sell * price_thb, 2)
    realized = round(proceeds - cost_basis, 2)
    state["cash_thb"] = round(float(state.get("cash_thb", 0)) + proceeds, 2)
    state["realized_profit_thb"] = round(float(state.get("realized_profit_thb", 0)) + realized, 2)
    state["last_action"] = {"type": "SELL", "zec": round(zec_to_sell, 8), "price_thb": float(price_thb), "timestamp": timestamp or now_iso()}
    state = recalculate_position(state)
    trade = {
        "timestamp": timestamp or now_iso(),
        "type": "SELL",
        "zec_sold": round(zec_to_sell, 8),
        "sell_percent": sell_percent,
        "price_thb": float(price_thb),
        "price_usdt": float(price_usdt),
        "proceeds_thb": proceeds,
        "realized_profit_thb": realized,
        "lot_reductions": reductions,
        "position_after": deepcopy(state["position"]),
    }
    return state, trade


def sell_percent(state: dict[str, Any], percent: float, price_thb: float, price_usdt: float, timestamp: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if percent <= 0 or percent > 100:
        raise ValueError("Sell percent must be between 0 and 100")
    state = recalculate_position(state)
    zec_to_sell = round(float(state["position"]["total_zec"]) * (percent / 100), 8)
    return sell_zec(state, zec_to_sell, price_thb, price_usdt, sell_percent=percent, timestamp=timestamp)


def sell_all(state: dict[str, Any], price_thb: float, price_usdt: float, timestamp: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    state = recalculate_position(state)
    return sell_zec(state, float(state["position"]["total_zec"]), price_thb, price_usdt, sell_percent=100, timestamp=timestamp)


def holding_days(state: dict[str, Any], now: datetime | None = None) -> int:
    open_dates = []
    for lot in state.get("position", {}).get("lots", []):
        if lot.get("status") != "OPEN" or float(lot.get("remaining_zec", 0)) <= 0:
            continue
        raw = lot.get("opened_at")
        if raw:
            open_dates.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    if not open_dates:
        return 0
    now = now or datetime.now(timezone.utc)
    return max(0, (now - min(open_dates)).days)

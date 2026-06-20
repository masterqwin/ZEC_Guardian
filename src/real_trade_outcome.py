from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from storage import DEFAULT_MEMORY_BOOK, DEFAULT_OUTCOME_HISTORY, read_json, upsert_outcome_history, write_json


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def calculate_completed_outcome(signal_id: str, trades: list[dict[str, Any]]) -> dict[str, Any] | None:
    matching = [trade for trade in trades if trade.get("signal_id") == signal_id]
    buys = [trade for trade in matching if trade.get("action") == "BUY"]
    sells = [trade for trade in matching if str(trade.get("action", "")).startswith("SELL")]
    if not buys or not any(trade.get("action") == "SELL_ALL" for trade in sells):
        return None

    bought_zec = sum(float(trade.get("zec_amount", 0)) for trade in buys)
    sold_zec = sum(float(trade.get("zec_amount", 0)) for trade in sells)
    if bought_zec <= 0 or sold_zec <= 0:
        return None

    entry_cost_thb = sum(float(trade.get("zec_amount", 0)) * float(trade.get("price_thb", 0)) for trade in buys)
    entry_cost_usdt = sum(float(trade.get("zec_amount", 0)) * float(trade.get("price_usdt", 0)) for trade in buys)
    exit_value_thb = sum(float(trade.get("zec_amount", 0)) * float(trade.get("price_thb", 0)) for trade in sells)
    exit_value_usdt = sum(float(trade.get("zec_amount", 0)) * float(trade.get("price_usdt", 0)) for trade in sells)
    profit_thb = round(exit_value_thb - entry_cost_thb, 2)
    profit_usdt = round(exit_value_usdt - entry_cost_usdt, 4)
    profit_percent = round((profit_thb / entry_cost_thb) * 100, 2) if entry_cost_thb else 0.0
    opened_at = min(_parse_timestamp(str(trade["timestamp"])) for trade in buys)
    closed_at = max(_parse_timestamp(str(trade["timestamp"])) for trade in sells if trade.get("action") == "SELL_ALL")
    holding_hours = round(max(0.0, (closed_at - opened_at).total_seconds() / 3600), 2)

    return {
        "signal_id": signal_id,
        "created_at": opened_at.isoformat(),
        "closed_at": closed_at.isoformat(),
        "signal_type": "REAL_TRADE",
        "result": "WIN" if profit_thb > 0 else "LOSS" if profit_thb < 0 else "BREAKEVEN",
        "result_status": "COMPLETED",
        "zec_amount": round(min(bought_zec, sold_zec), 8),
        "entry_price": round(entry_cost_thb / bought_zec, 2),
        "entry_price_usdt": round(entry_cost_usdt / bought_zec, 4),
        "exit_price": round(exit_value_thb / sold_zec, 2),
        "exit_price_usdt": round(exit_value_usdt / sold_zec, 4),
        "holding_hours": holding_hours,
        "holding_days": round(holding_hours / 24, 2),
        "profit_percent": profit_percent,
        "profit_thb": profit_thb,
        "profit_usdt": profit_usdt,
    }


def build_statistics(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [record for record in outcomes if record.get("signal_type") == "REAL_TRADE" and record.get("result_status") == "COMPLETED"]
    profits = [float(record.get("profit_percent", 0)) for record in completed]
    holding_days = [float(record.get("holding_days", 0)) for record in completed]
    return {
        "total_completed_signals": len(completed),
        "win_count": sum(1 for record in completed if record.get("result") == "WIN"),
        "loss_count": sum(1 for record in completed if record.get("result") == "LOSS"),
        "average_profit_percent": round(sum(profits) / len(profits), 2) if profits else 0.0,
        "average_holding_days": round(sum(holding_days) / len(holding_days), 2) if holding_days else 0.0,
        "best_signal_profit": round(max(profits), 2) if profits else 0.0,
        "worst_signal_profit": round(min(profits), 2) if profits else 0.0,
    }


def complete_signal_outcome(data_dir: str, signal_id: str, trades: list[dict[str, Any]]) -> dict[str, Any] | None:
    outcome = calculate_completed_outcome(signal_id, trades)
    if outcome is None:
        return None
    upsert_outcome_history(data_dir, outcome)
    outcomes = read_json(Path(data_dir) / "outcome_history.json", DEFAULT_OUTCOME_HISTORY).get("outcomes", [])
    memory_book = {**DEFAULT_MEMORY_BOOK, "statistics": build_statistics(outcomes)}
    write_json(Path(data_dir) / "memory_book.json", memory_book)
    return outcome

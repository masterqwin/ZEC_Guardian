from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from storage import DEFAULT_TRADE_JOURNAL, DEFAULT_TRADES, archive_if_needed, read_json, write_json


def append_trade(data_dir: str, trade: dict[str, Any], limit: int = 500) -> None:
    journal_path = Path(data_dir) / "trade_journal.json"
    journal = read_json(journal_path, deepcopy(DEFAULT_TRADE_JOURNAL))
    journal.setdefault("trades", []).append(deepcopy(trade))
    write_json(journal_path, journal)
    archive_if_needed(data_dir, "trade_journal.json", "trades", 5000, "trade_journal")

    path = Path(data_dir) / "trades.json"
    payload = read_json(path, deepcopy(DEFAULT_TRADES))
    trades = payload.setdefault("trades", [])
    trades.append(trade)
    payload["trades"] = trades[-limit:]
    write_json(path, payload)


def buy_trade_record(lot: dict[str, Any], position_after: dict[str, Any], timestamp: str, signal_id: str | None = None) -> dict[str, Any]:
    return {
        "signal_id": signal_id,
        "action": "BUY",
        "timestamp": timestamp,
        "type": "BUY",
        "lot_id": lot["lot_id"],
        "zec_amount": float(lot["initial_zec"]),
        "zec": float(lot["initial_zec"]),
        "price_thb": float(lot["entry_price_thb"]),
        "price_usdt": float(lot["entry_price_usdt"]),
        "cost_thb": float(lot["cost_thb"]),
        "position_after": deepcopy(position_after),
    }


def normalize_sell_trade(trade: dict[str, Any], action: str, signal_id: str | None) -> dict[str, Any]:
    normalized = deepcopy(trade)
    normalized["signal_id"] = signal_id
    normalized["action"] = action
    normalized["zec_amount"] = float(trade.get("zec_sold", 0))
    return normalized


def load_trade_journal(data_dir: str) -> list[dict[str, Any]]:
    payload = read_json(Path(data_dir) / "trade_journal.json", deepcopy(DEFAULT_TRADE_JOURNAL))
    return payload.get("trades", [])

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from storage import DEFAULT_TRADES, read_json, write_json


def append_trade(data_dir: str, trade: dict[str, Any], limit: int = 500) -> None:
    path = Path(data_dir) / "trades.json"
    payload = read_json(path, deepcopy(DEFAULT_TRADES))
    trades = payload.setdefault("trades", [])
    trades.append(trade)
    payload["trades"] = trades[-limit:]
    write_json(path, payload)


def buy_trade_record(lot: dict[str, Any], position_after: dict[str, Any], timestamp: str) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "type": "BUY",
        "lot_id": lot["lot_id"],
        "zec": float(lot["initial_zec"]),
        "price_thb": float(lot["entry_price_thb"]),
        "price_usdt": float(lot["entry_price_usdt"]),
        "cost_thb": float(lot["cost_thb"]),
        "position_after": deepcopy(position_after),
    }

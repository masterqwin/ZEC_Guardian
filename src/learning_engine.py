from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from storage import DEFAULT_LEARNING, read_json, write_json


def build_learning_record(
    timestamp: str,
    price_thb: float | None,
    price_usdt: float | None,
    signal: Any,
    data_source: str | None,
    position_state: dict[str, Any],
    recommended_action: str,
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "price_thb": price_thb,
        "price_usdt": price_usdt,
        "signal": signal.grade,
        "confidence": signal.confidence,
        "reason": list(signal.reasons),
        "risk": list(signal.risk_flags),
        "data_source": data_source,
        "position_state": deepcopy(position_state),
        "recommended_action": recommended_action,
        "outcome_1h": None,
        "outcome_4h": None,
        "outcome_24h": None,
        "outcome_3d": None,
        "outcome_7d": None,
        "max_gain_percent": None,
        "max_drawdown_percent": None,
        "result_status": "PENDING",
    }


def append_learning_record(data_dir: str, record: dict[str, Any], limit: int = 500) -> None:
    path = Path(data_dir) / "learning.json"
    payload = read_json(path, deepcopy(DEFAULT_LEARNING))
    entries = payload.setdefault("learning", [])
    entries.append(record)
    payload["learning"] = entries[-limit:]
    write_json(path, payload)

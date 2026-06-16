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
    entry_score: int | None = None,
    bounce_probability: int | None = None,
    recovery_probability: int | None = None,
    opportunity_score: int | None = None,
    btc_guard: dict[str, Any] | None = None,
    blockers: list[str] | None = None,
    event_type: str | None = None,
    signal_type: str | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "price_thb": price_thb,
        "price_usdt": price_usdt,
        "signal": signal.grade,
        "signal_type": signal_type or signal.grade,
        "confidence": signal.confidence,
        "entry_score": entry_score,
        "bounce_probability": bounce_probability,
        "recovery_probability": recovery_probability,
        "opportunity_score": opportunity_score,
        "btc_guard": btc_guard,
        "reason": list(signal.reasons),
        "blockers": blockers or [],
        "risk": list(signal.risk_flags),
        "data_source": data_source,
        "position_state": deepcopy(position_state),
        "recommended_action": recommended_action,
        "action": recommended_action,
        "event_type": event_type,
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

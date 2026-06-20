from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from storage import DEFAULT_LEARNING, read_json, write_json
from storage import upsert_outcome_history


TRACKED_SIGNALS = {"NEAR_ENTRY", "ENTRY", "STRONG_ENTRY", "SS_PLUS"}


def create_outcome_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("signal_type") not in TRACKED_SIGNALS and record.get("signal") not in TRACKED_SIGNALS:
        return record
    record.setdefault("outcome_1h", None)
    record.setdefault("outcome_4h", None)
    record.setdefault("outcome_24h", None)
    record.setdefault("outcome_3d", None)
    record.setdefault("outcome_7d", None)
    record.setdefault("max_gain_percent", None)
    record.setdefault("max_drawdown_percent", None)
    record.setdefault("hit_5_percent", False)
    record.setdefault("hit_8_percent", False)
    record.setdefault("hit_10_percent", False)
    record["result_status"] = "PENDING"
    return record


def update_pending_outcomes(data_dir: str, current_price_thb: float, now: datetime | None = None) -> int:
    path = Path(data_dir) / "learning.json"
    payload = read_json(path, DEFAULT_LEARNING)
    now = now or datetime.now(timezone.utc)
    updated = 0
    for record in payload.get("learning", []):
        if record.get("result_status") != "PENDING" or not record.get("price_thb"):
            continue
        entry = float(record["price_thb"])
        gain = ((current_price_thb - entry) / entry) * 100
        record["max_gain_percent"] = max(record.get("max_gain_percent") or gain, gain)
        record["max_drawdown_percent"] = min(record.get("max_drawdown_percent") or gain, gain)
        record["hit_5_percent"] = bool(record.get("hit_5_percent") or gain >= 5)
        record["hit_8_percent"] = bool(record.get("hit_8_percent") or gain >= 8)
        record["hit_10_percent"] = bool(record.get("hit_10_percent") or gain >= 10)
        if gain >= 5:
            record["result_status"] = "WIN"
        elif gain <= -5:
            record["result_status"] = "LOSS"
        upsert_outcome_history(
            data_dir,
            {
                "signal_id": record.get("signal_id") or record.get("timestamp"),
                "created_at": record.get("timestamp"),
                "signal_type": record.get("signal_type"),
                "entry_price_thb": record.get("price_thb"),
                "entry_score": record.get("entry_score"),
                "bounce_probability": record.get("bounce_probability"),
                "opportunity_score": record.get("opportunity_score"),
                "outcome_1h": record.get("outcome_1h"),
                "outcome_4h": record.get("outcome_4h"),
                "outcome_24h": record.get("outcome_24h"),
                "outcome_3d": record.get("outcome_3d"),
                "outcome_7d": record.get("outcome_7d"),
                "max_gain_percent": record.get("max_gain_percent"),
                "max_drawdown_percent": record.get("max_drawdown_percent"),
                "hit_5_percent": record.get("hit_5_percent"),
                "hit_8_percent": record.get("hit_8_percent"),
                "hit_10_percent": record.get("hit_10_percent"),
                "result_status": record.get("result_status"),
            },
        )
        updated += 1
    write_json(path, payload)
    return updated

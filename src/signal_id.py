from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from storage import read_json


def _collect_signal_ids(data_dir: str) -> set[str]:
    path = Path(data_dir)
    sources = (
        ("signals.json", "signals"),
        ("signal_history.json", "signals"),
        ("outcome_history.json", "outcomes"),
        ("trade_journal.json", "trades"),
        ("trades.json", "trades"),
    )
    signal_ids: set[str] = set()
    for filename, key in sources:
        payload = read_json(path / filename, {"schema_version": 1, key: []})
        for record in payload.get(key, []):
            signal_id = record.get("signal_id")
            if signal_id:
                signal_ids.add(str(signal_id))
    return signal_ids


def generate_signal_id(data_dir: str, now: datetime | None = None, symbol: str = "ZEC") -> str:
    now = now or datetime.now(timezone.utc)
    date_key = now.strftime("%Y%m%d")
    prefix = f"{symbol.upper()}-{date_key}-"
    sequences = []
    for signal_id in _collect_signal_ids(data_dir):
        if not signal_id.startswith(prefix):
            continue
        try:
            sequences.append(int(signal_id.removeprefix(prefix)))
        except ValueError:
            continue
    return f"{prefix}{max(sequences, default=0) + 1:03d}"


def attach_signal_id(record: dict[str, Any], signal_id: str | None) -> dict[str, Any]:
    if signal_id:
        record["signal_id"] = signal_id
    return record

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from position_manager import DEFAULT_STATE_V2, migrate_state

DEFAULT_STATE = DEFAULT_STATE_V2
DEFAULT_TRADES = {"schema_version": 1, "trades": []}
DEFAULT_SIGNALS = {"schema_version": 1, "signals": []}
DEFAULT_LEARNING = {"schema_version": 1, "learning": []}
DEFAULT_SIGNAL_HISTORY = {"schema_version": 1, "signals": []}
DEFAULT_OUTCOME_HISTORY = {"schema_version": 1, "outcomes": []}
DEFAULT_DAILY_SUMMARY = {"schema_version": 1, "summaries": []}


def ensure_data_files(data_dir: str) -> None:
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    defaults = {
        "state.json": DEFAULT_STATE,
        "trades.json": DEFAULT_TRADES,
        "signals.json": DEFAULT_SIGNALS,
        "learning.json": DEFAULT_LEARNING,
        "signal_history.json": DEFAULT_SIGNAL_HISTORY,
        "outcome_history.json": DEFAULT_OUTCOME_HISTORY,
        "daily_summary.json": DEFAULT_DAILY_SUMMARY,
    }
    for filename, default in defaults.items():
        target = path / filename
        if not target.exists():
            write_json(target, default)


def read_json(path: str | Path, default: dict[str, Any]) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return default.copy()
    with target.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_state(data_dir: str) -> dict[str, Any]:
    return migrate_state(read_json(Path(data_dir) / "state.json", DEFAULT_STATE))


def save_state(data_dir: str, state: dict[str, Any]) -> None:
    write_json(Path(data_dir) / "state.json", state)


def append_signal(data_dir: str, signal_record: dict[str, Any], limit: int = 2000) -> None:
    path = Path(data_dir) / "signals.json"
    payload = read_json(path, DEFAULT_SIGNALS)
    signals = payload.setdefault("signals", [])
    signals.append(signal_record)
    payload["signals"] = signals[-limit:]
    write_json(path, payload)


def _record_year(record: dict[str, Any]) -> str:
    raw = record.get("timestamp") or record.get("created_at") or record.get("date") or "unknown"
    return str(raw)[:4] if str(raw)[:4].isdigit() else "unknown"


def _archive_records(data_dir: str, archive_name: str, key: str, records: list[dict[str, Any]]) -> None:
    archive_dir = Path(data_dir) / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    by_year: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_year.setdefault(_record_year(record), []).append(record)
    for year, items in by_year.items():
        path = archive_dir / f"{archive_name}_{year}.json"
        payload = read_json(path, {"schema_version": 1, key: []})
        payload.setdefault(key, []).extend(items)
        write_json(path, payload)


def archive_if_needed(data_dir: str, filename: str, key: str, active_limit: int, archive_name: str) -> None:
    path = Path(data_dir) / filename
    default = {"schema_version": 1, key: []}
    payload = read_json(path, default)
    records = payload.setdefault(key, [])
    if len(records) <= active_limit:
        return
    overflow = records[:-active_limit]
    payload[key] = records[-active_limit:]
    _archive_records(data_dir, archive_name, key, overflow)
    write_json(path, payload)


def append_signal_history(data_dir: str, record: dict[str, Any]) -> None:
    path = Path(data_dir) / "signal_history.json"
    payload = read_json(path, DEFAULT_SIGNAL_HISTORY)
    payload.setdefault("signals", []).append(record)
    write_json(path, payload)
    archive_if_needed(data_dir, "signal_history.json", "signals", 5000, "signal_history")


def append_outcome_history(data_dir: str, record: dict[str, Any]) -> None:
    path = Path(data_dir) / "outcome_history.json"
    payload = read_json(path, DEFAULT_OUTCOME_HISTORY)
    payload.setdefault("outcomes", []).append(record)
    write_json(path, payload)
    archive_if_needed(data_dir, "outcome_history.json", "outcomes", 5000, "outcome_history")


def append_daily_summary_history(data_dir: str, record: dict[str, Any]) -> None:
    path = Path(data_dir) / "daily_summary.json"
    payload = read_json(path, DEFAULT_DAILY_SUMMARY)
    payload.setdefault("summaries", []).append(record)
    write_json(path, payload)
    archive_if_needed(data_dir, "daily_summary.json", "summaries", 400, "daily_summary")

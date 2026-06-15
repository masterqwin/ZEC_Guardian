from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from position_manager import DEFAULT_STATE_V2, migrate_state

DEFAULT_STATE = DEFAULT_STATE_V2
DEFAULT_TRADES = {"schema_version": 1, "trades": []}
DEFAULT_SIGNALS = {"schema_version": 1, "signals": []}
DEFAULT_LEARNING = {"schema_version": 1, "learning": []}


def ensure_data_files(data_dir: str) -> None:
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    defaults = {
        "state.json": DEFAULT_STATE,
        "trades.json": DEFAULT_TRADES,
        "signals.json": DEFAULT_SIGNALS,
        "learning.json": DEFAULT_LEARNING,
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


def append_signal(data_dir: str, signal_record: dict[str, Any], limit: int = 200) -> None:
    path = Path(data_dir) / "signals.json"
    payload = read_json(path, DEFAULT_SIGNALS)
    signals = payload.setdefault("signals", [])
    signals.append(signal_record)
    payload["signals"] = signals[-limit:]
    write_json(path, payload)

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from storage import DEFAULT_CAPITAL_HISTORY, read_json, write_json


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def calculate_capital_record(initial_capital_thb: float, capital_thb: float, timestamp: str | None = None) -> dict[str, Any]:
    net_profit = round(capital_thb - initial_capital_thb, 2)
    return_percent = round((net_profit / initial_capital_thb) * 100, 2) if initial_capital_thb else 0.0
    return {
        "timestamp": timestamp or now_iso(),
        "capital_thb": round(capital_thb, 2),
        "net_profit_thb": net_profit,
        "return_percent": return_percent,
    }


def sync_capital(data_dir: str, capital_thb: float, timestamp: str | None = None) -> tuple[dict[str, Any], bool]:
    path = Path(data_dir) / "capital_history.json"
    payload = read_json(path, DEFAULT_CAPITAL_HISTORY)
    payload.setdefault("schema_version", 1)
    payload.setdefault("initial_capital_thb", DEFAULT_CAPITAL_HISTORY["initial_capital_thb"])
    records = payload.setdefault("records", [])
    current_capital = round(float(capital_thb), 2)

    if records and round(float(records[-1].get("capital_thb", 0)), 2) == current_capital:
        return payload, False

    records.append(calculate_capital_record(float(payload["initial_capital_thb"]), current_capital, timestamp=timestamp))
    write_json(path, payload)
    return payload, True


def build_capital_summary(payload: dict[str, Any]) -> dict[str, float]:
    initial = float(payload.get("initial_capital_thb", DEFAULT_CAPITAL_HISTORY["initial_capital_thb"]))
    records = payload.get("records", [])
    values = [float(record.get("capital_thb", initial)) for record in records] or [initial]
    latest = values[-1]
    best = max(values)
    worst_drawdown = round(min(((value - best) / best) * 100 for value in values), 2) if best else 0.0
    current_profit = round(latest - initial, 2)
    total_return = round((current_profit / initial) * 100, 2) if initial else 0.0
    return {
        "latest_capital_thb": round(latest, 2),
        "best_capital_thb": round(best, 2),
        "worst_drawdown_percent": worst_drawdown,
        "current_profit_thb": current_profit,
        "total_return_percent": total_return,
    }


def format_capital_sync_result(payload: dict[str, Any], appended: bool) -> str:
    records = payload.get("records", [])
    initial = float(payload.get("initial_capital_thb", DEFAULT_CAPITAL_HISTORY["initial_capital_thb"]))
    latest = records[-1] if records else calculate_capital_record(initial, initial)
    status = "Capital updated" if appended else "Capital unchanged"
    net_profit = float(latest.get("net_profit_thb", 0))
    return_percent = float(latest.get("return_percent", 0))
    return "\n".join(
        [
            status,
            f"Initial Capital: {initial:,.0f} THB",
            f"Current Capital: {float(latest.get('capital_thb', initial)):,.0f} THB",
            f"Net Profit: {net_profit:+,.0f} THB",
            f"Return: {return_percent:+.2f}%",
        ]
    )

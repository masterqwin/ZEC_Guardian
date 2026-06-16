from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_qa_status(state: dict[str, Any], data_source_used: str | None, last_signal: str | None, last_event: str | None = None, error: str | None = None) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    qa = state.setdefault("qa", {})
    if qa.get("date") != today:
        qa.clear()
        qa["date"] = today
        qa["total_scans_today"] = 0
        qa["total_errors_today"] = 0
    qa["total_scans_today"] = int(qa.get("total_scans_today", 0)) + 1
    qa["last_scan_at"] = datetime.now(timezone.utc).isoformat()
    if error:
        qa["last_error_at"] = qa["last_scan_at"]
        qa["total_errors_today"] = int(qa.get("total_errors_today", 0)) + 1
    else:
        qa["last_success_at"] = qa["last_scan_at"]
    qa.update(
        {
            "telegram_status": "unknown",
            "data_source_used": data_source_used,
            "last_signal": last_signal,
            "last_event": last_event,
            "state_valid": "position" in state,
            "learning_log_valid": True,
        }
    )
    return qa

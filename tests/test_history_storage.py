import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from storage import (
    append_daily_summary_history,
    append_outcome_history,
    append_signal_history,
    archive_if_needed,
    ensure_data_files,
    read_json,
    write_json,
)


def test_history_defaults_created():
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / "history_defaults"
    ensure_data_files(str(data_dir))
    assert (data_dir / "signal_history.json").exists()
    assert (data_dir / "outcome_history.json").exists()
    assert (data_dir / "daily_summary.json").exists()


def test_append_signal_history_writes_useful_signal():
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / "signal_history"
    append_signal_history(str(data_dir), {"timestamp": "2026-01-01T00:00:00+00:00", "signal_type": "ENTRY"})
    payload = read_json(data_dir / "signal_history.json", {})
    assert payload["signals"][0]["signal_type"] == "ENTRY"


def test_append_outcome_history_writes_outcome():
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / "outcome_history"
    append_outcome_history(str(data_dir), {"created_at": "2026-01-01T00:00:00+00:00", "result_status": "PENDING"})
    payload = read_json(data_dir / "outcome_history.json", {})
    assert payload["outcomes"][0]["result_status"] == "PENDING"


def test_append_daily_summary_history_writes_summary():
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / "daily_summary"
    append_daily_summary_history(str(data_dir), {"date": "2026-01-01", "system_status": "RUNNING"})
    payload = read_json(data_dir / "daily_summary.json", {})
    assert payload["summaries"][0]["system_status"] == "RUNNING"


def test_signal_history_archives_over_5000_records():
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / "signal_archive"
    records = [{"timestamp": "2026-01-01T00:00:00+00:00", "signal_type": "ENTRY", "i": index} for index in range(5001)]
    write_json(data_dir / "signal_history.json", {"schema_version": 1, "signals": records})
    archive_if_needed(str(data_dir), "signal_history.json", "signals", 5000, "signal_history")
    payload = read_json(data_dir / "signal_history.json", {})
    assert len(payload["signals"]) == 5000
    assert (data_dir / "archive" / "signal_history_2026.json").exists()


def test_daily_summary_archives_over_400_records():
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / "daily_archive"
    records = [{"date": f"2026-01-{(index % 28) + 1:02d}", "system_status": "RUNNING"} for index in range(401)]
    write_json(data_dir / "daily_summary.json", {"schema_version": 1, "summaries": records})
    archive_if_needed(str(data_dir), "daily_summary.json", "summaries", 400, "daily_summary")
    payload = read_json(data_dir / "daily_summary.json", {})
    assert len(payload["summaries"]) == 400
    assert (data_dir / "archive" / "daily_summary_2026.json").exists()

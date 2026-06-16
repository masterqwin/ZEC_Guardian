import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signal_outcome_tracker import create_outcome_record, update_pending_outcomes
from storage import read_json, write_json


def test_signal_outcome_record_created_for_entry():
    record = create_outcome_record({"signal_type": "ENTRY", "price_thb": 100})
    assert record["result_status"] == "PENDING"


def test_pending_outcomes_update_correctly():
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / "outcomes"
    data_dir.mkdir(parents=True, exist_ok=True)
    write_json(data_dir / "learning.json", {"schema_version": 1, "learning": [{"signal_type": "ENTRY", "price_thb": 100, "result_status": "PENDING"}]})
    updated = update_pending_outcomes(str(data_dir), 106)
    payload = read_json(data_dir / "learning.json", {})
    assert updated == 1
    assert payload["learning"][0]["result_status"] == "WIN"


def test_pending_outcomes_upsert_does_not_duplicate_signal_id():
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / "outcome_no_duplicate"
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        data_dir / "learning.json",
        {
            "schema_version": 1,
            "learning": [
                {
                    "timestamp": "signal-1",
                    "signal_type": "ENTRY",
                    "price_thb": 100,
                    "entry_score": 85,
                    "bounce_probability": 80,
                    "opportunity_score": 75,
                    "result_status": "PENDING",
                }
            ],
        },
    )

    update_pending_outcomes(str(data_dir), 101)
    update_pending_outcomes(str(data_dir), 102)

    payload = read_json(data_dir / "outcome_history.json", {})
    assert len(payload["outcomes"]) == 1
    assert payload["outcomes"][0]["signal_id"] == "signal-1"

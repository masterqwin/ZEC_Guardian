import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signal_id import generate_signal_id
from storage import write_json


def _data_dir(name):
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / name
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def test_signal_id_starts_at_one():
    data_dir = _data_dir("signal_id_first")
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)

    assert generate_signal_id(str(data_dir), now) == "ZEC-20260620-001"


def test_signal_id_does_not_duplicate_existing_ids():
    data_dir = _data_dir("signal_id_unique")
    write_json(
        data_dir / "signals.json",
        {"schema_version": 1, "signals": [{"signal_id": "ZEC-20260620-001"}]},
    )
    write_json(
        data_dir / "trade_journal.json",
        {"schema_version": 1, "trades": [{"signal_id": "ZEC-20260620-003"}]},
    )
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)

    assert generate_signal_id(str(data_dir), now) == "ZEC-20260620-004"

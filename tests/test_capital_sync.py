import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from capital_sync import calculate_capital_record, sync_capital
from storage import ensure_data_files, read_json


def _data_dir(name):
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / name
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def test_capital_sync_create_default():
    data_dir = _data_dir("capital_default")
    ensure_data_files(str(data_dir))
    payload = read_json(data_dir / "capital_history.json", {})

    assert payload == {"schema_version": 1, "initial_capital_thb": 57000, "records": []}


def test_capital_sync_append():
    data_dir = _data_dir("capital_append")
    payload, appended = sync_capital(str(data_dir), 57400, timestamp="2026-06-17T00:00:00+00:00")

    assert appended is True
    assert payload["initial_capital_thb"] == 57000
    assert payload["records"] == [
        {
            "timestamp": "2026-06-17T00:00:00+00:00",
            "capital_thb": 57400,
            "net_profit_thb": 400,
            "return_percent": 0.7,
        }
    ]


def test_capital_sync_duplicate_not_append():
    data_dir = _data_dir("capital_duplicate")
    sync_capital(str(data_dir), 57400, timestamp="2026-06-17T00:00:00+00:00")
    payload, appended = sync_capital(str(data_dir), 57400, timestamp="2026-06-18T00:00:00+00:00")

    assert appended is False
    assert len(payload["records"]) == 1


def test_profit_calculation():
    record = calculate_capital_record(57000, 57400, timestamp="2026-06-17T00:00:00+00:00")

    assert record["net_profit_thb"] == 400
    assert record["return_percent"] == 0.7

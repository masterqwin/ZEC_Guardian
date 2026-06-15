import sys
import shutil
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from learning_engine import append_learning_record, build_learning_record
from position_manager import default_state
from storage import read_json


def test_learning_log_appends_action_and_position_state():
    tmp_path = Path(__file__).resolve().parents[1] / ".test_tmp" / "learning_engine"
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True)
    signal = SimpleNamespace(grade="B", confidence=48, reasons=["reason"], risk_flags=["risk"])
    state = default_state()
    record = build_learning_record(
        "2026-06-16T00:00:00+00:00",
        17000,
        532.7,
        signal,
        "Kraken",
        state["position"],
        "WAIT / NO TRADE",
    )

    append_learning_record(str(tmp_path), record)
    payload = read_json(tmp_path / "learning.json", {"learning": []})

    assert payload["learning"][0]["recommended_action"] == "WAIT / NO TRADE"
    assert payload["learning"][0]["position_state"]["total_zec"] == 0
    assert payload["learning"][0]["result_status"] == "PENDING"
    shutil.rmtree(tmp_path)

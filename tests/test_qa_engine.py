import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_engine import build_qa_status


def test_qa_engine_reports_system_alive():
    status = build_qa_status({"position": {}, "qa": {}}, "CoinGecko", "WAIT")
    assert status["state_valid"] is True
    assert status["total_scans_today"] == 1

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from daily_summary import build_daily_summary


def test_daily_summary_generated_without_signal():
    text = build_daily_summary({"position": {"total_zec": 0}}, {"qa_status": {"total_scans_today": 1}, "price_thb": 15908})
    assert "SEK Trade Guardian" in text
    assert "ZEC Guardian Mode" in text
    assert "Daily Summary" in text
    assert "System: RUNNING" in text

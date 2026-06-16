import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dashboard import render_text_dashboard


def test_dashboard_smoke_renders_data_without_crash():
    text = render_text_dashboard({"state": {"position": {"total_zec": 0}}, "signals": {"signals": []}})
    assert "ZEC Guardian Dashboard Lite" in text

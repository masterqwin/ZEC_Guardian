import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bounce_engine import estimate_bounce_probability


def test_bounce_engine_returns_model_estimate():
    result = estimate_bounce_probability({"entry_score": 78, "reasons": ["rsi"], "blockers": []}, {"status": "SAFE"})
    assert result["bounce_probability"] == 78
    assert result["model"] == "model_estimate"

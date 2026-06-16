import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from opportunity_engine import evaluate_opportunity


def test_opportunity_engine_reward_risk():
    result = evaluate_opportunity(85, 80, expected_gain_percent=6, expected_drawdown_percent=3)
    assert result["reward_risk_ratio"] == 2
    assert result["opportunity_score"] >= 70

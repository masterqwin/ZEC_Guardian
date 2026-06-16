from __future__ import annotations


def evaluate_opportunity(entry_score: int, bounce_probability: int, expected_gain_percent: float = 6.5, expected_drawdown_percent: float = 3.0) -> dict[str, float | str]:
    reward_risk = round(expected_gain_percent / expected_drawdown_percent, 2) if expected_drawdown_percent > 0 else 0
    score = round((entry_score * 0.5) + (bounce_probability * 0.3) + (min(reward_risk, 3) / 3 * 20))
    if expected_drawdown_percent > 5:
        score -= 10
    score = max(0, min(100, int(score)))
    if score >= 85:
        bias = "TAKE SETUP IF USER CONFIRMS"
    elif score >= 70:
        bias = "WATCH CLOSELY"
    else:
        bias = "WAIT"
    return {
        "opportunity_score": score,
        "expected_gain_percent": expected_gain_percent,
        "expected_drawdown_percent": expected_drawdown_percent,
        "reward_risk_ratio": reward_risk,
        "expected_holding_days_range": "1-7",
        "action_bias": bias,
    }

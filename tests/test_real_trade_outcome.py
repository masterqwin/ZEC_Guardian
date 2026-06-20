import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from real_trade_outcome import build_statistics, calculate_completed_outcome, complete_signal_outcome
from storage import read_json
from trade_journal import append_trade, load_trade_journal


SIGNAL_ID = "ZEC-20260620-001"


def _data_dir(name):
    data_dir = Path(__file__).resolve().parents[1] / ".test_tmp" / name
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _trades():
    return [
        {
            "signal_id": SIGNAL_ID,
            "action": "BUY",
            "zec_amount": 1.5,
            "price_thb": 14765.0,
            "price_usdt": 449.55,
            "timestamp": "2026-06-20T00:00:00+00:00",
        },
        {
            "signal_id": SIGNAL_ID,
            "action": "SELL_ALL",
            "zec_amount": 1.5,
            "price_thb": 15500.0,
            "price_usdt": 472.30,
            "timestamp": "2026-06-22T12:00:00+00:00",
        },
    ]


def test_sell_all_calculates_real_trade_outcome():
    outcome = calculate_completed_outcome(SIGNAL_ID, _trades())

    assert outcome["result"] == "WIN"
    assert outcome["holding_hours"] == 60.0
    assert outcome["holding_days"] == 2.5
    assert outcome["profit_percent"] == 4.98
    assert outcome["profit_thb"] == 1102.5
    assert outcome["profit_usdt"] == 34.125


def test_signal_outcome_update_is_idempotent():
    data_dir = _data_dir("outcome_idempotent")
    for trade in _trades():
        append_trade(str(data_dir), trade)
    trades = load_trade_journal(str(data_dir))

    complete_signal_outcome(str(data_dir), SIGNAL_ID, trades)
    complete_signal_outcome(str(data_dir), SIGNAL_ID, trades)

    outcomes = read_json(data_dir / "outcome_history.json", {"outcomes": []})["outcomes"]
    assert len(outcomes) == 1
    assert outcomes[0]["signal_id"] == SIGNAL_ID


def test_memory_book_contains_summarized_statistics_only():
    data_dir = _data_dir("memory_statistics")
    for trade in _trades():
        append_trade(str(data_dir), trade)

    complete_signal_outcome(str(data_dir), SIGNAL_ID, load_trade_journal(str(data_dir)))
    memory = read_json(data_dir / "memory_book.json", {})

    assert set(memory) == {"schema_version", "statistics"}
    assert memory["statistics"]["total_completed_signals"] == 1
    assert memory["statistics"]["win_count"] == 1
    assert memory["statistics"]["loss_count"] == 0
    assert memory["statistics"]["best_signal_profit"] == 4.98


def test_statistics_include_wins_and_losses():
    stats = build_statistics(
        [
            {"signal_type": "REAL_TRADE", "result_status": "COMPLETED", "result": "WIN", "profit_percent": 5, "holding_days": 2},
            {"signal_type": "REAL_TRADE", "result_status": "COMPLETED", "result": "LOSS", "profit_percent": -3, "holding_days": 1},
        ]
    )

    assert stats == {
        "total_completed_signals": 2,
        "win_count": 1,
        "loss_count": 1,
        "average_profit_percent": 1.0,
        "average_holding_days": 1.5,
        "best_signal_profit": 5.0,
        "worst_signal_profit": -3.0,
    }

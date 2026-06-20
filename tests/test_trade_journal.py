import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from position_manager import buy_lot, default_state
from trade_journal import append_trade, buy_trade_record
from storage import read_json


def test_trade_journal_appends_buy():
    tmp_path = Path(__file__).resolve().parents[1] / ".test_tmp" / "trade_journal"
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True)
    data_dir = str(tmp_path)
    state = default_state()
    state, lot = buy_lot(state, 1, 17000, 532.7, timestamp="2026-06-16T00:00:00+00:00")
    trade = buy_trade_record(lot, state["position"], "2026-06-16T00:00:00+00:00", signal_id="ZEC-20260616-001")

    append_trade(data_dir, trade)
    payload = read_json(tmp_path / "trades.json", {"trades": []})

    assert payload["trades"][0]["type"] == "BUY"
    assert payload["trades"][0]["signal_id"] == "ZEC-20260616-001"
    assert payload["trades"][0]["action"] == "BUY"
    assert payload["trades"][0]["zec_amount"] == 1
    assert payload["trades"][0]["lot_id"] == "L1"
    assert payload["trades"][0]["position_after"]["total_zec"] == 1
    journal = read_json(tmp_path / "trade_journal.json", {"trades": []})
    assert journal["trades"] == payload["trades"]
    shutil.rmtree(tmp_path)

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from daily_summary import build_daily_summary
from telegram_alert import format_signal_message, format_v2_message


def signal(grade, risk_flags=None, confidence=70):
    return SimpleNamespace(
        grade=grade,
        action="raw action",
        confidence=confidence,
        reasons=["reason one"],
        risk_flags=risk_flags or [],
    )


def test_signal_a_without_position_shows_entry_targets():
    plan = {
        "mode": "no_position",
        "action": "entry",
        "buy_zone_usdt": 100,
        "tp50_usdt": 105,
        "tp100_usdt": 107,
    }
    message = format_signal_message(signal("A"), 100, 32.5, plan)
    assert "Buy Zone: 100.0000 USDT" in message
    assert "TP50: 105 USDT" in message
    assert "TP100: 107 USDT" in message
    assert "SEK Trade Guardian" in message
    assert "ZEC Guardian Mode" in message


def test_signal_b_without_position_hides_numeric_targets():
    plan = {
        "mode": "no_position",
        "action": "wait",
        "buy_zone_usdt": 100,
        "tp50_usdt": 105,
        "tp100_usdt": 107,
    }
    message = format_signal_message(signal("B"), 100, 32.5, plan)
    assert "TP50/TP100:" in message
    assert "TP50: 105 USDT" not in message
    assert "TP100: 107 USDT" not in message


def test_signal_c_hides_entry_targets_and_shows_risk():
    plan = {
        "mode": "no_position",
        "action": "wait",
        "buy_zone_usdt": 100,
        "tp50_usdt": 105,
        "tp100_usdt": 107,
    }
    message = format_signal_message(signal("C", ["BTC Guard risk"]), 100, 32.5, plan)
    assert "Action: ห้ามเข้า / งดช้อน" in message
    assert "Buy Zone" not in message
    assert "TP50:" not in message
    assert "TP100:" not in message
    assert "Risk: BTC Guard risk" in message


def test_position_message_shows_position_metrics_and_targets():
    plan = {
        "mode": "has_position",
        "action": "hold",
        "average_cost_usdt": 90,
        "average_cost_thb": 3285,
        "unrealized_pnl_usdt": 10,
        "unrealized_pnl_thb": 365,
        "unrealized_pnl_percent": 11.11,
        "tp50_usdt": 96.3,
        "tp50_thb": 3514.95,
        "tp100_usdt": 98.1,
        "tp100_thb": 3580.65,
        "holding_days": 4,
    }
    message = format_signal_message(signal("B"), 100, 32.5, plan)
    assert "Average Cost: 90.0000 USDT / 3,285.00 THB" in message
    assert "Unrealized PNL: 10.0000 USDT / 365.00 THB (11.11%)" in message
    assert "TP50: 96.3 USDT / 3514.95 THB" in message
    assert "TP100: 98.1 USDT / 3580.65 THB" in message
    assert "Holding Days: 4" in message


def test_v2_wait_mode_does_not_show_tp_numbers():
    message = format_v2_message(
        signal("B"),
        17000,
        532.7,
        "Kraken",
        {"total_zec": 0, "total_cost_thb": 0, "average_cost_thb": 0, "lots": []},
        "WAIT / NO TRADE",
    )

    assert "TP50" not in message
    assert "TP100" not in message
    assert "Action: WAIT / NO TRADE" in message
    assert "รอดูต่อ ยังไม่ควรเข้า" in message


def test_v2_wait_mode_has_bilingual_action_and_reasons():
    message = format_v2_message(
        signal("B"),
        17000,
        532.7,
        "Kraken",
        {"total_zec": 0, "total_cost_thb": 0, "average_cost_thb": 0, "lots": []},
        "WAIT / NO TRADE",
        entry_result={
            "label": "B",
            "entry_score": 56,
            "blockers": ["support proximity not confirmed", "volume confirmation missing"],
        },
        bounce_result={"bounce_probability": 48},
        opportunity_result={"opportunity_score": 57},
        btc_guard={"status": "WARNING"},
    )

    assert "Entry Score: 56" in message
    assert "(คะแนนความน่าสนใจในการเข้า)" in message
    assert "Action: WAIT / NO TRADE" in message
    assert "รอดูต่อ ยังไม่ควรเข้า" in message
    assert "ราคาใกล้แนวรับยังไม่ชัด" in message
    assert "ปริมาณซื้อยังไม่ยืนยัน" in message
    assert "(BTC ตลาดใหญ่เริ่มอ่อนแรง)" in message


def test_v2_position_update_shows_average_cost_and_unrealized_pnl():
    message = format_v2_message(
        signal("B"),
        17600,
        550,
        "Kraken",
        {"total_zec": 1, "total_cost_thb": 16000, "average_cost_thb": 16000, "lots": []},
        "TAKE PROFIT ALL",
        profit_state={
            "total_zec": 1,
            "total_cost_thb": 16000,
            "average_cost_thb": 16000,
            "unrealized_pnl_thb": 1600,
            "unrealized_pnl_percent": 10,
            "tp50_price": 16800,
            "tp100_price": 17600,
            "tp3_price": 18400,
            "amount_to_sell_50_percent": 0.5,
            "holding_days": 2,
        },
    )

    assert "Average Cost: 16,000.00 THB" in message
    assert "Unrealized PNL: 1,600.00 THB (10%)" in message


def test_v2_entry_signal_has_bilingual_targets_and_confidence():
    message = format_v2_message(
        signal("A", confidence=94),
        17000,
        532.7,
        "Kraken",
        {"total_zec": 0, "total_cost_thb": 0, "average_cost_thb": 0, "lots": []},
        "BUY LEG1",
        entry_result={"label": "A", "entry_score": 94, "reasons": ["reason one"]},
        bounce_result={"bounce_probability": 82},
        opportunity_result={"opportunity_score": 88},
        btc_guard={"status": "SAFE"},
    )

    assert "Action: BUY LEG1" in message
    assert "เปิดไม้แรก" in message
    assert "กำไรประมาณ +5%" in message
    assert "กำไรประมาณ +10%" in message
    assert "กำไรประมาณ +15%" in message
    assert "ความมั่นใจสูง" in message


def test_v2_rolling_drop_has_bilingual_event_text():
    message = format_v2_message(
        signal("B"),
        17000,
        532.7,
        "Kraken",
        {"total_zec": 0, "total_cost_thb": 0, "average_cost_thb": 0, "lots": []},
        "WAIT / NO TRADE",
        entry_result={"label": "B", "entry_score": 56, "blockers": ["BTC Guard WARNING"]},
        bounce_result={"bounce_probability": 48},
        opportunity_result={"opportunity_score": 57},
        btc_guard={"status": "WARNING"},
        event={"event_type": "ROLLING_DROP_5", "high_24h": 17908.21, "drop_from_24h_high_percent": -5.07},
    )

    assert "⚠️ ZEC ROLLING 24H DROP" in message
    assert "(ราคาลงสะสมในรอบ 24 ชั่วโมง)" in message
    assert "Event: ROLLING_DROP_5" in message
    assert "(ลงมากกว่า 5%)" in message
    assert "รอดูต่อ ยังไม่ควรเข้า" in message


def test_error_message_has_bilingual_sections():
    message = format_signal_message(
        signal("C"),
        None,
        32.5,
        None,
        error="fetch failed",
        tried_sources=["Binance", "Kraken"],
        final_error="all sources failed",
    )

    assert "❌ ERROR" in message
    assert "Reason:" in message
    assert "สาเหตุ: all sources failed" in message
    assert "Action:" in message
    assert "คำแนะนำ: ห้ามเข้า / งดช้อน" in message
    assert "Risk:" in message
    assert "ความเสี่ยง: data_error" in message


def test_daily_summary_has_bilingual_labels():
    message = build_daily_summary(
        {"position": {"total_zec": 0}},
        {
            "price_thb": 17000,
            "btc_guard": {"status": "WARNING"},
            "signal_label": "WAIT",
            "entry_score": 56,
            "bounce_probability": 48,
            "opportunity_score": 57,
            "qa_status": {"state_valid": True},
        },
    )

    assert "📊 DAILY SUMMARY" in message
    assert "(สรุปประจำวัน)" in message
    assert "Current Price / ราคาปัจจุบัน" in message
    assert "BTC Guard / สถานะตลาดใหญ่" in message
    assert "Position / สถานะการถือเหรียญ" in message

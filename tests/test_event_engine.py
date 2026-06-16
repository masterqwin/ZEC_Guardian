import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from event_engine import detect_events, detect_rolling_drop, should_send_event


def test_price_drop_5_generates_alert_even_if_wait():
    state = {"alerts": {"last_reference_price_thb": 17192}}
    events = detect_events(15908, state, 60, "WAIT")
    assert events[0]["event_type"] == "PRICE_DROP_7"


def test_dedup_does_not_block_major_price_drop_event():
    state = {"alerts": {"PRICE_DROP_7": {"sent_at": "now"}}}
    assert should_send_event({"event_type": "PRICE_DROP_7"}, state) is True


def test_rolling_24h_drop_5_triggers():
    event = detect_rolling_drop(95, 100)
    assert event["event_type"] == "ROLLING_DROP_5"


def test_rolling_drop_escalation_5_to_7_sends_again():
    state = {"alerts": {"last_rolling_drop_event": "ROLLING_DROP_5"}}
    assert should_send_event({"event_type": "ROLLING_DROP_7"}, state) is True


def test_dedup_does_not_suppress_first_rolling_drop_7():
    state = {"alerts": {}}
    assert should_send_event({"event_type": "ROLLING_DROP_7"}, state) is True


def test_fomo_warning_when_price_runs_too_far():
    state = {"alerts": {"last_reference_price_thb": 15900, "last_entry_signal_price_thb": 15900}}
    events = detect_events(16750, state, 90, "ENTRY")
    assert any(event["event_type"] == "FOMO_WARNING" for event in events)

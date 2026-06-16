from __future__ import annotations

from pathlib import Path
import json


def load_dashboard_data(data_dir: str = "data") -> dict:
    base = Path(data_dir)
    result = {}
    for name in ["state", "signals", "learning", "trades", "signal_history", "outcome_history", "daily_summary"]:
        path = base / f"{name}.json"
        result[name] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return result


def render_text_dashboard(data: dict) -> str:
    state = data.get("state", {})
    position = state.get("position", {})
    signals = data.get("signals", {}).get("signals", [])
    latest = signals[-1] if signals else {}
    return "\n".join(
        [
            "ZEC Guardian Dashboard Lite",
            "SEK Trade Guardian",
            "Mode: ZEC Guardian Mode",
            f"Current price: {latest.get('price_thb', '-')}",
            f"Current signal: {latest.get('signal_type', latest.get('grade', '-'))}",
            f"Entry Score: {latest.get('entry_score', '-')}",
            f"Bounce Probability: {latest.get('bounce_probability', '-')}",
            f"Recovery Probability: {latest.get('recovery_probability', '-')}",
            f"Opportunity Score: {latest.get('opportunity_score', '-')}",
            f"BTC Guard: {latest.get('btc_guard_status', '-')}",
            f"Why Not Entry: {latest.get('why_not_entry', '-')}",
            f"Near Entry: {'YES' if latest.get('entry_score', 0) >= 70 else 'NO'}",
            f"Position ZEC: {position.get('total_zec', 0)}",
            f"Average Cost: {position.get('average_cost_thb', 0)}",
            f"Cash: {state.get('cash_thb', 0)}",
            f"Recent signals count: {len(signals)}",
            f"Signal history count: {len(data.get('signal_history', {}).get('signals', []))}",
            f"Outcome history count: {len(data.get('outcome_history', {}).get('outcomes', []))}",
            f"Daily summary count: {len(data.get('daily_summary', {}).get('summaries', []))}",
            f"Last archive status: {'data/archive enabled'}",
        ]
    )


def main() -> None:
    try:
        import streamlit as st

        data = load_dashboard_data()
        st.title("SEK Trade Guardian")
        st.caption("Mode: ZEC Guardian Mode")
        st.text(render_text_dashboard(data))
        st.json(data.get("state", {}))
    except Exception:
        print(render_text_dashboard(load_dashboard_data()))


if __name__ == "__main__":
    main()

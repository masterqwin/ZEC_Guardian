from __future__ import annotations

from pathlib import Path
import json


def load_dashboard_data(data_dir: str = "data") -> dict:
    base = Path(data_dir)
    result = {}
    for name in ["state", "signals", "learning", "trades"]:
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
        ]
    )


def main() -> None:
    try:
        import streamlit as st

        data = load_dashboard_data()
        st.title("ZEC Guardian Dashboard Lite")
        st.text(render_text_dashboard(data))
        st.json(data.get("state", {}))
    except Exception:
        print(render_text_dashboard(load_dashboard_data()))


if __name__ == "__main__":
    main()

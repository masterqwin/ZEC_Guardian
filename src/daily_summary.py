from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_daily_summary(state: dict[str, Any], scan_context: dict[str, Any]) -> str:
    qa = scan_context.get("qa_status", {})
    counts = scan_context.get("signal_counts_today", {})
    return "\n".join(
        [
            "🛡️ SEK Trade Guardian",
            "Mode: ZEC Guardian Mode",
            "📊 DAILY SUMMARY / Daily Summary",
            "(สรุปประจำวัน)",
            "System: RUNNING",
            f"Scans Today: {qa.get('total_scans_today', 1)}",
            f"Errors: {qa.get('total_errors_today', 0)}",
            f"Last Scan: {qa.get('last_scan_at', datetime.now(timezone.utc).isoformat())}",
            "",
            f"Current Price / ราคาปัจจุบัน: {scan_context.get('price_thb', 0):,.2f} THB",
            f"BTC Guard / สถานะตลาดใหญ่: {scan_context.get('btc_guard', {}).get('status', '-')}",
            f"Current Signal / สัญญาณปัจจุบัน: {scan_context.get('signal_label', '-')}",
            f"Entry Score / คะแนนการเข้า: {scan_context.get('entry_score', '-')}",
            f"Bounce Probability / โอกาสเด้งกลับ: {scan_context.get('bounce_probability', '-')}",
            f"Opportunity Score / ความน่าสนใจ: {scan_context.get('opportunity_score', '-')}",
            "",
            f"Signal Count: {counts}",
            f"Position / สถานะการถือเหรียญ: {state.get('position', {}).get('total_zec', 0)} ZEC",
            f"Near Entry: {'YES' if scan_context.get('entry_score', 0) >= 70 else 'NO'}",
            f"Last Major Event: {scan_context.get('last_event', '-')}",
            f"QA Status: {'OK' if qa.get('state_valid', True) else 'CHECK'}",
        ]
    )

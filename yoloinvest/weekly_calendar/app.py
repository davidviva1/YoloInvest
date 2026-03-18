"""Weekly economic calendar push — runs Sunday evening, sends next week's calendar to Telegram."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

# Allow running as module from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from yoloinvest.common.fetchers import EconomicDataFetcher
from yoloinvest.common.sender import TelegramSender
from yoloinvest.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, TELEGRAM_BOT_TOKEN


def _next_week_range() -> tuple[str, str]:
    """Return (monday, friday) date strings for the coming week."""
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    if today.weekday() == 6:
        days_until_monday = 1
    monday = today + timedelta(days=days_until_monday)
    friday = monday + timedelta(days=4)
    return monday.strftime("%Y-%m-%d"), friday.strftime("%Y-%m-%d")


def _et_to_pt(date_str: str) -> str | None:
    """Convert a ForexFactory ET timestamp to Pacific Time display string (e.g. '5:30 AM PT').

    ForexFactory dates look like '2026-03-18T08:30:00-04:00' (EDT) or '-05:00' (EST).
    Pacific is always 3 hours behind Eastern.
    """
    if not date_str or "T" not in date_str:
        return None
    try:
        # Parse the offset-aware datetime
        match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2})", date_str)
        if not match:
            return None
        dt_str, offset_str = match.groups()
        dt = datetime.fromisoformat(date_str)
        # ET offset is -04:00 (EDT) or -05:00 (EST); PT is always 3h behind ET
        pt_offset_hours = dt.utcoffset().total_seconds() / 3600 - 3
        pt_tz = timezone(timedelta(hours=pt_offset_hours))
        pt_dt = dt.astimezone(pt_tz)
        return pt_dt.strftime("%-I:%M %p PT")
    except Exception:
        return None


def _generate_ai_analysis(events: list[dict]) -> str:
    """Call LLM to generate macro/stock impact analysis for the weekly calendar."""
    if not LLM_API_KEY:
        return ""

    events_text = json.dumps(events, indent=2, ensure_ascii=False)
    prompt = f"""你是一位资深美股分析师。以下是下周即将公布的重要经济数据和事件：

{events_text}

请提供简洁的分析（中文）：

1. **宏观影响**：这些数据对整体市场情绪和美联储政策路径的影响（2-3句）
2. **板块影响**：哪些板块会受到最大影响，为什么（2-3句）
3. **个股机会**：基于这些经济事件，有哪些个股值得重点关注，给出具体理由（3-5只）
4. **风险提示**：本周最大的风险事件是什么，交易者应该如何应对（1-2句）

保持简洁专业，不要废话。"""

    try:
        response = requests.post(
            f"{LLM_API_BASE}/v1/messages",
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        return result["content"][0]["text"]
    except Exception as exc:
        print(f"AI analysis failed: {exc}")
        return ""


def build_calendar_message() -> str | None:
    """Fetch economic calendar and format next week's events with AI analysis."""
    fetcher = EconomicDataFetcher()
    data = fetcher.fetch()
    calendar = data.get("calendar", [])

    if not calendar:
        print("No economic calendar data available.")
        return None

    monday, friday = _next_week_range()
    next_week = [
        e for e in calendar
        if monday <= e.get("date_short", e.get("date", "")[:10]) <= friday
    ]

    if next_week:
        title_range = f"{monday} ~ {friday}"
        events = next_week
    else:
        events = calendar
        dates = sorted(set(e.get("date_short", e.get("date", "")[:10]) for e in events))
        title_range = f"{dates[0]} ~ {dates[-1]}" if dates else f"{monday} ~ {friday}"

    lines = [f"📅 *下周重要经济数据 ({title_range})*\n"]

    # Group by date
    by_date: dict[str, list[dict]] = {}
    for e in events:
        d = e.get("date_short", e.get("date", "")[:10])
        by_date.setdefault(d, []).append(e)

    for date in sorted(by_date.keys()):
        lines.append(f"\n*{date}*")
        for event in by_date[date]:
            impact = event.get("impact", "")
            emoji = "🔴" if impact == "High" else "🟡" if impact == "Medium" else "⚪"
            critical = " ⚠️" if event.get("critical") else ""

            # Time conversion
            pt_time = _et_to_pt(event.get("date", ""))
            time_str = f" [{pt_time}]" if pt_time else ""

            line = f"  {emoji}{time_str} {event['event']}{critical}"
            details = []
            if event.get("forecast"):
                details.append(f"预期: {event['forecast']}")
            if event.get("previous"):
                details.append(f"前值: {event['previous']}")
            if details:
                line += f" ({' | '.join(details)})"
            lines.append(line)

    lines.append("\n🔴 = High Impact | 🟡 = Medium Impact | ⚠️ = 关键事件")

    # AI analysis
    print("Generating AI analysis...")
    analysis = _generate_ai_analysis(events)
    if analysis:
        lines.append("\n" + "=" * 40)
        lines.append("\n📊 *下周经济数据影响分析*\n")
        lines.append(analysis)

    return "\n".join(lines)


def main() -> int:
    chat_id = os.getenv("TELEGRAM_CHAT_ID_MARKET_BRIEFING", os.getenv("TELEGRAM_CHAT_ID", ""))
    if not chat_id:
        print("TELEGRAM_CHAT_ID_MARKET_BRIEFING is not set", file=sys.stderr)
        return 1

    message = build_calendar_message()
    if not message:
        print("No calendar data to send.")
        return 1

    sender = TelegramSender(bot_token=TELEGRAM_BOT_TOKEN, chat_id=chat_id)
    if sender.send_long_message(message):
        print("✅ Weekly calendar sent successfully!")
        return 0
    else:
        print("❌ Failed to send weekly calendar", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

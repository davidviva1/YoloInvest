"""Weekly economic calendar push — runs Sunday evening, sends next week's calendar to Telegram."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

# Allow running as module from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from yoloinvest.common.fetchers import EconomicDataFetcher
from yoloinvest.common.sender import TelegramSender
from yoloinvest.config import TELEGRAM_BOT_TOKEN


def _next_week_range() -> tuple[str, str]:
    """Return (monday, friday) date strings for the coming week."""
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # If today is Monday, target next Monday
    # If called on Sunday, next Monday is tomorrow
    if today.weekday() == 6:
        days_until_monday = 1
    monday = today + timedelta(days=days_until_monday)
    friday = monday + timedelta(days=4)
    return monday.strftime("%Y-%m-%d"), friday.strftime("%Y-%m-%d")


def build_calendar_message() -> str | None:
    """Fetch economic calendar and format next week's events."""
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
        # We have next week's data
        title_range = f"{monday} ~ {friday}"
        events = next_week
    else:
        # ForexFactory hasn't rolled over yet — send all available events
        # and label with the actual date range
        events = calendar
        dates = sorted(set(e.get("date_short", e.get("date", "")[:10]) for e in events))
        if dates:
            title_range = f"{dates[0]} ~ {dates[-1]}"
        else:
            title_range = f"{monday} ~ {friday}"

    lines = [f"📅 *下周重要经济数据 ({title_range})*\n"]

    # Group by date
    by_date: dict[str, list[dict]] = {}
    for e in next_week:
        d = e.get("date_short", e.get("date", "")[:10])
        by_date.setdefault(d, []).append(e)

    for date in sorted(by_date.keys()):
        lines.append(f"\n*{date}*")
        for event in by_date[date]:
            impact = event.get("impact", "")
            emoji = "🔴" if impact == "High" else "🟡" if impact == "Medium" else "⚪"
            critical = " ⚠️" if event.get("critical") else ""
            line = f"  {emoji} {event['event']}{critical}"
            details = []
            if event.get("forecast"):
                details.append(f"预期: {event['forecast']}")
            if event.get("previous"):
                details.append(f"前值: {event['previous']}")
            if details:
                line += f" ({' | '.join(details)})"
            lines.append(line)

    lines.append("\n🔴 = High Impact | 🟡 = Medium Impact | ⚠️ = 关键事件")
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

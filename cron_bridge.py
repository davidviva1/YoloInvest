#!/usr/bin/env python3
"""Minimal bridge for OpenClaw cron-triggered shell tasks."""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import holidays


def _easter_sunday(year: int) -> date:
    """Compute Easter Sunday using Anonymous Gregorian algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nyse_holidays(year: int) -> set[date]:
    """Return set of NYSE market holiday dates for given year."""
    holidays_set = set()
    # Fixed-date holidays (fetch a wider range so the library has data available)
    us = holidays.US(years=range(year - 1, year + 2))
    for d, name in us.items():
        if d.year != year:
            continue
        # Exclude federal holidays not observed by NYSE (Columbus Day, Veterans Day)
        if name not in ("Columbus Day", "Veterans Day"):
            holidays_set.add(d)
    # Good Friday (2 days before Easter Sunday)
    easter = _easter_sunday(year)
    holidays_set.add(easter.replace(day=easter.day - 2))
    return holidays_set


def is_market_closed() -> bool:
    """Return True if US equity markets are closed today (weekend or NYSE holiday)."""
    today = date.today()
    if today.weekday() >= 5:
        return True
    return today in _nyse_holidays(today.year)


COMMANDS = {
    "briefing": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_briefing.sh"],
    "alerts": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_options_alert.sh"],
    "alert-review": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_alert_review.sh"],
    "regime": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_market_regime.sh"],
    "regime-confirm": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_market_regime.sh", "确认"],
    "weekly-calendar": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_weekly_calendar.sh"],
    "swing-alert": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_swing_alert.sh"],
}


def main() -> int:
    valid = "|".join(COMMANDS.keys())
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: cron_bridge.py [{valid}]", file=sys.stderr)
        return 2

    if is_market_closed():
        # Silent exit — market closed, nothing to do
        return 0

    command = COMMANDS[sys.argv[1]]
    result = subprocess.run(command, cwd=Path(command[0]).resolve().parent)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

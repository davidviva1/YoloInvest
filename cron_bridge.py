#!/usr/bin/env python3
"""Minimal bridge for OpenClaw cron-triggered shell tasks."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS = {
    "briefing": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_briefing.sh"],
    "alerts": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_options_alert.sh"],
    "alert-review": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_alert_review.sh"],
    "regime": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_market_regime.sh"],
    "regime-confirm": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_market_regime.sh", "确认"],
}


def main() -> int:
    valid = "|".join(COMMANDS.keys())
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: cron_bridge.py [{valid}]", file=sys.stderr)
        return 2

    command = COMMANDS[sys.argv[1]]
    result = subprocess.run(command, cwd=Path(command[0]).resolve().parent)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

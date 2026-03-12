#!/usr/bin/env python3
"""Minimal bridge for OpenClaw cron-triggered shell tasks."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS = {
    "briefing": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_briefing.sh"],
    "alerts": ["/home/ec2-user/.openclaw/workspace/YoloInvest/run_options_alert.sh"],
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print("Usage: cron_bridge.py [briefing|alerts]", file=sys.stderr)
        return 2

    command = COMMANDS[sys.argv[1]]
    result = subprocess.run(command, cwd=Path(command[0]).resolve().parent)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

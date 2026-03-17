"""CLI entry point for market regime detection.

Usage:
    python -m yoloinvest.market_regime.cli scheduled [--phase 初判|确认]
    python -m yoloinvest.market_regime.cli manual TICKER
"""
from __future__ import annotations

import sys

from yoloinvest.market_regime.regime import run_manual, run_scheduled


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: cli.py [scheduled|manual] [args]", file=sys.stderr)
        return 2

    cmd = sys.argv[1]

    if cmd == "scheduled":
        phase = "初判"
        if "--phase" in sys.argv:
            idx = sys.argv.index("--phase")
            if idx + 1 < len(sys.argv):
                phase = sys.argv[idx + 1]
        return run_scheduled(phase=phase)

    elif cmd == "manual":
        if len(sys.argv) < 3:
            print("Usage: cli.py manual TICKER", file=sys.stderr)
            return 2
        return run_manual(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Review the latest intraday alert state for quick manual inspection."""
from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = Path('/tmp/options_alert_state.json')


def main() -> int:
    if not STATE_FILE.exists():
        print('No alert state file found')
        return 0

    payload = json.loads(STATE_FILE.read_text())
    alerts = payload.get('alerts', {})
    updated_at = payload.get('updated_at', 'unknown')

    print(f'Intraday alert review snapshot: {updated_at}')
    print(f'Tracked candidates: {len(alerts)}')
    print('')

    ranked = sorted(
        alerts.values(),
        key=lambda item: (item.get('score', 0), abs(item.get('day_change_pct', 0))),
        reverse=True,
    )

    if not ranked:
        print('No active alert candidates in state')
        return 0

    for item in ranked[:20]:
        symbol = item.get('symbol', '?')
        severity = str(item.get('severity', 'low')).upper()
        score = float(item.get('score', 0))
        day_change = float(item.get('day_change_pct', 0))
        intraday_move = float(item.get('intraday_move_pct', 0))
        volume_ratio = float(item.get('volume_ratio', 0))
        reasons = item.get('trigger_reasons') or []
        print(
            f'- {symbol}: [{severity}] score {score:.1f} | day {day_change:+.2f}% | open {intraday_move:+.2f}% | volume {volume_ratio:.2f}x'
        )
        if reasons:
            print(f'  reasons: {", ".join(reasons[:4])}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

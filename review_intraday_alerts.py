#!/usr/bin/env python3
"""End-of-day intraday alert review with closing-performance pillar."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from yoloinvest.config import REQUEST_TIMEOUT, USER_AGENT, YAHOO_FINANCE_BASE

STATE_FILE = Path('/tmp/options_alert_state.json')
REPORT_FILE = Path('/tmp/intraday_alert_review.txt')


def fetch_latest_close(symbol: str) -> float | None:
    url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "5d", "includePrePost": "false"}
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json().get('chart', {}).get('result')
    if not payload:
        return None
    closes = payload[0].get('indicators', {}).get('quote', [{}])[0].get('close', [])
    closes = [value for value in closes if value is not None]
    if not closes:
        return None
    return float(closes[-1])


def build_close_pillar(item: dict[str, Any]) -> tuple[str, float | None]:
    symbol = item.get('symbol', '?')
    alert_price = float(item.get('price', 0))
    close_price = fetch_latest_close(symbol)
    if not close_price or not alert_price:
        return f'- {symbol}: close performance unavailable', None
    perf_pct = ((close_price - alert_price) / alert_price) * 100
    return (
        f'- {symbol}: alert ${alert_price:.2f} -> close ${close_price:.2f} ({perf_pct:+.2f}%)',
        perf_pct,
    )


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text())


def render_report(payload: dict[str, Any]) -> str:
    updated_at = payload.get('updated_at', 'unknown')
    alerts = payload.get('alerts', {})
    ranked = sorted(
        alerts.values(),
        key=lambda item: (item.get('score', 0), abs(item.get('day_change_pct', 0))),
        reverse=True,
    )

    now = datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')
    lines = [f'📘 Intraday Alert Closing Review ({now})', '', f'State snapshot: {updated_at}', f'Candidates tracked: {len(ranked)}', '']

    if not ranked:
        lines.append('No active alert candidates in state.')
        return '\n'.join(lines)

    lines.append('Top alerts')
    for item in ranked[:10]:
        symbol = item.get('symbol', '?')
        severity = str(item.get('severity', 'low')).upper()
        score = float(item.get('score', 0))
        day_change = float(item.get('day_change_pct', 0))
        intraday_move = float(item.get('intraday_move_pct', 0))
        volume_ratio = float(item.get('volume_ratio', 0))
        reasons = item.get('trigger_reasons') or []
        lines.append(
            f'- {symbol}: [{severity}] score {score:.1f} | day {day_change:+.2f}% | open {intraday_move:+.2f}% | volume {volume_ratio:.2f}x'
        )
        if reasons:
            lines.append(f"  reasons: {', '.join(reasons[:4])}")

    lines.append('')
    lines.append('Close performance pillar')
    pillar_values: list[float] = []
    for item in ranked[:10]:
        line, perf = build_close_pillar(item)
        lines.append(line)
        if perf is not None:
            pillar_values.append(perf)

    if pillar_values:
        avg_perf = sum(pillar_values) / len(pillar_values)
        winners = sum(1 for value in pillar_values if value > 0)
        losers = sum(1 for value in pillar_values if value < 0)
        lines.append('')
        lines.append(f'Pillar summary: avg close performance {avg_perf:+.2f}% | winners {winners} | losers {losers}')

    return '\n'.join(lines)


def main() -> int:
    payload = load_state()
    report = render_report(payload)
    REPORT_FILE.write_text(report)
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

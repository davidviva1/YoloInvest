#!/usr/bin/env python3
"""End-of-day intraday alert review with quality metrics and closing-performance pillar."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
import requests

from yoloinvest.common.sender import TelegramSender
from yoloinvest.config import REQUEST_TIMEOUT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USER_AGENT, YAHOO_FINANCE_BASE

STATE_FILE = Path('/tmp/options_alert_state.json')
HISTORY_FILE = Path('/tmp/options_alert_history.jsonl')
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


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text())


def load_history_for_today() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    today = date.today().isoformat()
    rows: list[dict[str, Any]] = []
    for line in HISTORY_FILE.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get('timestamp', '')).startswith(today):
            rows.append(row)
    return rows


def classify_bucket(score: float) -> str:
    if score >= 8:
        return '8+'
    if score >= 6:
        return '6-7.9'
    if score >= 4:
        return '4-5.9'
    return '<4'


def compute_follow_through(entry: dict[str, Any], close_price: float | None) -> tuple[float | None, bool | None]:
    alert_price = float(entry.get('price', 0))
    if not alert_price or close_price is None:
        return None, None
    raw_return = ((close_price - alert_price) / alert_price) * 100
    directional_return = raw_return if entry.get('direction') == 'bullish' else -raw_return
    hit = directional_return > 0
    return directional_return, hit


def build_close_pillar(entries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    lines: list[str] = []
    metrics: list[dict[str, Any]] = []
    for entry in entries:
        symbol = entry.get('symbol', '?')
        alert_price = float(entry.get('price', 0))
        close_price = fetch_latest_close(symbol)
        if close_price is None or not alert_price:
            lines.append(f'- {symbol}: close performance unavailable')
            continue
        raw_return = ((close_price - alert_price) / alert_price) * 100
        directional_return, hit = compute_follow_through(entry, close_price)
        lines.append(
            f"- {symbol}: alert ${alert_price:.2f} -> close ${close_price:.2f} | raw {raw_return:+.2f}% | directional {directional_return:+.2f}% | hit {hit}"
        )
        metrics.append(
            {
                'symbol': symbol,
                'severity': entry.get('severity', 'low'),
                'score': float(entry.get('score', 0)),
                'bucket': classify_bucket(float(entry.get('score', 0))),
                'directional_return': directional_return,
                'hit': hit,
            }
        )
    return lines, metrics


def summarize_metrics(metrics: list[dict[str, Any]]) -> list[str]:
    if not metrics:
        return ['No close-performance metrics available yet.']

    overall_returns = [item['directional_return'] for item in metrics if item['directional_return'] is not None]
    hits = [item['hit'] for item in metrics if item['hit'] is not None]
    lines = []
    avg_return = sum(overall_returns) / len(overall_returns)
    hit_rate = sum(1 for item in hits if item) / len(hits) * 100 if hits else 0.0
    lines.append(f'- Overall: avg directional return {avg_return:+.2f}% | hit rate {hit_rate:.1f}% | sample {len(overall_returns)}')

    by_severity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in metrics:
        by_severity[str(item['severity']).upper()].append(item)
        by_bucket[str(item['bucket'])].append(item)

    lines.append('- By severity:')
    for severity in sorted(by_severity.keys()):
        items = by_severity[severity]
        returns = [entry['directional_return'] for entry in items if entry['directional_return'] is not None]
        hit_values = [entry['hit'] for entry in items if entry['hit'] is not None]
        if not returns:
            continue
        avg = sum(returns) / len(returns)
        hit = sum(1 for value in hit_values if value) / len(hit_values) * 100 if hit_values else 0.0
        lines.append(f'  - {severity}: avg {avg:+.2f}% | hit rate {hit:.1f}% | sample {len(returns)}')

    lines.append('- By score bucket:')
    for bucket in ['8+', '6-7.9', '4-5.9', '<4']:
        items = by_bucket.get(bucket, [])
        returns = [entry['directional_return'] for entry in items if entry['directional_return'] is not None]
        hit_values = [entry['hit'] for entry in items if entry['hit'] is not None]
        if not returns:
            continue
        avg = sum(returns) / len(returns)
        hit = sum(1 for value in hit_values if value) / len(hit_values) * 100 if hit_values else 0.0
        lines.append(f'  - {bucket}: avg {avg:+.2f}% | hit rate {hit:.1f}% | sample {len(returns)}')

    return lines


def send_telegram(text: str) -> None:
    sender = TelegramSender(bot_token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID)
    sender.send_long_message(text)


def render_report(payload: dict[str, Any], history_rows: list[dict[str, Any]]) -> str:
    updated_at = payload.get('updated_at', 'unknown')
    alerts = payload.get('alerts', {})
    ranked_state = sorted(
        alerts.values(),
        key=lambda item: (item.get('score', 0), abs(item.get('day_change_pct', 0))),
        reverse=True,
    )
    ranked_history = sorted(history_rows, key=lambda item: item.get('score', 0), reverse=True)

    now = datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        f'📘 Intraday Alert Closing Review ({now})',
        '',
        f'State snapshot: {updated_at}',
        f'Candidates tracked in state: {len(ranked_state)}',
        f'Alerts triggered today: {len(ranked_history)}',
        '',
    ]

    lines.append('Triggered alerts today')
    if not ranked_history:
        lines.append('No intraday alerts were triggered today.')
    else:
        for item in ranked_history[:20]:
            symbol = item.get('symbol', '?')
            severity = str(item.get('severity', 'low')).upper()
            score = float(item.get('score', 0))
            direction = item.get('direction', 'unknown')
            reasons = item.get('trigger_reasons') or []
            lines.append(f'- {symbol}: [{severity}] {direction} | score {score:.1f} | alert ${float(item.get("price", 0)):.2f}')
            if reasons:
                lines.append(f"  reasons: {', '.join(reasons[:4])}")

    lines.append('')
    lines.append('Top state snapshot')
    if not ranked_state:
        lines.append('No active alert candidates in state.')
    else:
        for item in ranked_state[:10]:
            symbol = item.get('symbol', '?')
            severity = str(item.get('severity', 'low')).upper()
            score = float(item.get('score', 0))
            day_change = float(item.get('day_change_pct', 0))
            intraday_move = float(item.get('intraday_move_pct', 0))
            volume_ratio = float(item.get('volume_ratio', 0))
            lines.append(
                f'- {symbol}: [{severity}] score {score:.1f} | day {day_change:+.2f}% | open {intraday_move:+.2f}% | volume {volume_ratio:.2f}x'
            )

    lines.append('')
    lines.append('Close performance pillar')
    close_lines, metrics = build_close_pillar(ranked_history[:20])
    lines.extend(close_lines or ['No close performance data available.'])

    lines.append('')
    lines.append('Quality summary')
    lines.extend(summarize_metrics(metrics))
    return '\n'.join(lines)


def main() -> int:
    payload = load_state()
    history_rows = load_history_for_today()
    report = render_report(payload, history_rows)
    REPORT_FILE.write_text(report)
    send_telegram(report)
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

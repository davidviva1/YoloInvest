#!/usr/bin/env python3
"""Intraday options-style alert script for highly liquid mega-cap tech stocks.

V1.1 adds lightweight news confirmation on top of intraday price/volume signals.
It is still not a true options-flow feed, but it creates a useful alerting layer
that can later be upgraded to real options tape providers.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional

import feedparser
import requests

from config import REQUEST_TIMEOUT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USER_AGENT, YAHOO_FINANCE_BASE

ALERT_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "MRVL", "ALAB", "NBIS"]
STATE_FILE = Path("/tmp/options_alert_state.json")
TECH_NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA,AVGO,MRVL,ALAB,NBIS&region=US&lang=en-US",
    "https://www.cnbc.com/id/19854910/device/rss/rss.html",
]


@dataclass
class AlertCandidate:
    symbol: str
    price: float
    day_change_pct: float
    intraday_move_pct: float
    volume_ratio: float
    regular_volume: int
    avg_volume: int
    market_state: str
    news_hits: List[str]

    @property
    def score(self) -> float:
        news_bonus = min(len(self.news_hits), 3) * 0.8
        return abs(self.day_change_pct) * 0.5 + abs(self.intraday_move_pct) * 0.3 + self.volume_ratio * 0.2 + news_bonus


def fetch_symbol_snapshot(symbol: str) -> Optional[AlertCandidate]:
    url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
    params = {"interval": "5m", "range": "2d", "includePrePost": "false"}
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    payload = response.json().get("chart", {}).get("result")
    if not payload:
        return None

    result = payload[0]
    meta = result.get("meta", {})
    quote_data = result.get("indicators", {}).get("quote", [{}])[0]
    closes = [value for value in quote_data.get("close", []) if value is not None]
    volumes = [value for value in quote_data.get("volume", []) if value is not None]

    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    open_price = meta.get("regularMarketOpen") or prev_close
    regular_volume = meta.get("regularMarketVolume") or (volumes[-1] if volumes else 0)
    avg_volume = meta.get("averageDailyVolume3Month") or meta.get("averageDailyVolume10Day") or 0

    if not price or not prev_close or not open_price or not avg_volume:
        return None

    day_change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
    intraday_move_pct = ((price - open_price) / open_price) * 100 if open_price else 0
    volume_ratio = regular_volume / avg_volume if avg_volume else 0

    return AlertCandidate(
        symbol=symbol,
        price=price,
        day_change_pct=day_change_pct,
        intraday_move_pct=intraday_move_pct,
        volume_ratio=volume_ratio,
        regular_volume=int(regular_volume),
        avg_volume=int(avg_volume),
        market_state=meta.get("marketState", "UNKNOWN"),
        news_hits=[],
    )


def fetch_candidates(symbols: List[str]) -> List[AlertCandidate]:
    candidates: List[AlertCandidate] = []
    for symbol in symbols:
        try:
            snapshot = fetch_symbol_snapshot(symbol)
            if snapshot:
                candidates.append(snapshot)
        except Exception as exc:
            print(f"Error fetching {symbol}: {exc}")
    return candidates


def fetch_news_hits(symbols: List[str]) -> Dict[str, List[str]]:
    hits = {symbol: [] for symbol in symbols}
    for url in TECH_NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                combined = f"{title} {summary}".upper()
                for symbol in symbols:
                    if symbol in combined and title not in hits[symbol]:
                        hits[symbol].append(title)
        except Exception as exc:
            print(f"Error fetching news from {url}: {exc}")
    return hits


def attach_news(candidates: List[AlertCandidate], news_hits: Dict[str, List[str]]) -> List[AlertCandidate]:
    for candidate in candidates:
        candidate.news_hits = news_hits.get(candidate.symbol, [])[:3]
    return candidates


def filter_alerts(candidates: List[AlertCandidate]) -> List[AlertCandidate]:
    filtered: List[AlertCandidate] = []
    for candidate in candidates:
        if abs(candidate.day_change_pct) < 2.0:
            continue
        if abs(candidate.intraday_move_pct) < 1.0:
            continue
        if candidate.volume_ratio < 1.2:
            continue
        if candidate.news_hits:
            filtered.append(candidate)
            continue
        if abs(candidate.day_change_pct) >= 3.5 and candidate.volume_ratio >= 1.8:
            filtered.append(candidate)
    return filtered


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"alerts": {}}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return {"alerts": {}}


def save_state(alerts: List[AlertCandidate]) -> None:
    payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "alerts": {alert.symbol: asdict(alert) for alert in alerts},
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2))


def fresh_alerts(alerts: List[AlertCandidate], state: dict) -> List[AlertCandidate]:
    previous = state.get("alerts", {})
    result: List[AlertCandidate] = []
    for alert in alerts:
        old = previous.get(alert.symbol)
        if not old:
            result.append(alert)
            continue
        old_score = abs(old.get("day_change_pct", 0)) + abs(old.get("intraday_move_pct", 0)) + old.get("volume_ratio", 0) + len(old.get("news_hits", []))
        new_score = abs(alert.day_change_pct) + abs(alert.intraday_move_pct) + alert.volume_ratio + len(alert.news_hits)
        if new_score >= old_score + 1.5:
            result.append(alert)
    return result


def format_message(alerts: List[AlertCandidate]) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"🚨 *盘中异动预警 V1.1* ({now})", "", "范围：高流动性大型科技股", ""]
    for alert in sorted(alerts, key=lambda item: item.score, reverse=True):
        direction = "看涨异动" if alert.day_change_pct > 0 else "看跌异动"
        lines.append(
            f"• *{alert.symbol}* {direction} | ${alert.price:.2f} | 日内 {alert.day_change_pct:+.2f}% | "
            f"开盘后 {alert.intraday_move_pct:+.2f}% | 量比 {alert.volume_ratio:.2f}x"
        )
        if alert.news_hits:
            lines.append(f"  新闻：{alert.news_hits[0]}")
    lines.append("")
    lines.append("说明：V1.1 在价格/量能代理信号上叠加相关新闻确认；后续可接入真实期权流数据。")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set")
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()


def main() -> int:
    candidates = fetch_candidates(ALERT_SYMBOLS)
    news_hits = fetch_news_hits(ALERT_SYMBOLS)
    candidates = attach_news(candidates, news_hits)
    alerts = filter_alerts(candidates)
    state = load_state()
    new_alerts = fresh_alerts(alerts, state)
    save_state(alerts)

    if not new_alerts:
        print("No fresh alerts")
        return 0

    message = format_message(new_alerts)
    send_telegram(message)
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

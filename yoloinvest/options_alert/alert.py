"""Intraday alert module for highly liquid tech stocks."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional

import feedparser
import requests

from yoloinvest.common.sender import TelegramSender
from yoloinvest.config import REQUEST_TIMEOUT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USER_AGENT, YAHOO_FINANCE_BASE

ALERT_SYMBOLS = [
    # 指数 ETF + 杠杆
    "SPY", "QQQ", "TQQQ", "SQQQ", "SPXL", "SPXS", "SOXL", "SOXS", "UPRO",
    # 个股杠杆 ETF (2x bull & bear)
    "NVDL", "NVDD",       # NVDA 2x bull / 2x bear
    "NVDU",               # NVDA 2x bull (Direxion)
    "TSLL", "TSLS",       # TSLA 2x bull / 1x bear
    "TSLR",               # TSLA 2x bear (T-Rex)
    "METD",               # META 2x bear
    "FBL",                # META 2x bull (GraniteShares)
    "AMZU", "AMZD",       # AMZN 2x bull / 2x bear
    # 高流动性个股
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "MRVL", "ALAB", "NBIS",
]
STATE_FILE = Path("/tmp/options_alert_state.json")
HISTORY_FILE = Path("/tmp/options_alert_history.jsonl")
TECH_NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA,AVGO,MRVL,ALAB,NBIS,SPY,QQQ&region=US&lang=en-US",
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
    score: float = 0.0
    severity: str = "low"
    trigger_reasons: List[str] | None = None

    def compute_score(self) -> float:
        score = 0.0
        reasons: List[str] = []

        abs_day = abs(self.day_change_pct)
        abs_intraday = abs(self.intraday_move_pct)

        # 杠杆 ETF 门槛更高（日常波动就大），个股/指数 ETF 门槛更低
        is_leveraged = self.symbol in {
            "TQQQ", "SQQQ", "SPXL", "SPXS", "SOXL", "SOXS", "UPRO",
            "NVDL", "NVDD", "NVDU", "TSLL", "TSLS", "TSLR",
            "METD", "FBL", "AMZU", "AMZD",
        }

        # Day change scoring — 杠杆 ETF 用 2x 门槛
        day_thresholds = (8, 5, 3) if is_leveraged else (4, 2.5, 1.2)
        if abs_day >= day_thresholds[0]:
            score += 4.0
            reasons.append(f"day move {self.day_change_pct:+.2f}%")
        elif abs_day >= day_thresholds[1]:
            score += 3.0
            reasons.append(f"day move {self.day_change_pct:+.2f}%")
        elif abs_day >= day_thresholds[2]:
            score += 2.0
            reasons.append(f"day move {self.day_change_pct:+.2f}%")

        # Intraday move scoring
        intra_thresholds = (4, 2.5, 1.5) if is_leveraged else (2, 1.2, 0.6)
        if abs_intraday >= intra_thresholds[0]:
            score += 3.0
            reasons.append(f"move vs open {self.intraday_move_pct:+.2f}%")
        elif abs_intraday >= intra_thresholds[1]:
            score += 2.0
            reasons.append(f"move vs open {self.intraday_move_pct:+.2f}%")
        elif abs_intraday >= intra_thresholds[2]:
            score += 1.0
            reasons.append(f"move vs open {self.intraday_move_pct:+.2f}%")

        # Volume ratio scoring — 降低门槛
        if self.volume_ratio >= 2.5:
            score += 3.0
            reasons.append(f"volume {self.volume_ratio:.2f}x")
        elif self.volume_ratio >= 1.5:
            score += 2.0
            reasons.append(f"volume {self.volume_ratio:.2f}x")
        elif self.volume_ratio >= 0.8:
            score += 1.0
            reasons.append(f"volume {self.volume_ratio:.2f}x")

        news_count = min(len(self.news_hits), 3)
        if news_count:
            score += news_count * 1.0
            reasons.append(f"news x{news_count}")

        if self.market_state.upper() in {"REGULAR", "POSTPOST", "POST"}:
            score += 0.5

        self.score = round(score, 2)
        self.trigger_reasons = reasons
        if self.score >= 6:
            self.severity = "high"
        elif self.score >= 3.5:
            self.severity = "medium"
        else:
            self.severity = "low"
        return self.score

    @property
    def direction(self) -> str:
        return "bullish" if self.day_change_pct >= 0 else "bearish"


def fetch_symbol_snapshot(symbol: str) -> Optional[AlertCandidate]:
    url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "5d", "includePrePost": "false"}
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

    # Estimate avg volume from chart data if API doesn't provide it
    if not avg_volume and len(volumes) >= 2:
        avg_volume = int(sum(volumes[:-1]) / len(volumes[:-1]))

    if not price or not prev_close:
        return None

    day_change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
    intraday_move_pct = ((price - open_price) / open_price) * 100 if open_price else 0
    volume_ratio = regular_volume / avg_volume if avg_volume else 1.0

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
        candidate.compute_score()
    return candidates


def filter_alerts(candidates: List[AlertCandidate]) -> List[AlertCandidate]:
    filtered: List[AlertCandidate] = []
    for candidate in candidates:
        abs_day = abs(candidate.day_change_pct)
        abs_intraday = abs(candidate.intraday_move_pct)
        is_leveraged = candidate.symbol in {
            "TQQQ", "SQQQ", "SPXL", "SPXS", "SOXL", "SOXS", "UPRO",
            "NVDL", "NVDD", "NVDU", "TSLL", "TSLS", "TSLR",
            "METD", "FBL", "AMZU", "AMZD",
        }

        # 杠杆 ETF 用更高的日内门槛
        day_min = 3.0 if is_leveraged else 1.0
        intra_min = 1.5 if is_leveraged else 0.5

        if abs_day < day_min and abs_intraday < intra_min:
            continue
        # medium/high 直接通过
        if candidate.severity in {"high", "medium"}:
            filtered.append(candidate)
            continue
        # low severity 但有新闻或 score >= 3 也通过
        if candidate.news_hits and candidate.score >= 3.0:
            filtered.append(candidate)
            continue
        if candidate.score >= 3.5:
            filtered.append(candidate)
    return filtered
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


def append_history(alerts: List[AlertCandidate]) -> None:
    if not alerts:
        return
    with HISTORY_FILE.open("a") as handle:
        for alert in alerts:
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "symbol": alert.symbol,
                "direction": alert.direction,
                "price": alert.price,
                "score": alert.score,
                "severity": alert.severity,
                "day_change_pct": alert.day_change_pct,
                "intraday_move_pct": alert.intraday_move_pct,
                "volume_ratio": alert.volume_ratio,
                "trigger_reasons": alert.trigger_reasons or [],
                "news_hits": alert.news_hits,
            }
            handle.write(json.dumps(record) + "\n")


def is_escalated(alert: AlertCandidate, old: dict) -> bool:
    old_score = float(old.get("score", 0))
    old_severity = old.get("severity", "low")
    severity_rank = {"low": 1, "medium": 2, "high": 3}

    if severity_rank.get(alert.severity, 1) > severity_rank.get(old_severity, 1):
        return True
    # score 增加 1.5 就算升级（之前是 2.0）
    if alert.score >= old_score + 1.5:
        return True
    # 方向反转也算新 alert
    old_day_change = float(old.get("day_change_pct", 0))
    if (alert.day_change_pct > 0) != (old_day_change > 0):
        return True
    return False


def fresh_alerts(alerts: List[AlertCandidate], state: dict) -> List[AlertCandidate]:
    previous = state.get("alerts", {})
    result: List[AlertCandidate] = []
    for alert in alerts:
        old = previous.get(alert.symbol)
        if not old:
            result.append(alert)
            continue
        if is_escalated(alert, old):
            result.append(alert)
    return result


def format_message(alerts: List[AlertCandidate]) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"🚨 *盘中异动预警 V2.1* ({now})", "", "范围：高流动性大型科技股", ""]
    for alert in sorted(alerts, key=lambda item: item.score, reverse=True):
        direction = "看涨异动" if alert.day_change_pct > 0 else "看跌异动"
        level = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(alert.severity, alert.severity.upper())
        lines.append(
            f"• *{alert.symbol}* [{level}] {direction} | score {alert.score:.1f} | ${alert.price:.2f} | 日内 {alert.day_change_pct:+.2f}% | 开盘后 {alert.intraday_move_pct:+.2f}% | 量比 {alert.volume_ratio:.2f}x"
        )
        if alert.trigger_reasons:
            lines.append(f"  触发：{', '.join(alert.trigger_reasons[:3])}")
        if alert.news_hits:
            lines.append(f"  新闻：{alert.news_hits[0]}")
    lines.append("")
    lines.append("说明：V2.1 在 V2.0 基础上增加 alert history，为后续质量统计和收盘复盘提供数据基础。")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    sender = TelegramSender(bot_token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID)
    sender.send_long_message(text)


def main() -> int:
    candidates = fetch_candidates(ALERT_SYMBOLS)
    news_hits = fetch_news_hits(ALERT_SYMBOLS)
    candidates = attach_news(candidates, news_hits)
    alerts = filter_alerts(candidates)
    state = load_state()
    new_alerts = fresh_alerts(alerts, state)
    save_state(alerts)
    append_history(new_alerts)

    if not new_alerts:
        print("No fresh alerts")
        return 0

    message = format_message(new_alerts)
    send_telegram(message)
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

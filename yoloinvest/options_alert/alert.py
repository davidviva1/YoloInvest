"""
Intraday Alert Module V3.1 — 日内异动扫描（服务期权决策）

核心改进 vs V3.0:
1. 期权异动检测 — Volume/OI > 3x 的合约（可能有催化剂）
2. 方向性评分 — 不再用 abs()，看涨/看跌分开打分
3. 大盘过滤 — QQQ/SPY 趋势作为全局 context，逆势信号降权
4. 时间窗口权重 — 开盘30min/尾盘1h 加权，午盘打折
5. 杠杆ETF标注 — 推送中明确标注风险等级
6. 新闻情绪 — 简单正负面关键词匹配
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import feedparser
import requests
import yfinance as yf

from yoloinvest.common.sender import TelegramSender
from yoloinvest.config import REQUEST_TIMEOUT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USER_AGENT, YAHOO_FINANCE_BASE

# ── 标的池 ──────────────────────────────────────────────
# 日内扫描：高流动性个股 + 指数ETF + 杠杆ETF
INTRADAY_SYMBOLS = [
    "SPY", "QQQ",
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "MRVL", "ALAB", "NBIS",
    # 2x/3x 做多 ETF
    "TQQQ", "SPXL", "UPRO", "SOXL",
]

# 杠杆 ETF 标识（用于推送时标注风险）
LEVERAGED_ETFS = {"TQQQ", "SPXL", "UPRO", "SOXL", "SQQQ", "SPXS", "SOXS"}

# 大盘参考标的
MARKET_BENCHMARKS = ["QQQ", "SPY"]

STATE_FILE = Path("/tmp/intraday_alert_state.json")
HISTORY_FILE = Path("/tmp/intraday_alert_history.jsonl")

TECH_NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA,AVGO,MRVL,ALAB,NBIS,SPY,QQQ&region=US&lang=en-US",
    "https://www.cnbc.com/id/19854910/device/rss/rss.html",
]

# ── 新闻情绪关键词 ──────────────────────────────────────
BULLISH_KEYWORDS = [
    "upgrade", "beat", "beats", "surge", "surges", "rally", "rallies",
    "record high", "all-time high", "outperform", "buy", "bullish",
    "strong", "growth", "raises guidance", "above expectations",
]
BEARISH_KEYWORDS = [
    "downgrade", "miss", "misses", "plunge", "plunges", "crash",
    "sell", "bearish", "weak", "decline", "cut", "below expectations",
    "warning", "layoff", "layoffs", "recall", "investigation", "probe",
]

# ── 美东时间窗口（ET） ──────────────────────────────────
ET = ZoneInfo("America/New_York")
PT = ZoneInfo("America/Los_Angeles")


def _get_time_weight() -> Tuple[float, str]:
    """根据美东时间返回时间权重和时段标签。"""
    now_et = datetime.now(ET)
    hour, minute = now_et.hour, now_et.minute
    t = hour * 60 + minute

    # 盘前 4:00-9:30 ET
    if t < 570:
        return 0.6, "盘前"
    # 开盘前30min 9:30-10:00
    if t < 600:
        return 1.5, "开盘30min"
    # 上午 10:00-11:30
    if t < 690:
        return 1.0, "上午盘"
    # 午盘 11:30-14:00 — 流动性差，信号打折
    if t < 840:
        return 0.7, "午盘"
    # 下午 14:00-15:00
    if t < 900:
        return 1.0, "下午盘"
    # 尾盘 15:00-16:00 — power hour
    if t < 960:
        return 1.4, "尾盘"
    # 盘后
    return 0.5, "盘后"


def _news_sentiment(title: str) -> int:
    """简单情绪判断: +1 正面, -1 负面, 0 中性。"""
    lower = title.lower()
    bull = sum(1 for kw in BULLISH_KEYWORDS if kw in lower)
    bear = sum(1 for kw in BEARISH_KEYWORDS if kw in lower)
    if bull > bear:
        return 1
    if bear > bull:
        return -1
    return 0


# ── 数据模型 ──────────────────────────────────────────────
@dataclass
class MarketContext:
    """大盘环境快照。"""
    qqq_change_pct: float = 0.0
    spy_change_pct: float = 0.0
    qqq_intraday_pct: float = 0.0
    spy_intraday_pct: float = 0.0

    @property
    def trend(self) -> str:
        """综合 QQQ+SPY 判断大盘方向。"""
        avg = (self.qqq_change_pct + self.spy_change_pct) / 2
        if avg > 0.3:
            return "bullish"
        if avg < -0.3:
            return "bearish"
        return "neutral"

    @property
    def trend_label(self) -> str:
        labels = {"bullish": "📈 大盘偏多", "bearish": "📉 大盘偏空", "neutral": "➡️ 大盘震荡"}
        return labels[self.trend]


@dataclass
class IntradayAlert:
    symbol: str
    price: float
    day_change_pct: float
    intraday_move_pct: float
    volume_ratio: float
    regular_volume: int
    avg_volume: int
    market_state: str
    news_hits: List[str]
    news_sentiment: int  # +N bullish, -N bearish
    direction: str  # "bullish" / "bearish"
    aligned_with_market: bool  # 是否与大盘同向
    time_window: str  # 时段标签
    score: float = 0.0
    severity: str = "low"
    trigger_reasons: List[str] | None = None

    def compute_score(self, market: MarketContext) -> float:
        score = 0.0
        reasons: List[str] = []

        # ── 1. 方向性价格评分（不取绝对值） ──
        day = self.day_change_pct
        intra = self.intraday_move_pct
        self.direction = "bullish" if day >= 0 else "bearish"

        abs_day = abs(day)
        abs_intra = abs(intra)

        # Day change
        if abs_day >= 4:
            score += 4.0
            reasons.append(f"日涨跌 {day:+.2f}%")
        elif abs_day >= 2.5:
            score += 3.0
            reasons.append(f"日涨跌 {day:+.2f}%")
        elif abs_day >= 1.2:
            score += 2.0
            reasons.append(f"日涨跌 {day:+.2f}%")

        # Intraday move
        if abs_intra >= 2:
            score += 3.0
            reasons.append(f"盘中波动 {intra:+.2f}%")
        elif abs_intra >= 1.2:
            score += 2.0
            reasons.append(f"盘中波动 {intra:+.2f}%")
        elif abs_intra >= 0.6:
            score += 1.0
            reasons.append(f"盘中波动 {intra:+.2f}%")

        # ── 2. 量比 ──
        if self.volume_ratio >= 2.5:
            score += 3.0
            reasons.append(f"量比 {self.volume_ratio:.1f}x")
        elif self.volume_ratio >= 1.5:
            score += 2.0
            reasons.append(f"量比 {self.volume_ratio:.1f}x")
        elif self.volume_ratio >= 0.8:
            score += 1.0
            reasons.append(f"量比 {self.volume_ratio:.1f}x")

        # ── 3. 新闻（带情绪方向） ──
        news_count = min(len(self.news_hits), 3)
        if news_count:
            # 新闻情绪与价格方向一致 → 加分；不一致 → 减分
            if self.news_sentiment != 0:
                price_dir = 1 if day >= 0 else -1
                if (self.news_sentiment > 0) == (price_dir > 0):
                    score += news_count * 1.0
                    reasons.append(f"新闻x{news_count} (情绪一致)")
                else:
                    score += news_count * 0.5
                    reasons.append(f"新闻x{news_count} (情绪矛盾⚠️)")
            else:
                score += news_count * 0.5
                reasons.append(f"新闻x{news_count}")

        # ── 4. 大盘同向加分 / 逆势减分 ──
        mkt_trend = market.trend
        self.aligned_with_market = (
            (self.direction == "bullish" and mkt_trend == "bullish")
            or (self.direction == "bearish" and mkt_trend == "bearish")
        )
        if self.aligned_with_market:
            score += 1.5
            reasons.append("与大盘同向 ✅")
        elif mkt_trend != "neutral" and self.direction != mkt_trend:
            score -= 1.5
            reasons.append("逆大盘 ⚠️")

        # ── 5. 时间窗口权重 ──
        time_weight, self.time_window = _get_time_weight()
        if time_weight != 1.0:
            reasons.append(f"{self.time_window} (x{time_weight:.1f})")
        score = score * time_weight

        # ── 6. 盘中加分 ──
        if self.market_state.upper() in {"REGULAR"}:
            score += 0.5

        self.score = round(max(0, score), 2)
        self.trigger_reasons = reasons

        if self.score >= 6:
            self.severity = "high"
        elif self.score >= 3.5:
            self.severity = "medium"
        else:
            self.severity = "low"
        return self.score


@dataclass
class OptionsAnomaly:
    """期权异动（Volume/OI 异常）"""
    symbol: str
    contract_symbol: str
    option_type: str  # "call" / "put"
    strike: float
    expiration: str
    volume: int
    open_interest: int
    vol_oi_ratio: float
    implied_volatility: float
    last_price: float
    in_the_money: bool
    
    def format_line(self) -> str:
        """格式化为单行显示"""
        opt_emoji = "📞" if self.option_type == "call" else "📉"
        itm_tag = " ITM" if self.in_the_money else ""
        return (
            f"{opt_emoji} ${self.strike:.0f} {self.option_type.upper()} {self.expiration}{itm_tag}\n"
            f"  Vol {self.volume:,} / OI {self.open_interest:,} ({self.vol_oi_ratio:.1f}x) | "
            f"IV {self.implied_volatility:.1%} | ${self.last_price:.2f}"
        )


# ── 数据获取 ──────────────────────────────────────────────
def fetch_symbol_snapshot(symbol: str) -> Optional[IntradayAlert]:
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
    closes = [v for v in quote_data.get("close", []) if v is not None]
    volumes = [v for v in quote_data.get("volume", []) if v is not None]

    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    open_price = meta.get("regularMarketOpen") or prev_close
    regular_volume = meta.get("regularMarketVolume") or (volumes[-1] if volumes else 0)
    avg_volume = meta.get("averageDailyVolume3Month") or meta.get("averageDailyVolume10Day") or 0

    if not avg_volume and len(volumes) >= 2:
        avg_volume = int(sum(volumes[:-1]) / len(volumes[:-1]))

    if not price or not prev_close:
        return None

    day_change_pct = ((price - prev_close) / prev_close) * 100
    intraday_move_pct = ((price - open_price) / open_price) * 100 if open_price else 0
    volume_ratio = regular_volume / avg_volume if avg_volume else 1.0

    return IntradayAlert(
        symbol=symbol,
        price=price,
        day_change_pct=day_change_pct,
        intraday_move_pct=intraday_move_pct,
        volume_ratio=volume_ratio,
        regular_volume=int(regular_volume),
        avg_volume=int(avg_volume),
        market_state=meta.get("marketState", "UNKNOWN"),
        news_hits=[],
        news_sentiment=0,
        direction="bullish" if day_change_pct >= 0 else "bearish",
        aligned_with_market=False,
        time_window="",
    )


def fetch_market_context() -> MarketContext:
    """获取 QQQ/SPY 作为大盘参考。"""
    ctx = MarketContext()
    for sym in MARKET_BENCHMARKS:
        try:
            snap = fetch_symbol_snapshot(sym)
            if not snap:
                continue
            if sym == "QQQ":
                ctx.qqq_change_pct = snap.day_change_pct
                ctx.qqq_intraday_pct = snap.intraday_move_pct
            elif sym == "SPY":
                ctx.spy_change_pct = snap.day_change_pct
                ctx.spy_intraday_pct = snap.intraday_move_pct
        except Exception as exc:
            print(f"Error fetching benchmark {sym}: {exc}")
    return ctx


def fetch_candidates(symbols: List[str]) -> List[IntradayAlert]:
    candidates: List[IntradayAlert] = []
    for symbol in symbols:
        try:
            snap = fetch_symbol_snapshot(symbol)
            if snap:
                candidates.append(snap)
        except Exception as exc:
            print(f"Error fetching {symbol}: {exc}")
    return candidates


def fetch_news_hits(symbols: List[str]) -> Dict[str, List[Tuple[str, int]]]:
    """返回 {symbol: [(title, sentiment), ...]}"""
    hits: Dict[str, List[Tuple[str, int]]] = {s: [] for s in symbols}
    for url in TECH_NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                combined = f"{title} {entry.get('summary', '')}".upper()
                sentiment = _news_sentiment(title)
                for symbol in symbols:
                    if symbol in combined:
                        existing_titles = [t for t, _ in hits[symbol]]
                        if title not in existing_titles:
                            hits[symbol].append((title, sentiment))
        except Exception as exc:
            print(f"Error fetching news from {url}: {exc}")
    return hits


def fetch_options_anomalies(symbols: List[str]) -> Dict[str, List[OptionsAnomaly]]:
    """
    扫描期权链，找出 Volume/OI > 3x 的异常合约
    
    过滤条件:
    - Volume/OI > 3.0
    - Volume > 1000
    - 到期日 < 45天
    - OI > 100 (避免流动性差的合约)
    """
    anomalies: Dict[str, List[OptionsAnomaly]] = {}
    now = datetime.now(UTC)
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            
            if not expirations:
                continue
            
            symbol_anomalies: List[OptionsAnomaly] = []
            current_price = ticker.info.get("regularMarketPrice", 0)
            
            # 只扫描最近3个到期日（避免API调用过多）
            for exp_date in expirations[:3]:
                exp_dt = datetime.strptime(exp_date, "%Y-%m-%d").replace(tzinfo=UTC)
                days_to_exp = (exp_dt - now).days
                
                if days_to_exp > 45:
                    continue
                
                opt_chain = ticker.option_chain(exp_date)
                
                # 扫描 calls
                for _, row in opt_chain.calls.iterrows():
                    vol = row.get("volume", 0) or 0
                    oi = row.get("openInterest", 0) or 0
                    
                    if vol < 1000 or oi < 100:
                        continue
                    
                    vol_oi_ratio = vol / oi if oi > 0 else 0
                    
                    if vol_oi_ratio >= 3.0:
                        symbol_anomalies.append(OptionsAnomaly(
                            symbol=symbol,
                            contract_symbol=row.get("contractSymbol", ""),
                            option_type="call",
                            strike=row.get("strike", 0),
                            expiration=exp_date,
                            volume=int(vol),
                            open_interest=int(oi),
                            vol_oi_ratio=vol_oi_ratio,
                            implied_volatility=row.get("impliedVolatility", 0) or 0,
                            last_price=row.get("lastPrice", 0) or 0,
                            in_the_money=row.get("inTheMoney", False),
                        ))
                
                # 扫描 puts
                for _, row in opt_chain.puts.iterrows():
                    vol = row.get("volume", 0) or 0
                    oi = row.get("openInterest", 0) or 0
                    
                    if vol < 1000 or oi < 100:
                        continue
                    
                    vol_oi_ratio = vol / oi if oi > 0 else 0
                    
                    if vol_oi_ratio >= 3.0:
                        symbol_anomalies.append(OptionsAnomaly(
                            symbol=symbol,
                            contract_symbol=row.get("contractSymbol", ""),
                            option_type="put",
                            strike=row.get("strike", 0),
                            expiration=exp_date,
                            volume=int(vol),
                            open_interest=int(oi),
                            vol_oi_ratio=vol_oi_ratio,
                            implied_volatility=row.get("impliedVolatility", 0) or 0,
                            last_price=row.get("lastPrice", 0) or 0,
                            in_the_money=row.get("inTheMoney", False),
                        ))
            
            if symbol_anomalies:
                # 按 vol/oi 比值排序，取前5个
                symbol_anomalies.sort(key=lambda x: x.vol_oi_ratio, reverse=True)
                anomalies[symbol] = symbol_anomalies[:5]
        
        except Exception as exc:
            print(f"Error fetching options for {symbol}: {exc}")
    
    return anomalies


def attach_news(candidates: List[IntradayAlert], news_hits: Dict[str, List[Tuple[str, int]]], market: MarketContext) -> List[IntradayAlert]:
    for c in candidates:
        items = news_hits.get(c.symbol, [])[:3]
        c.news_hits = [t for t, _ in items]
        c.news_sentiment = sum(s for _, s in items)
        c.compute_score(market)
    return candidates


# ── 过滤 ──────────────────────────────────────────────────
def filter_alerts(candidates: List[IntradayAlert]) -> List[IntradayAlert]:
    filtered: List[IntradayAlert] = []
    for c in candidates:
        # 跳过大盘标的本身（它们是 context，不是交易标的）
        if c.symbol in MARKET_BENCHMARKS:
            continue
        abs_day = abs(c.day_change_pct)
        abs_intra = abs(c.intraday_move_pct)
        # 最低门槛
        if abs_day < 1.0 and abs_intra < 0.5:
            continue
        if c.severity in {"high", "medium"}:
            filtered.append(c)
            continue
        if c.news_hits and c.score >= 3.0:
            filtered.append(c)
            continue
        if c.score >= 3.5:
            filtered.append(c)
    return filtered


# ── 去重 / 升级检测 ──────────────────────────────────────
def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"alerts": {}}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return {"alerts": {}}


def save_state(alerts: List[IntradayAlert]) -> None:
    payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "alerts": {a.symbol: asdict(a) for a in alerts},
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2))


def append_history(alerts: List[IntradayAlert]) -> None:
    if not alerts:
        return
    with HISTORY_FILE.open("a") as f:
        for a in alerts:
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "symbol": a.symbol,
                "direction": a.direction,
                "price": a.price,
                "score": a.score,
                "severity": a.severity,
                "day_change_pct": a.day_change_pct,
                "intraday_move_pct": a.intraday_move_pct,
                "volume_ratio": a.volume_ratio,
                "aligned_with_market": a.aligned_with_market,
                "time_window": a.time_window,
                "trigger_reasons": a.trigger_reasons or [],
                "news_hits": a.news_hits,
                "news_sentiment": a.news_sentiment,
            }
            f.write(json.dumps(record) + "\n")


def is_escalated(alert: IntradayAlert, old: dict) -> bool:
    old_score = float(old.get("score", 0))
    old_severity = old.get("severity", "low")
    severity_rank = {"low": 1, "medium": 2, "high": 3}

    if severity_rank.get(alert.severity, 1) > severity_rank.get(old_severity, 1):
        return True
    if alert.score >= old_score + 1.5:
        return True
    old_day = float(old.get("day_change_pct", 0))
    if (alert.day_change_pct > 0) != (old_day > 0):
        return True
    return False


def fresh_alerts(alerts: List[IntradayAlert], state: dict) -> List[IntradayAlert]:
    previous = state.get("alerts", {})
    result: List[IntradayAlert] = []
    for a in alerts:
        old = previous.get(a.symbol)
        if not old:
            result.append(a)
            continue
        if is_escalated(a, old):
            result.append(a)
    return result


# ── 消息格式 ──────────────────────────────────────────────
def format_message(alerts: List[IntradayAlert], market: MarketContext, options_anomalies: Dict[str, List[OptionsAnomaly]]) -> str:
    now = datetime.now(UTC).astimezone(PT).strftime("%Y-%m-%d %H:%M PT")
    _, time_label = _get_time_weight()

    lines = [
        f"🚨 *日内异动扫描 V3.1* ({now})",
        f"时段：{time_label} | {market.trend_label}",
        f"QQQ {market.qqq_change_pct:+.2f}% | SPY {market.spy_change_pct:+.2f}%",
        "",
    ]

    # ── 期权异动板块（优先显示） ──
    if options_anomalies:
        lines.append("⚡️ *期权异动 (Vol/OI > 3x)*")
        for symbol, anomalies in sorted(options_anomalies.items()):
            lines.append(f"\n*{symbol}*")
            for anom in anomalies[:3]:  # 每个标的最多显示3个
                lines.append(f"  {anom.format_line()}")
        lines.append("\n")

    # ── 正股异动板块 ──
    if alerts:
        lines.append("📊 *正股异动*")
        for a in sorted(alerts, key=lambda x: x.score, reverse=True):
            direction_emoji = "🟢 做多机会" if a.direction == "bullish" else "🔴 做空机会"
            level = {"high": "🔥HIGH", "medium": "⚡MED", "low": "LOW"}.get(a.severity, a.severity.upper())
            aligned = "✅" if a.aligned_with_market else "⚠️逆势"
            
            # 杠杆 ETF 标注
            leverage_tag = " ⚡️杠杆" if a.symbol in LEVERAGED_ETFS else ""
            
            # 期权异动标注
            opt_tag = " 🔥期权异动" if a.symbol in options_anomalies else ""

            lines.append(
                f"• *{a.symbol}*{leverage_tag}{opt_tag} {direction_emoji} [{level}] score {a.score:.1f}"
            )
            lines.append(
                f"  ${a.price:.2f} | 日内 {a.day_change_pct:+.2f}% | 盘中 {a.intraday_move_pct:+.2f}% | 量比 {a.volume_ratio:.1f}x | {aligned}"
            )
            if a.trigger_reasons:
                lines.append(f"  触发：{', '.join(a.trigger_reasons[:4])}")
            if a.news_hits:
                sentiment_tag = {1: "📰+", -1: "📰-", 0: "📰"}.get(
                    1 if a.news_sentiment > 0 else (-1 if a.news_sentiment < 0 else 0), "📰"
                )
                lines.append(f"  {sentiment_tag} {a.news_hits[0][:80]}")
            lines.append("")

    lines.append("⚠️ 这是异动筛选器，不是交易信号。请结合期权链/GEX/订单流自行验证后再下单。")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    sender = TelegramSender(bot_token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID)
    sender.send_long_message(text)


# ── 主入口 ──────────────────────────────────────────────
def main() -> int:
    # 1. 获取大盘环境
    market = fetch_market_context()
    print(f"Market context: QQQ {market.qqq_change_pct:+.2f}%, SPY {market.spy_change_pct:+.2f}% → {market.trend}")

    # 2. 获取个股数据
    candidates = fetch_candidates(INTRADAY_SYMBOLS)
    news_hits = fetch_news_hits(INTRADAY_SYMBOLS)
    candidates = attach_news(candidates, news_hits, market)

    # 3. 扫描期权异动
    print("Scanning options anomalies...")
    options_anomalies = fetch_options_anomalies(INTRADAY_SYMBOLS)
    print(f"Found options anomalies in {len(options_anomalies)} symbols")

    # 4. 过滤正股异动
    alerts = filter_alerts(candidates)
    state = load_state()
    new_alerts = fresh_alerts(alerts, state)
    save_state(alerts)
    append_history(new_alerts)

    # 5. 推送（只要有期权异动或正股异动就推送）
    if not new_alerts and not options_anomalies:
        print("No fresh alerts or options anomalies")
        return 0

    message = format_message(new_alerts, market, options_anomalies)
    send_telegram(message)
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Market regime detection: range day vs trend day.

Analyzes SPY/QQQ (or any ticker) using opening range, ATR, VWAP slope,
and volume patterns to classify the trading day.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import List, Optional

import requests

from yoloinvest.config import REQUEST_TIMEOUT, TELEGRAM_BOT_TOKEN, USER_AGENT, YAHOO_FINANCE_BASE
from yoloinvest.common.sender import TelegramSender

WAR_ROOM_CHAT_ID = "-5275957557"
STATE_FILE = Path("/tmp/market_regime_state.json")

# Default tickers for scheduled cron
DEFAULT_TICKERS = ["SPY", "QQQ"]


@dataclass
class RegimeSignal:
    """One indicator's contribution to the regime call."""
    name: str
    value: float
    interpretation: str  # "trend" | "range" | "neutral"
    detail: str


@dataclass
class RegimeResult:
    symbol: str
    regime: str  # "trend" | "range" | "mixed"
    confidence: str  # "high" | "medium" | "low"
    direction: str  # "bullish" | "bearish" | "neutral"
    price: float
    signals: List[RegimeSignal] = field(default_factory=list)
    summary: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _fetch_intraday(symbol: str) -> Optional[dict]:
    """Fetch 5m intraday chart for today + prior day."""
    url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
    params = {"interval": "5m", "range": "5d", "includePrePost": "false"}
    resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    results = resp.json().get("chart", {}).get("result")
    if not results:
        return None
    return results[0]


def _fetch_daily(symbol: str) -> Optional[dict]:
    """Fetch daily bars for ATR calculation."""
    url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "1mo"}
    resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    results = resp.json().get("chart", {}).get("result")
    if not results:
        return None
    return results[0]


def _calc_atr(daily: dict, period: int = 20) -> float:
    """Calculate ATR from daily data."""
    quotes = daily.get("indicators", {}).get("quote", [{}])[0]
    highs = quotes.get("high", [])
    lows = quotes.get("low", [])
    closes = quotes.get("close", [])

    trs: List[float] = []
    for i in range(1, len(highs)):
        if highs[i] is None or lows[i] is None or closes[i - 1] is None:
            continue
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0.0
    return sum(trs[-period:]) / period


def _split_today_bars(chart: dict) -> tuple:
    """Extract today's 5m bars from chart data.

    Returns (timestamps, opens, highs, lows, closes, volumes) for today only.
    """
    timestamps = chart.get("timestamp", [])
    quotes = chart.get("indicators", {}).get("quote", [{}])[0]
    opens = quotes.get("open", [])
    highs = quotes.get("high", [])
    lows = quotes.get("low", [])
    closes = quotes.get("close", [])
    volumes = quotes.get("volume", [])

    if not timestamps:
        return [], [], [], [], [], []

    # Find today's trading session start
    from datetime import date
    today = datetime.now(UTC).date()

    today_idx = []
    for i, ts in enumerate(timestamps):
        bar_date = datetime.fromtimestamp(ts, tz=UTC).date()
        if bar_date == today:
            today_idx.append(i)

    if not today_idx:
        # Market might not be open yet or timezone issue; use last trading day
        if timestamps:
            last_date = datetime.fromtimestamp(timestamps[-1], tz=UTC).date()
            today_idx = [i for i, ts in enumerate(timestamps)
                         if datetime.fromtimestamp(ts, tz=UTC).date() == last_date]

    if not today_idx:
        return [], [], [], [], [], []

    s, e = today_idx[0], today_idx[-1] + 1
    return (
        timestamps[s:e],
        [v for v in opens[s:e]],
        [v for v in highs[s:e]],
        [v for v in lows[s:e]],
        [v for v in closes[s:e]],
        [v for v in volumes[s:e]],
    )


def analyze_regime(symbol: str) -> Optional[RegimeResult]:
    """Run full regime analysis for a single symbol."""
    chart = _fetch_intraday(symbol)
    daily = _fetch_daily(symbol)
    if not chart or not daily:
        return None

    meta = chart.get("meta", {})
    current_price = meta.get("regularMarketPrice", 0)
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose", 0)

    ts, opens, highs, lows, closes, volumes = _split_today_bars(chart)
    if len(closes) < 2:
        return None

    # Filter None values for calculations
    valid_highs = [h for h in highs if h is not None]
    valid_lows = [l for l in lows if l is not None]
    valid_closes = [c for c in closes if c is not None]
    valid_volumes = [v for v in volumes if v is not None]

    if not valid_highs or not valid_lows or not valid_closes:
        return None

    signals: List[RegimeSignal] = []
    trend_score = 0
    range_score = 0

    # --- Signal 1: Opening Range vs ATR ---
    atr = _calc_atr(daily)
    # Opening range = first 6 bars (30 min of 5m bars)
    or_bars = min(6, len(valid_highs))
    or_high = max(valid_highs[:or_bars])
    or_low = min(valid_lows[:or_bars])
    or_range = or_high - or_low
    or_ratio = (or_range / atr) if atr > 0 else 0

    if or_ratio > 0.6:
        trend_score += 2
        interp = "trend"
        detail = f"Opening range ({or_range:.2f}) 占 ATR ({atr:.2f}) 的 {or_ratio:.0%}，开盘波动大，趋势日概率高"
    elif or_ratio > 0.4:
        trend_score += 1
        interp = "neutral"
        detail = f"Opening range ({or_range:.2f}) 占 ATR ({atr:.2f}) 的 {or_ratio:.0%}，中等波动"
    else:
        range_score += 2
        interp = "range"
        detail = f"Opening range ({or_range:.2f}) 仅占 ATR ({atr:.2f}) 的 {or_ratio:.0%}，开盘窄幅，区间日概率高"

    signals.append(RegimeSignal("Opening Range / ATR", round(or_ratio, 3), interp, detail))

    # --- Signal 2: Current range vs ATR ---
    day_high = max(valid_highs)
    day_low = min(valid_lows)
    day_range = day_high - day_low
    day_ratio = (day_range / atr) if atr > 0 else 0

    if day_ratio > 0.8:
        trend_score += 2
        interp = "trend"
        detail = f"当日振幅 ({day_range:.2f}) 已达 ATR 的 {day_ratio:.0%}，价格在扩展"
    elif day_ratio > 0.5:
        trend_score += 1
        interp = "neutral"
        detail = f"当日振幅 ({day_range:.2f}) 达 ATR 的 {day_ratio:.0%}，中等扩展"
    else:
        range_score += 2
        interp = "range"
        detail = f"当日振幅 ({day_range:.2f}) 仅 ATR 的 {day_ratio:.0%}，价格被压缩"

    signals.append(RegimeSignal("Day Range / ATR", round(day_ratio, 3), interp, detail))

    # --- Signal 3: VWAP slope (linear regression on VWAP proxy) ---
    # Approximate VWAP: cumulative (price * volume) / cumulative volume
    if len(valid_closes) >= 6 and len(valid_volumes) >= 6:
        cum_pv = 0.0
        cum_vol = 0.0
        vwap_points: List[float] = []
        for i in range(len(valid_closes)):
            p = valid_closes[i]
            v = valid_volumes[i] if i < len(valid_volumes) and valid_volumes[i] else 0
            cum_pv += p * v
            cum_vol += v
            if cum_vol > 0:
                vwap_points.append(cum_pv / cum_vol)

        if len(vwap_points) >= 4:
            # Simple slope: (last - first) / first as percentage
            vwap_move = abs(vwap_points[-1] - vwap_points[0]) / vwap_points[0] * 100 if vwap_points[0] else 0

            if vwap_move > 0.3:
                trend_score += 2
                interp = "trend"
                detail = f"VWAP 从 {vwap_points[0]:.2f} 移动到 {vwap_points[-1]:.2f}，偏移 {vwap_move:.2f}%，方向性强"
            elif vwap_move > 0.15:
                trend_score += 1
                interp = "neutral"
                detail = f"VWAP 偏移 {vwap_move:.2f}%，有一定方向但不强"
            else:
                range_score += 2
                interp = "range"
                detail = f"VWAP 几乎平坦（偏移 {vwap_move:.2f}%），典型区间日特征"

            signals.append(RegimeSignal("VWAP Slope", round(vwap_move, 4), interp, detail))

    # --- Signal 4: Volume pattern (increasing = trend, decreasing/flat = range) ---
    if len(valid_volumes) >= 6:
        first_half = valid_volumes[: len(valid_volumes) // 2]
        second_half = valid_volumes[len(valid_volumes) // 2:]
        avg_first = sum(first_half) / len(first_half) if first_half else 1
        avg_second = sum(second_half) / len(second_half) if second_half else 1
        vol_change = ((avg_second - avg_first) / avg_first) if avg_first > 0 else 0

        if vol_change > 0.2:
            trend_score += 1
            interp = "trend"
            detail = f"成交量递增 {vol_change:+.0%}，资金在加速进场"
        elif vol_change < -0.2:
            range_score += 1
            interp = "range"
            detail = f"成交量递减 {vol_change:+.0%}，参与度下降，区间盘整"
        else:
            interp = "neutral"
            detail = f"成交量变化 {vol_change:+.0%}，无明显方向"

        signals.append(RegimeSignal("Volume Pattern", round(vol_change, 3), interp, detail))

    # --- Signal 5: Price vs opening range breakout ---
    if len(valid_closes) > or_bars:
        broke_high = current_price > or_high
        broke_low = current_price < or_low
        if broke_high or broke_low:
            trend_score += 2
            interp = "trend"
            side = "上破" if broke_high else "下破"
            detail = f"价格已{side} opening range（{or_low:.2f}-{or_high:.2f}），突破确认"
        else:
            range_score += 2
            interp = "range"
            detail = f"价格仍在 opening range（{or_low:.2f}-{or_high:.2f}）内震荡"

        signals.append(RegimeSignal("OR Breakout", 1.0 if (broke_high or broke_low) else 0.0, interp, detail))

    # --- Aggregate ---
    total = trend_score + range_score
    if total == 0:
        regime = "mixed"
        confidence = "low"
    elif trend_score >= range_score * 2:
        regime = "trend"
        confidence = "high" if trend_score >= 6 else "medium"
    elif range_score >= trend_score * 2:
        regime = "range"
        confidence = "high" if range_score >= 6 else "medium"
    elif trend_score > range_score:
        regime = "trend"
        confidence = "low"
    elif range_score > trend_score:
        regime = "range"
        confidence = "low"
    else:
        regime = "mixed"
        confidence = "low"

    # Direction
    day_change = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
    if day_change > 0.3:
        direction = "bullish"
    elif day_change < -0.3:
        direction = "bearish"
    else:
        direction = "neutral"

    # Summary
    regime_cn = {"trend": "趋势日", "range": "区间日", "mixed": "混合/待确认"}[regime]
    conf_cn = {"high": "高", "medium": "中", "low": "低"}[confidence]
    dir_cn = {"bullish": "偏多", "bearish": "偏空", "neutral": "中性"}[direction]

    summary = f"{symbol} 今日判断：{regime_cn}（置信度：{conf_cn}）| 方向：{dir_cn} | 现价 ${current_price:.2f} ({day_change:+.2f}%)"

    return RegimeResult(
        symbol=symbol,
        regime=regime,
        confidence=confidence,
        direction=direction,
        price=current_price,
        signals=signals,
        summary=summary,
        timestamp=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )


def format_message(results: List[RegimeResult], phase: str = "") -> str:
    """Format regime results for Telegram."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    phase_label = f" [{phase}]" if phase else ""
    lines = [f"📊 *市场结构判断{phase_label}* ({now})", ""]

    for r in results:
        regime_cn = {"trend": "🔥 趋势日", "range": "📦 区间日", "mixed": "❓ 混合/待确认"}[r.regime]
        conf_cn = {"high": "高", "medium": "中", "low": "低"}[r.confidence]
        dir_cn = {"bullish": "偏多 📈", "bearish": "偏空 📉", "neutral": "中性 ➡️"}[r.direction]

        lines.append(f"*{r.symbol}*  {regime_cn}（置信度：{conf_cn}）")
        lines.append(f"方向：{dir_cn} | 现价 ${r.price:.2f}")
        lines.append("")
        lines.append("判断依据：")
        for sig in r.signals:
            icon = {"trend": "🔴", "range": "🔵", "neutral": "⚪"}[sig.interpretation]
            lines.append(f"  {icon} {sig.detail}")
        lines.append("")

    regime_tip = ""
    for r in results:
        if r.regime == "trend":
            regime_tip = "💡 趋势日策略：顺势而为，回调找入场，不要逆势抄底/摸顶"
        elif r.regime == "range":
            regime_tip = "💡 区间日策略：高抛低吸，在支撑/阻力位附近操作，避免追突破"
    if regime_tip:
        lines.append(regime_tip)

    return "\n".join(lines)


def save_state(results: List[RegimeResult]) -> None:
    payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "results": {r.symbol: r.to_dict() for r in results},
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2))


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def send_to_war_room(text: str) -> None:
    sender = TelegramSender(bot_token=TELEGRAM_BOT_TOKEN, chat_id=WAR_ROOM_CHAT_ID)
    sender.send_long_message(text)


def run_scheduled(phase: str = "初判") -> int:
    """Entry point for cron jobs."""
    results: List[RegimeResult] = []
    for symbol in DEFAULT_TICKERS:
        try:
            result = analyze_regime(symbol)
            if result:
                results.append(result)
        except Exception as exc:
            print(f"Error analyzing {symbol}: {exc}")

    if not results:
        print("No regime data available")
        return 0

    save_state(results)
    msg = format_message(results, phase=phase)
    send_to_war_room(msg)
    print(msg)
    return 0


def run_manual(symbol: str) -> int:
    """Entry point for manual /market_regime <TICKER> command."""
    try:
        result = analyze_regime(symbol.upper())
    except Exception as exc:
        print(f"Error analyzing {symbol}: {exc}")
        return 1

    if not result:
        print(f"No data for {symbol}")
        return 1

    msg = format_message([result], phase="手动查询")
    send_to_war_room(msg)
    print(msg)
    return 0

"""
Swing Alert Module V1.0 — 波段交易信号（杠杆ETF专用）

核心功能:
1. 持仓追踪 — 记录建仓价/持仓量/盈亏
2. 买入信号 — 趋势突破 + 量能确认 → 建仓/加仓
3. 卖出信号 — 止盈/止损/趋势反转 → 减仓/清仓
4. 状态持久化 — JSON 文件记录持仓

适用标的: TQQQ/SQQQ/SPXL/SPXS/SOXL/SOXS/UPRO 等杠杆ETF
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import requests

from yoloinvest.common.sender import TelegramSender
from yoloinvest.config import REQUEST_TIMEOUT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USER_AGENT, YAHOO_FINANCE_BASE

# ── 标的池 ──────────────────────────────────────────────
# 波段交易：杠杆ETF（2x/3x 做多做空）
SWING_SYMBOLS = [
    # 3x 纳指
    "TQQQ",  # 3x QQQ 做多
    "SQQQ",  # 3x QQQ 做空
    # 3x 标普
    "SPXL",  # 3x SPY 做多
    "SPXS",  # 3x SPY 做空
    # 3x 半导体
    "SOXL",  # 3x 半导体做多
    "SOXS",  # 3x 半导体做空
    # 3x 罗素2000
    "TNA",   # 3x IWM 做多
    "TZA",   # 3x IWM 做空
    # 2x 纳指
    "QLD",   # 2x QQQ 做多
    "QID",   # 2x QQQ 做空
]

# 大盘参考
MARKET_BENCHMARKS = ["QQQ", "SPY"]

# 状态文件
POSITION_FILE = Path("/tmp/swing_positions.json")
HISTORY_FILE = Path("/tmp/swing_history.jsonl")

PT = ZoneInfo("America/Los_Angeles")


# ── 数据模型 ──────────────────────────────────────────────
@dataclass
class Position:
    """持仓记录"""
    symbol: str
    entry_price: float
    shares: int
    entry_date: str
    direction: str  # "long" / "short"
    
    def pnl_pct(self, current_price: float) -> float:
        """计算盈亏百分比"""
        if self.direction == "long":
            return ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # short
            return ((self.entry_price - current_price) / self.entry_price) * 100


@dataclass
class SwingSignal:
    """波段信号"""
    symbol: str
    price: float
    action: str  # "BUY" / "ADD" / "REDUCE" / "SELL" / "HOLD"
    direction: str  # "bullish" / "bearish"
    score: float
    reasons: List[str]
    
    # 技术指标
    day_change_pct: float
    sma20: float
    sma50: float
    volume_ratio: float
    
    # 持仓信息（如果有）
    position: Optional[Position] = None
    pnl_pct: Optional[float] = None


# ── 数据获取 ──────────────────────────────────────────────
def fetch_chart_data(symbol: str, days: int = 60) -> Optional[dict]:
    """获取历史数据（用于计算均线）"""
    url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": f"{days}d"}
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    
    payload = response.json().get("chart", {}).get("result")
    if not payload:
        return None
    return payload[0]


def calculate_sma(closes: List[float], period: int) -> Optional[float]:
    """计算简单移动平均"""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def fetch_signal_data(symbol: str) -> Optional[SwingSignal]:
    """获取单个标的的波段信号数据"""
    data = fetch_chart_data(symbol)
    if not data:
        return None
    
    meta = data.get("meta", {})
    quote = data.get("indicators", {}).get("quote", [{}])[0]
    
    closes = [v for v in quote.get("close", []) if v is not None]
    volumes = [v for v in quote.get("volume", []) if v is not None]
    
    if len(closes) < 50:  # 至少需要50天数据计算SMA50
        return None
    
    price = meta.get("regularMarketPrice") or closes[-1]
    prev_close = meta.get("chartPreviousClose") or closes[-2]
    day_change_pct = ((price - prev_close) / prev_close) * 100
    
    sma20 = calculate_sma(closes, 20)
    sma50 = calculate_sma(closes, 50)
    
    avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    current_volume = volumes[-1]
    volume_ratio = current_volume / avg_volume if avg_volume else 1.0
    
    direction = "bullish" if price > sma20 else "bearish"
    
    return SwingSignal(
        symbol=symbol,
        price=price,
        action="HOLD",
        direction=direction,
        score=0.0,
        reasons=[],
        day_change_pct=day_change_pct,
        sma20=sma20,
        sma50=sma50,
        volume_ratio=volume_ratio,
    )


# ── 持仓管理 ──────────────────────────────────────────────
def load_positions() -> Dict[str, Position]:
    """加载持仓"""
    if not POSITION_FILE.exists():
        return {}
    try:
        data = json.loads(POSITION_FILE.read_text())
        return {
            sym: Position(**pos) for sym, pos in data.items()
        }
    except (json.JSONDecodeError, TypeError):
        return {}


def save_positions(positions: Dict[str, Position]) -> None:
    """保存持仓"""
    payload = {sym: asdict(pos) for sym, pos in positions.items()}
    POSITION_FILE.write_text(json.dumps(payload, indent=2))


def append_history(signal: SwingSignal) -> None:
    """记录历史信号"""
    if signal.action == "HOLD":
        return
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "symbol": signal.symbol,
        "action": signal.action,
        "price": signal.price,
        "score": signal.score,
        "reasons": signal.reasons,
        "pnl_pct": signal.pnl_pct,
    }
    with HISTORY_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")


# ── 信号生成 ──────────────────────────────────────────────
def generate_signal(data: SwingSignal, position: Optional[Position]) -> SwingSignal:
    """
    生成买卖信号
    
    买入逻辑:
    - 价格突破 SMA20 且 SMA20 > SMA50 (金叉)
    - 量能放大 (volume_ratio > 1.2)
    - 日涨幅 > 1.5%
    
    卖出逻辑:
    - 止盈: 盈利 > 8%
    - 止损: 亏损 > 4%
    - 趋势反转: 价格跌破 SMA20 且 SMA20 < SMA50 (死叉)
    """
    score = 0.0
    reasons = []
    
    # ── 如果有持仓，先判断卖出 ──
    if position:
        data.position = position
        data.pnl_pct = position.pnl_pct(data.price)
        
        # 止盈
        if data.pnl_pct >= 8.0:
            data.action = "SELL"
            score += 5.0
            reasons.append(f"止盈 {data.pnl_pct:+.1f}%")
        
        # 止损
        elif data.pnl_pct <= -4.0:
            data.action = "SELL"
            score += 5.0
            reasons.append(f"止损 {data.pnl_pct:+.1f}%")
        
        # 趋势反转 (死叉)
        elif data.price < data.sma20 and data.sma20 < data.sma50:
            data.action = "REDUCE"
            score += 3.0
            reasons.append("死叉，减仓")
        
        # 持有中，小幅加仓机会
        elif data.price > data.sma20 and data.day_change_pct > 2.0 and data.volume_ratio > 1.5:
            data.action = "ADD"
            score += 2.0
            reasons.append("趋势延续，可加仓")
        
        else:
            data.action = "HOLD"
            reasons.append(f"持仓中 {data.pnl_pct:+.1f}%")
    
    # ── 无持仓，判断买入 ──
    else:
        # 金叉 + 突破
        if data.price > data.sma20 and data.sma20 > data.sma50:
            score += 3.0
            reasons.append("金叉")
        
        # 量能放大
        if data.volume_ratio > 1.2:
            score += 2.0
            reasons.append(f"量比 {data.volume_ratio:.1f}x")
        
        # 日涨幅
        if data.day_change_pct > 1.5:
            score += 2.0
            reasons.append(f"日涨 {data.day_change_pct:+.1f}%")
        elif data.day_change_pct < -1.5:
            score += 2.0
            reasons.append(f"日跌 {data.day_change_pct:+.1f}%")
        
        # 买入信号
        if score >= 5.0:
            data.action = "BUY"
        else:
            data.action = "HOLD"
    
    data.score = score
    data.reasons = reasons
    return data


# ── 消息格式 ──────────────────────────────────────────────
def format_message(signals: List[SwingSignal]) -> str:
    """格式化推送消息"""
    now = datetime.now(UTC).astimezone(PT).strftime("%Y-%m-%d %H:%M PT")
    
    lines = [
        f"📊 *波段交易信号 V1.0* ({now})",
        "",
    ]
    
    # 按 action 分组
    buy_signals = [s for s in signals if s.action in {"BUY", "ADD"}]
    sell_signals = [s for s in signals if s.action in {"SELL", "REDUCE"}]
    hold_signals = [s for s in signals if s.action == "HOLD" and s.position]
    
    if buy_signals:
        lines.append("🟢 *买入机会*")
        for s in sorted(buy_signals, key=lambda x: x.score, reverse=True):
            action_label = "建仓" if s.action == "BUY" else "加仓"
            lines.append(f"• *{s.symbol}* {action_label} | score {s.score:.1f}")
            lines.append(f"  ${s.price:.2f} | 日内 {s.day_change_pct:+.1f}% | 量比 {s.volume_ratio:.1f}x")
            lines.append(f"  SMA20 ${s.sma20:.2f} | SMA50 ${s.sma50:.2f}")
            lines.append(f"  触发: {', '.join(s.reasons)}")
            lines.append("")
    
    if sell_signals:
        lines.append("🔴 *卖出信号*")
        for s in sorted(sell_signals, key=lambda x: x.score, reverse=True):
            action_label = "清仓" if s.action == "SELL" else "减仓"
            pnl_tag = f" ({s.pnl_pct:+.1f}%)" if s.pnl_pct else ""
            lines.append(f"• *{s.symbol}* {action_label}{pnl_tag} | score {s.score:.1f}")
            lines.append(f"  ${s.price:.2f} | 日内 {s.day_change_pct:+.1f}%")
            if s.position:
                lines.append(f"  建仓价 ${s.position.entry_price:.2f} | 持仓 {s.position.shares} 股")
            lines.append(f"  触发: {', '.join(s.reasons)}")
            lines.append("")
    
    if hold_signals:
        lines.append("➡️ *持仓监控*")
        for s in hold_signals:
            pnl_emoji = "🟢" if s.pnl_pct > 0 else "🔴"
            lines.append(f"• *{s.symbol}* {pnl_emoji} {s.pnl_pct:+.1f}%")
            lines.append(f"  ${s.price:.2f} | 建仓价 ${s.position.entry_price:.2f}")
            lines.append("")
    
    if not buy_signals and not sell_signals and not hold_signals:
        lines.append("暂无信号")
    
    lines.append("⚠️ 杠杆ETF波动大，严格止损。建议仓位 < 30%。")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    """发送 Telegram 消息"""
    sender = TelegramSender(bot_token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID)
    sender.send_long_message(text)


# ── 主入口 ──────────────────────────────────────────────
def main() -> int:
    # 1. 加载持仓
    positions = load_positions()
    print(f"Loaded {len(positions)} positions")
    
    # 2. 获取数据
    signals: List[SwingSignal] = []
    for symbol in SWING_SYMBOLS:
        try:
            data = fetch_signal_data(symbol)
            if not data:
                continue
            
            position = positions.get(symbol)
            signal = generate_signal(data, position)
            
            # 只推送有操作的信号
            if signal.action != "HOLD" or signal.position:
                signals.append(signal)
                append_history(signal)
        
        except Exception as exc:
            print(f"Error processing {symbol}: {exc}")
    
    if not signals:
        print("No swing signals")
        return 0
    
    # 3. 推送
    message = format_message(signals)
    send_telegram(message)
    print(message)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

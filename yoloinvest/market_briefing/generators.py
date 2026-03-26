"""Report generators for the market briefing module."""
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple


class ReportGenerator:
    def __init__(self, brand_name: str = "YoloInvest"):
        self.brand_name = brand_name

    @staticmethod
    def _quote_line(label: str, quote: Dict, bold: bool = False) -> str:
        emoji = "🟢" if quote.get("change", 0) >= 0 else "🔴"
        price = quote.get("price", 0)
        change_pct = quote.get("change_percent", quote.get("changePercent", 0))
        vol = quote.get("volume")
        label_text = f"*{label}*" if bold else label
        base = f"{emoji} {label_text}: ${price:.2f} ({change_pct:+.2f}%)"
        if vol is not None:
            vol_str = f"{vol/1e6:.1f}M" if vol else "N/A"
            return f"{base} Vol: {vol_str}"
        return base

    @staticmethod
    def _extract_market_dates(market_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        candidates = []
        for section in ("stocks", "crypto", "commodities"):
            section_data = market_data.get(section, {})
            values: Iterable[Dict]
            if section == "stocks":
                values = (
                    quote
                    for category_quotes in section_data.values()
                    for quote in category_quotes.values()
                )
            else:
                values = section_data.values()
            for quote in values:
                price_date = quote.get("price_date")
                previous_date = quote.get("previous_close_date")
                if price_date or previous_date:
                    candidates.append((price_date, previous_date))
        return candidates[0] if candidates else (None, None)

    @staticmethod
    def _format_date(date_str: Optional[str]) -> str:
        if not date_str:
            return "未知交易日"
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y年%m月%d日")
        except ValueError:
            return date_str

    def generate_detailed(self, data: Dict) -> str:
        market_data = data.get("market_data", {})
        price_date, previous_date = self._extract_market_dates(market_data)
        price_date_text = self._format_date(price_date)
        previous_date_text = self._format_date(previous_date)

        today = datetime.now().strftime("%Y年%m月%d日")
        lines = [f"📊 *{self.brand_name} 市场简报 - {today}*\n"]

        # Sentiment Dashboard — very top for instant mood read
        sentiment = data.get("sentiment", {})
        vix_data = sentiment.get("vix", {})
        fng_data = sentiment.get("fear_greed", {})
        sentiment_summary = sentiment.get("summary", "")

        if vix_data or fng_data:
            lines.append("🌡 *盘前情绪仪表盘*")
            if vix_data:
                vix_val = vix_data.get("current", "N/A")
                vix_pct = vix_data.get("percentile_30d", "N/A")
                vix_label = vix_data.get("label", "")
                lines.append(f"  VIX: {vix_val}（近30日 {vix_pct:.0f}% 分位，{vix_label}）")
            if fng_data:
                fng_score = fng_data.get("score", "N/A")
                fng_rating_cn = fng_data.get("rating_cn", "")
                fng_prev = fng_data.get("previous_close", "")
                fng_week = fng_data.get("previous_1_week", "")
                lines.append(f"  Fear & Greed: {fng_score} / {fng_rating_cn}（昨日 {fng_prev}，上周 {fng_week}）")
            if sentiment_summary:
                lines.append(f"  → {sentiment_summary}")
            lines.append("")

        # Futures & VIX — top of report for immediate sentiment read
        if market_data.get("futures_vix"):
            lines.append("📡 *盘前 Futures & VIX*")
            for name, quote in market_data["futures_vix"].items():
                emoji = "🟢" if quote.get("change", 0) >= 0 else "🔴"
                price = quote.get("price", 0)
                change_pct = quote.get("change_percent", 0)
                if "VIX" in name:
                    # VIX: show level + change, flag elevated levels
                    vix_flag = ""
                    if price >= 30:
                        vix_flag = " 🚨 极度恐慌"
                    elif price >= 25:
                        vix_flag = " ⚠️ 恐慌偏高"
                    elif price >= 20:
                        vix_flag = " 📈 偏高"
                    elif price <= 13:
                        vix_flag = " 😴 极度平静"
                    lines.append(f"  {emoji} *{name}*: {price:.2f} ({change_pct:+.2f}%){vix_flag}")
                else:
                    lines.append(f"  {emoji} *{name}*: {price:.2f} ({change_pct:+.2f}%)")
            lines.append("")

        if "analysis" in data:
            lines.append("📰 *新闻影响分析*")
            lines.append(data["analysis"])
            lines.append("\n" + "=" * 50 + "\n")

        if data.get("earnings"):
            lines.append("📅 *本周财报日历*")
            by_date = defaultdict(list)
            for event in data["earnings"]:
                by_date[event["date"]].append(event)
            for date in sorted(by_date.keys()):
                lines.append(f"\n*{date}*")
                for event in by_date[date]:
                    lines.append(f"  • {event['symbol']}: {event['name']}")
            lines.append("\n" + "=" * 50 + "\n")

        if data.get("economic_calendar"):
            # Separate today's critical events from the rest
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_critical = [
                e for e in data["economic_calendar"]
                if e.get("date_short", e.get("date", "")[:10]) == today_str and e.get("critical")
            ]
            if today_critical:
                lines.append("🚨 *今日重大事件*")
                for event in today_critical:
                    line = f"  🔴 {event['event']}"
                    details = []
                    if event.get("forecast"):
                        details.append(f"预期: {event['forecast']}")
                    if event.get("previous"):
                        details.append(f"前值: {event['previous']}")
                    if details:
                        line += f" ({' | '.join(details)})"
                    lines.append(line)
                lines.append("")

            lines.append("📅 *本周重要经济数据*")
            for event in data["economic_calendar"]:
                date_display = event.get("date_short", event.get("date", "")[:10])
                impact = event.get("impact", "")
                impact_emoji = "🔴" if impact == "High" else "🟡" if impact == "Medium" else "⚪"
                line = f"  {impact_emoji} {date_display}: {event['event']}"
                details = []
                if event.get("forecast"):
                    details.append(f"预期: {event['forecast']}")
                if event.get("previous"):
                    details.append(f"前值: {event['previous']}")
                if details:
                    line += f" ({' | '.join(details)})"
                lines.append(line)
            lines.append("\n" + "=" * 50 + "\n")

        if market_data.get("crypto"):
            lines.append("💰 *加密货币市场*")
            for symbol, quote in market_data["crypto"].items():
                lines.append(self._quote_line(symbol, quote, bold=True))
            lines.append("")

        if market_data.get("commodities"):
            lines.append("🛢️ *大宗商品*")
            for name, quote in market_data["commodities"].items():
                lines.append(self._quote_line(name, quote, bold=True))
            lines.append("")

        if market_data.get("stocks"):
            for category, stocks in market_data["stocks"].items():
                lines.append(f"📈 *{category}板块*")
                for symbol, quote in stocks.items():
                    lines.append(self._quote_line(symbol, quote))
                lines.append("")

        lines.append("=" * 50)
        lines.append("")
        lines.append("🧮 *计算说明*")
        lines.append(f"• 价格：采用 {price_date_text} 的收盘价")
        lines.append(f"• 涨跌幅：{price_date_text} 收盘价相对 {previous_date_text} 收盘价的变化百分比")
        lines.append(f"• 成交量：采用 {price_date_text} 的总成交量")

        return "\n".join(lines)

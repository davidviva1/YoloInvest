"""AI analyzers for the market briefing module."""
from abc import ABC, abstractmethod
from typing import Dict
import json

import requests

from yoloinvest.config import FOCUS_STOCKS, LLM_API_BASE, LLM_API_KEY, LLM_MODEL


class Analyzer(ABC):
    @abstractmethod
    def analyze(self, data: Dict) -> str:
        raise NotImplementedError


class AINewsAnalyzer(Analyzer):
    def _build_prompt(self, news: Dict, market_data: Dict, economic_data: Dict | None = None) -> str:
        economic_section = ""
        today_critical_section = ""
        if economic_data and economic_data.get("calendar"):
            from datetime import datetime as _dt

            today_str = _dt.now().strftime("%Y-%m-%d")
            today_critical = [
                e for e in economic_data["calendar"]
                if e.get("date_short", e.get("date", "")[:10]) == today_str and e.get("critical")
            ]
            all_events = economic_data["calendar"]

            if today_critical:
                today_critical_section = f"""

## ⚠️ 今日重大事件（必须重点分析）
{json.dumps(today_critical, indent=2, ensure_ascii=False)}
请在宏观影响分析的最开头，用醒目的方式说明今日有哪些重大事件、预期影响、以及交易者需要注意的时间点和风险。
"""

            economic_section = f"""

## 本周重要经济数据发布（含 impact 级别和预测值）
{json.dumps(all_events, indent=2, ensure_ascii=False)}
"""

        futures_section = ""
        futures_vix = market_data.get("futures_vix", {})
        if futures_vix:
            futures_section = f"""

## 盘前 Futures & VIX（实时快照）
{json.dumps(futures_vix, indent=2, ensure_ascii=False)}
请在宏观影响分析中结合 futures 方向和 VIX 水平判断今日开盘情绪。VIX ≥ 25 表示恐慌偏高，≥ 30 极度恐慌，≤ 13 极度平静。
"""

        focus_stocks_text = "、".join(FOCUS_STOCKS)
        return f"""你是一位资深的美股分析师。请分析以下新闻和经济数据对美股市场的影响。

## 当前市场数据
{json.dumps(market_data, indent=2, ensure_ascii=False)}
{futures_section}
## 最新新闻
{json.dumps(news, indent=2, ensure_ascii=False)}
{today_critical_section}
{economic_section}

请提供：
1. **宏观影响分析**：这些新闻和即将发布的经济数据对整体市场情绪的影响（看涨/看跌/中性）。如果今日有重大事件（如 FOMC 利率决议、CPI、非农等），必须在最开头醒目标注，并说明预期时间、市场预期、以及对盘中交易的影响。
2. **板块影响**：科技、芯片、数据中心、电力/能源、稀土
3. **重点个股分析**：必须包含 **{focus_stocks_text}**
   - 对于 SPY 和 QQQ，必须列出以下关键价位（从市场数据中提取）：
     • 前日收盘价 (previous_close)
     • 盘前高点 (premarket_high)
     • 盘前低点 (premarket_low)
     • 昨日高点 (prev_day_high)
     • 昨日低点 (prev_day_low)
   - 对于其他重点个股，给出技术面关键价位和交易建议
4. **加密货币影响**：BTC/ETH 的潜在走势
5. **大宗商品影响**：原油、黄金、铜、白银、天然气的潜在走势

请用简洁、专业的语言，每个板块 2-3 句话即可。"""

    def analyze(self, data: Dict) -> str:
        news = data.get("news", {})
        market_data = data.get("market_data", {})
        economic_data = data.get("economic_data")
        prompt = self._build_prompt(news, market_data, economic_data)

        try:
            if not LLM_API_KEY:
                raise RuntimeError("LLM_API_KEY is not set")
            response = requests.post(
                f"{LLM_API_BASE}/v1/messages",
                headers={
                    "x-api-key": LLM_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"]
        except Exception as exc:
            print(f"Error calling LLM API: {exc}")
            return "新闻分析暂时不可用"

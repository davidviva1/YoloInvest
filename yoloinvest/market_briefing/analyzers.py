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
        if economic_data and economic_data.get("calendar"):
            economic_section = f"""

## 本周重要经济数据发布
{json.dumps(economic_data['calendar'], indent=2, ensure_ascii=False)}
"""

        focus_stocks_text = "、".join(FOCUS_STOCKS)
        return f"""你是一位资深的美股分析师。请分析以下新闻和经济数据对美股市场的影响。

## 当前市场数据
{json.dumps(market_data, indent=2, ensure_ascii=False)}

## 最新新闻
{json.dumps(news, indent=2, ensure_ascii=False)}
{economic_section}

请提供：
1. **宏观影响分析**：这些新闻和即将发布的经济数据对整体市场情绪的影响（看涨/看跌/中性）
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
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"]
        except Exception as exc:
            print(f"Error calling LLM API: {exc}")
            return "新闻分析暂时不可用"

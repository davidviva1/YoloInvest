"""
Analyzers - 分析层
使用策略模式，易于扩展不同的分析方法
"""
from abc import ABC, abstractmethod
from typing import Dict
import requests
import json

from config import FOCUS_STOCKS, LLM_API_BASE, LLM_API_KEY, LLM_MODEL


class Analyzer(ABC):
    """分析器基类"""

    @abstractmethod
    def analyze(self, data: Dict) -> str:
        """分析数据并返回结果"""
        pass


class AINewsAnalyzer(Analyzer):
    """AI 新闻分析器"""

    def _build_prompt(self, news: Dict, market_data: Dict, economic_data: Dict = None) -> str:
        """构建分析提示词"""
        economic_section = ""
        if economic_data and economic_data.get("calendar"):
            economic_section = f"""

## 本周重要经济数据发布
{json.dumps(economic_data['calendar'], indent=2, ensure_ascii=False)}
"""

        focus_stocks_text = "、".join(FOCUS_STOCKS)

        prompt = f"""你是一位资深的美股分析师。请分析以下新闻和经济数据对美股市场的影响。

## 当前市场数据
{json.dumps(market_data, indent=2, ensure_ascii=False)}

## 最新新闻
{json.dumps(news, indent=2, ensure_ascii=False)}
{economic_section}

请提供：
1. **宏观影响分析**：这些新闻和即将发布的经济数据对整体市场情绪的影响（看涨/看跌/中性）
   - 如果有重要经济数据即将发布（如CPI、非农、FOMC），请重点分析其潜在影响
   - 分析当前通胀、利率、就业等宏观环境对市场的影响
2. **板块影响**：
   - 科技板块（AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA）
   - 芯片板块（AVGO, MRVL, TSM, AMD, INTC, QCOM等）
   - 数据中心板块（APLD, GEV, EQIX, DLR等）
   - 电力/能源板块（NNE, VST, CEG等）
   - 稀土板块（MP, USAR, REE等）
3. **重点个股分析**：
   - **{focus_stocks_text}**：必须详细分析这些股票
   - 其他受新闻影响较大的股票
4. **加密货币影响**：BTC/ETH 的潜在走势
5. **大宗商品影响**：原油、黄金、铜、白银、天然气的潜在走势

请用简洁、专业的语言，每个板块 2-3 句话即可。重点个股必须包含且详细分析。"""

        return prompt

    def analyze(self, data: Dict) -> str:
        """使用 Claude 兼容接口分析新闻影响"""
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
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return "新闻分析暂时不可用"

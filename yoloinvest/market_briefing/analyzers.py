"""AI analyzers for the market briefing module."""
from abc import ABC, abstractmethod
from typing import Dict
import json

import requests
import time

from yoloinvest.config import FOCUS_STOCKS, LLM_API_BASE, LLM_API_KEY, LLM_MODEL


class Analyzer(ABC):
    @abstractmethod
    def analyze(self, data: Dict) -> str:
        raise NotImplementedError


class AINewsAnalyzer(Analyzer):

    @staticmethod
    def _slim_market_data(market_data: Dict) -> Dict:
        """Strip market_data to only the fields the LLM needs."""
        slim = {"timestamp": market_data.get("timestamp", "")}

        # Futures & VIX — keep full (small)
        if market_data.get("futures_vix"):
            slim["futures_vix"] = {
                name: {k: q[k] for k in ("symbol", "price", "change_percent") if k in q}
                for name, q in market_data["futures_vix"].items()
            }

        # Stocks — only price, change%, and key levels for focus stocks
        focus = set(FOCUS_STOCKS)
        if market_data.get("stocks"):
            slim["stocks"] = {}
            for category, stocks in market_data["stocks"].items():
                cat_slim = {}
                for sym, q in stocks.items():
                    entry = {"price": q.get("price"), "chg%": q.get("change_percent")}
                    if sym in focus:
                        for k in ("previous_close", "prev_day_high", "prev_day_low",
                                  "premarket_high", "premarket_low"):
                            if q.get(k) is not None:
                                entry[k] = q[k]
                    cat_slim[sym] = entry
                slim["stocks"][category] = cat_slim

        # Crypto — price + change%
        if market_data.get("crypto"):
            slim["crypto"] = {
                sym: {"price": q.get("price"), "chg%": q.get("change_percent")}
                for sym, q in market_data["crypto"].items()
            }

        # Commodities — price + change%
        if market_data.get("commodities"):
            slim["commodities"] = {
                name: {"price": q.get("price"), "chg%": q.get("change_percent")}
                for name, q in market_data["commodities"].items()
            }

        return slim

    @staticmethod
    def _slim_news(news: Dict) -> str:
        """Flatten news to title-only bullets grouped by category."""
        lines = []
        for category, items in news.items():
            if not items:
                continue
            titles = [it.get("title", "") for it in items if it.get("title")]
            if titles:
                lines.append(f"[{category}]")
                for t in titles:
                    lines.append(f"- {t}")
        return "\n".join(lines)

    @staticmethod
    def _slim_economic(economic_data: Dict) -> tuple[str, str]:
        """Return (today_critical_text, calendar_text) as compact strings."""
        from datetime import datetime as _dt
        calendar = economic_data.get("calendar", [])
        if not calendar:
            return "", ""

        today_str = _dt.now().strftime("%Y-%m-%d")
        critical_lines = []
        cal_lines = []
        for e in calendar:
            date_s = e.get("date_short", e.get("date", "")[:10])
            impact = e.get("impact", "")
            evt = e.get("event", "")
            parts = [f"{date_s} [{impact}] {evt}"]
            if e.get("forecast"):
                parts.append(f"预期:{e['forecast']}")
            if e.get("previous"):
                parts.append(f"前值:{e['previous']}")
            line = " | ".join(parts)
            cal_lines.append(line)
            if date_s == today_str and e.get("critical"):
                critical_lines.append(line)
        return "\n".join(critical_lines), "\n".join(cal_lines)

    def _build_prompt(self, news: Dict, market_data: Dict, economic_data: Dict | None = None) -> str:
        slim_mkt = json.dumps(self._slim_market_data(market_data), ensure_ascii=False)
        slim_news = self._slim_news(news)
        today_critical, eco_cal = self._slim_economic(economic_data) if economic_data else ("", "")

        today_block = ""
        if today_critical:
            today_block = f"""
⚠️ 今日重大事件:
{today_critical}
"""

        eco_block = ""
        if eco_cal:
            eco_block = f"""
本周经济日历:
{eco_cal}
"""

        focus_stocks_text = "、".join(FOCUS_STOCKS)
        return f"""你是资深美股分析师。根据以下数据分析市场影响。

## 市场数据
{slim_mkt}

## 新闻标题
{slim_news}
{today_block}{eco_block}
## 分析要求
1. **宏观影响**（看涨/看跌/中性）。今日若有重大事件（FOMC/CPI/非农等）须醒目标注时间、预期和风险。结合 futures 方向和 VIX（≥25恐慌偏高，≥30极度恐慌，≤13极度平静）判断开盘情绪。
2. **板块影响**：科技、芯片、数据中心、电力/能源、稀土（各2-3句）
3. **重点个股 {focus_stocks_text}**：SPY/QQQ 须列出 previous_close / premarket_high / premarket_low / prev_day_high / prev_day_low；其他个股给关键价位和交易建议
4. **加密货币**：BTC/ETH 走势
5. **大宗商品**：原油、黄金、铜、白银、天然气走势

简洁专业，直接输出分析。"""

    def analyze(self, data: Dict) -> str:
        news = data.get("news", {})
        market_data = data.get("market_data", {})
        economic_data = data.get("economic_data")
        prompt = self._build_prompt(news, market_data, economic_data)

        if not LLM_API_KEY:
            print("Error: LLM_API_KEY is not set")
            return "新闻分析暂时不可用"

        max_retries = 1
        last_error = None
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{LLM_API_BASE}/v1/messages",
                    headers={
                        "Authorization": "Bearer " + LLM_API_KEY,
                        "AI-Resource": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": LLM_MODEL,
                        "max_tokens": 2000,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=120,
                )
                if response.status_code == 503 and attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"API 503, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                result = response.json()
                # Find first text block (skip thinking blocks from MiniMax)
                for block in result.get("content", []):
                    if block.get("type") == "text":
                        return block["text"]
                return "新闻分析暂时不可用"
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"API error: {exc}, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                print(f"Error calling LLM API after {max_retries} attempts: {exc}")
                return "新闻分析暂时不可用"

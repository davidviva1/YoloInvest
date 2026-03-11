"""
Data Fetchers - 数据获取层
遵循开闭原则，易于扩展新的数据源
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import requests
import feedparser
from datetime import datetime

from models import Quote, NewsItem, EarningsEvent, EconomicEvent
from config import (
    YAHOO_FINANCE_BASE, REQUEST_TIMEOUT, USER_AGENT,
    STOCKS, CRYPTO_SYMBOLS, COMMODITIES, NEWS_SOURCES
)


class DataFetcher(ABC):
    """数据获取器基类"""

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self.headers = {"User-Agent": USER_AGENT}

    @abstractmethod
    def fetch(self) -> any:
        """获取数据"""
        pass


class YahooFinanceFetcher(DataFetcher):
    """Yahoo Finance 数据获取器"""

    @staticmethod
    def _extract_daily_series(result: Dict) -> Tuple[List[str], List[float], List[Optional[int]]]:
        timestamps = result.get("timestamp", [])
        quote_data = result.get("indicators", {}).get("quote", [{}])[0]
        closes = quote_data.get("close", [])
        volumes = quote_data.get("volume", [])

        dates = []
        valid_closes = []
        valid_volumes = []

        for ts, close, volume in zip(timestamps, closes, volumes):
            if close is None:
                continue
            dates.append(datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"))
            valid_closes.append(close)
            valid_volumes.append(volume)

        return dates, valid_closes, valid_volumes

    def fetch_quote(self, symbol: str) -> Optional[Quote]:
        """获取单个标的报价"""
        try:
            url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
            params = {"interval": "1d", "range": "10d", "includePrePost": "false"}

            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            data = response.json()

            if "chart" not in data or not data["chart"].get("result"):
                return None

            result = data["chart"]["result"][0]
            dates, closes, volumes = self._extract_daily_series(result)

            if len(closes) >= 2:
                price = closes[-1]
                previous_close = closes[-2]
                price_date = dates[-1]
                previous_close_date = dates[-2]
                volume = volumes[-1]
            elif len(closes) == 1:
                price = closes[-1]
                previous_close = closes[-1]
                price_date = dates[-1]
                previous_close_date = dates[-1]
                volume = volumes[-1]
            else:
                return None

            change = price - previous_close
            change_pct = (change / previous_close * 100) if previous_close else 0

            return Quote(
                symbol=symbol,
                price=price,
                change=change,
                change_percent=change_pct,
                volume=volume,
                previous_close=previous_close,
                price_date=price_date,
                previous_close_date=previous_close_date,
            )

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def fetch(self) -> Dict:
        """获取所有市场数据"""
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "stocks": {},
            "crypto": {},
            "commodities": {}
        }

        for category, symbols in STOCKS.items():
            result["stocks"][category] = {}
            for symbol in symbols:
                quote = self.fetch_quote(symbol)
                if quote:
                    result["stocks"][category][symbol] = quote.__dict__

        for crypto in CRYPTO_SYMBOLS:
            quote = self.fetch_quote(f"{crypto}-USD")
            if quote:
                result["crypto"][crypto] = quote.__dict__

        for name, symbol in COMMODITIES.items():
            quote = self.fetch_quote(symbol)
            if quote:
                result["commodities"][name] = quote.__dict__

        return result


class RSSNewsFetcher(DataFetcher):
    """RSS 新闻获取器"""

    def fetch_feed(self, url: str, max_items: int = 5) -> List[NewsItem]:
        """获取单个 RSS feed"""
        try:
            feed = feedparser.parse(url)
            items = []

            for entry in feed.entries[:max_items]:
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    link=entry.get("link", ""),
                    published=entry.get("published", ""),
                    summary=entry.get("summary", "")[:200]
                ))

            return items

        except Exception as e:
            print(f"Error fetching RSS {url}: {e}")
            return []

    def fetch(self) -> Dict[str, List[Dict]]:
        """获取所有新闻"""
        result = {}

        for category, urls in NEWS_SOURCES.items():
            result[category] = []
            for url in urls:
                items = self.fetch_feed(url, max_items=5)
                result[category].extend([item.__dict__ for item in items])

        return result


class EarningsCalendarFetcher(DataFetcher):
    """财报日历获取器（占位实现）"""

    def fetch(self) -> List[Dict]:
        """获取财报日历"""
        return []


class EconomicDataFetcher(DataFetcher):
    """经济数据获取器（占位实现）"""

    def fetch(self) -> Dict:
        """获取经济数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "indicators": {},
            "calendar": [
                {
                    "date": "2026-03-10",
                    "event": "CPI (Consumer Price Index)",
                    "importance": "High",
                    "forecast": "0.3% MoM",
                    "previous": "0.4% MoM"
                },
                {
                    "date": "2026-03-12",
                    "event": "PPI (Producer Price Index)",
                    "importance": "Medium",
                    "forecast": "0.2% MoM",
                    "previous": "0.3% MoM"
                },
                {
                    "date": "2026-03-14",
                    "event": "Retail Sales",
                    "importance": "High",
                    "forecast": "0.5% MoM",
                    "previous": "0.6% MoM"
                }
            ]
        }

"""Shared data models for YoloInvest."""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Quote:
    """股票/加密货币/商品报价"""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: Optional[int]
    previous_close: float
    price_date: Optional[str] = None
    previous_close_date: Optional[str] = None

    @property
    def is_up(self) -> bool:
        return self.change >= 0


@dataclass
class NewsItem:
    title: str
    link: str
    published: str
    summary: str


@dataclass
class EarningsEvent:
    symbol: str
    name: str
    date: str
    time: Optional[str] = None


@dataclass
class EconomicEvent:
    date: str
    event: str
    importance: str
    forecast: Optional[str] = None
    previous: Optional[str] = None


@dataclass
class MarketData:
    timestamp: str
    stocks: Dict[str, Dict[str, Quote]]
    crypto: Dict[str, Quote]
    commodities: Dict[str, Quote]

    def get_all_stocks(self) -> List[tuple[str, Quote]]:
        result = []
        for _, stocks in self.stocks.items():
            for symbol, quote in stocks.items():
                result.append((symbol, quote))
        return result

    def get_top_gainers(self, n: int = 5) -> List[tuple[str, Quote]]:
        return sorted(self.get_all_stocks(), key=lambda x: x[1].change_percent, reverse=True)[:n]

    def get_top_losers(self, n: int = 5) -> List[tuple[str, Quote]]:
        return sorted(self.get_all_stocks(), key=lambda x: x[1].change_percent)[:n]

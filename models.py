"""
Data Models - 数据模型定义
遵循单一职责原则，每个类只负责一种数据结构
"""
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime


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
        """是否上涨"""
        return self.change >= 0


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    link: str
    published: str
    summary: str


@dataclass
class EarningsEvent:
    """财报事件"""
    symbol: str
    name: str
    date: str
    time: Optional[str] = None


@dataclass
class EconomicEvent:
    """经济数据事件"""
    date: str
    event: str
    importance: str
    forecast: Optional[str] = None
    previous: Optional[str] = None


@dataclass
class MarketData:
    """市场数据集合"""
    timestamp: str
    stocks: Dict[str, Dict[str, Quote]]
    crypto: Dict[str, Quote]
    commodities: Dict[str, Quote]
    
    def get_all_stocks(self) -> List[tuple[str, Quote]]:
        """获取所有股票的扁平列表"""
        result = []
        for category, stocks in self.stocks.items():
            for symbol, quote in stocks.items():
                result.append((symbol, quote))
        return result
    
    def get_top_gainers(self, n: int = 5) -> List[tuple[str, Quote]]:
        """获取涨幅前N名"""
        all_stocks = self.get_all_stocks()
        return sorted(all_stocks, key=lambda x: x[1].change_percent, reverse=True)[:n]
    
    def get_top_losers(self, n: int = 5) -> List[tuple[str, Quote]]:
        """获取跌幅前N名"""
        all_stocks = self.get_all_stocks()
        return sorted(all_stocks, key=lambda x: x[1].change_percent)[:n]

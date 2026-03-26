"""
YoloInvest Configuration
集中管理所有配置项
"""
from typing import Dict, List
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ===== API 配置 =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.tabcode.cc/claude/kiropower")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929")

# ===== 监控标的 =====
STOCKS: Dict[str, List[str]] = {
    "科技巨头": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "芯片": ["AVGO", "MRVL", "ALAB", "TSM", "CRDO", "AMD", "INTC", "QCOM", "MU", "ASML", "KLAC", "LRCX"],
    "数据中心": ["APLD", "GEV", "EQIX", "DLR", "VRT", "SMCI"],
    "电力": ["NNE", "VST", "CEG", "NRG", "TLN", "OKLO", "SMR"],
    "稀土": ["MP", "REE", "UUUU", "REMX", "USAR"]
}

CRYPTO_SYMBOLS = ["BTC", "ETH"]

FUTURES_VIX: Dict[str, str] = {
    "ES (S&P 500)": "ES=F",
    "NQ (Nasdaq 100)": "NQ=F",
    "YM (Dow 30)": "YM=F",
    "VIX": "^VIX",
}

COMMODITIES: Dict[str, str] = {
    "原油": "CL=F",
    "黄金": "GC=F",
    "铜": "HG=F",
    "白银": "SI=F",
    "天然气": "NG=F"
}

# ===== 新闻源 =====
NEWS_SOURCES: Dict[str, List[str]] = {
    "crypto": [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    ],
    "tech": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA&region=US&lang=en-US",
        "https://www.cnbc.com/id/19854910/device/rss/rss.html",
    ],
    "energy": [
        "https://www.reuters.com/business/energy/rss",
    ],
    "markets": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,^DJI,^IXIC&region=US&lang=en-US",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    ]
}

# ===== 重点分析股票 =====
FOCUS_STOCKS = ["NVDA", "AVGO", "SPY", "QQQ", "TSLA"]

# ===== 文件路径 =====
OUTPUT_DIR = "/tmp"
MARKET_DATA_FILE = f"{OUTPUT_DIR}/market_data.json"
NEWS_FILE = f"{OUTPUT_DIR}/market_news.json"
EARNINGS_FILE = f"{OUTPUT_DIR}/earnings_calendar.json"
ECONOMIC_FILE = f"{OUTPUT_DIR}/economic_data.json"
SENTIMENT_FILE = f"{OUTPUT_DIR}/sentiment_data.json"
ANALYSIS_FILE = f"{OUTPUT_DIR}/news_analysis.txt"
BRIEF_FILE = f"{OUTPUT_DIR}/brief.txt"
DETAILED_FILE = f"{OUTPUT_DIR}/detailed.txt"

# ===== API 配置 =====
YAHOO_FINANCE_BASE = "https://query1.finance.yahoo.com"
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

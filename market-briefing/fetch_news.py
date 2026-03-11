#!/usr/bin/env python3
"""
News Fetcher - 抓取市场新闻
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json

NEWS_SOURCES = {
    "crypto": [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    ],
    "tech": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA&region=US&lang=en-US",
        "https://www.cnbc.com/id/19854910/device/rss/rss.html",  # Tech
    ],
    "energy": [
        "https://www.reuters.com/business/energy/rss",
    ],
    "markets": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,^DJI,^IXIC&region=US&lang=en-US",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # Markets
    ]
}

def fetch_rss_feed(url, max_items=5):
    """抓取 RSS feed"""
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")[:200]
            })
        return items
    except Exception as e:
        print(f"Error fetching RSS {url}: {e}")
        return []

def fetch_all_news():
    """抓取所有新闻源"""
    news = {}
    
    for category, urls in NEWS_SOURCES.items():
        news[category] = []
        for url in urls:
            items = fetch_rss_feed(url, max_items=5)
            news[category].extend(items)
    
    return news

if __name__ == "__main__":
    print("Fetching news...")
    news = fetch_all_news()
    
    # 保存到文件
    output_file = "/tmp/market_news.json"
    with open(output_file, "w") as f:
        json.dump(news, f, indent=2)
    
    total = sum(len(items) for items in news.values())
    print(f"Fetched {total} news items across {len(news)} categories")
    print(f"Saved to {output_file}")

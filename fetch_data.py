#!/usr/bin/env python3
"""
Market Data Fetcher - 获取美股、加密货币、大宗商品数据
"""
import json
from yoloinvest.common.fetchers import YahooFinanceFetcher


def fetch_all_data():
    """获取所有市场数据"""
    return YahooFinanceFetcher().fetch()


if __name__ == "__main__":
    print("Fetching market data...")
    data = fetch_all_data()

    output_file = "/tmp/market_data.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    stock_count = sum(len(category) for category in data["stocks"].values())
    print(f"Data saved to {output_file}")
    print(f"Fetched {stock_count} stocks, {len(data['crypto'])} cryptos, {len(data['commodities'])} commodities")

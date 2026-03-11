#!/usr/bin/env python3
"""
Earnings Calendar Fetcher - 获取本周财报日历
"""
import requests
from datetime import datetime, timedelta
import json

def fetch_earnings_calendar():
    """获取本周财报日历"""
    try:
        # Yahoo Finance Earnings Calendar API
        # 获取未来7天的财报
        today = datetime.now()
        end_date = today + timedelta(days=7)
        
        url = "https://query2.finance.yahoo.com/v1/finance/screener"
        
        # 使用 screener API 获取即将发布财报的公司
        payload = {
            "size": 100,
            "offset": 0,
            "sortField": "earningsdate",
            "sortType": "ASC",
            "quoteType": "EQUITY",
            "query": {
                "operator": "AND",
                "operands": [
                    {
                        "operator": "gt",
                        "operands": ["earningsdate", int(today.timestamp())]
                    },
                    {
                        "operator": "lt",
                        "operands": ["earningsdate", int(end_date.timestamp())]
                    }
                ]
            }
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"API returned status {response.status_code}")
            return fetch_earnings_fallback()
        
        data = response.json()
        
        earnings = []
        if "finance" in data and "result" in data["finance"]:
            for result in data["finance"]["result"]:
                if "quotes" in result:
                    for quote in result["quotes"]:
                        earnings.append({
                            "symbol": quote.get("symbol"),
                            "name": quote.get("shortName", quote.get("longName", "")),
                            "date": datetime.fromtimestamp(quote.get("earningsTimestamp", 0)).strftime("%Y-%m-%d") if quote.get("earningsTimestamp") else "TBD"
                        })
        
        return earnings
        
    except Exception as e:
        print(f"Error fetching earnings calendar: {e}")
        return fetch_earnings_fallback()

def fetch_earnings_fallback():
    """备用方案：爬取 Nasdaq earnings calendar"""
    try:
        # 使用 Nasdaq earnings calendar
        url = "https://api.nasdaq.com/api/calendar/earnings"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        today = datetime.now()
        
        earnings = []
        
        # 获取本周每一天的财报
        for i in range(7):
            date = today + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            params = {"date": date_str}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "rows" in data["data"]:
                    for row in data["data"]["rows"][:20]:  # 每天最多20个
                        earnings.append({
                            "symbol": row.get("symbol", ""),
                            "name": row.get("companyName", ""),
                            "date": date_str,
                            "time": row.get("time", "")
                        })
        
        return earnings
        
    except Exception as e:
        print(f"Fallback also failed: {e}")
        return []

if __name__ == "__main__":
    print("Fetching earnings calendar...")
    earnings = fetch_earnings_calendar()
    
    # 保存到文件
    output_file = "/tmp/earnings_calendar.json"
    with open(output_file, "w") as f:
        json.dump(earnings, f, indent=2)
    
    print(f"Fetched {len(earnings)} earnings reports")
    print(f"Saved to {output_file}")
    
    # 打印前10个
    for e in earnings[:10]:
        print(f"  {e['date']} - {e['symbol']}: {e['name']}")

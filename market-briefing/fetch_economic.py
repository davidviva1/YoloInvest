#!/usr/bin/env python3
"""
Economic Data Fetcher - 获取政府经济数据
"""
import requests
from datetime import datetime, timedelta
import json

# FRED API (Federal Reserve Economic Data)
# 免费，但需要 API key。如果没有，用备用方案
FRED_API_KEY = None  # 可以在 https://fred.stlouisfed.org/docs/api/api_key.html 申请

# 关键经济指标
ECONOMIC_INDICATORS = {
    "CPI": "CPIAUCSL",           # 消费者物价指数
    "Core_CPI": "CPILFESL",      # 核心CPI
    "Unemployment": "UNRATE",     # 失业率
    "GDP": "GDP",                 # GDP
    "Fed_Rate": "FEDFUNDS",       # 联邦基金利率
    "10Y_Treasury": "DGS10",      # 10年期国债收益率
    "2Y_Treasury": "DGS2",        # 2年期国债收益率
}

def fetch_fred_data(series_id, api_key=None):
    """从 FRED 获取经济数据"""
    if not api_key:
        return None
    
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 5
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "observations" in data and len(data["observations"]) > 0:
            latest = data["observations"][0]
            return {
                "value": float(latest["value"]) if latest["value"] != "." else None,
                "date": latest["date"]
            }
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
    
    return None

def fetch_economic_calendar():
    """获取本周重要经济事件日历"""
    # 使用 Trading Economics API 或者爬取经济日历网站
    # 这里提供一个简化版本
    
    events = []
    
    try:
        # 使用 Investing.com 的经济日历 API（非官方）
        url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
        
        today = datetime.now()
        end_date = today + timedelta(days=7)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        payload = {
            "dateFrom": today.strftime("%Y-%m-%d"),
            "dateTo": end_date.strftime("%Y-%m-%d"),
            "country[]": [5],  # USA
            "importance[]": [2, 3],  # Medium and High importance
            "limit": 50
        }
        
        response = requests.post(url, data=payload, headers=headers, timeout=15)
        
        # 解析返回的 HTML（简化处理）
        # 实际使用中可能需要 BeautifulSoup 解析
        
    except Exception as e:
        print(f"Error fetching economic calendar: {e}")
    
    # 返回硬编码的常见事件（作为备用）
    return get_upcoming_economic_events()

def get_upcoming_economic_events():
    """获取即将发布的重要经济数据（基于日历）"""
    today = datetime.now()
    
    # 常见的经济数据发布时间表
    events = []
    
    # CPI 通常在每月第二周发布
    # 非农就业报告通常在每月第一个周五
    # FOMC 会议每6-8周一次
    
    # 这里返回一个示例结构
    # 实际使用中应该从真实 API 获取
    
    return [
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

def fetch_all_economic_data():
    """获取所有经济数据"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "indicators": {},
        "calendar": []
    }
    
    # 如果有 FRED API key，获取实时数据
    if FRED_API_KEY:
        for name, series_id in ECONOMIC_INDICATORS.items():
            result = fetch_fred_data(series_id, FRED_API_KEY)
            if result:
                data["indicators"][name] = result
    
    # 获取经济日历
    data["calendar"] = fetch_economic_calendar()
    
    return data

if __name__ == "__main__":
    print("Fetching economic data...")
    data = fetch_all_economic_data()
    
    # 保存到文件
    output_file = "/tmp/economic_data.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved to {output_file}")
    print(f"Indicators: {len(data['indicators'])}")
    print(f"Calendar events: {len(data['calendar'])}")

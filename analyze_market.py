#!/usr/bin/env python3
"""
Legacy wrapper - 使用当前生成器输出简报文件
"""
import json

from yoloinvest.market_briefing.generators import ReportGenerator


if __name__ == "__main__":
    with open("/tmp/market_data.json", "r") as f:
        market_data = json.load(f)

    try:
        with open("/tmp/news_analysis.txt", "r") as f:
            analysis = f.read()
    except FileNotFoundError:
        analysis = "新闻分析暂时不可用"

    try:
        with open("/tmp/earnings_calendar.json", "r") as f:
            earnings = json.load(f)
    except FileNotFoundError:
        earnings = []

    try:
        with open("/tmp/economic_data.json", "r") as f:
            economic = json.load(f)
    except FileNotFoundError:
        economic = {"calendar": []}

    generator = ReportGenerator(brand_name="YoloInvest")
    report = generator.generate_detailed({
        "market_data": market_data,
        "analysis": analysis,
        "earnings": earnings,
        "economic_calendar": economic.get("calendar", []),
    })

    with open("/tmp/detailed.txt", "w") as f:
        f.write(report)

    print("Detailed briefing generated")

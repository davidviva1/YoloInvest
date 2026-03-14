#!/usr/bin/env python3
"""
Legacy wrapper - 使用当前分析器生成新闻分析结果
"""
from yoloinvest.market_briefing.app import YoloInvestApp


if __name__ == "__main__":
    app = YoloInvestApp()
    data = {
        "market_data": app.market_fetcher.fetch(),
        "news": app.news_fetcher.fetch(),
        "earnings": app.earnings_fetcher.fetch(),
        "economic_data": app.economic_fetcher.fetch(),
    }

    print("Analyzing news impact with AI...")
    analysis = app.analyzer.analyze(data)
    app._save_text(analysis, "/tmp/news_analysis.txt")
    print("Analysis saved to /tmp/news_analysis.txt")
    print("\n" + "=" * 50)
    print(analysis)

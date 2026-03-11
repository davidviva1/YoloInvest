#!/usr/bin/env python3
"""
YoloInvest Main Application
遵循 SOLID 原则的主程序
"""
import json
from typing import Dict

from fetchers import (
    YahooFinanceFetcher,
    RSSNewsFetcher,
    EarningsCalendarFetcher,
    EconomicDataFetcher
)
from analyzers import AINewsAnalyzer
from generators import ReportGenerator
from config import (
    MARKET_DATA_FILE,
    NEWS_FILE,
    EARNINGS_FILE,
    ECONOMIC_FILE,
    ANALYSIS_FILE,
    DETAILED_FILE
)


class YoloInvestApp:
    """YoloInvest 应用主类"""
    
    def __init__(self):
        # 依赖注入
        self.market_fetcher = YahooFinanceFetcher()
        self.news_fetcher = RSSNewsFetcher()
        self.earnings_fetcher = EarningsCalendarFetcher()
        self.economic_fetcher = EconomicDataFetcher()
        self.analyzer = AINewsAnalyzer()
        self.generator = ReportGenerator(brand_name="YoloInvest")
    
    def fetch_all_data(self) -> Dict:
        """获取所有数据"""
        print("Fetching market data...")
        market_data = self.market_fetcher.fetch()
        self._save_json(market_data, MARKET_DATA_FILE)
        
        print("Fetching news...")
        news = self.news_fetcher.fetch()
        self._save_json(news, NEWS_FILE)
        
        print("Fetching earnings calendar...")
        earnings = self.earnings_fetcher.fetch()
        self._save_json(earnings, EARNINGS_FILE)
        
        print("Fetching economic data...")
        economic = self.economic_fetcher.fetch()
        self._save_json(economic, ECONOMIC_FILE)
        
        return {
            "market_data": market_data,
            "news": news,
            "earnings": earnings,
            "economic_data": economic
        }
    
    def analyze_data(self, data: Dict) -> str:
        """分析数据"""
        print("Analyzing news impact with AI...")
        analysis = self.analyzer.analyze(data)
        self._save_text(analysis, ANALYSIS_FILE)
        return analysis
    
    def generate_report(self, data: Dict, analysis: str) -> str:
        """生成简报"""
        print("Generating report...")
        
        report_data = {
            "market_data": data["market_data"],
            "analysis": analysis,
            "earnings": data["earnings"],
            "economic_calendar": data["economic_data"].get("calendar", [])
        }
        
        detailed = self.generator.generate_detailed(report_data)
        self._save_text(detailed, DETAILED_FILE)
        
        return detailed
    
    def run(self) -> str:
        """运行完整流程"""
        print("=== YoloInvest Market Briefing Pipeline ===")
        
        # 1. 获取数据
        data = self.fetch_all_data()
        
        # 2. 分析
        analysis = self.analyze_data(data)
        
        # 3. 生成简报
        report = self.generate_report(data, analysis)
        
        print("=== Done ===")
        return report
    
    @staticmethod
    def _save_json(data: Dict, filepath: str):
        """保存 JSON 文件"""
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def _save_text(text: str, filepath: str):
        """保存文本文件"""
        with open(filepath, "w") as f:
            f.write(text)


if __name__ == "__main__":
    app = YoloInvestApp()
    app.run()

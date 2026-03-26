"""Main application for the market briefing module."""
import json
from typing import Dict

from yoloinvest.common.fetchers import EconomicDataFetcher, EarningsCalendarFetcher, RSSNewsFetcher, SentimentFetcher, YahooFinanceFetcher
from yoloinvest.config import ANALYSIS_FILE, DETAILED_FILE, EARNINGS_FILE, ECONOMIC_FILE, MARKET_DATA_FILE, NEWS_FILE, SENTIMENT_FILE
from yoloinvest.market_briefing.analyzers import AINewsAnalyzer
from yoloinvest.market_briefing.generators import ReportGenerator


class YoloInvestApp:
    def __init__(self):
        self.market_fetcher = YahooFinanceFetcher()
        self.news_fetcher = RSSNewsFetcher()
        self.earnings_fetcher = EarningsCalendarFetcher()
        self.economic_fetcher = EconomicDataFetcher()
        self.sentiment_fetcher = SentimentFetcher()
        self.analyzer = AINewsAnalyzer()
        self.generator = ReportGenerator(brand_name="YoloInvest")

    def fetch_all_data(self) -> Dict:
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

        print("Fetching sentiment data...")
        sentiment = self.sentiment_fetcher.fetch()
        self._save_json(sentiment, SENTIMENT_FILE)

        return {"market_data": market_data, "news": news, "earnings": earnings, "economic_data": economic, "sentiment": sentiment}

    def analyze_data(self, data: Dict) -> str:
        print("Analyzing news impact with AI...")
        analysis = self.analyzer.analyze(data)
        self._save_text(analysis, ANALYSIS_FILE)
        return analysis

    def generate_report(self, data: Dict, analysis: str) -> str:
        print("Generating report...")
        report_data = {
            "market_data": data["market_data"],
            "analysis": analysis,
            "earnings": data["earnings"],
            "economic_calendar": data["economic_data"].get("calendar", []),
            "sentiment": data.get("sentiment", {}),
        }
        detailed = self.generator.generate_detailed(report_data)
        self._save_text(detailed, DETAILED_FILE)
        return detailed

    def run(self) -> str:
        print("=== YoloInvest Market Briefing Pipeline ===")
        data = self.fetch_all_data()
        analysis = self.analyze_data(data)
        report = self.generate_report(data, analysis)
        print("=== Done ===")
        return report

    @staticmethod
    def _save_json(data: Dict, filepath: str):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _save_text(text: str, filepath: str):
        with open(filepath, "w") as f:
            f.write(text)


if __name__ == "__main__":
    YoloInvestApp().run()

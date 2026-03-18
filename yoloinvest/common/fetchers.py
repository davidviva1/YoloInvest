"""Shared data fetchers for YoloInvest."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import feedparser
import requests

from yoloinvest.common.models import NewsItem, Quote
from yoloinvest.config import (
    COMMODITIES,
    CRYPTO_SYMBOLS,
    NEWS_SOURCES,
    REQUEST_TIMEOUT,
    STOCKS,
    USER_AGENT,
    YAHOO_FINANCE_BASE,
)


class DataFetcher(ABC):
    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self.headers = {"User-Agent": USER_AGENT}

    @abstractmethod
    def fetch(self):
        raise NotImplementedError


class YahooFinanceFetcher(DataFetcher):
    @staticmethod
    def _extract_daily_series(result: Dict) -> Tuple[List[str], List[float], List[Optional[int]]]:
        timestamps = result.get("timestamp", [])
        quote_data = result.get("indicators", {}).get("quote", [{}])[0]
        closes = quote_data.get("close", [])
        volumes = quote_data.get("volume", [])

        dates: List[str] = []
        valid_closes: List[float] = []
        valid_volumes: List[Optional[int]] = []
        for ts, close, volume in zip(timestamps, closes, volumes):
            if close is None:
                continue
            dates.append(datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"))
            valid_closes.append(close)
            valid_volumes.append(volume)
        return dates, valid_closes, valid_volumes

    @staticmethod
    def _extract_high_low(result: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Extract high/low from the last trading day."""
        quote_data = result.get("indicators", {}).get("quote", [{}])[0]
        highs = quote_data.get("high", [])
        lows = quote_data.get("low", [])
        # Filter out None values and get last valid pair
        valid_highs = [h for h in highs if h is not None]
        valid_lows = [l for l in lows if l is not None]
        high = valid_highs[-1] if valid_highs else None
        low = valid_lows[-1] if valid_lows else None
        return high, low

    def _fetch_premarket(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """Fetch premarket high/low for a symbol."""
        try:
            url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
            params = {"interval": "5m", "range": "1d", "includePrePost": "true"}
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            data = response.json()
            if "chart" not in data or not data["chart"].get("result"):
                return None, None

            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            quote_data = result.get("indicators", {}).get("quote", [{}])[0]
            highs = quote_data.get("high", [])
            lows = quote_data.get("low", [])

            meta = result.get("meta", {})
            regular_start = meta.get("currentTradingPeriod", {}).get("regular", {}).get("start", 0)

            pre_highs = []
            pre_lows = []
            for ts, h, l in zip(timestamps, highs, lows):
                if ts < regular_start and h is not None and l is not None:
                    pre_highs.append(h)
                    pre_lows.append(l)

            if pre_highs and pre_lows:
                return max(pre_highs), min(pre_lows)
            return None, None
        except Exception as exc:
            print(f"Error fetching premarket for {symbol}: {exc}")
            return None, None

    def fetch_quote(self, symbol: str) -> Optional[Quote]:
        try:
            url = f"{YAHOO_FINANCE_BASE}/v8/finance/chart/{symbol}"
            params = {"interval": "1d", "range": "10d", "includePrePost": "false"}
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            data = response.json()

            if "chart" not in data or not data["chart"].get("result"):
                return None

            result = data["chart"]["result"][0]
            dates, closes, volumes = self._extract_daily_series(result)

            if len(closes) >= 2:
                price = closes[-1]
                previous_close = closes[-2]
                price_date = dates[-1]
                previous_close_date = dates[-2]
                volume = volumes[-1]
            elif len(closes) == 1:
                price = closes[-1]
                previous_close = closes[-1]
                price_date = dates[-1]
                previous_close_date = dates[-1]
                volume = volumes[-1]
            else:
                return None

            # Extract previous day high/low
            prev_day_high, prev_day_low = self._extract_high_low(result)

            change = price - previous_close
            change_pct = (change / previous_close * 100) if previous_close else 0
            return Quote(
                symbol=symbol,
                price=price,
                change=change,
                change_percent=change_pct,
                volume=volume,
                previous_close=previous_close,
                price_date=price_date,
                previous_close_date=previous_close_date,
                prev_day_high=prev_day_high,
                prev_day_low=prev_day_low,
            )
        except Exception as exc:
            print(f"Error fetching {symbol}: {exc}")
            return None

    def fetch(self) -> Dict:
        result = {"timestamp": datetime.utcnow().isoformat(), "stocks": {}, "crypto": {}, "commodities": {}}

        premarket_symbols = {"SPY", "QQQ"}

        for category, symbols in STOCKS.items():
            result["stocks"][category] = {}
            for symbol in symbols:
                quote = self.fetch_quote(symbol)
                if quote:
                    if symbol in premarket_symbols:
                        pm_high, pm_low = self._fetch_premarket(symbol)
                        quote.premarket_high = pm_high
                        quote.premarket_low = pm_low
                    result["stocks"][category][symbol] = quote.__dict__

        for crypto in CRYPTO_SYMBOLS:
            quote = self.fetch_quote(f"{crypto}-USD")
            if quote:
                result["crypto"][crypto] = quote.__dict__

        for name, symbol in COMMODITIES.items():
            quote = self.fetch_quote(symbol)
            if quote:
                result["commodities"][name] = quote.__dict__

        return result


class RSSNewsFetcher(DataFetcher):
    def fetch_feed(self, url: str, max_items: int = 5) -> List[NewsItem]:
        try:
            feed = feedparser.parse(url)
            items = []
            for entry in feed.entries[:max_items]:
                items.append(
                    NewsItem(
                        title=entry.get("title", ""),
                        link=entry.get("link", ""),
                        published=entry.get("published", ""),
                        summary=entry.get("summary", "")[:200],
                    )
                )
            return items
        except Exception as exc:
            print(f"Error fetching RSS {url}: {exc}")
            return []

    def fetch(self) -> Dict[str, List[Dict]]:
        result: Dict[str, List[Dict]] = {}
        for category, urls in NEWS_SOURCES.items():
            result[category] = []
            for url in urls:
                items = self.fetch_feed(url, max_items=5)
                result[category].extend([item.__dict__ for item in items])
        return result


class EarningsCalendarFetcher(DataFetcher):
    """Fetch upcoming earnings from Yahoo Finance screener API."""

    def fetch(self) -> List[Dict]:
        try:
            from datetime import timedelta

            today = datetime.utcnow()
            end = today + timedelta(days=7)
            url = "https://finance.yahoo.com/calendar/earnings"
            params = {
                "from": today.strftime("%Y-%m-%d"),
                "to": end.strftime("%Y-%m-%d"),
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                print(f"Earnings calendar HTTP {resp.status_code}")
                return []
            # Yahoo returns HTML; extract JSON embedded in the page
            import re

            match = re.search(r'"rows"\s*:\s*(\[.*?\])\s*,\s*"total"', resp.text, re.DOTALL)
            if not match:
                return []
            import json as _json

            rows = _json.loads(match.group(1))
            results: List[Dict] = []
            for row in rows[:30]:
                results.append(
                    {
                        "symbol": row.get("ticker", ""),
                        "name": row.get("companyName", row.get("companyShortName", "")),
                        "date": row.get("startDateTime", "")[:10],
                        "time": row.get("startDateTimeType", ""),
                    }
                )
            return results
        except Exception as exc:
            print(f"Error fetching earnings calendar: {exc}")
            return []


class EconomicDataFetcher(DataFetcher):
    """Fetch upcoming economic events from ForexFactory JSON + Fed official calendar."""

    # Events that should always be flagged as critical in the briefing
    CRITICAL_KEYWORDS = [
        "FOMC", "Federal Funds Rate", "Fed Chair", "Nonfarm Payrolls",
        "Non-Farm", "CPI ", "Core CPI", "PCE ", "Core PCE", "GDP ",
    ]

    @staticmethod
    def _fetch_forexfactory_calendar() -> List[Dict]:
        """Primary source: ForexFactory weekly calendar JSON (free, reliable)."""
        try:
            resp = requests.get(
                "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            events: List[Dict] = []
            for item in data:
                if item.get("country") != "USD":
                    continue
                impact = item.get("impact", "")
                if impact not in ("High", "Medium"):
                    continue
                raw_date = item.get("date", "")
                date_str = raw_date[:10] if raw_date else ""
                events.append(
                    {
                        "date": raw_date,
                        "date_short": date_str,
                        "event": item.get("title", ""),
                        "impact": impact,
                        "forecast": item.get("forecast") or None,
                        "previous": item.get("previous") or None,
                    }
                )
            return events
        except Exception as exc:
            print(f"ForexFactory calendar failed: {exc}")
            return []

    @staticmethod
    def _fetch_fed_calendar() -> List[Dict]:
        """Supplementary: Fed official press-release calendar for FOMC / monetary policy."""
        try:
            import json as _json

            resp = requests.get(
                "https://www.federalreserve.gov/json/ne-press.json",
                timeout=10,
            )
            resp.raise_for_status()
            data = _json.loads(resp.content.decode("utf-8-sig"))
            today_str = datetime.utcnow().strftime("%m/%d/%Y").lstrip("0").replace("/0", "/")
            events: List[Dict] = []
            for item in data:
                raw = item.get("d", "")
                if not raw:
                    continue
                # Only include Monetary Policy items within the next 7 days
                if item.get("pt") != "Monetary Policy":
                    continue
                try:
                    dt = datetime.strptime(raw, "%m/%d/%Y %I:%M:%S %p")
                except ValueError:
                    continue
                diff = (dt - datetime.utcnow()).days
                if -1 <= diff <= 7:
                    events.append(
                        {
                            "date": dt.strftime("%Y-%m-%dT%H:%M:%S-04:00"),
                            "date_short": dt.strftime("%Y-%m-%d"),
                            "event": item.get("t", ""),
                            "impact": "High",
                            "forecast": None,
                            "previous": None,
                        }
                    )
            return events
        except Exception as exc:
            print(f"Fed calendar failed: {exc}")
            return []

    @classmethod
    def _classify_critical(cls, events: List[Dict]) -> List[Dict]:
        """Tag events that match critical keywords."""
        for event in events:
            title = event.get("event", "")
            is_critical = any(kw.lower() in title.lower() for kw in cls.CRITICAL_KEYWORDS)
            event["critical"] = is_critical or event.get("impact") == "High"
        return events

    def fetch(self) -> Dict:
        calendar = self._fetch_forexfactory_calendar()
        # Merge Fed official calendar (dedup: skip if same date and overlapping keywords)
        fed_events = self._fetch_fed_calendar()
        ff_by_date: Dict[str, List[str]] = {}
        for e in calendar:
            d = e.get("date_short", "")
            ff_by_date.setdefault(d, []).append(e["event"].lower())
        for fe in fed_events:
            fe_date = fe.get("date_short", "")
            fe_lower = fe["event"].lower()
            fe_words = set(fe_lower.split())
            existing = ff_by_date.get(fe_date, [])
            # Skip if any existing event on the same date shares 2+ significant words
            skip = False
            for ex_title in existing:
                common = fe_words & set(ex_title.split())
                # Remove trivial words
                common -= {"the", "a", "an", "and", "of", "from", "in", "for", "to"}
                if len(common) >= 2:
                    skip = True
                    break
            if not skip:
                calendar.append(fe)
        calendar = self._classify_critical(calendar)
        # Sort by date
        calendar.sort(key=lambda e: e.get("date", ""))
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "indicators": {},
            "calendar": calendar,
        }

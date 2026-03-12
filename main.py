#!/usr/bin/env python3
"""Compatibility entrypoint for the YoloInvest market briefing module."""
from yoloinvest.market_briefing.app import YoloInvestApp


if __name__ == "__main__":
    app = YoloInvestApp()
    app.run()

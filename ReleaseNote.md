# ReleaseNote

## 2026-03-18

- Replaced unreliable economic calendar sources (Trading Economics RSS + Investing.com scraper) with ForexFactory weekly JSON API as primary source and Fed official press-release calendar (`federalreserve.gov/json/ne-press.json`) as supplementary source.
- Economic calendar now includes impact level (High/Medium) and forecast/previous values for each event.
- Added critical event detection: FOMC, Federal Funds Rate, CPI, PCE, GDP, Nonfarm Payrolls, and Fed Chair speeches are auto-tagged as critical.
- Briefing report now shows a dedicated "🚨 今日重大事件" section at the top of the economic calendar when critical events fall on the briefing date.
- Weekly economic calendar entries now display impact emoji (🔴 High / 🟡 Medium), forecast, and previous values.
- AI analysis prompt updated to require prominent coverage of same-day critical events (e.g., FOMC rate decision) at the top of the macro analysis section.
- Smart dedup between ForexFactory and Fed calendar prevents duplicate entries for the same event.
- Market briefing cron restricted to weekdays only (Mon-Fri).
- New module: `yoloinvest.weekly_calendar` — pushes next week's economic calendar to the briefing Telegram group every Sunday 8:00 PM Pacific.
- Added `run_weekly_calendar.sh` runner and `cron_bridge.py` entry for `weekly-calendar`.
- Removed pre-market alert scan (6:30-7:00 AM) to avoid opening noise false positives; intraday alerts now start at 7:00 AM.
- README now includes full script reference table and cron schedule table.

## 2026-03-17

- Fixed critical bug: `app.py` missing `if __name__ == "__main__"` block, causing `python3 -m yoloinvest.market_briefing.app` to import the module without executing `run()`. This meant cron-triggered briefings never re-fetched data and always sent the stale `/tmp/detailed.txt` cache.
- Briefing title now correctly shows the send date (`datetime.now()`).
- Calculation notes (`计算说明`) now dynamically reflect the actual trading dates (`price_date` / `previous_close_date`) from Yahoo Finance market data.
- Added individual stock leveraged ETFs to alert symbols: NVDL, NVDD, NVDU, TSLL, TSLS, TSLR, METD, FBL, AMZU, AMZD.
- Added AVGX (AVGO 2x bull) to alert symbols.
- Options alert: lowered trigger thresholds, added ETF/index tickers, fixed volume ratio calculation.

## 2026-03-12

- Renamed the project from `market-briefing` to `YoloInvest`.
- Renamed the GitHub repository to `davidviva1/YoloInvest` and updated the local `origin` remote.
- Reorganized the codebase into modules:
  - `yoloinvest.common`
  - `yoloinvest.market_briefing`
  - `yoloinvest.options_alert`
- Removed compatibility wrappers and old top-level forwarding entrypoints so the project now runs only through the modular structure.
- Rebuilt the local virtual environment after the project rename so execution paths are valid again.
- Updated `run_briefing.sh` and `run_options_alert.sh` to use the modular entrypoints directly.
- Verified both canonical entrypoints:
  - `run_briefing.sh`
  - `run_options_alert.sh`
- Verified direct module entrypoints:
  - `python3 -m yoloinvest.market_briefing.app`
  - `python3 -m yoloinvest.options_alert.alert`
- Updated `README.md`, `DEPLOYMENT.md`, `Makefile`, and GitHub Actions CI to match the new `YoloInvest` structure.
- Fixed daily delivery reliability by introducing `cron_bridge.py` as a deterministic bridge between OpenClaw cron `agentTurn` jobs and the shell entrypoints.
- Confirmed the daily briefing path now executes through `YoloInvest/run_briefing.sh` and successfully delivers to Telegram.
- Kept OpenClaw cron aligned with the new `YoloInvest` paths.
- Split Telegram delivery targets:
  - market briefing -> `TELEGRAM_CHAT_ID_MARKET_BRIEFING`
  - intraday alerts -> `TELEGRAM_CHAT_ID_OPTIONS_ALERT`
- Tightened intraday scheduling to regular-session coverage around 6:30 AM-1:00 PM America/Los_Angeles.
- Added a dedicated weekday end-of-day intraday review cron job for 1:10 PM America/Los_Angeles.
- Upgraded intraday alerting from V1.1 to V2.0 with score-based ranking, severity levels, trigger reasons, and stronger de-duplication rules.
- Preserved lightweight news confirmation in the intraday alert pipeline.
- Added `review_intraday_alerts.py` for quick inspection of the latest saved intraday alert state.
- Expanded `review_intraday_alerts.py` into an end-of-day review report that includes a dedicated close-performance pillar for alert follow-through.
- Documented intraday alert scoring, severity mapping, repeat-notification rules, and review workflow in the project docs.
- Added persistent intraday alert history logging in `/tmp/options_alert_history.jsonl` for quality analysis.
- Expanded the end-of-day review to report triggered alerts, directional close returns, hit rate, and score-bucket / severity summaries.

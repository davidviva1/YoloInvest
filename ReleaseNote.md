# ReleaseNote

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

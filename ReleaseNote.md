# ReleaseNote

## 2026-03-12

- Renamed the project from `market-briefing` to `YoloInvest`.
- Renamed the GitHub repository to `YoloInvest`.
- Reorganized the codebase into modules:
  - `yoloinvest.common`
  - `yoloinvest.market_briefing`
  - `yoloinvest.options_alert`
- Removed compatibility wrappers and old top-level forwarding entrypoints.
- Rebuilt the local virtual environment after the project rename so execution paths are valid again.
- Verified both canonical entrypoints:
  - `run_briefing.sh`
  - `run_options_alert.sh`
- Kept OpenClaw cron aligned with the new `YoloInvest` paths.
- Preserved the V1.1 intraday alert logic with lightweight news confirmation.

- Upgraded intraday alerting to V2.0 with score-based ranking, severity levels, and stronger de-duplication rules.
- Separated alert delivery to the dedicated Telegram alert group via `TELEGRAM_CHAT_ID_OPTIONS_ALERT`.
- Planned intraday schedule tightened to regular-session hours around 6:30 AM-1:00 PM America/Los_Angeles.
- Added `review_intraday_alerts.py` for quick inspection of the latest saved intraday alert state.

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

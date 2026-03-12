# ReleaseNote

## 2026-03-11

- Switched YoloInvest YoloInvest AI analysis to Claude-compatible endpoint at `https://api.tabcode.cc/claude/kiropower/v1/messages`.
- Removed OpenAI analysis path from the project to avoid mixed-provider confusion.
- Removed `LYNAS.AX` from the rare earth watchlist because Yahoo Finance quote retrieval was unreliable.
- Changed market data calculation to pure daily-close logic:
  - `price` = most recent completed trading day's close
  - `previous_close` = prior completed trading day's close
  - `change_percent` = close-to-close percentage change
  - `volume` = most recent completed trading day's total volume
- Verified `AVGO` now uses 2026-03-10 close versus 2026-03-09 close, which yields about `-0.92%`, not `+9%`.
- Added a calculation notes section to the end of the generated report so the pricing basis is explicit.
- Calculation notes now state the exact market dates used in each generated report.
- Moved Telegram credentials to environment variables and added runtime checks for required env vars.
- Reduced project redundancy by centralizing market data fetching in `fetchers.py` and keeping legacy scripts as wrappers.
- Re-ran the pipeline successfully and confirmed Telegram delivery works.
- Scheduling uses OpenClaw cron instead of systemd to avoid gateway conflicts.
- Added formal deployment guidance for running the project through OpenClaw cron with a local `.env.YoloInvest` file.
- Added `requirements.in` and locked `requirements.txt` so local runs, cron, and GitHub Actions share the same dependency set.
- Added `update_requirements.sh` and documented the recommended dependency upgrade workflow.
- Added a `Makefile` and a requirements consistency check so CI can verify locked dependencies stay in sync.
- Added `DEPLOYMENT.md`, a Quick Start section, and `.env.YoloInvest.example` for cleaner onboarding.
- Added `options_alert.py` as a V1 intraday alert script for highly liquid mega-cap tech stocks.
- Upgraded the alert logic to V1.1 with lightweight news confirmation and added an OpenClaw cron job for intraday scans.

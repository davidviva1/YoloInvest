# Deployment

## Recommended Runtime Model

YoloInvest is designed to run through OpenClaw cron instead of systemd timers.

Why:
- avoids multiple gateway-like background services on one host
- keeps scheduling in the same OpenClaw runtime
- keeps manual runs and scheduled runs on the same shell entrypoints

## Local Deployment Steps

1. Clone the repository
2. Create a virtual environment
3. Install locked dependencies from `requirements.txt`
4. Create `.env.market-briefing` from `.env.market-briefing.example`
5. Fill in Telegram and LLM credentials
6. Run `./run_briefing.sh` manually once
7. Run `./run_options_alert.sh` manually once
8. Confirm Telegram delivery
9. Configure OpenClaw cron jobs pointing to the shell entrypoints

## Canonical Entrypoints

- Daily briefing:
  - `/home/ec2-user/.openclaw/workspace/YoloInvest/run_briefing.sh`
- Intraday alerts:
  - `/home/ec2-user/.openclaw/workspace/YoloInvest/run_options_alert.sh`
- End-of-day intraday review:
  - `/home/ec2-user/.openclaw/workspace/YoloInvest/venv/bin/python3 /home/ec2-user/.openclaw/workspace/YoloInvest/review_intraday_alerts.py`

## OpenClaw Cron Jobs

Expected schedules:
- Daily briefing: `0 6 * * *` in `America/Los_Angeles`
- Intraday alerts: `*/10 30-59 6 * * 1-5` and `*/10 7-12 * * 1-5` and `0 13 * * 1-5` equivalent coverage within 6:30 AM-1:00 PM America/Los_Angeles
- End-of-day review: `10 13 * * 1-5` in `America/Los_Angeles`

## Environment File

Expected file:
- `.env.market-briefing`

Expected keys:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `LLM_API_KEY`
- optional: `LLM_API_BASE`
- optional: `LLM_MODEL`

## Operational Notes

- `run_briefing.sh` is the canonical daily-briefing entrypoint
- `run_options_alert.sh` is the canonical intraday-alert entrypoint
- `requirements.txt` is the canonical locked dependency set
- `requirements.in` is only for maintaining top-level dependencies
- do not mix OpenClaw cron with systemd timers for this project
- validate lock consistency with `./venv/bin/python3 check_requirements.py`

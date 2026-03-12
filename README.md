# YoloInvest

YoloInvest is a modular market intelligence project with two primary apps:
- `market_briefing`: daily market briefing generation and Telegram delivery
- `options_alert`: intraday alerting for highly liquid large-cap tech stocks

## Modules

- `yoloinvest.market_briefing`
  - Generates the daily market briefing
  - Pulls market data, news, earnings, and economic calendar data
  - Runs AI analysis and sends the final Telegram report

- `yoloinvest.options_alert`
  - Runs intraday scans on selected large-cap tech names
  - Uses a lightweight score model with severity levels
  - Uses price/volume plus lightweight news confirmation
  - Sends Telegram alerts only when signals are new or materially stronger

## Quick Start

```bash
cd ~/.openclaw/workspace/YoloInvest
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.market-briefing.example .env.market-briefing
# edit .env.market-briefing with real credentials
./run_briefing.sh
```

## Environment

Required variables in `.env.market-briefing`:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `LLM_API_KEY`

Optional:
- `LLM_API_BASE`
- `LLM_MODEL`

## Start Commands

Daily market briefing:

```bash
cd ~/.openclaw/workspace/YoloInvest
source venv/bin/activate
./run_briefing.sh
```

Intraday alerts:

```bash
cd ~/.openclaw/workspace/YoloInvest
source venv/bin/activate
./run_options_alert.sh
```

Direct module entrypoints:

```bash
./venv/bin/python3 -m yoloinvest.market_briefing.app
./venv/bin/python3 -m yoloinvest.options_alert.alert
```

## Deployment

Canonical deployment model:
- one OpenClaw gateway
- OpenClaw cron for scheduling
- no systemd timer duplication
- `.env.market-briefing` as the local secret file

Current scheduled jobs:
- Daily briefing: 6:00 AM America/Los_Angeles
- Intraday alerts: every 10 minutes during 6:30 AM-1:00 PM America/Los_Angeles on weekdays

Detailed deployment notes are in `DEPLOYMENT.md`.

## Dependency Management

- `requirements.in`: top-level runtime dependencies
- `requirements.txt`: locked dependency set
- `update_requirements.sh`: regenerate locked dependencies
- `check_requirements.py`: verify lock consistency

Useful commands:

```bash
make deps
make update-deps
make run
make ci-check
```

## Project Structure

```text
YoloInvest/
├── README.md
├── DEPLOYMENT.md
├── ReleaseNote.md
├── LICENSE
├── Makefile
├── requirements.in
├── requirements.txt
├── run_briefing.sh
├── run_options_alert.sh
├── update_requirements.sh
├── check_requirements.py
├── .env.market-briefing.example
├── yoloinvest/
│   ├── __init__.py
│   ├── config.py
│   ├── common/
│   │   ├── __init__.py
│   │   ├── fetchers.py
│   │   ├── models.py
│   │   └── sender.py
│   ├── market_briefing/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── analyzers.py
│   │   └── generators.py
│   └── options_alert/
│       ├── __init__.py
│       └── alert.py
└── fonts/
```

## Notes

- `LYNAS.AX` has been removed from the watchlist due to unstable Yahoo Finance data.
- `options_alert` currently uses a proxy signal layer, not a true options tape feed.
- The project has been renamed from `market-briefing` to `YoloInvest` and reorganized into modules.

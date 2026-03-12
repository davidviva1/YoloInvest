# Deployment

## Recommended runtime model

This project is designed to run through OpenClaw cron instead of systemd timers.

Why:
- Avoids multiple gateway-like background services on the same host
- Keeps scheduling inside the same OpenClaw runtime
- Makes manual runs, cron runs, and environment loading use the same entrypoint

## Deployment steps

1. Clone the repository
2. Create a virtual environment
3. Install locked dependencies from `requirements.txt`
4. Create `.env.YoloInvest` from `.env.YoloInvest.example`
5. Fill in Telegram and LLM credentials
6. Run `./run_briefing.sh` once manually
7. Confirm Telegram delivery
8. Configure OpenClaw cron to run:
   - `/home/ec2-user/.openclaw/workspace/YoloInvest/run_briefing.sh`

## Environment file

Expected file:
- `.env.YoloInvest`

Expected keys:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `LLM_API_KEY`
- optional: `LLM_API_BASE`
- optional: `LLM_MODEL`

## Operational notes

- `run_briefing.sh` is the canonical entrypoint
- `requirements.txt` is the canonical locked dependency set
- `requirements.in` is only for maintaining top-level dependencies
- Do not mix OpenClaw cron with a separate systemd timer for this project
- Validate dependency lock consistency with `python check_requirements.py`

## Useful commands

```bash
make deps
make update-deps
make run
make ci-check
```

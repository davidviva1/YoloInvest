# Architecture

## Overview

Release line: `v2.1.0`


YoloInvest has two production workflows:
- `market_briefing`: daily market briefing generation and Telegram delivery
- `options_alert`: intraday alert scanning, alert delivery, and end-of-day review

The project is scheduled through OpenClaw cron, but execution is stabilized by a thin Python bridge so cron-triggered agent turns do not need to reason about the business workflow.

## Runtime Layers

- OpenClaw cron: scheduler
- isolated `agentTurn`: task trigger surface
- `cron_bridge.py`: deterministic command bridge
- shell entrypoints: environment setup and command orchestration
- Python modules: data fetch, analysis, formatting, delivery
- Telegram: final delivery surface

## Daily Briefing Sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as OpenClaw Cron
    participant A as Isolated AgentTurn
    participant B as cron_bridge.py
    participant S as run_briefing.sh
    participant P as market_briefing.app
    participant T as Telegram API
    participant G as Briefing Group

    C->>A: Trigger daily job at 06:00 America/Los_Angeles
    A->>B: python3 cron_bridge.py briefing
    B->>S: Execute run_briefing.sh
    S->>S: Load .env.market-briefing
    S->>S: Activate venv
    S->>S: Verify/install locked dependencies
    S->>P: python3 -m yoloinvest.market_briefing.app
    P->>P: Fetch market/news/earnings/economic data
    P->>P: Run AI analysis
    P->>P: Generate report files
    S->>T: send_report()
    T->>G: Deliver briefing message
    G-->>T: 200 OK
    T-->>S: Success
    S-->>B: Exit 0
    B-->>A: Exit 0
    A-->>C: Run completed
```

## Intraday Alert Sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as OpenClaw Cron
    participant A as Isolated AgentTurn
    participant B as cron_bridge.py
    participant S as run_options_alert.sh
    participant P as options_alert.alert
    participant T as Telegram API
    participant G as Alert Group

    C->>A: Trigger alert job every 10 min
    A->>B: python3 cron_bridge.py alerts
    B->>S: Execute run_options_alert.sh
    S->>S: Load .env.market-briefing
    S->>S: Activate venv
    S->>S: Verify/install locked dependencies
    S->>P: python3 -m yoloinvest.options_alert.alert
    P->>P: Fetch prices/volume/news
    P->>P: Compute score and severity
    P->>P: Compare with saved state
    alt Fresh or stronger alert exists
        P->>T: Send alert message
        T->>G: Deliver alert
        G-->>T: 200 OK
        T-->>P: Success
    else No fresh alert
        P-->>S: Exit without message
    end
    S-->>B: Exit 0
    B-->>A: Exit 0
    A-->>C: Run completed
```

## End-of-Day Review Sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as OpenClaw Cron
    participant A as Isolated AgentTurn
    participant B as cron_bridge.py
    participant R as review_intraday_alerts.py
    participant Y as Yahoo Finance

    C->>A: Trigger review job at 13:10 America/Los_Angeles
    A->>B: python3 cron_bridge.py alert-review
    B->>R: Execute review_intraday_alerts.py
    R->>R: Read /tmp/options_alert_state.json
    R->>Y: Fetch latest close for ranked symbols
    Y-->>R: Return close data
    R->>R: Build close-performance pillar
    R->>R: Write /tmp/intraday_alert_review.txt
    R-->>B: Exit 0
    B-->>A: Exit 0
    A-->>C: Run completed
```

## Cron Topology

- `yoloinvest-market-briefing-daily`
  - `0 6 * * *`
  - `America/Los_Angeles`
- `yoloinvest-intraday-tech-alerts`
  - `*/10 30-59 6 * * 1-5`
  - `America/Los_Angeles`
- `yoloinvest-intraday-tech-alerts-core`
  - `*/10 7-12 * * 1-5`
  - `America/Los_Angeles`
- `yoloinvest-intraday-tech-alerts-close`
  - `0 13 * * 1-5`
  - `America/Los_Angeles`
- `yoloinvest-intraday-alert-review`
  - `10 13 * * 1-5`
  - `America/Los_Angeles`

## Why `cron_bridge.py` Exists

OpenClaw cron isolated jobs run through `agentTurn`, not a raw shell runner. In practice this means a natural-language cron prompt can introduce unnecessary uncertainty around tool execution and completion. `cron_bridge.py` reduces that uncertainty by giving cron a single deterministic command target.

Execution model:
- cron -> isolated agentTurn
- isolated agentTurn -> `cron_bridge.py`
- `cron_bridge.py` -> canonical shell entrypoint or review script

That keeps the scheduler simple and makes debugging easier because each layer has one responsibility.

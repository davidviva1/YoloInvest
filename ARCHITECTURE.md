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

## Market Regime Detection Sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as OpenClaw Cron
    participant A as Isolated AgentTurn
    participant B as cron_bridge.py
    participant S as run_market_regime.sh
    participant P as market_regime.cli
    participant Y as Yahoo Finance
    participant T as Telegram API
    participant W as War Room Group

    C->>A: Trigger regime job (7:00 初判 / 9:00 确认)
    A->>B: python3 cron_bridge.py regime|regime-confirm
    B->>S: Execute run_market_regime.sh [phase]
    S->>S: Load .env.market-briefing
    S->>S: Activate venv
    S->>P: python3 -m yoloinvest.market_regime.cli scheduled --phase [初判|确认]
    P->>Y: Fetch SPY/QQQ 5m intraday + 1mo daily
    Y-->>P: Return chart data
    P->>P: Compute 5 signals (OR/ATR, Range/ATR, VWAP slope, volume pattern, OR breakout)
    P->>P: Aggregate regime (trend/range/mixed) + confidence + direction
    P->>P: Save state to /tmp/market_regime_state.json
    P->>T: Send formatted message with reasons
    T->>W: Deliver to War Room (-5275957557)
    W-->>T: 200 OK
    T-->>P: Success
    P-->>S: Exit 0
    S-->>B: Exit 0
    B-->>A: Exit 0
    A-->>C: Run completed
```

### Manual Trigger (via Telegram group)

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant TG as Telegram War Room
    participant GW as OpenClaw Gateway
    participant A as Trader Agent
    participant P as market_regime.cli
    participant Y as Yahoo Finance

    U->>TG: /market_regime NVDA
    TG->>GW: Message matches mentionPattern
    GW->>A: Wake trader agent with message
    A->>A: Parse command and ticker
    A->>P: python3 -m yoloinvest.market_regime.cli manual NVDA
    P->>Y: Fetch NVDA 5m intraday + 1mo daily
    Y-->>P: Return chart data
    P->>P: Compute regime signals
    P->>TG: Send result to War Room
    TG-->>U: Display regime analysis
```

### Regime Detection Signals

| Signal | Trend | Range |
|--------|-------|-------|
| Opening Range / ATR | > 60% | < 40% |
| Day Range / ATR | > 80% | < 50% |
| VWAP Slope | > 0.3% drift | < 0.15% drift |
| Volume Pattern | Increasing > 20% | Decreasing > 20% |
| OR Breakout | Price outside OR | Price inside OR |

Each signal contributes a weighted score. Final regime is determined by trend_score vs range_score ratio, with confidence levels (high/medium/low).

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
- `yoloinvest-market-regime-initial`
  - `0 7 * * 1-5`
  - `America/Los_Angeles`
  - SPY/QQQ 区间日/趋势日初判（开盘30min后）
- `yoloinvest-market-regime-confirm`
  - `0 9 * * 1-5`
  - `America/Los_Angeles`
  - 盘中确认/修正判断

## Why `cron_bridge.py` Exists

OpenClaw cron isolated jobs run through `agentTurn`, not a raw shell runner. In practice this means a natural-language cron prompt can introduce unnecessary uncertainty around tool execution and completion. `cron_bridge.py` reduces that uncertainty by giving cron a single deterministic command target.

Execution model:
- cron -> isolated agentTurn
- isolated agentTurn -> `cron_bridge.py`
- `cron_bridge.py` -> canonical shell entrypoint or review script

That keeps the scheduler simple and makes debugging easier because each layer has one responsibility.

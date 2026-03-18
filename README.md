# YoloInvest

YoloInvest is a modular market intelligence project with two primary apps:
- `market_briefing`: daily market briefing generation and Telegram delivery
- `options_alert`: intraday alerting for highly liquid large-cap tech stocks

## Modules

- `yoloinvest.market_briefing`
  - Generates the daily market briefing
  - Pulls market data, news, earnings, and economic calendar data
  - Economic calendar sourced from ForexFactory JSON API (primary) + Fed official calendar (supplementary)
  - Auto-detects critical events (FOMC, CPI, NFP, PCE, GDP) and highlights them in the briefing
  - Shows impact level, forecast, and previous values for each economic event
  - Runs AI analysis and sends the final Telegram report

- `yoloinvest.options_alert`
  - Runs intraday scans on selected large-cap tech names and leveraged ETFs
  - Uses a lightweight score model with severity levels
  - Uses price/volume plus lightweight news confirmation
  - Sends Telegram alerts only when signals are new or materially stronger

- `yoloinvest.market_regime`
  - Detects whether the current day is a trend day or range day
  - Analyzes opening range, ATR, VWAP slope, volume patterns, and OR breakout
  - Sends regime classification to War Room Telegram group

- `yoloinvest.weekly_calendar`
  - Pushes next week's economic calendar to the briefing Telegram group
  - Runs every Sunday 8:00 PM Pacific
  - Shows impact level (🔴/🟡), forecast, previous values, and critical event markers

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
- `TELEGRAM_CHAT_ID_MARKET_BRIEFING`
- `TELEGRAM_CHAT_ID_OPTIONS_ALERT`
- `LLM_API_KEY`

Optional:
- `LLM_API_BASE`
- `LLM_MODEL`

## Reference Docs

- Architecture: `ARCHITECTURE.md`
- Change log: `ReleaseNote.md`

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

## Options Alert (V2.2)

### 监控标的 (31 symbols)

| 类别 | 标的 |
|------|------|
| 指数 ETF | SPY, QQQ |
| 指数杠杆 ETF | TQQQ, SQQQ, SPXL, SPXS, SOXL, SOXS, UPRO |
| NVDA 杠杆 | NVDL (2x bull), NVDD (2x bear), NVDU (2x bull Direxion) |
| TSLA 杠杆 | TSLL (2x bull), TSLS (1x bear), TSLR (2x bear) |
| META 杠杆 | FBL (2x bull), METD (2x bear) |
| AMZN 杠杆 | AMZU (2x bull), AMZD (2x bear) |
| AVGO 杠杆 | AVGX (2x bull) |
| 个股 | AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AVGO, MRVL, ALAB, NBIS |

### Score 计算规则

Score 由 5 个维度累加，杠杆 ETF 和个股/指数 ETF 使用不同门槛：

**1. Day Change（日涨跌幅）**

| 分数 | 个股/指数 ETF | 杠杆 ETF |
|------|--------------|----------|
| +4 | ≥ 4% | ≥ 8% |
| +3 | ≥ 2.5% | ≥ 5% |
| +2 | ≥ 1.2% | ≥ 3% |

**2. Intraday Move（开盘后涨跌幅）**

| 分数 | 个股/指数 ETF | 杠杆 ETF |
|------|--------------|----------|
| +3 | ≥ 2% | ≥ 4% |
| +2 | ≥ 1.2% | ≥ 2.5% |
| +1 | ≥ 0.6% | ≥ 1.5% |

**3. Volume Ratio（量比 = 当日成交量 / 3 月均量）**

| 分数 | 门槛 |
|------|------|
| +3 | ≥ 2.5x |
| +2 | ≥ 1.5x |
| +1 | ≥ 0.8x |

**4. News（新闻命中）**
- 每条相关新闻 +1，最多 +3

**5. Market State**
- 盘中（REGULAR/POST/POSTPOST）+0.5

### Severity 分级

| 级别 | Score |
|------|-------|
| HIGH | ≥ 6 |
| MEDIUM | ≥ 3.5 |
| LOW | < 3.5 |

### 推送规则

1. **新 alert**：首次触发的标的立即推送
2. **升级推送**：severity 升级，或 score 增加 ≥ 1.5 时再次推送
3. **方向反转**：同一标的从涨转跌（或反之）视为新 alert
4. **过滤门槛**：
   - 个股/指数 ETF：日涨跌 ≥ 1% 或盘中波动 ≥ 0.5%
   - 杠杆 ETF：日涨跌 ≥ 3% 或盘中波动 ≥ 1.5%
   - medium/high severity 直接通过
   - low severity 需要有新闻且 score ≥ 3，或 score ≥ 3.5
5. **去重**：已推送且未升级的 alert 不重复发送

### 运行时间

- 盘中扫描：每 10 分钟，7:00 AM - 1:00 PM Pacific（工作日）
- 开盘前 30 分钟（6:30-7:00 AM）故意跳过，避免开盘噪音产生误报
- 收盘复盘：1:10 PM Pacific（工作日）

### 数据源

- 行情：Yahoo Finance（`query1.finance.yahoo.com`，5 天日线）
- 新闻：Yahoo Finance RSS + CNBC RSS

### 历史记录

- 状态文件：`/tmp/options_alert_state.json`
- 历史日志：`/tmp/options_alert_history.jsonl`

### 命令

```bash
# 手动运行 alert
./run_options_alert.sh

# 收盘复盘
./run_alert_review.sh

# 直接调用
python3 -m yoloinvest.options_alert.alert
```

---

## Market Regime（市场结构判断）

判断当日是趋势日还是区间日，推送到 War Room（Telegram 群 `-5275957557`）。

### 分析维度

| 信号 | 趋势日特征 | 区间日特征 |
|------|-----------|-----------|
| Opening Range / ATR | > 60% → 开盘波动大 | < 40% → 开盘窄幅 |
| Day Range / ATR | > 80% → 价格在扩展 | < 50% → 价格被压缩 |
| VWAP Slope | > 0.3% → 方向性强 | < 0.15% → VWAP 平坦 |
| Volume Pattern | 递增 > 20% → 资金加速 | 递减 > 20% → 参与度下降 |
| OR Breakout | 价格突破 opening range | 价格仍在 range 内 |

每个信号贡献 trend 或 range 分数，最终汇总判断：
- **趋势日**：trend score ≥ 2x range score（高置信度需 ≥ 6 分）
- **区间日**：range score ≥ 2x trend score（高置信度需 ≥ 6 分）
- **混合/待确认**：两者接近

### 方向判断

- 日涨幅 > 0.3% → 偏多
- 日跌幅 > 0.3% → 偏空
- 其他 → 中性

### 策略提示

- 趋势日：顺势而为，回调找入场，不要逆势抄底/摸顶
- 区间日：高抛低吸，在支撑/阻力位附近操作，避免追突破

### 运行方式

```bash
# 定时推送（初判 / 确认）
./run_market_regime.sh 初判
./run_market_regime.sh 确认

# 手动查询单个标的
python3 -m yoloinvest.market_regime.cli manual TSLA

# 直接调用
python3 -m yoloinvest.market_regime.cli scheduled --phase 初判
```

### 默认标的

SPY, QQQ

### 推送目标

War Room Telegram 群（`-5275957557`）

### 状态文件

`/tmp/market_regime_state.json`

## Deployment

Canonical deployment model:
- one OpenClaw gateway
- OpenClaw cron for scheduling
- no systemd timer duplication
- `.env.market-briefing` as the local secret file

### 脚本一览

| 脚本 | 用途 | 手动运行 |
|------|------|----------|
| `run_briefing.sh` | 每日市场简报（数据采集 → AI 分析 → Telegram 推送） | `./run_briefing.sh` |
| `run_options_alert.sh` | 盘中异动扫描（价格/量/新闻 → 评分 → 推送） | `./run_options_alert.sh` |
| `run_alert_review.sh` | 收盘复盘（当日 alert 命中率/方向/收益总结） | `./run_alert_review.sh` |
| `run_market_regime.sh` | 市场结构判断（趋势日 vs 区间日） | `./run_market_regime.sh [初判\|确认]` |
| `run_weekly_calendar.sh` | 下周经济日历推送（impact/预期/前值） | `./run_weekly_calendar.sh` |

### 定时任务 (Cron)

所有时间均为 America/Los_Angeles (Pacific Time)。

| 名称 | 时间 | 频率 | 说明 |
|------|------|------|------|
| `yoloinvest-market-briefing-daily` | 6:00 AM | 周一至周五 | 每日市场简报 → 简报群 |
| `yoloinvest-intraday-tech-alerts-core` | 7:00 AM - 12:59 PM 每 10 分钟 | 周一至周五 | 盘中异动扫描 → alert 群 |
| `yoloinvest-intraday-tech-alerts-close` | 1:00 PM | 周一至周五 | 收盘前最后一次扫描 → alert 群 |
| `yoloinvest-intraday-alert-review` | 1:10 PM | 周一至周五 | 收盘复盘报告 → alert 群 |
| `yoloinvest-market-regime-initial` | 7:00 AM | 周一至周五 | 市场结构初判 → War Room 群 |
| `yoloinvest-market-regime-confirm` | 9:00 AM | 周一至周五 | 市场结构确认 → War Room 群 |
| `yoloinvest-weekly-calendar-sunday` | 8:00 PM | 周日 | 下周经济日历 → 简报群 |

注：开盘前 30 分钟（6:30-7:00 AM）不扫描，避免开盘噪音误报。

Detailed deployment notes are in `DEPLOYMENT.md`.

## Dependency Management

- `requirements.in`: top-level runtime dependencies
- `requirements.txt`: locked dependency set
- `update_requirements.sh`: regenerate locked dependencies
- `check_requirements.py`: verify lock consistency

Useful commands:

```bash
make deps
make run
make alert
make update-deps
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
├── run_alert_review.sh
├── run_market_regime.sh
├── run_weekly_calendar.sh
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
│   ├── options_alert/
│   │   ├── __init__.py
│   │   └── alert.py
│   ├── market_regime/
│   │   ├── __init__.py
│   │   ├── regime.py
│   │   └── cli.py
│   └── weekly_calendar/
│       ├── __init__.py
│       └── app.py
└── fonts/
```

## Release Status

- Current stable release tag: `v2.1.0`
- Historical tag from the old layout: `v1.0.0`

## Notes

- `LYNAS.AX` has been removed from the watchlist due to unstable Yahoo Finance data.
- `options_alert` currently uses a proxy signal layer, not a true options tape feed.
- The project has been renamed from `market-briefing` to `YoloInvest` and reorganized into modules.

# YoloInvest — Claude Code 指令

## 重要：当用户说"跑简报"时的行为

**禁止** 运行 `python3 -m yoloinvest.market_briefing.app` 或 `run_briefing.sh`。
**禁止** 调用外部 LLM API。
**必须** 按照下面的三步流程执行：由 Claude 自己采集数据、读取数据、在对话中直接输出分析简报。

## 项目概览

美股市场情报系统，通过 Telegram 推送。详见 `ARCHITECTURE.md` 和 `README.md`。

## 快捷指令

### "跑简报" — 每日市场简报

当用户说"跑简报"时，**严格**执行以下流程：

#### 第一步：仅运行数据采集（不运行分析和报告生成）
```bash
.venv/bin/python3 -c "from yoloinvest.market_briefing.app import YoloInvestApp; YoloInvestApp().fetch_all_data()"
```

#### 第二步：读取数据

读取以下文件：
- `/tmp/market_data.json` — 行情（股票、期货、VIX、加密货币、大宗商品）
- `/tmp/market_news.json` — 新闻
- `/tmp/earnings_calendar.json` — 财报日历
- `/tmp/economic_data.json` — 经济数据日历

#### 第三步：在对话中输出简报

按以下结构和顺序输出，使用资深美股分析师视角，中文，简洁专业：

---

**一、盘前情绪速读**

用 futures_vix 数据，格式：
```
ES (S&P 500): 6412.25 (-1.73%) | NQ (Nasdaq 100): 23328.50 (-1.96%) | YM (Dow 30): 45424.00 (-1.74%)
VIX: 31.05 (+13.16%) — 极度恐慌 🚨
Fear & Greed Index: 34 / Fear（如能获取）
```
VIX 分级：≥30 极度恐慌 🚨，≥25 恐慌偏高 ⚠️，≥20 偏高 📈，≤13 极度平静 😴

Fear & Greed 数据源（尝试获取，失败则跳过）：
```bash
curl -s "https://production.dataviz.cnn.io/index/fearandgreed/graphdata" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['fear_and_greed']['score'], d['fear_and_greed']['rating'])"
```

---

**二、重大事件预警**

**2a. 市场结构性事件**

根据当前日期，主动检查本周是否有以下特殊交易日并提醒：

| 事件 | 时间规则 | 影响 |
|------|----------|------|
| 四巫日 (Quad Witching) | 每年 3/6/9/12 月第三个周五 | 期权+期货同时到期，成交量暴增，尾盘波动剧烈，最后一小时尤其危险 |
| 月度期权到期 (Monthly OpEx) | 每月第三个周五 | 期权到期 pin risk，gamma exposure 变化，收盘前波动加大 |
| 周期权到期 (0DTE 集中日) | 每周一/三/五（SPY/QQQ） | 0DTE gamma 效应可能放大盘中波动 |
| FOMC 会议日 | 见经济日历 | 2:00 PM ET 决议公布，2:30 PM ET 记者会，之前市场观望，之后波动剧烈 |
| CPI/PCE 公布日 | 见经济日历 | 8:30 AM ET 公布，盘前即大幅波动 |
| NFP 非农日 | 见经济日历 | 8:30 AM ET 公布，通常当月第一个周五 |
| 月末/季末 rebalance | 每月/季度最后 1-2 个交易日 | 机构 rebalance 资金流可能造成反直觉的价格波动 |
| 长假前半日交易 | 感恩节后周五、圣诞/元旦前夕 | 1:00 PM ET 收盘，流动性极低 |

输出示例：
```
⚠️ 本周五 (3/21) 是三月四巫日 — 期权+期货同时到期
→ 预计成交量比平日高 2-3 倍，最后一小时波动剧烈
→ 策略：避免尾盘持有大量 gamma 敞口，提前平仓或对冲
```

**2b. 经济数据事件**

从 economic_data.json 的 calendar 中提取 critical=true 的事件，用表格展示：
| 日期 | 事件 | 预期 | 前值 | 关注点 |
标注本周最关键的 1-2 个事件（如 FOMC、NFP、CPI），说明预期时间和对盘中交易的影响。

---

**三、涨跌排行榜**

从全部个股中提取涨跌幅前 5 和后 5，快速一览：
```
跌幅前五：APLD -7.6% | SMR -6.3% | NNE -4.1% | META -4.0% | AMZN -4.0%
涨幅前五：CEG +2.1% | VST +2.1% | REMX +1.8% | REE +1.4% | NRG +1.1%
```

---

**四、宏观影响分析**

结合新闻、经济日历、期货方向、VIX 水平，判断整体市场情绪（看涨/看跌/中性），2-3 段。如果有重大新闻事件驱动，优先分析。周末新闻为空时注明。

---

**五、板块分析**

每个板块先列行情表，再给 2-3 句分析：

**科技巨头**
```
🔴 AAPL: $248.80 (-1.62%) Vol: 47.8M
🔴 MSFT: $356.77 (-2.51%) Vol: 37.8M
...
```
分析：xxxxx

**芯片** / **数据中心** / **电力/核能** / **稀土** 同上格式。

---

**六、重点个股深度分析**

必须包含 NVDA、AVGO、TSLA、SPY、QQQ。对每只标注：
- 收盘价、涨跌幅、成交量
- 关键价位：前收、昨高、昨低（从 previous_close / prev_day_high / prev_day_low 字段提取）
- 盘前高低（premarket_high / premarket_low，有值时展示）
- 距离 52 周高点/低点的百分比距离（可通过 yfinance 快速查询，或根据已知信息估算）
- 最近整数关口（如 $170、$500、$360）的支撑/阻力意义
- 短期支撑/阻力位判断
- 交易建议

注意：SPY 和 QQQ 在 futures_vix 中以 ES/NQ 期货形式存在，分析时同时参考期货和现货数据。如果 stocks 中没有 SPY/QQQ 现货数据，使用 ES/NQ 期货数据并注明。

---

**七、加密货币**

BTC、ETH 各 1-2 句，标注价格、涨跌、关键支撑/阻力。

---

**八、大宗商品**

先列行情表（原油、黄金、铜、白银、天然气），再给整体分析。重点关注：
- 原油对通胀预期的影响
- 黄金作为避险指标的信号
- 铜对经济前景的指示

---

**九、财报日历**

从 earnings_calendar.json 提取，按日期分组展示。为空时注明"本周无重要财报"。

---

**十、总结与操作建议**

3-5 句话，包括：
- 本周核心风险和机会
- 仓位管理建议（根据 VIX 水平）
- 关键时间节点提醒（经济数据发布 + 四巫日/OpEx 等结构性事件）
- 如果有 market regime 数据（/tmp/market_regime_state.json），结合趋势日/区间日策略给出具体建议
- 如果本周有四巫日/月度 OpEx，提醒尾盘 gamma 风险和 pin risk
- 如果临近月末/季末，提醒机构 rebalance 资金流风险

---

## 环境

- Python venv: `.venv/`
- 数据源: Yahoo Finance + RSS 新闻 + ForexFactory 经济日历
- 输出目录: `/tmp/`
- 重点个股 (FOCUS_STOCKS): NVDA, AVGO, SPY, QQQ, TSLA
- 监控板块: 科技巨头、芯片、数据中心、电力/核能、稀土

# Future Features

## GEX (Gamma Exposure) Integration

### 目标
在每日简报中加入 GEX 环境判断，帮助用户了解当天市场的 gamma 特征，辅助交易风格决策。

### 功能需求

#### 1. 盘前 GEX 环境判断
- **Positive/Negative Gamma** — 判断当天是容易 mean revert 还是容易 trend
- **输出示例**：
  ```
  今日 GEX 环境：
  - SPY: Negative Gamma → 容易趋势加速，适合 breakout
  - QQQ: Positive Gamma → 容易区间震荡，适合 fade
  - NVDA: Neutral → 观察盘中 price action
  ```

#### 2. 交易风格建议（基于 GEX + 技术面）
- 结合 GEX 环境 + 技术分析，给出当天交易风格建议
- **输出示例**：
  ```
  交易策略建议：
  - SPY: Negative gamma + 突破前高 → 适合 breakout 追单
  - QQQ: Positive gamma + VWAP 附近震荡 → 适合 fade 反转
  - NVDA: 无明确催化 + 低波动 → 建议观望或小仓位 scalp
  ```

### 数据源选项

#### 选项 1: SpotGamma API
- **优点**: 数据质量高，实时更新
- **缺点**: 需要付费订阅（$50-100/月），API 接入需要开发
- **适用场景**: 如果预算允许，这是最稳定的方案

#### 选项 2: yehangshe.com (Nightwatch)
- **优点**: 免费，数据较全
- **缺点**: 需要爬取（可能不稳定），数据更新频率不确定
- **适用场景**: 预算有限，可以接受偶尔数据缺失

#### 选项 3: 自建 GEX 计算
- **优点**: 完全自主，无依赖
- **缺点**: 需要期权链数据（CBOE/Yahoo Finance），计算复杂度高
- **适用场景**: 长期方案，需要较多开发时间

### 实现优先级
- **Phase 1** (MVP): 只输出 Positive/Negative Gamma 判断（基于 yehangshe.com 或简化计算）
- **Phase 2**: 加入 Call/Put Wall 位置（盘前参考）
- **Phase 3**: 结合技术面给出交易风格建议

### 注意事项
- **盘前 GEX 是"环境判断"，不是精确交易信号** — 真正的交易决策还是要看盘中 price action
- **GEX 会盘中变化** — 大单进出会改变 gamma 分布，盘前数据只是起点
- **不要过度依赖 GEX** — 它是辅助工具，不是圣杯

### 相关资源
- SpotGamma: https://spotgamma.com
- Perfiliev GEX 教程: https://perfiliev.co.uk/market-commentary/
- yehangshe.com: https://yehangshe.com
- CBOE 期权数据: https://www.cboe.com/delayed_quotes/

---

**记录日期**: 2026-03-14  
**提出人**: Hayden  
**优先级**: Medium（在完成核心功能后考虑）



# Future Features

## 🟢 快赢 — 高价值，1-2 天实现

---

### Alert 胜率追踪

**目标**

每周自动汇总 `options_alert_history.jsonl`，生成信号质量报告并推送到 War Room 群，帮助持续校准评分权重。

**功能需求**

* 统计各标的命中率（触发后 EOD 方向正确率）
* 对比 HIGH vs MEDIUM severity 的精准度差异
* 输出最近 5 个交易日的 score 分布和 hit rate 趋势
* 每周一开盘前自动推送，推送目标：War Room 群

**输出示例**

```
📊 YoloInvest 信号周报（3/17-3/21）
HIGH severity:  12 次触发 → 命中率 75%
MEDIUM severity: 28 次触发 → 命中率 46%
表现最佳：NVDA（8/10）、TQQQ（6/8）
表现最差：AMZU（2/7）
建议：考虑提高 AMZU 的 volume ratio 门槛
```

**实现说明**

* 数据源：`/tmp/options_alert_history.jsonl`（已有）
* 命中判断：触发方向 vs 当日收盘涨跌符号一致 = 命中
* 新增脚本：`yoloinvest/weekly_review/app.py`
* 新增 runner：`run_weekly_review.sh`
* Cron：每周一 5:50 AM Pacific（早于日报）

**优先级**：High（数据已有，只差汇总逻辑）

---

### 盘前情绪仪表盘

**目标**

在每日市场简报开头加入两个市场情绪指标，让用户在读详细分析前先感知整体温度。

**功能需求**

* **VIX**：当前值 + 近 30 日百分位（如：VIX 18.3，处于近30日 62% 分位）
* **Fear & Greed Index**：CNN 免费 API，输出数值 + 文字标签（Extreme Fear / Fear / Neutral / Greed / Extreme Greed）

**输出示例**

```
🌡️ 市场情绪
VIX: 18.3（近30日 62% 分位，偏高）
Fear & Greed: 34 / Fear
→ 市场情绪偏谨慎，注意假突破风险
```

**数据源**

* VIX：Yahoo Finance（`^VIX`，已有 yfinance）
* Fear & Greed：`https://production.dataviz.cnn.io/index/fearandgreed/graphdata`（免费，无需 key）

**实现说明**

* 修改：`yoloinvest/market_briefing/app.py`，在报告最前面插入情绪摘要段
* 修改：`yoloinvest/common/fetchers.py`，新增 `fetch_vix()` 和 `fetch_fear_greed()`

**优先级**：High

---

### 关键技术位提示

**目标**

在 Market Regime 输出里附加当前 SPY/QQQ 的关键价格位信息，减少交易时手动查价的操作。

**功能需求**

* 距离 52 周高点 / 低点的百分比距离
* 距离最近整数关口（如 500、510）的距离
* 当前是否处于 VWAP 上方 / 下方

**输出示例**

```
📍 关键价位（SPY）
当前：512.4
52w High：585.2（距离 -12.4%）
52w Low：480.1（距离 +6.7%）
最近整数关口：510（下方支撑），515（上方阻力）
VWAP：511.8（当前价格在 VWAP 上方）
```

**数据源**

* Yahoo Finance（已有 yfinance）

**实现说明**

* 修改：`yoloinvest/market_regime/regime.py`，新增 `get_key_levels()` 函数

**优先级**：High

---

### 经济事件静默模式

**目标**

在重大经济数据发布前后自动提升 alert 触发门槛，减少数据公布前假突破带来的噪音 alert。

**背景**

当前系统已有 ForexFactory 经济日历数据，options_alert 模块完全没有读取它。FOMC/CPI/NFP 等事件发布前30分钟市场波动异常，容易产生大量 LOW severity 误报。

**功能需求**

* 检测当日是否有 HIGH impact 经济事件（FOMC、CPI、NFP、PCE、GDP）
* 发布前 30 分钟：自动将 LOW severity 过滤门槛提升（score 门槛 +1.5）
* 发布后 15 分钟：恢复正常门槛
* 在推送的 alert 消息里标注"⚠️ 注意：XX 分钟后有 CPI 数据"

**实现说明**

* 修改：`yoloinvest/options_alert/alert.py`，新增 `get_silence_mode()` 函数
* 数据源：复用 `yoloinvest/common/fetchers.py` 中已有的经济日历数据

**优先级**：High（改动小，收益大）

---

## 🟡 中等优先 — 明显提升体验，约 1 周实现

---

### GEX 自建计算（Gamma Exposure）

**目标**

在每日简报中加入 GEX 环境判断，帮助了解当天市场的 gamma 特征，辅助交易风格决策。

**功能需求**

#### 1. 盘前 GEX 环境判断

* **Positive/Negative Gamma** — 判断当天是容易 mean revert 还是容易 trend
* **输出示例**：

```
今日 GEX 环境：
- SPY: Negative Gamma → 容易趋势加速，适合 breakout
- QQQ: Positive Gamma → 容易区间震荡，适合 fade
- NVDA: Neutral → 观察盘中 price action
```

#### 2. 交易风格建议（基于 GEX + 技术面）

* 结合 GEX 环境 + 技术分析，给出当天交易风格建议
* **输出示例**：

```
交易策略建议：
- SPY: Negative gamma + 突破前高 → 适合 breakout 追单
- QQQ: Positive gamma + VWAP 附近震荡 → 适合 fade 反转
- NVDA: 无明确催化 + 低波动 → 建议观望或小仓位 scalp
```

**数据源**

自建计算（推荐，无需付费）：从 Yahoo Finance 拉 SPY/QQQ 期权链，按 Strike 计算 `Gamma × OI`，正负 GEX 求和判断方向。付费备选：SpotGamma API（$50-100/月）。

**实现优先级**

* Phase 1（MVP）：正 / 负 Gamma 判断 + 一句话结论
* Phase 2：加入 Call/Put Wall 位置
* Phase 3：结合技术面给出交易风格建议

**注意事项**

* GEX 是"环境判断"，不是精确交易信号，真正的决策仍看盘中 price action
* GEX 盘中会随大单进出变化，盘前数据只是起点
* 不要过度依赖，它是辅助工具

**参考资源**

* SpotGamma: <https://spotgamma.com>
* Perfiliev GEX 教程: <https://perfiliev.co.uk/market-commentary/>
* CBOE 期权数据: <https://www.cboe.com/delayed_quotes/>

**优先级**：Medium（在完成快赢功能后）

---

### Telegram Bot 交互查询

**目标**

给 Telegram Bot 加 webhook，把工具从"推送"模式升级为"可对话"模式。

**功能需求**

| 命令 | 说明 |
|------|------|
| `/status NVDA` | 查询 NVDA 当前实时信号和 score |
| `/history TSLA` | 查看 TSLA 今日已触发的 alert 记录 |
| `/regime` | 查询当前市场结构（趋势 / 区间 / 混合）|
| `/levels SPY` | 查询 SPY 当前关键技术位 |
| `/briefing` | 手动触发一次简报生成并推送 |

**实现说明**

* 使用 `python-telegram-bot` 库的 webhook 模式
* 新增模块：`yoloinvest/bot/app.py`
* 需要部署一个常驻进程（或用 OpenClaw webhook 接收）

**优先级**：Medium

---

### 杠杆 ETF 跟踪误差监控

**目标**

当杠杆 ETF 的实际涨幅与理论值出现异常偏差时，自动发出警告，识别 rebalancing 压力或流动性异常。

**背景**

理论上 NVDL ≈ 2× NVDA，TQQQ ≈ 3× QQQ。当实际偏差持续超过阈值，可能预示大规模 rebalancing 或机构异动。

**功能需求**

* 计算每个杠杆 ETF 的"理论涨跌"（基础标的 × 杠杆倍数）
* 对比"实际涨跌"，计算偏差百分比
* 偏差超过 2% 时推送 alert（含偏差方向和大小）
* 纳入盘中扫描周期（复用现有 options_alert 的 cron）

**监控对标关系**

| 杠杆 ETF | 基础标的 | 倍数 |
|----------|----------|------|
| NVDL / NVDU | NVDA | 2x |
| NVDD | NVDA | -2x |
| TSLL | TSLA | 2x |
| TSLR | TSLA | -2x |
| TQQQ | QQQ | 3x |
| SQQQ | QQQ | -3x |
| SPXL / UPRO | SPY | 3x |
| SPXS | SPY | -3x |
| SOXL | SOXX | 3x |

**优先级**：Medium

---

### 隐含波动率（IV）摘要

**目标**

在每日简报中加入 SPY/QQQ/NVDA 的 ATM 隐含波动率和 IV Rank，辅助判断期权策略方向。

**功能需求**

* ATM IV：最近到期月份的平值期权 IV
* IV Rank：当前 IV 在近 52 周范围内的百分位
* 一句话结论：IV 高 → 适合卖权；IV 低 → 适合买权

**输出示例**

```
📉 隐含波动率摘要
SPY: IV 18.2%，IV Rank 45%（中性）
QQQ: IV 22.4%，IV Rank 71%（偏高，考虑卖权）
NVDA: IV 51.3%，IV Rank 83%（高，财报前注意）
```

**数据源**

* Yahoo Finance 期权链（`yfinance.Ticker.options`，免费）

**优先级**：Medium

---

## 🔴 长期演进 — 值得规划，暂不急

---

### 信号回测框架

**目标**

用历史数据验证 options_alert 评分模型的有效性，提供数据基础替代凭感觉调参。

**功能需求**

* 用 yfinance 拉历史 OHLCV，模拟评分模型的历史触发点
* 统计"触发后 1h / EOD 平均收益"
* 对比不同 score 门槛下的信噪比
* 输出各维度权重的灵敏度分析（改变 Day Change 权重 +1 后整体命中率如何变化）

**实现说明**

* 新增模块：`yoloinvest/backtest/`
* 可先做离线脚本，不需要加入 cron

**优先级**：Low（先积累足够的实盘历史数据再做）

---

### Web Dashboard

**目标**

用 Streamlit 或轻量 FastAPI + HTML 展示实时状态和历史统计，提供 Telegram 推送之外的全局视角。

**功能需求**

* 实时展示 31 个标的的当前 score 热力图
* 今日已触发 alert 列表（含 severity 和触发原因）
* 历史命中率趋势图（按标的、按 severity 分类）
* Market Regime 当前状态

**实现说明**

* 推荐 Streamlit（最快上线）
* 数据源：读取 `/tmp/options_alert_state.json` 和 `options_alert_history.jsonl`

**优先级**：Low

---

**文档维护说明**

* 记录新想法时请注明提出日期和提出人
* 功能完成后移入 `ReleaseNote.md`，从本文件删除







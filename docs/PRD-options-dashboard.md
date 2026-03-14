# PRD: YoloInvest Options Structure Dashboard

## 产品概述

构建一个面向日内期权交易者的实时期权结构分析平台，提供 Gamma Exposure (GEX) 可视化、隐含波动率分析、关键价位标注和盘中资金流向追踪。

产品定位：为活跃期权交易者打造的一体式交易终端，把市场结构分析、期权 Flow 监控、波动率评估整合在同一个网页中。

竞品参考：yehangshe.com (Nightwatch) — 目前已上线 GEX 结构图、GEX 热力图、IV 波动率分析三个模块，0DTE Tide 即将上线。

---

## 目标用户

- 美股日内期权交易者（0DTE / 周度 / 近月）
- 交易标的：SPY、QQQ、IWM、NVDA、TSLA、AVGO、AAPL 等高流动性大盘股
- 核心需求：盘中快速判断市场结构、找到关键支撑阻力位、理解 dealer positioning

---

## 核心问题

日内期权交易者在盘中需要快速回答以下问题：

1. 现价附近最大的 Call Wall / Put Wall 在哪？
2. Gamma Flip 在哪？当前是正 gamma 还是负 gamma 环境？
3. 哪个到期日最关键？
4. Dealer positioning 是偏压制波动还是放大波动？
5. 哪些 strike 是市场当天最可能反复博弈的磁铁位？
6. 零日期权的资金流向偏多还是偏空？

目前这些信息散落在多个数据源中，没有统一的可视化界面。

---

## 功能规划

### Phase 1: MVP（6-8 周）

目标：最小可用产品，验证核心价值。

#### 1.1 GEX 结构图（核心功能）

- 实时 Gamma Exposure 各行权价分布柱状图
- 自动标注关键位：
  - Call Wall（最大正 gamma 暴露的 strike）
  - Put Wall（最大负 gamma 暴露的 strike）
  - Gamma Flip（gamma 从正转负的价格点）
  - Spot Price（当前价格标线）
- 数据刷新频率：1-5 分钟
- 支持标的切换：SPY、QQQ、IWM、NVDA、TSLA、AVGO、AAPL、AMZN、META、MSFT
- 支持到期日切换：0DTE / 本周 / 下周 / 月度 / 全部

#### 1.2 GEX 热力图

- 盘中价格 × 到期日矩阵
- 颜色编码 Gamma 强度变化
- 快速捕捉异常积聚区域
- 支持时间轴滚动查看盘中变化

#### 1.3 IV 波动率面板

- IV Rank：当前 IV 在 52 周历史中的分位排名
- IV Term Structure：各到期日 ATM 隐含波动率曲线
- IV Skew (25Δ)：同一到期日不同 delta 的 IV 差异
- 用途：快速判断波动率高低水平，决定买方/卖方策略

#### 1.4 基础设施

- 用户认证：Discord OAuth
- 订阅支付：Stripe 或 Whop
- 响应式 Web 界面

### Phase 2: 增强功能（Phase 1 后 4-6 周）

#### 2.1 0DTE Tide（零日期权资金流）

- 零日期权 Call / Put 净权利金实时累积
- 追踪日内资金方向（偏多/偏空）
- 可视化累积曲线 + 价格叠加

#### 2.2 历史回放系统

- 选择历史日期回放盘中 GEX 快照
- 分钟级时间轴拖动
- 用途：复盘验证结构信号的有效性

#### 2.3 盘中告警系统

- 价格接近 Call Wall / Put Wall 时推送
- Gamma Flip 被击穿时推送
- 某一 strike OI/Volume 激增时推送
- 推送渠道：Telegram / Discord / 浏览器通知

#### 2.4 Strike Ladder

- 以执行价为核心的纵向面板
- 每个 strike 显示：Call/Put OI、Volume、Delta、Gamma
- 高亮关键位：Call Wall、Put Wall、Active Strike

### Phase 3: 高级功能（长期）

#### 3.1 环境判断引擎

- 基于 GEX 结构自动判断当日市场环境：
  - Mean Reversion Day（正 gamma 主导，波动被压制）
  - Breakout Day（负 gamma 主导，波动被放大）
  - Gamma Pin Day（大量 gamma 集中在现价附近）
  - Squeeze Risk（极端定位可能引发逼空/逼多）

#### 3.2 质量追踪系统

- 每个 Call Wall / Put Wall / Gamma Flip 标注后，追踪后续价格表现
- 统计命中率、平均偏离度
- 按标的、按市场环境分类统计
- 用途：持续验证和优化结构信号的有效性

#### 3.3 多标的对比视图

- 同时查看多个标的的 GEX 结构
- 板块级别的 gamma 暴露汇总

#### 3.4 Intraday Flow Overlay

- 在 GEX 结构图上叠加盘中新成交期权量
- 区分主动买入/卖出
- 更接近"真实 flow"而非静态 OI

---

## 技术架构

### 前端

- 框架：React 18 + Vite
- 状态管理：Zustand
- 图表：D3.js + SVG（GEX 结构图、热力图）、Recharts（IV 曲线）
- 样式：Tailwind CSS
- 实时通信：WebSocket（原生）
- 部署：Cloudflare Pages 或 Vercel

### 后端

- 运行时：Node.js
- 框架：Express 或 Fastify
- 数据库：PostgreSQL（用户、订阅、历史快照）
- 缓存：Redis（实时数据缓存、WebSocket 状态）
- 任务调度：Node cron 或外部 cron
- 部署：Railway / Render / Fly.io / EC2

### 数据管道

- 数据源：Polygon.io Options API（核心）
- 数据流：
  1. Polygon API → 拉取期权链（strikes、OI、volume、IV、Greeks）
  2. 计算引擎 → 计算 GEX、Call Wall、Put Wall、Gamma Flip
  3. 快照存储 → PostgreSQL（历史回放用）
  4. WebSocket 广播 → 推送到前端
- 刷新频率：
  - 盘中（9:30 AM - 4:00 PM ET）：每 1-5 分钟
  - 盘前/盘后：每 15 分钟
  - 收盘后：停止刷新，保留最后快照

### 核心计算逻辑

#### Gamma Exposure (GEX) 计算

```
对每个 strike K：
  GEX(K) = Call_OI(K) × Call_Gamma(K) × 100 × Spot²× 0.01
          - Put_OI(K) × Put_Gamma(K) × 100 × Spot² × 0.01

Call Wall = argmax(Call_OI(K) × Call_Gamma(K))
Put Wall  = argmax(Put_OI(K) × Put_Gamma(K))  [put 侧]
Gamma Flip = K where cumulative GEX changes sign
Total GEX = sum(GEX(K)) for all K
```

#### IV Rank 计算

```
IV_Rank = (Current_IV - 52w_Low_IV) / (52w_High_IV - 52w_Low_IV) × 100
```

### API 设计

```
GET  /api/health                          # 服务健康检查
GET  /api/public/config                   # 公开配置（支付链接等）

POST /api/auth/discord                    # Discord OAuth 登录
POST /api/auth/logout                     # 登出
GET  /api/auth/me                         # 当前用户信息
POST /api/auth/refresh                    # 刷新 token

GET  /api/subscription/status             # 订阅状态

GET  /api/gex/latest?ticker=SPY           # 最新 GEX 快照
GET  /api/gex/intraday-history?ticker=SPY&date=2026-03-14  # 盘中历史
GET  /api/gex/replay-dates?ticker=SPY     # 可回放日期列表
GET  /api/gex/replay-day?ticker=SPY&date=2026-03-14        # 某日完整回放数据

GET  /api/volatility/latest?ticker=SPY    # 最新 IV 数据
GET  /api/volatility/history?ticker=SPY   # IV 历史（52 周）

GET  /api/flow/0dte?ticker=SPY            # 0DTE 资金流（Phase 2）

WebSocket /ws                             # 实时推送通道
  → subscribe: { type: "subscribe", ticker: "SPY" }
  ← snapshot:  { type: "gex_snapshot", data: {...} }
  ← update:    { type: "gex_update", data: {...} }
```

### 数据库 Schema

```sql
-- 用户表
CREATE TABLE users (
  id            UUID PRIMARY KEY,
  discord_id    TEXT UNIQUE NOT NULL,
  discord_name  TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

-- 订阅表
CREATE TABLE subscriptions (
  id            UUID PRIMARY KEY,
  user_id       UUID REFERENCES users(id),
  status        TEXT NOT NULL,  -- active / inactive / trial
  provider      TEXT NOT NULL,  -- stripe / whop
  provider_id   TEXT,
  expires_at    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- GEX 快照表
CREATE TABLE gex_snapshots (
  id            BIGSERIAL PRIMARY KEY,
  ticker        TEXT NOT NULL,
  snapshot_at   TIMESTAMPTZ NOT NULL,
  spot_price    NUMERIC NOT NULL,
  total_gex     NUMERIC,
  call_wall     NUMERIC,
  put_wall      NUMERIC,
  gamma_flip    NUMERIC,
  strikes_data  JSONB NOT NULL,  -- 各 strike 的 GEX 明细
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_gex_ticker_time ON gex_snapshots(ticker, snapshot_at DESC);

-- IV 快照表
CREATE TABLE iv_snapshots (
  id            BIGSERIAL PRIMARY KEY,
  ticker        TEXT NOT NULL,
  snapshot_at   TIMESTAMPTZ NOT NULL,
  iv_rank       NUMERIC,
  atm_iv        NUMERIC,
  term_structure JSONB,  -- 各到期日 ATM IV
  skew_data     JSONB,   -- 25Δ skew
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_iv_ticker_time ON iv_snapshots(ticker, snapshot_at DESC);

-- 告警历史表（Phase 2）
CREATE TABLE alert_events (
  id            BIGSERIAL PRIMARY KEY,
  ticker        TEXT NOT NULL,
  alert_type    TEXT NOT NULL,  -- call_wall_touch / put_wall_touch / gamma_flip_cross
  trigger_price NUMERIC NOT NULL,
  level_price   NUMERIC NOT NULL,
  triggered_at  TIMESTAMPTZ NOT NULL,
  follow_up     JSONB  -- 后续价格表现追踪
);
```

---

## 页面结构

```
/                       # 落地页（产品介绍、功能展示、注册入口）
/auth/error             # 登录错误页
/status                 # 系统状态页

/app                    # 应用主入口（需登录）
/app/start              # 新用户引导
/app/subscribe          # 订阅开通页
/app/access             # 权限检查/等待页
/app/waiting            # 等待权限同步
/app/dashboard          # 主仪表盘（GEX 结构图 + 热力图 + 关键位）
/app/volatility         # IV 波动率分析页
/app/account            # 账户管理
/app/support            # 支持页面
```

### Dashboard 布局

```
┌─────────────────────────────────────────────────────┐
│  Ticker: [SPY ▼]   Expiry: [0DTE ▼]   ● Live      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Summary Cards                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │
│  │ Spot │ │Call  │ │Put   │ │Gamma │ │Total │     │
│  │Price │ │Wall  │ │Wall  │ │Flip  │ │ GEX  │     │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘     │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  GEX Structure Chart                                │
│  (Gamma Exposure by Strike, 柱状图)                  │
│  ← Put Side (红) ──── Spot ──── Call Side (绿) →    │
│  标注: Call Wall | Put Wall | Gamma Flip            │
│                                                     │
├──────────────────────┬──────────────────────────────┤
│                      │                              │
│  GEX Heatmap         │  IV Panel                    │
│  (Price × Expiry)    │  - IV Rank gauge             │
│                      │  - Term Structure curve      │
│                      │  - IV Skew (25Δ)             │
│                      │                              │
├──────────────────────┴──────────────────────────────┤
│                                                     │
│  0DTE Tide (Phase 2)                                │
│  Call/Put 净权利金累积曲线 + 价格叠加                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 成本估算

### 一次性开发成本

| 模块 | 工作量 | 说明 |
|------|--------|------|
| 前端 SPA + 实时图表 | 3-4 周 | React + D3 + WebSocket |
| 后端 API + WebSocket + 计算引擎 | 2-3 周 | GEX/IV 计算、数据广播 |
| Polygon 数据管道 + 快照存储 | 1-2 周 | 期权链拉取、清洗、存储 |
| 认证 + 订阅支付 | 1 周 | Discord OAuth + Stripe/Whop |
| 部署 + 监控 + 调试 | 1 周 | CI/CD、日志、告警 |
| **总计** | **8-11 周** | 一个全栈开发者 |

外包价格：$8K-20K

### 月度运营成本

| 项目 | 费用 | 说明 |
|------|------|------|
| Polygon.io Options 数据 | $199-799/月 | 核心开支，取决于延迟要求 |
| 服务器（API + WebSocket + Worker） | $50-150/月 | Railway / Render / EC2 |
| PostgreSQL 托管 | $15-50/月 | Supabase / RDS / Neon |
| Redis | $0-30/月 | Upstash 免费层可能够用 |
| Cloudflare | $0-20/月 | CDN + DDoS 防护 |
| 前端托管 | $0-20/月 | Vercel / CF Pages |
| 域名 | ~$1/月 | |
| **月度总计** | **$300-1,100/月** | |

数据源占总成本的 60-70%。

### 回本模型

| 付费用户数 | 月收入（$30/人） | 月收入（$50/人） | 状态 |
|-----------|-----------------|-----------------|------|
| 10 | $300 | $500 | 刚覆盖成本 |
| 20 | $600 | $1,000 | 盈亏平衡 |
| 50 | $1,500 | $2,500 | 盈利 |
| 100 | $3,000 | $5,000 | 健康盈利 |

盈亏平衡点：约 15-20 个付费用户。

---

## 开发里程碑

### M1: 基础设施（第 1-2 周）

- [ ] 项目脚手架（React + Vite + Tailwind + Node.js）
- [ ] PostgreSQL schema 建表
- [ ] Discord OAuth 认证流程
- [ ] Polygon.io API 接入 + 期权链拉取验证
- [ ] 基础 CI/CD 部署流程

### M2: GEX 计算引擎（第 3-4 周）

- [ ] GEX 计算逻辑实现（Call Wall / Put Wall / Gamma Flip / Total GEX）
- [ ] 快照存储 + 定时刷新任务
- [ ] REST API：/api/gex/latest、/api/gex/intraday-history
- [ ] WebSocket 服务 + 实时广播

### M3: 前端 Dashboard（第 5-7 周）

- [ ] 落地页设计 + 实现
- [ ] Dashboard 主页面
- [ ] GEX 结构图（D3 柱状图 + 关键位标注）
- [ ] GEX 热力图（Price × Expiry 矩阵）
- [ ] IV 面板（IV Rank + Term Structure + Skew）
- [ ] Summary Cards
- [ ] Ticker / Expiry 切换器
- [ ] WebSocket 实时更新集成

### M4: 订阅 + 上线（第 8-9 周）

- [ ] Stripe 或 Whop 订阅集成
- [ ] 付费墙 + 试用流程
- [ ] 生产环境部署
- [ ] 监控 + 告警配置
- [ ] Beta 测试 + 修复

### M5: Phase 2 功能（第 10-15 周）

- [ ] 历史回放系统
- [ ] 0DTE Tide
- [ ] 盘中告警系统（Telegram / Discord 推送）
- [ ] Strike Ladder 视图

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Polygon API 费用过高 | 运营成本失控 | 先用 $199/月基础套餐验证，按需升级 |
| 期权链数据量大 | DB 存储快速增长 | 只存关键 strike 的聚合数据，原始数据不落盘 |
| GEX 计算口径争议 | 用户质疑数据准确性 | 文档化计算方法，提供计算说明页 |
| WebSocket 并发压力 | 服务不稳定 | 限制单用户连接数，做好限速和降级 |
| Polygon API 变更 | 数据管道中断 | 监控数据质量，备选 Tradier / CBOE 数据源 |
| 用户增长慢 | 无法覆盖成本 | 先做 Telegram 推送版验证需求，再投入前端 |

---

## 成功指标

### Phase 1 上线后 30 天

- 注册用户 ≥ 50
- 日活用户 ≥ 10
- 付费转化率 ≥ 10%
- WebSocket 平均延迟 < 2 秒
- 数据刷新成功率 > 99%

### Phase 2 上线后 90 天

- 付费用户 ≥ 20（盈亏平衡）
- 告警推送准确率 > 95%
- 历史回放数据覆盖 ≥ 30 个交易日
- 用户留存率（月）≥ 60%

---

## 附录

### A. 竞品对比

| 功能 | Nightwatch (yehangshe.com) | SpotGamma | Unusual Whales | 本产品目标 |
|------|---------------------------|-----------|----------------|-----------|
| GEX 结构图 | ✅ | ✅ | ❌ | ✅ |
| GEX 热力图 | ✅ | ✅ | ❌ | ✅ |
| IV 分析 | ✅ | 部分 | ✅ | ✅ |
| 0DTE Flow | 即将上线 | ✅ | ✅ | Phase 2 |
| 历史回放 | ✅ | ❌ | ❌ | Phase 2 |
| 盘中告警 | ❌ | ✅ | ✅ | Phase 2 |
| 环境判断 | ❌ | ✅ | ❌ | Phase 3 |
| 质量追踪 | ❌ | ❌ | ❌ | Phase 3 |
| 中文界面 | ✅ | ❌ | ❌ | ✅ |
| 价格 | 免费试用 | $49/月 | $28-48/月 | $30-50/月 |

### B. 技术栈总结

```
前端: React 18 + Vite + Zustand + D3.js + Tailwind CSS
后端: Node.js + Express/Fastify
数据库: PostgreSQL + Redis
数据源: Polygon.io Options API
实时通信: 原生 WebSocket
认证: Discord OAuth
支付: Stripe / Whop
部署: Cloudflare (CDN) + Railway/Render (后端) + Vercel/CF Pages (前端)
CI/CD: GitHub Actions
```

### C. 支持标的列表（MVP）

| 类别 | 标的 |
|------|------|
| 指数 ETF | SPY, QQQ, IWM |
| 科技巨头 | AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA |
| 芯片 | AVGO, AMD |

后续可扩展至更多高流动性标的。

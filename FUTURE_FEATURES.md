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

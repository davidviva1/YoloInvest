# YoloInvest 市场简报系统

自动化市场分析和简报生成系统。

## 功能

- 📈 **股票监控**（科技巨头、芯片、数据中心、电力、稀土）
- 💰 **加密货币**（BTC、ETH）
- 🛢️ **大宗商品**（原油、黄金、铜、白银、天然气）
- 📰 **新闻抓取与 AI 分析**
- 📅 **财报日历**
- 📊 **经济数据日历**
- 📬 **自动发送到 Telegram 群**
- ✅ **GitHub Actions 基础 CI 检查**

## License

本项目采用 `MIT` License。

## 自动运行

每天西雅图时间早上 6:00 自动生成并发送简报。

当前调度方式：
- 使用 **OpenClaw cron**
- 不使用 systemd timer，避免和 OpenClaw gateway 冲突

## OpenClaw cron 部署说明

推荐的正式部署方式如下：

1. 准备环境变量文件
   - 在项目根目录创建 `market-briefing/.env.market-briefing`
   - 写入以下变量：
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_CHAT_ID`
     - `LLM_API_KEY`
     - 可选：`LLM_API_BASE`
     - 可选：`LLM_MODEL`

2. 使用统一入口脚本
   - 由 `market-briefing/run_briefing.sh` 作为唯一执行入口
   - 脚本会自动：
     - 激活 `venv`
     - 按 `requirements.txt` 安装锁定依赖
     - 加载 `.env.market-briefing`
     - 检查关键环境变量
     - 运行主流程并发送 Telegram 简报

3. 通过 OpenClaw cron 调度
   - 推荐由 OpenClaw cron 在西雅图时间每天早上 6:00 触发
   - 对应 UTC 时间通常为 `14:00`（冬令时）
   - cron 任务只需要调用：
     - `/home/ec2-user/.openclaw/workspace/market-briefing/run_briefing.sh`

4. 避免 systemd 双重调度
   - 不要再创建额外的 systemd service / timer 来跑这个项目
   - 一台机器保持一个 OpenClaw gateway 即可
   - 这样能避免 gateway 端口、状态目录和后台进程冲突

5. 建议的运维检查项
   - 确认 OpenClaw gateway 正常运行
   - 确认 `.env.market-briefing` 文件存在且未被提交到 git
   - 手动执行一次 `./run_briefing.sh` 验证
   - 检查 Telegram 是否收到简报

## Quick Start

```bash
cd ~/.openclaw/workspace/market-briefing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.market-briefing.example .env.market-briefing
# 编辑 .env.market-briefing 填入真实配置
./run_briefing.sh
```

## 手动运行

```bash
cd ~/.openclaw/workspace/market-briefing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN='...'
export TELEGRAM_CHAT_ID='...'
export LLM_API_KEY='...'
# 可选
export LLM_API_BASE='https://api.tabcode.cc/claude/kiropower'
export LLM_MODEL='claude-sonnet-4-5-20250929'
./run_briefing.sh
```

## 依赖管理

项目采用“稳定档”依赖管理方式：

- `requirements.in` 维护顶层运行依赖
- `requirements.txt` 锁定当前确认可用的完整依赖版本

推荐维护流程：

1. 新增或移除顶层依赖时，先修改 `requirements.in`
2. 运行 `./update_requirements.sh` 重新生成锁定后的 `requirements.txt`
3. 本地运行 `./run_briefing.sh` 验证
4. GitHub Actions 会按 `requirements.txt` 做基础检查

运行环境、cron、CI 都统一以 `requirements.txt` 为准。

### 升级依赖

推荐一次只升级一小部分依赖，并在每次升级后验证：

1. 修改 `requirements.in` 中的顶层依赖约束
2. 运行：

```bash
./update_requirements.sh
```

3. 重新安装并验证：

```bash
source venv/bin/activate
pip install -r requirements.txt
./run_briefing.sh
```

4. 确认 Telegram 收到简报、GitHub Actions 通过后再提交

如果升级后出现依赖冲突：
- 优先回退刚刚调整的顶层依赖版本
- 再重新生成 `requirements.txt`
- 不建议一次性大范围升级全部包

### 常用命令

```bash
make deps         # 安装锁定依赖
make update-deps  # 重新生成 requirements.txt
make run          # 运行完整简报流程
make ci-check     # 本地执行基础 CI 检查
```

## 环境变量

必需：

- `TELEGRAM_BOT_TOKEN` - Telegram Bot token
- `TELEGRAM_CHAT_ID` - Telegram 群组或会话 ID
- `LLM_API_KEY` - Claude 兼容接口 API key

可选：

- `LLM_API_BASE` - Claude 兼容接口基础地址
  - 默认：`https://api.tabcode.cc/claude/kiropower`
- `LLM_MODEL` - 分析模型名
  - 默认：`claude-sonnet-4-5-20250929`

## 项目结构

```text
market-briefing/
├── README.md             # 项目说明
├── DEPLOYMENT.md         # OpenClaw cron 部署说明
├── ReleaseNote.md        # 发布记录与变更日志
├── main.py               # 主入口，串联抓数、分析、生成
├── run_briefing.sh       # 一键运行主流程并发送结果
├── update_requirements.sh # 从 requirements.in 生成锁定依赖
├── check_requirements.py # 校验 requirements.txt 是否与 requirements.in 同步
├── Makefile              # 常用开发命令入口
├── requirements.in       # 顶层运行依赖
├── requirements.txt      # 锁定后的完整运行依赖
├── config.py             # 全局配置（环境变量、标的、路径等）
├── models.py             # 数据模型定义
├── fetchers.py           # 统一数据抓取层
├── analyzers.py          # AI 分析层（Claude 兼容接口）
├── generators.py         # 文本简报生成器
├── sender.py             # Telegram 发送器
├── options_alert.py      # V1 盘中异动预警脚本（大型科技股）
├── fetch_data.py         # 抓取市场数据的轻量包装脚本
├── fetch_news.py         # 抓取新闻的独立脚本
├── fetch_earnings.py     # 抓取财报数据的独立脚本
├── fetch_economic.py     # 抓取经济数据的独立脚本
├── analyze_news.py       # 兼容旧流程的分析包装脚本
├── analyze_market.py     # 兼容旧流程的生成包装脚本
├── generate_image.py     # 生成图片版简报
├── fonts/                # 中文字体资源
├── __pycache__/          # Python 缓存
└── venv/                 # Python 虚拟环境
```

## 当前数据口径

股票、加密货币和大宗商品目前统一使用 **纯日线口径**：

- `price` = 最近一个完整交易日的收盘价
- `previous_close` = 前一个完整交易日的收盘价
- `change_percent` = 两个完整交易日收盘价之间的涨跌幅
- `volume` = 最近一个完整交易日的总成交量
- `price_date` = 本次报告实际采用的收盘日期
- `previous_close_date` = 本次涨跌幅对比所用的上一交易日日期

生成后的报告末尾会直接写明：
- 本报告价格采用哪一天的收盘价
- 涨跌幅是相对哪一天的收盘价计算
- 成交量采用哪一天的总成交量

## AI 分析接口

当前使用 Claude 兼容接口：

- Base URL: `https://api.tabcode.cc/claude/kiropower`
- Messages URL: `https://api.tabcode.cc/claude/kiropower/v1/messages`

## 盘中异动预警 V1

新增脚本：`options_alert.py`

V1 目标：
- 只看高流动性大型科技股
- 先用现货价格/量能做代理信号
- 识别盘中异常强弱和放量
- 通过 Telegram 推送新出现或明显增强的异动

当前监控标的：
- `AAPL`
- `MSFT`
- `GOOGL`
- `AMZN`
- `META`
- `NVDA`
- `TSLA`
- `AVGO`

当前规则：
- 日涨跌幅绝对值 >= `2%`
- 相对开盘涨跌幅绝对值 >= `1%`
- 成交量 / 3个月平均成交量 >= `1.2x`

手动运行：

```bash
cd ~/.openclaw/workspace/market-briefing
source venv/bin/activate
python options_alert.py
```

说明：
- 这还不是真实期权流扫描
- V1 是为了先把盘中异动 alert 链路搭起来
- 后续可接入真正的 options flow 数据源替换信号层

## 输出文件

流程运行时会把中间结果写到 `/tmp`：

- `/tmp/market_data.json`
- `/tmp/market_news.json`
- `/tmp/earnings_calendar.json`
- `/tmp/economic_data.json`
- `/tmp/news_analysis.txt`
- `/tmp/detailed.txt`

## 备注

- `LYNAS.AX` 已从稀土 watchlist 中移除，因为 Yahoo Finance 返回不稳定
- 文本简报链路已验证可用，Telegram 发送正常
- 旧脚本仍保留为 wrapper，避免打断已有使用方式，但核心逻辑已集中到 `fetchers.py`、`analyzers.py`、`generators.py`
- 正式部署建议始终通过 OpenClaw cron + `run_briefing.sh` 完成，不要混用 systemd
- 部署细节已单独整理到 `DEPLOYMENT.md`

---

**YoloInvest** - Powered by OpenClaw & Claude AI

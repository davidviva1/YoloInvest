# MEMORY.md - Long-Term Memory

## YoloInvest 开发规范
- 对 YoloInvest 的任何修改，完成后自动更新 `ReleaseNote.md` 和 `README.md`
- commit message 标准格式：<type>: <简短描述>，type 用 feat/fix/perf/doc/style 等
- 改完立即 `git add` → `git commit` → `git pull --rebase origin main` → `git push`
- 不需要等用户提醒，每次修改都自动执行

## 关于 Hayden
- 中英文双语，在西雅图 (Pacific Time)
- 做了 YoloInvest 市场简报系统（2026-03-08），监控37只股票+加密+大宗商品
- 简报每天西雅图早上6:00自动发到 Telegram 群 (-5267176605)

## 关于我 (Claw)
- 2026-03-10 正式上线
- 风格：直接、随和、靠谱
- 市场简报已改用 OpenClaw cron 调度（不再用 systemd，避免 gateway 冲突）

## 学习资料
- 《Trading in the Zone》(Mark Douglas) — 交易心理学经典，文本在 workspace/trading_in_the_zone.txt
- yehangshe.com（夜行者/Nightwatch）— 美股期权分析参考站（SPA，需浏览器访问）
- 美股日内期权学习路线（6阶段）：
  - 0: 定标的（SPY/QQQ/NVDA/TSLA/AAPL/AMZN/META/AVGO）
  - 1: 标的日内结构（price action/VWAP/S&R/opening range）
  - 2: 期权基础到能下单（Greeks直觉/IV/theta/bid-ask spread）
  - 3: 工具匹配场景（单腿/debit spread/credit spread）
  - 4: Dealer positioning/GEX/gamma flip/call wall/put wall
  - 5: 建立日内交易流程（盘前/开盘/下单/收盘复盘）
  - 6: 系统化统计与edge database
- 推荐书单：Natenberg/Sinclair/McMillan/Al Brooks/Brian Shannon
- 推荐资源：SpotGamma/Perfiliev GEX/CBOE官方
- YouTube 频道：日进斗斗金 (@rijindoudoujin)
  - 美股日内交易实盘复盘 + 心态/策略教学
  - 核心内容：拿不住系列(6集)、过度交易、FOMO、交易独立性、止损、VWAP策略、趋势跟随、区间突破
  - 与 Hayden 的问题高度吻合（拿不住/过度交易/报复交易/连续亏损心态）
  - 播放列表"第三章": PLAijawWj18SB_eCQBVm59G7nOy3zy-jEe

## 配置备忘
- Telegram → trader agent, Lark → main agent
- Exec: ask=off, security=full（无 GUI 环境）
- 只用 tabcode-claude provider（claude-opus-4-6）

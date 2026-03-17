# Changelog

## 2026-03-17

### Bug Fixes
- **简报日期修复**: `app.py` 缺少 `if __name__ == "__main__"` 入口，导致 cron 触发时数据未重新拉取，简报一直使用旧缓存文件（标题和计算说明日期不更新）
- **标题日期**: 使用 `datetime.now()` 显示发送当天日期
- **计算说明日期**: 从 market data 的 `price_date` / `previous_close_date` 动态获取，确保反映实际交易日

### New Features
- 新增个股杠杆 ETF 监控: NVDL/NVDD/NVDU/TSLL/TSLS/TSLR/METD/FBL/AMZU/AMZD
- 新增 AVGX (AVGO 2x bull) 到 alert 标的
- Options alert: 降低触发阈值，新增 ETF/指数 ticker，修复 volume ratio 计算

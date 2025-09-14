# 成交量突破监控策略

## 概述

这是一个简单的动量币监控策略，专门监控15分钟K线的成交量突破。当某个币种的15分钟成交量突然达到过去7天平均15分钟成交量的10倍时，系统会自动发送买入提醒。

## 功能特点

- ✅ **实时监控**: 支持连续监控模式，自动扫描所有币种
- ✅ **智能提醒**: 通过钉钉机器人发送买入信号通知
- ✅ **防重复提醒**: 避免同一币种在短时间内重复提醒
- ✅ **灵活配置**: 支持自定义成交量倍数阈值和历史数据回看天数
- ✅ **多种运行模式**: 单次扫描、连续监控、单币种检测
- ✅ **详细日志**: 完整的运行日志记录

## 文件结构

```
crypto/monitor/
├── volume_breakout_strategy.py    # 核心策略实现
├── run_volume_monitor.py          # 运行脚本
├── test_volume_monitor.py         # 测试脚本
└── README.md                      # 使用说明
```

## 安装依赖

确保已安装必要的Python包：

```bash
pip install pandas numpy requests
```

## 使用方法

### 1. 单次扫描模式

快速扫描所有币种，检测当前是否有成交量突破：

```bash
cd crypto/monitor
python run_volume_monitor.py --mode scan
```

### 2. 连续监控模式

持续监控，每15分钟扫描一次：

```bash
python run_volume_monitor.py --mode monitor --interval 15
```

### 3. 单币种检测模式

检测特定币种的成交量突破情况：

```bash
python run_volume_monitor.py --mode single --coin BTCUSDT
```

### 4. 自定义参数

```bash
# 自定义成交量倍数阈值为8倍，回看天数为5天
python run_volume_monitor.py --mode scan --volume-multiplier 8.0 --lookback-days 5

# 自定义数据目录
python run_volume_monitor.py --mode scan --data-dir /path/to/your/data
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `--mode` | scan | 运行模式：scan(单次扫描)、monitor(连续监控)、single(单币种检测) |
| `--data-dir` | crypto/data/spot_min_binance | 15分钟K线数据文件目录 |
| `--volume-multiplier` | 10.0 | 成交量突破倍数阈值 |
| `--lookback-days` | 7 | 历史数据回看天数 |
| `--interval` | 15 | 连续监控模式下的扫描间隔(分钟) |
| `--coin` | - | 单币种检测模式下的币种符号 |

## 测试

运行测试脚本验证功能：

```bash
python test_volume_monitor.py
```

测试将验证：
- 数据加载功能
- 成交量基准计算
- 突破检测逻辑
- 多币种扫描
- 提醒功能

## 策略逻辑

### 1. 数据获取

- 读取 `crypto/data/spot_min_binance/` 目录下的15分钟K线数据
- 支持多个币种的并行处理

### 2. 成交量基准计算

- 计算过去N天（默认7天）的15分钟成交量平均值
- 过去7天 = 7 × 24 × 4 = 672个15分钟周期

### 3. 突破检测

- 当前15分钟成交量 ÷ 历史平均成交量 ≥ 设定倍数（默认10倍）
- 触发买入信号

### 4. 提醒发送

- 通过钉钉机器人发送格式化的提醒消息
- 包含币种、价格、成交量倍数、时间等信息
- 同一币种每天最多提醒一次

## 日志文件

运行日志保存在 `crypto/data/log/` 目录下：

```
crypto/data/log/volume_monitor_20250115_143022.log
```

日志包含：
- 运行参数记录
- 数据加载状态
- 突破检测结果
- 提醒发送记录
- 错误信息

## 配置钉钉机器人

在 `crypto/utils/chat_robot.py` 中配置钉钉机器人的 access_token：

```python
access_token = 'your_dingtalk_robot_token'
```

## 注意事项

1. **数据质量**: 确保数据文件完整且格式正确
2. **网络连接**: 发送钉钉通知需要网络连接
3. **资源使用**: 连续监控模式会持续运行，注意系统资源
4. **参数调优**: 根据市场情况调整成交量倍数阈值
5. **风险控制**: 这只是信号提醒，实际交易需要人工确认

## 监控输出示例

```
============================================================
      成交量突破监控策略
============================================================
运行模式: scan
数据目录: crypto/data/spot_min_binance
成交量倍数阈值: 10.0
回看天数: 7
============================================================

🚀 [成交量突破提醒] SOLUSDT
💰 当前价格: 245.67
📈 成交量倍数: 12.3倍
⏰ 时间: 2025-01-15 14:30:00
💡 建议: 考虑买入
```

## 高级用法

### 定时运行

可以结合cron定时任务实现定期扫描：

```bash
# 每15分钟执行一次扫描
*/15 * * * * cd /path/to/crypto && python monitor/run_volume_monitor.py --mode scan
```

### 自定义通知

修改 `volume_breakout_strategy.py` 中的 `send_alert` 方法，支持更多通知渠道（微信、邮件等）。

### 集成到现有策略

将 `VolumeBreakoutMonitor` 类集成到现有的交易策略中，作为买入信号的一个指标。

## 故障排除

**问题**: 提示"数据目录不存在"
**解决**: 确认 `crypto/data/spot_min_binance` 目录存在且包含CSV文件

**问题**: 提示"未找到数据文件"  
**解决**: 检查数据文件命名格式是否为 `{COIN}_15m_*.csv`

**问题**: 钉钉通知发送失败
**解决**: 检查网络连接和钉钉机器人token配置

**问题**: 程序运行缓慢
**解决**: 检查数据文件大小，考虑清理过期数据 
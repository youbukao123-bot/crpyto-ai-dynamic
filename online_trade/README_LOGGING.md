# 📝 在线交易系统日志功能

## 🎯 功能概述

在线交易系统集成了完整的日志记录功能，支持操作日志和系统日志的分天存储，帮助用户追踪所有交易操作和系统运行状态。

## 📂 日志目录结构

```
online_trade/
├── ope_log/              # 操作日志目录
│   └── operation_YYYYMMDD.log
├── log/                  # 系统日志目录
│   └── system_YYYYMMDD.log
├── dat_log/              # 数据拉取日志目录
│   ├── log/
│   │   └── system_YYYYMMDD.log
│   └── ope_log/
│       └── operation_YYYYMMDD.log
└── log_manager.py        # 日志管理模块
```

## 📋 日志类型

### 1. 操作日志 (ope_log/)

记录所有仓位变动和交易操作：

#### 支持的操作类型
- **开仓** - 新建仓位
- **平仓** - 关闭仓位  
- **挂单** - 限价单下单
- **订单成交** - 挂单执行成功
- **撤单** - 取消挂单
- **风控操作** - 止损/止盈触发
- **余额变动** - 资金变化记录

#### 日志格式示例
```
2025-09-15 13:13:49 [INFO] 操作类型: 开仓 | 交易对: ETHUSDT | entry_price: 3500.0 | quantity: 0.1 | cost: 350.0 | strategy: 测试策略 | reason: 测试开仓日志 | trading_mode: 模拟
```

### 2. 系统日志 (log/)

记录交易系统运行日志：

### 3. 数据拉取日志 (dat_log/)

专门记录数据拉取器的运行日志：

#### 支持的日志级别
- **DEBUG** - 调试信息
- **INFO** - 一般信息
- **WARNING** - 警告信息  
- **ERROR** - 错误信息
- **CRITICAL** - 严重错误

#### 日志格式示例
```
2025-09-15 13:13:49 [INFO] [trading_system] [EnhancedTrader] EnhancedTrader 系统启动
2025-09-15 13:13:49 [ERROR] [trading_system] [TestAPI] API调用失败: place_order - 余额不足
```

## 🔧 核心功能

### 1. 日志管理器 (`LogManager`)

主要功能：
- ✅ 自动按日期分文件存储
- ✅ 支持操作日志和系统日志分离
- ✅ 可配置控制台输出
- ✅ 支持北京时区时间戳
- ✅ 提供便捷的记录方法

### 2. 操作日志记录

专门记录交易相关操作：

```python
# 开仓日志
logger.log_position_open(
    symbol="BTCUSDT",
    entry_price=65000.0,
    quantity=0.001,
    cost=65.0,
    strategy="volume_breakout",
    reason="成交量突破信号",
    is_simulation=True
)

# 平仓日志
logger.log_position_close(
    symbol="BTCUSDT", 
    exit_price=66000.0,
    quantity=0.001,
    revenue=66.0,
    pnl=1.0,
    pnl_pct=1.54,
    reason="止盈",
    is_simulation=True
)

# 挂单日志
logger.log_order_placed(
    symbol="ETHUSDT",
    order_type="限价单",
    side="BUY", 
    price=3500.0,
    quantity=0.1,
    order_id="ORDER_001",
    is_simulation=True
)
```

### 3. 系统日志记录

记录系统运行状态：

```python
# 基本日志
logger.info("系统启动成功", "TradingEngine")
logger.warning("网络连接不稳定", "DataFetcher") 
logger.error("API调用失败", "BinanceAPI")

# 专用日志
logger.log_system_start("TradingSystem", {"version": "1.0"})
logger.log_api_call("BinanceAPI", "get_balance", success=True)
logger.log_data_fetch("DataFetcher", "BTCUSDT", "15m", 100, success=True)
logger.log_signal_detected("Strategy", "ETHUSDT", "突破信号", 0.85)
```

## 🚀 使用方法

### 1. 基本使用

```python
from online_trade.log_manager import get_log_manager, init_log_manager

# 初始化日志管理器
logger = init_log_manager(base_dir=".", enable_console=True)

# 记录操作日志
logger.log_position_open(
    symbol="BTCUSDT",
    entry_price=65000.0,
    quantity=0.001,
    cost=65.0,
    strategy="test",
    is_simulation=True
)

# 记录系统日志
logger.info("这是一条信息日志", "MyComponent")
logger.error("这是一条错误日志", "MyComponent")
```

### 2. 在交易器中的集成

交易器自动记录所有操作：

```python
# 增强交易器已集成日志功能
trader = EnhancedTrader(config_override=config, dingtalk_webhook=webhook)

# 以下操作会自动记录日志：
trader.open_position("BTCUSDT", 0.8)        # 自动记录开仓日志
trader.close_position("BTCUSDT", "止盈")     # 自动记录平仓日志
trader.place_golden_ratio_order(...)        # 自动记录挂单日志
```

### 3. 便捷函数

```python
from online_trade.log_manager import log_operation, log_info, log_warning, log_error

# 直接使用便捷函数
log_operation("测试操作", "BTCUSDT", {"price": 65000})
log_info("系统运行正常") 
log_warning("内存使用率较高")
log_error("数据库连接失败")
```

## 📊 日志查看

### 1. 实时查看
```bash
# 查看操作日志
tail -f online_trade/ope_log/operation_$(date +%Y%m%d).log

# 查看系统日志  
tail -f online_trade/log/system_$(date +%Y%m%d).log
```

### 2. 历史查看
```bash
# 查看特定日期的操作日志
cat online_trade/ope_log/operation_20250915.log

# 搜索特定交易对的操作
grep "BTCUSDT" online_trade/ope_log/operation_*.log

# 搜索错误日志
grep "ERROR" online_trade/log/system_*.log
```

### 3. 程序化查看
```python
# 获取日志统计信息
logger = get_log_manager()
stats = logger.get_log_stats()

print(f"操作日志文件: {stats['operation_files']}")
print(f"系统日志文件: {stats['system_files']}")
```

## 🔧 配置选项

### 1. 日志管理器配置

```python
logger = LogManager(
    base_dir="./logs",        # 日志基础目录
    enable_console=True       # 是否启用控制台输出
)
```

### 2. 日志级别控制

系统日志支持不同级别：
- 生产环境建议使用 `INFO` 级别
- 开发环境可使用 `DEBUG` 级别
- 操作日志始终记录所有操作

### 3. 日志清理

```python
# 清理30天前的旧日志
logger.cleanup_old_logs(days_to_keep=30)
```

## 🎯 最佳实践

### 1. 操作日志
- ✅ 记录所有仓位变动
- ✅ 明确标识模拟/真实交易
- ✅ 包含详细的操作参数
- ✅ 记录操作原因和策略

### 2. 系统日志
- ✅ 记录关键系统事件
- ✅ 记录API调用结果
- ✅ 记录异常和错误
- ✅ 使用合适的日志级别

### 3. 性能考虑
- ✅ 日志写入是异步的，不影响交易性能
- ✅ 自动按日期分文件，避免单文件过大
- ✅ 支持日志清理，控制磁盘空间

## 🛠️ 故障排除

### 1. 日志文件未生成
检查目录权限和磁盘空间：
```bash
ls -la online_trade/ope_log/
ls -la online_trade/log/
df -h
```

### 2. 日志内容缺失
检查日志级别设置和组件初始化：
```python
# 确保正确初始化
logger = init_log_manager(enable_console=True)
logger.info("测试日志", "TestComponent")
```

### 3. 日志文件过大
定期清理旧日志：
```python
# 清理超过30天的日志
logger.cleanup_old_logs(30)
```

## 📈 监控建议

### 1. 日常监控
- 定期检查日志文件大小
- 监控错误日志频率
- 关注异常操作记录

### 2. 自动化监控
```bash
# 创建日志监控脚本
#!/bin/bash
# 检查今日错误日志
grep "ERROR" online_trade/log/system_$(date +%Y%m%d).log | wc -l

# 检查今日交易操作数量
grep "开仓\|平仓" online_trade/ope_log/operation_$(date +%Y%m%d).log | wc -l
```

## 🔐 安全注意事项

1. **不记录敏感信息** - API密钥等敏感信息不会写入日志
2. **文件权限控制** - 设置适当的日志文件访问权限
3. **定期备份** - 重要的交易日志应定期备份
4. **审计追踪** - 操作日志可用于交易审计和分析

---

## 🎉 总结

在线交易系统的日志功能提供了：

✅ **完整的操作追踪** - 记录所有仓位变动和交易操作  
✅ **详细的系统监控** - 记录系统运行状态和异常  
✅ **分天自动存储** - 按日期自动分文件，便于管理  
✅ **模拟真实区分** - 清楚标识模拟交易和真实交易  
✅ **易于查看分析** - 结构化格式，支持程序化分析  
✅ **高性能设计** - 异步写入，不影响交易性能  

📂 **日志目录说明**:
   - **操作日志**: `online_trade/ope_log/` - 记录交易操作
   - **系统日志**: `online_trade/log/` - 记录交易系统运行状态  
   - **数据拉取日志**: `online_trade/dat_log/` - 记录数据拉取器运行状态

通过完善的日志系统，用户可以全面掌控交易系统的运行状态，及时发现问题，优化交易策略。

# 统一配置管理指南

## 📋 概述

所有系统参数现在都统一管理在 `config.json` 文件中，方便您一站式修改所有设置。

## 🔧 配置文件结构

### API配置 (`api`)
```json
{
  "api": {
    "api_key": "您的API密钥",
    "api_secret": "您的API密钥Secret",
    "base_url": "https://api.binance.com",
    "proxy_host": null,
    "proxy_port": 0,
    "timeout": 5,
    "try_counts": 5
  }
}
```

**主要参数说明：**
- `api_key`: Binance API密钥
- `api_secret`: Binance API密钥Secret
- `base_url`: API基础URL
- `proxy_host/proxy_port`: 代理设置（可选）
- `timeout`: 请求超时时间（秒）

### 交易配置 (`trading`)
```json
{
  "trading": {
    "initial_capital": 1000,
    "max_position_pct": 0.15,
    "max_total_exposure": 0.80,
    "stop_loss_pct": -0.08,
    "take_profit_pct": 0.15,
    "max_profit_pct": 0.80,
    "trailing_stop_activation": 0.20,
    "trailing_stop_ratio": 0.15,
    "min_investment_amount": 10.0,
    "buy_strategy": "golden_ratio",
    "golden_ratio": 0.618,
    "use_limit_order": true,
    "slippage_limit": 0.001
  }
}
```

**主要参数说明：**
- `initial_capital`: 初始资金（USDT）
- `max_position_pct`: 单个币种最大仓位比例（15% = 0.15）
- `max_total_exposure`: 最大总仓位比例（80% = 0.80）
- `stop_loss_pct`: 止损比例（-8% = -0.08）
- `take_profit_pct`: 止盈比例（15% = 0.15）
- `max_profit_pct`: 最大止盈比例（80% = 0.80）
- `buy_strategy`: 买入策略（"close" 或 "golden_ratio"）
- `use_limit_order`: 是否使用限价单（推荐true）
- `slippage_limit`: 滑点限制（0.1% = 0.001）

### 策略配置 (`strategy`)
```json
{
  "strategy": {
    "volume_multiplier": 5.0,
    "timeframe": "4h",
    "price_change_max": 0.20,
    "consolidation_min_days": 3,
    "consolidation_volatility_threshold": 0.05,
    "signal_strength_base": 5.0,
    "signal_strength_max_multiplier": 2.0
  }
}
```

**主要参数说明：**
- `volume_multiplier`: 成交量突破倍数（5倍）
- `timeframe`: 交易时间框架（"15m", "30m", "1h", "2h", "4h"）
- `price_change_max`: 最大涨幅限制（20% = 0.20）
- `consolidation_min_days`: 盘整最小天数

### 系统配置 (`system`)
```json
{
  "system": {
    "data_dir": "../online_data/spot_klines",
    "market_file": "../online_data/exchange_binance_market.txt",
    "interval": "15m",
    "trade_cycle_hours": 4,
    "risk_check_interval_minutes": 30,
    "data_fetch_interval_hours": 1,
    "log_level": "INFO",
    "enable_detailed_logging": true
  }
}
```

**主要参数说明：**
- `trade_cycle_hours`: 交易周期（小时）
- `risk_check_interval_minutes`: 风险检查频率（分钟）
- `data_fetch_interval_hours`: 数据拉取频率（小时）

### 时间退出配置 (`time_exit`)
```json
{
  "time_exit": {
    "enable_time_exit": true,
    "quick_profit_hours": 72,
    "quick_profit_threshold": 0.10,
    "profit_taking_hours": 168,
    "profit_taking_threshold": 0.03,
    "stop_loss_hours": 240,
    "stop_loss_threshold": -0.03,
    "forced_close_hours": 336
  }
}
```

**主要参数说明：**
- `enable_time_exit`: 是否启用时间退出
- `quick_profit_hours`: 快速止盈时间（72小时=3天）
- `quick_profit_threshold`: 快速止盈阈值（10%）
- `forced_close_hours`: 强制平仓时间（336小时=14天）

## 🛠️ 使用方法

### 1. 直接修改配置文件
```bash
# 编辑配置文件
nano online_data/config/config.json
```

### 2. 使用配置加载器（编程方式）
```python
from online_trade.config_loader import get_config

# 获取配置
config = get_config()

# 读取配置
print(f"初始资金: ${config.initial_capital:,}")
print(f"止损比例: {config.stop_loss_pct:.1%}")

# 修改配置
config.set('trading', 'initial_capital', 2000)
config.set('trading', 'stop_loss_pct', -0.05)

# 保存配置
config.save_config()
```

### 3. 运行时配置覆盖
```python
# 临时覆盖配置（不保存到文件）
config_override = {
    'trading': {
        'initial_capital': 5000,
        'stop_loss_pct': -0.05
    },
    'strategy': {
        'volume_multiplier': 8.0
    }
}

# 使用覆盖配置启动系统
trader = EnhancedTrader(config_override=config_override)
engine = OnlineStrategyEngine(config_override=config_override)
```

## 📊 常用配置场景

### 场景1：保守交易
```json
{
  "trading": {
    "initial_capital": 1000,
    "max_position_pct": 0.10,
    "max_total_exposure": 0.60,
    "stop_loss_pct": -0.05,
    "take_profit_pct": 0.10
  },
  "strategy": {
    "volume_multiplier": 8.0,
    "timeframe": "2h"
  }
}
```

### 场景2：激进交易
```json
{
  "trading": {
    "initial_capital": 5000,
    "max_position_pct": 0.20,
    "max_total_exposure": 1.0,
    "stop_loss_pct": -0.10,
    "take_profit_pct": 0.25
  },
  "strategy": {
    "volume_multiplier": 3.0,
    "timeframe": "1h"
  }
}
```

### 场景3：测试模式
```json
{
  "trading": {
    "initial_capital": 100,
    "max_position_pct": 0.05,
    "max_total_exposure": 0.20,
    "stop_loss_pct": -0.03,
    "take_profit_pct": 0.05
  }
}
```

## ⚠️ 重要提示

1. **修改前备份**：修改配置前请备份原文件
2. **JSON格式**：确保JSON格式正确，否则系统无法启动
3. **数值范围**：
   - 百分比用小数表示（10% = 0.10）
   - 负数表示损失（-8% = -0.08）
   - 仓位比例不超过1.0（100%）
4. **重启生效**：修改配置后需要重启系统才能生效
5. **测试验证**：建议先用小资金测试新配置

## 🔧 配置验证

运行配置测试脚本验证设置：
```bash
cd online_trade
python3 test_config_system.py
```

## 📞 技术支持

如果您在配置过程中遇到问题，请检查：
1. JSON格式是否正确
2. 数值范围是否合理
3. 文件权限是否正确
4. 系统日志中的错误信息

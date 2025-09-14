# Ubuntu 22.04 部署指南

## 🚀 快速部署

### 1. 自动部署（推荐）

```bash
# 进入在线交易目录
cd online_trade

# 运行自动部署脚本
chmod +x deploy_ubuntu.sh
./deploy_ubuntu.sh
```

### 2. 手动部署

如果你偏好手动安装，请按以下步骤：

#### 步骤1: 更新系统
```bash
sudo apt update && sudo apt upgrade -y
```

#### 步骤2: 安装Python和依赖
```bash
# 安装 Python 3 和相关工具
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential

# 检查版本
python3 --version  # 应该是 3.10+
pip3 --version
```

#### 步骤3: 创建虚拟环境
```bash
# 在 online_trade 目录下创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

#### 步骤4: 安装Python依赖
```bash
# 安装最小依赖（推荐）
pip install -r requirements-minimal.txt

# 或安装完整依赖
pip install -r requirements.txt
```

## 📦 依赖说明

### 核心依赖 (requirements-minimal.txt)
- `pandas>=1.5.0` - 数据处理和分析
- `numpy>=1.24.0` - 数值计算
- `requests>=2.28.0` - HTTP请求
- `pytz>=2022.7` - 时区处理
- `schedule>=1.2.0` - 任务调度
- `python-binance>=1.0.17` - 币安API（可选）

### 扩展依赖 (requirements.txt)
包含核心依赖以及：
- 可视化工具
- 异步支持
- 日志增强
- 配置验证
- 性能监控

## ⚙️ 配置设置

### 1. 创建配置文件
```bash
# 创建配置目录
mkdir -p ../online_data/config

# 创建配置文件
cat > ../online_data/config/config.json << 'EOF'
{
  "api": {
    "api_key": "your_binance_api_key",
    "api_secret": "your_binance_api_secret",
    "base_url": "https://api.binance.com",
    "timeout": 5
  },
  "trading": {
    "enable_real_trading": false,
    "initial_capital": 1000,
    "max_position_pct": 0.15,
    "max_total_exposure": 0.9,
    "stop_loss_pct": -0.08,
    "take_profit_pct": 0.15
  },
  "strategy": {
    "volume_multiplier": 8.0,
    "timeframe": "2h"
  },
  "system": {
    "data_dir": "../online_data/spot_klines",
    "interval": "15m",
    "trade_cycle_hours": 4
  }
}
EOF
```

### 2. 创建数据目录
```bash
mkdir -p ../online_data/spot_klines
mkdir -p ../online_data/log
```

### 3. 币种列表（可选）
```bash
# 如果需要自定义币种列表
echo "BTCUSDT
ETHUSDT
BNBUSDT
ADAUSDT
SOLUSDT" > ../online_data/exchange_binance_market.txt
```

## 🎮 测试系统

### 1. 运行自动测试
```bash
# 使用自动生成的测试脚本
./test_system.sh
```

### 2. 手动测试
```bash
# 激活虚拟环境
source venv/bin/activate

# 测试依赖导入
python3 -c "import pandas, numpy, requests, pytz, schedule; print('✅ 所有依赖正常')"

# 测试配置加载
python3 -c "from online_trade.config_loader import get_config; config = get_config(); print('✅ 配置加载正常')"

# 测试模拟交易
python3 test_simulation_mode.py
```

## 🚀 启动系统

### 方法1: 使用启动脚本
```bash
# 模拟交易模式（默认，安全）
./start_trading.sh

# 真实交易模式（谨慎使用）
./start_trading.sh --enable-real-trading

# 自定义参数
./start_trading.sh --capital 5000 --disable-dingtalk
```

### 方法2: 直接启动
```bash
# 激活虚拟环境
source venv/bin/activate

# 启动系统
python3 start_online_trading.py --help  # 查看所有参数
python3 start_online_trading.py         # 默认模拟模式
```

## 🛑 停止系统

```bash
# 使用停止脚本
./stop_trading.sh

# 或手动停止
pkill -f "start_online_trading.py"
```

## 🔧 系统服务化（可选）

### 创建systemd服务
```bash
# 创建服务文件
sudo tee /etc/systemd/system/crypto-trading.service > /dev/null << EOF
[Unit]
Description=Crypto Trading System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/start_trading.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable crypto-trading.service
sudo systemctl start crypto-trading.service

# 查看状态
sudo systemctl status crypto-trading.service
```

## 📊 监控和日志

### 查看实时日志
```bash
# 系统日志
journalctl -u crypto-trading.service -f

# 应用日志
tail -f ../online_data/log/*.log
```

### 系统监控
```bash
# 查看进程
ps aux | grep python3

# 查看资源使用
htop

# 查看网络连接
netstat -tulpn | grep python3
```

## 🚨 故障排除

### 常见问题

1. **导入错误**
   ```bash
   # 重新安装依赖
   pip install -r requirements-minimal.txt --force-reinstall
   ```

2. **权限问题**
   ```bash
   # 修复权限
   chmod +x *.sh
   chmod 644 *.py
   ```

3. **配置文件错误**
   ```bash
   # 验证JSON格式
   python3 -m json.tool ../online_data/config/config.json
   ```

4. **网络问题**
   ```bash
   # 测试API连接
   curl -s https://api.binance.com/api/v3/ping
   ```

### 日志位置
- 系统日志: `/var/log/syslog`
- 服务日志: `journalctl -u crypto-trading.service`
- 应用日志: `../online_data/log/`

## 🔐 安全建议

1. **不要使用root用户运行**
2. **妥善保管API密钥**
3. **定期备份配置和日志**
4. **监控系统资源使用**
5. **定期更新依赖包**

## 📚 更多文档

- [模拟交易说明](README_SIMULATION.md)
- [钉钉通知说明](README_DINGTALK.md)
- [系统架构说明](README.md)

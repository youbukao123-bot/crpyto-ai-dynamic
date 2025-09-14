#!/bin/bash

# Ubuntu 22.04 在线交易系统部署脚本
# 使用方法: chmod +x deploy_ubuntu.sh && ./deploy_ubuntu.sh

echo "🚀 开始部署在线交易系统到 Ubuntu 22.04..."

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  建议不要使用 root 用户运行此脚本"
    read -p "确定要继续吗? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 更新系统包
echo "📦 更新系统包..."
sudo apt update
sudo apt upgrade -y

# 安装 Python 3 和 pip
echo "🐍 安装 Python 3 和相关工具..."
sudo apt install -y python3 python3-pip python3-dev

# 安装系统级依赖
echo "🔧 安装系统级依赖..."
sudo apt install -y build-essential curl wget git vim htop

# 检查 Python 版本
echo "🔍 检查 Python 版本..."
python3 --version
pip3 --version

# 跳过虚拟环境创建，直接使用系统Python
echo "⚡ 使用系统 Python 环境..."

# 升级 pip
echo "📈 升级 pip..."
pip3 install --upgrade pip

# 安装 Python 依赖
echo "📚 安装 Python 依赖包..."
if [ -f "requirements-minimal.txt" ]; then
    echo "使用最小依赖包..."
    pip3 install -r requirements-minimal.txt
elif [ -f "requirements.txt" ]; then
    echo "使用完整依赖包..."
    pip3 install -r requirements.txt
else
    echo "❌ 未找到 requirements.txt 文件"
    echo "手动安装核心依赖..."
    pip3 install pandas numpy requests pytz schedule python-binance
fi

# 检查关键包安装状态
echo "✅ 检查依赖包安装状态..."
python3 -c "
import pandas as pd
import numpy as np
import requests
import pytz
import schedule
print('✅ 所有核心依赖包安装成功')
print(f'pandas: {pd.__version__}')
print(f'numpy: {np.__version__}')
print(f'requests: {requests.__version__}')
print(f'pytz: {pytz.__version__}')
print(f'schedule: {schedule.__version__}')
"

# 创建配置文件目录（如果不存在）
echo "📂 检查配置文件..."
if [ ! -d "../online_data/config" ]; then
    mkdir -p ../online_data/config
    echo "📁 创建配置目录: ../online_data/config"
fi

if [ ! -f "../online_data/config/config.json" ]; then
    echo "⚠️  配置文件不存在，请确保创建 ../online_data/config/config.json"
    echo "参考配置模板:"
    echo '{'
    echo '  "api": {'
    echo '    "api_key": "your_binance_api_key",'
    echo '    "api_secret": "your_binance_api_secret",'
    echo '    "base_url": "https://api.binance.com",'
    echo '    "timeout": 5'
    echo '  },'
    echo '  "trading": {'
    echo '    "enable_real_trading": false,'
    echo '    "initial_capital": 1000'
    echo '  }'
    echo '}'
fi

# 检查数据目录
if [ ! -d "../online_data/spot_klines" ]; then
    mkdir -p ../online_data/spot_klines
    echo "📁 创建数据目录: ../online_data/spot_klines"
fi

# 设置权限
echo "🔐 设置文件权限..."
chmod +x *.py 2>/dev/null || true

# 创建启动脚本
echo "📝 创建启动脚本..."
cat > start_trading.sh << 'EOF'
#!/bin/bash
# 启动在线交易系统

cd "$(dirname "$0")"

# 检查配置文件
if [ ! -f "../online_data/config/config.json" ]; then
    echo "❌ 配置文件不存在: ../online_data/config/config.json"
    exit 1
fi

echo "🚀 启动在线交易系统..."
echo "默认为模拟交易模式，使用 --enable-real-trading 启用真实交易"
echo ""

# 启动系统（默认模拟模式）
python3 start_online_trading.py "$@"
EOF

chmod +x start_trading.sh

# 创建测试脚本
echo "🧪 创建测试脚本..."
cat > test_system.sh << 'EOF'
#!/bin/bash
# 测试系统各组件

cd "$(dirname "$0")"

echo "🧪 测试系统组件..."

# 测试导入
echo "1. 测试依赖包导入..."
python3 -c "
try:
    import pandas, numpy, requests, pytz, schedule
    print('✅ 所有依赖包导入成功')
except ImportError as e:
    print(f'❌ 导入失败: {e}')
    exit(1)
"

# 测试配置加载
echo "2. 测试配置加载..."
if [ -f "test_config_system.py" ]; then
    python3 test_config_system.py
else
    echo "⚠️  配置测试脚本不存在"
fi

# 测试模拟交易
echo "3. 测试模拟交易..."
if [ -f "test_simulation_mode.py" ]; then
    python3 test_simulation_mode.py
else
    echo "⚠️  模拟交易测试脚本不存在"
fi

echo "🎉 测试完成"
EOF

chmod +x test_system.sh

# 创建停止脚本
echo "🛑 创建停止脚本..."
cat > stop_trading.sh << 'EOF'
#!/bin/bash
# 停止在线交易系统

echo "🛑 停止在线交易系统..."

# 查找并停止相关进程
pkill -f "start_online_trading.py" && echo "✅ 主进程已停止" || echo "ℹ️  未找到运行中的主进程"
pkill -f "online_strategy_engine.py" && echo "✅ 策略引擎已停止" || echo "ℹ️  未找到运行中的策略引擎"
pkill -f "data_fetcher.py" && echo "✅ 数据拉取器已停止" || echo "ℹ️  未找到运行中的数据拉取器"

echo "🎉 系统停止完成"
EOF

chmod +x stop_trading.sh

echo ""
echo "🎉 Ubuntu 22.04 部署完成！"
echo ""
echo "📋 接下来的步骤:"
echo "1. 配置 API 密钥: 编辑 ../online_data/config/config.json"
echo "2. 测试系统: ./test_system.sh"
echo "3. 启动系统: ./start_trading.sh"
echo "4. 停止系统: ./stop_trading.sh"
echo ""
echo "🔧 启动选项:"
echo "  模拟模式: ./start_trading.sh"
echo "  真实交易: ./start_trading.sh --enable-real-trading"
echo "  指定资金: ./start_trading.sh --capital 5000"
echo "  禁用通知: ./start_trading.sh --disable-dingtalk"
echo ""
echo "📚 更多信息请查看 README_SIMULATION.md 和 README_DINGTALK.md"
echo ""
echo "⚠️  注意: 本部署使用系统Python环境，无虚拟环境隔离"

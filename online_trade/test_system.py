"""
在线交易系统测试脚本
用于验证各个组件的基本功能
"""

import os
import sys
import pandas as pd
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_data_fetcher():
    """测试数据拉取器"""
    print("🧪 测试数据拉取器...")
    
    try:
        from online_trade.data_fetcher import OnlineDataFetcher
        
        fetcher = OnlineDataFetcher()
        
        # 测试加载币种列表
        symbols = fetcher.load_symbol_list()
        print(f"✅ 币种列表加载成功，共 {len(symbols)} 个币种")
        
        if symbols:
            # 测试单个币种数据拉取
            test_symbol = symbols[0]
            print(f"🔍 测试拉取 {test_symbol} 数据...")
            
            success = fetcher.update_symbol_data(test_symbol)
            if success:
                print(f"✅ {test_symbol} 数据拉取成功")
            else:
                print(f"❌ {test_symbol} 数据拉取失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据拉取器测试失败: {str(e)}")
        return False

def test_trader():
    """测试交易器"""
    print("🧪 测试交易器...")
    
    try:
        from online_trade.enhanced_trader import EnhancedTrader
        
        # 创建交易器实例（测试模式，小额资金）
        trader = EnhancedTrader(initial_capital=100)
        
        # 测试获取账户余额
        balances = trader.get_account_balance()
        print(f"✅ 账户余额获取成功: {len(balances)} 个币种")
        
        # 测试获取USDT余额
        usdt_balance = trader.get_usdt_balance()
        print(f"✅ USDT余额: ${usdt_balance:.2f}")
        
        # 测试获取价格
        test_symbol = "BTCUSDT"
        price = trader.get_symbol_price(test_symbol)
        if price > 0:
            print(f"✅ {test_symbol} 价格获取成功: ${price:.2f}")
        else:
            print(f"❌ {test_symbol} 价格获取失败")
        
        # 测试投资组合摘要
        summary = trader.get_portfolio_summary()
        print(f"✅ 投资组合摘要: {summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ 交易器测试失败: {str(e)}")
        return False

def test_strategy_engine():
    """测试策略引擎"""
    print("🧪 测试策略引擎...")
    
    try:
        from online_trade.online_strategy_engine import OnlineStrategyEngine
        
        # 创建策略引擎实例
        engine = OnlineStrategyEngine(initial_capital=100)
        
        # 测试加载币种列表
        symbols = engine.load_symbol_list()
        print(f"✅ 币种列表加载成功，共 {len(symbols)} 个币种")
        
        # 测试信号检测（仅检测，不执行交易）
        print("🔍 测试信号检测...")
        signals = engine.detect_signals()
        print(f"✅ 信号检测完成，发现 {len(signals)} 个信号")
        
        # 显示前几个信号的详情
        for i, signal in enumerate(signals[:3]):
            print(f"   信号 {i+1}: {signal['symbol']} - 强度: {signal['signal_strength']:.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 策略引擎测试失败: {str(e)}")
        return False

def test_volume_strategy():
    """测试成交量突破策略"""
    print("🧪 测试成交量突破策略...")
    
    try:
        from monitor.volume_breakout_strategy import VolumeBreakoutMonitor
        
        # 创建成交量监控器
        monitor = VolumeBreakoutMonitor(
            data_dir="../online_data/spot_klines",
            timeframe="4h",
            volume_multiplier=5.0
        )
        
        print("✅ 成交量突破监控器创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 成交量突破策略测试失败: {str(e)}")
        return False

def test_data_files():
    """测试数据文件存在性"""
    print("🧪 测试数据文件...")
    
    # 检查必要的目录和文件
    required_paths = [
        "../online_data",
        "../online_data/exchange_binance_market.txt",
        "../online_data/config",
    ]
    
    all_exist = True
    for path in required_paths:
        full_path = os.path.abspath(path)
        if os.path.exists(full_path):
            print(f"✅ {path} 存在")
        else:
            print(f"❌ {path} 不存在")
            all_exist = False
    
    # 检查数据目录
    data_dir = "../online_data/spot_klines"
    if os.path.exists(data_dir):
        files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        print(f"✅ 数据目录存在，包含 {len(files)} 个CSV文件")
    else:
        print(f"❌ 数据目录不存在: {data_dir}")
        all_exist = False
    
    return all_exist

def main():
    """主测试函数"""
    print("🌟 在线交易系统测试")
    print("=" * 60)
    
    test_results = []
    
    # 1. 测试数据文件
    print("\n1️⃣ 数据文件检查")
    print("-" * 30)
    result1 = test_data_files()
    test_results.append(("数据文件", result1))
    
    # 2. 测试成交量策略
    print("\n2️⃣ 成交量突破策略")
    print("-" * 30)
    result2 = test_volume_strategy()
    test_results.append(("成交量策略", result2))
    
    # 3. 测试数据拉取器
    print("\n3️⃣ 数据拉取器")
    print("-" * 30)
    result3 = test_data_fetcher()
    test_results.append(("数据拉取器", result3))
    
    # 4. 测试交易器
    print("\n4️⃣ 交易器")
    print("-" * 30)
    result4 = test_trader()
    test_results.append(("交易器", result4))
    
    # 5. 测试策略引擎
    print("\n5️⃣ 策略引擎")
    print("-" * 30)
    result5 = test_strategy_engine()
    test_results.append(("策略引擎", result5))
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<15} {status}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"📈 总体结果: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！系统已准备就绪。")
        print("\n💡 建议:")
        print("   1. 先运行 'python start_online_trading.py --data-only' 拉取数据")
        print("   2. 等待数据拉取完成后，运行完整系统")
        print("   3. 使用小额资金进行实际测试")
    else:
        print("⚠️  部分测试失败，请检查配置和依赖。")
    
    print("=" * 60)

if __name__ == '__main__':
    main()

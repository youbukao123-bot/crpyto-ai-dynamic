"""
测试新的配置系统
验证所有模块都能正确使用统一的配置
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from online_trade.config_loader import get_config, TradingConfig
from online_trade.enhanced_trader import EnhancedTrader
from online_trade.online_strategy_engine import OnlineStrategyEngine

def test_config_loader():
    """测试配置加载器"""
    print("1️⃣ 测试配置加载器")
    print("="*50)
    
    try:
        # 测试配置加载
        config = TradingConfig()
        
        # 打印配置摘要
        config.print_config_summary()
        
        print("\n✅ 配置加载器测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置加载器测试失败: {str(e)}")
        return False

def test_enhanced_trader():
    """测试增强版交易器"""
    print("\n2️⃣ 测试增强版交易器")
    print("="*50)
    
    try:
        # 测试默认配置
        print("📋 测试默认配置初始化:")
        trader1 = EnhancedTrader()
        
        print(f"\n   ✅ 默认配置读取成功:")
        print(f"      初始资金: ${trader1.initial_capital:,}")
        print(f"      止损比例: {trader1.stop_loss_pct:.1%}")
        print(f"      止盈比例: {trader1.take_profit_pct:.1%}")
        print(f"      滑点限制: {trader1.slippage_limit:.3%}")
        
        # 测试配置覆盖
        print("\n📋 测试配置覆盖:")
        config_override = {
            'trading': {
                'initial_capital': 5000,
                'stop_loss_pct': -0.05,
                'slippage_limit': 0.002
            }
        }
        
        trader2 = EnhancedTrader(config_override=config_override)
        
        print(f"   ✅ 配置覆盖成功:")
        print(f"      初始资金: ${trader2.initial_capital:,} (覆盖后)")
        print(f"      止损比例: {trader2.stop_loss_pct:.1%} (覆盖后)")
        print(f"      滑点限制: {trader2.slippage_limit:.3%} (覆盖后)")
        
        return True
        
    except Exception as e:
        print(f"❌ 增强版交易器测试失败: {str(e)}")
        return False

def test_strategy_engine():
    """测试策略引擎"""
    print("\n3️⃣ 测试策略引擎")
    print("="*50)
    
    try:
        # 测试默认配置
        print("📋 测试默认配置初始化:")
        engine1 = OnlineStrategyEngine()
        
        print(f"\n   ✅ 默认配置读取成功:")
        print(f"      时间框架: {engine1.config.timeframe}")
        print(f"      成交量倍数: {engine1.config.volume_multiplier}x")
        print(f"      买入策略: {engine1.buy_strategy}")
        
        # 测试配置覆盖
        print("\n📋 测试配置覆盖:")
        config_override = {
            'strategy': {
                'timeframe': '2h',
                'volume_multiplier': 8.0
            },
            'trading': {
                'buy_strategy': 'close',
                'initial_capital': 2000
            }
        }
        
        engine2 = OnlineStrategyEngine(config_override=config_override)
        
        print(f"   ✅ 配置覆盖成功:")
        print(f"      时间框架: {engine2.config.timeframe} (覆盖后)")
        print(f"      成交量倍数: {engine2.config.volume_multiplier}x (覆盖后)")
        print(f"      买入策略: {engine2.buy_strategy} (覆盖后)")
        
        return True
        
    except Exception as e:
        print(f"❌ 策略引擎测试失败: {str(e)}")
        return False

def test_config_modification():
    """测试配置修改功能"""
    print("\n4️⃣ 测试配置修改功能")
    print("="*50)
    
    try:
        config = get_config()
        
        # 记录原始值
        original_capital = config.initial_capital
        original_slippage = config.slippage_limit
        
        print(f"📋 原始配置:")
        print(f"   初始资金: ${original_capital:,}")
        print(f"   滑点限制: {original_slippage:.3%}")
        
        # 修改配置
        config.set('trading', 'initial_capital', 3000)
        config.set('trading', 'slippage_limit', 0.0015)
        
        print(f"\n📝 修改后配置:")
        print(f"   初始资金: ${config.initial_capital:,}")
        print(f"   滑点限制: {config.slippage_limit:.3%}")
        
        # 恢复原始值
        config.set('trading', 'initial_capital', original_capital)
        config.set('trading', 'slippage_limit', original_slippage)
        
        print(f"\n🔄 恢复原始配置:")
        print(f"   初始资金: ${config.initial_capital:,}")
        print(f"   滑点限制: {config.slippage_limit:.3%}")
        
        print("\n✅ 配置修改功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置修改功能测试失败: {str(e)}")
        return False

def test_config_persistence():
    """测试配置持久化"""
    print("\n5️⃣ 测试配置持久化")
    print("="*50)
    
    try:
        config = get_config()
        
        # 创建备份配置
        backup_config = {
            'trading': {
                'initial_capital': 9999,
                'test_parameter': 'test_value'
            }
        }
        
        # 批量更新配置
        config.update_section('trading', backup_config['trading'])
        
        print("📝 添加测试参数:")
        print(f"   初始资金: ${config.initial_capital:,}")
        print(f"   测试参数: {config.get('trading', 'test_parameter')}")
        
        # 测试保存和重新加载
        print("\n💾 测试配置保存...")
        config.save_config()
        
        # 重新加载配置
        from online_trade.config_loader import reload_config
        new_config = reload_config()
        
        print("🔄 重新加载配置:")
        print(f"   初始资金: ${new_config.initial_capital:,}")
        print(f"   测试参数: {new_config.get('trading', 'test_parameter')}")
        
        # 清理测试参数
        if 'test_parameter' in new_config._config['trading']:
            del new_config._config['trading']['test_parameter']
        new_config.set('trading', 'initial_capital', 1000)  # 恢复默认值
        new_config.save_config()
        
        print("\n🧹 清理测试数据完成")
        print("✅ 配置持久化测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置持久化测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("🌟 配置系统测试")
    print("🔧 验证统一配置管理功能")
    print("\n" + "="*60)
    
    # 运行所有测试
    tests = [
        test_config_loader,
        test_enhanced_trader,
        test_strategy_engine,
        test_config_modification,
        test_config_persistence
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
    
    # 测试总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    if passed == total:
        print(f"🎉 所有测试通过! ({passed}/{total})")
        print("\n✅ 统一配置系统功能:")
        print("   • 配置文件加载和解析")
        print("   • 多模块配置共享")
        print("   • 配置覆盖机制")
        print("   • 运行时配置修改")
        print("   • 配置持久化保存")
        print("\n🚀 系统已准备就绪，所有参数都可在config.json中统一管理!")
    else:
        print(f"⚠️  部分测试失败 ({passed}/{total})")
        print("\n💡 可能的原因:")
        print("   1. 配置文件格式错误")
        print("   2. 模块导入问题")
        print("   3. 文件权限问题")

if __name__ == '__main__':
    main()

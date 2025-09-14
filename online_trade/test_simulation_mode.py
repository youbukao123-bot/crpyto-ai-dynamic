"""
模拟交易模式测试脚本
测试模拟交易功能是否正常工作
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from online_trade.enhanced_trader import EnhancedTrader
from online_trade.config_loader import get_config

def test_simulation_mode():
    """测试模拟交易模式"""
    
    print("🎮 开始测试模拟交易模式...")
    print("="*60)
    
    # 钉钉通知配置
    dingtalk_webhook = "https://oapi.dingtalk.com/robot/send?access_token=562f41c37f10bc9d77fb0e3535c1cc778e7666ad9c1173fffcf9fb8a939118a7"
    
    # 模拟交易配置覆盖
    config_override = {
        'trading': {
            'enable_real_trading': False,  # 启用模拟模式
            'initial_capital': 1000,       # 模拟资金
            'max_position_pct': 0.2,      # 单仓位上限20%
            'min_investment_amount': 10    # 最小投资金额
        }
    }
    
    # 初始化交易器
    trader = EnhancedTrader(config_override=config_override, dingtalk_webhook=dingtalk_webhook)
    
    print(f"\n📊 初始状态:")
    summary = trader.get_portfolio_summary()
    print(f"   交易模式: {summary['trading_mode']}")
    print(f"   模拟余额: ${summary['usdt_balance']:.2f}")
    print(f"   持仓数量: {summary['position_count']}")
    
    # 测试1: 模拟开仓
    print(f"\n🔄 测试1: 模拟开仓...")
    test_symbol = "BTCUSDT"
    
    try:
        success = trader.open_position(
            symbol=test_symbol,
            signal_strength=7.5,
            strategy_type="test_simulation",
            use_limit_order=False  # 使用市价单进行模拟
        )
        
        if success:
            print(f"✅ {test_symbol} 模拟开仓成功")
        else:
            print(f"❌ {test_symbol} 模拟开仓失败")
            
    except Exception as e:
        print(f"❌ 模拟开仓异常: {str(e)}")
    
    # 检查开仓后状态
    print(f"\n📊 开仓后状态:")
    summary = trader.get_portfolio_summary()
    print(f"   模拟余额: ${summary['usdt_balance']:.2f}")
    print(f"   持仓价值: ${summary['position_value']:.2f}")
    print(f"   总资产: ${summary['total_value']:.2f}")
    print(f"   持仓数量: {summary['position_count']}")
    print(f"   仓位占比: {summary['exposure']:.2%}")
    
    # 测试2: 模拟平仓
    if test_symbol in trader.positions:
        print(f"\n🔄 测试2: 模拟平仓...")
        
        try:
            success = trader.close_position(
                symbol=test_symbol,
                reason="测试模拟平仓",
                use_limit_order=False  # 使用市价单进行模拟
            )
            
            if success:
                print(f"✅ {test_symbol} 模拟平仓成功")
            else:
                print(f"❌ {test_symbol} 模拟平仓失败")
                
        except Exception as e:
            print(f"❌ 模拟平仓异常: {str(e)}")
    else:
        print(f"\n⚠️ 跳过平仓测试，因为没有持仓")
    
    # 检查平仓后状态
    print(f"\n📊 平仓后状态:")
    summary = trader.get_portfolio_summary()
    print(f"   模拟余额: ${summary['usdt_balance']:.2f}")
    print(f"   持仓价值: ${summary['position_value']:.2f}")
    print(f"   总资产: ${summary['total_value']:.2f}")
    print(f"   持仓数量: {summary['position_count']}")
    
    # 测试3: 模拟挂单
    print(f"\n🔄 测试3: 模拟挂单...")
    test_symbol2 = "ETHUSDT"
    
    try:
        # 获取当前价格用于挂单测试
        current_price = trader.get_symbol_price(test_symbol2)
        if current_price > 0:
            # 设置挂单价格为当前价格的95%（低于市价）
            close_price = current_price * 0.98
            open_price = current_price * 0.95
            
            success, message = trader.place_golden_ratio_order(
                symbol=test_symbol2,
                close_price=close_price,
                open_price=open_price,
                signal_strength=6.0,
                strategy_type="test_simulation"
            )
            
            if success:
                print(f"✅ {test_symbol2} 模拟挂单成功: {message}")
            else:
                print(f"❌ {test_symbol2} 模拟挂单失败: {message}")
        else:
            print(f"❌ 无法获取 {test_symbol2} 价格")
            
    except Exception as e:
        print(f"❌ 模拟挂单异常: {str(e)}")
    
    # 检查挂单状态
    print(f"\n📊 挂单后状态:")
    summary = trader.get_portfolio_summary()
    print(f"   挂单数量: {summary['pending_count']}")
    print(f"   挂单价值: ${summary['pending_value']:.2f}")
    
    if trader.pending_orders:
        print(f"   挂单详情:")
        for symbol, order_info in trader.pending_orders.items():
            print(f"     {symbol}: ${order_info['price']:.6f} x {order_info['quantity']:.6f}")
    
    # 测试4: 取消模拟挂单
    if trader.pending_orders:
        print(f"\n🔄 测试4: 取消模拟挂单...")
        for symbol in list(trader.pending_orders.keys()):
            try:
                success, message = trader.cancel_pending_order(symbol, "测试取消")
                if success:
                    print(f"✅ {symbol} 模拟挂单取消成功: {message}")
                else:
                    print(f"❌ {symbol} 模拟挂单取消失败: {message}")
            except Exception as e:
                print(f"❌ 取消模拟挂单异常: {str(e)}")
    
    # 查看交易历史
    print(f"\n📋 交易历史记录:")
    if trader.trade_history:
        for i, trade in enumerate(trader.trade_history[-5:], 1):  # 显示最近5条
            action = trade['action']
            symbol = trade['symbol']
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            print(f"   {i}. {action} {symbol}: {quantity:.6f} @ ${price:.6f}")
    else:
        print(f"   暂无交易记录")
    
    # 最终状态
    print(f"\n📊 最终状态:")
    summary = trader.get_portfolio_summary()
    print(f"   交易模式: {summary['trading_mode']}")
    print(f"   模拟余额: ${summary['usdt_balance']:.2f}")
    print(f"   持仓数量: {summary['position_count']}")
    print(f"   挂单数量: {summary['pending_count']}")
    
    print(f"\n🎉 模拟交易模式测试完成！")
    print("="*60)
    
    return True

if __name__ == '__main__':
    test_simulation_mode()

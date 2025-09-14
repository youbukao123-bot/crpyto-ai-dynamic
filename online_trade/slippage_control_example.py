"""
滑点控制示例
展示如何使用限价单控制滑点在千分之一内
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from online_trade.enhanced_trader import EnhancedTrader

def demo_slippage_control():
    """演示滑点控制功能"""
    print("🎯 滑点控制演示")
    print("="*50)
    
    # 创建交易器
    trader = EnhancedTrader(initial_capital=100)
    
    # 测试币种
    test_symbol = "BTCUSDT"
    
    print(f"📊 测试币种: {test_symbol}")
    
    # 1. 获取当前价格和订单簿
    print("\n1️⃣ 获取市场数据")
    print("-" * 30)
    
    current_price = trader.get_symbol_price(test_symbol)
    print(f"当前价格: ${current_price:.2f}")
    
    order_book = trader.get_order_book(test_symbol)
    if order_book:
        print("订单簿深度:")
        print("  卖方 (Asks):")
        for i, (price, qty) in enumerate(order_book['asks'][:3]):
            print(f"    {i+1}. ${price:.2f} - {qty:.6f}")
        print("  买方 (Bids):")
        for i, (price, qty) in enumerate(order_book['bids'][:3]):
            print(f"    {i+1}. ${price:.2f} - {qty:.6f}")
    
    # 2. 计算不同滑点限制下的限价
    print("\n2️⃣ 滑点控制计算")
    print("-" * 30)
    
    slippage_levels = [0.0005, 0.001, 0.002, 0.005]  # 0.05%, 0.1%, 0.2%, 0.5%
    
    for slippage in slippage_levels:
        buy_limit = trader.calculate_limit_price(test_symbol, 'BUY', slippage)
        sell_limit = trader.calculate_limit_price(test_symbol, 'SELL', slippage)
        
        if buy_limit and sell_limit:
            buy_slippage = (buy_limit - current_price) / current_price
            sell_slippage = (current_price - sell_limit) / current_price
            
            print(f"滑点限制 {slippage:.3%}:")
            print(f"  买入限价: ${buy_limit:.6f} (滑点: {buy_slippage:.3%})")
            print(f"  卖出限价: ${sell_limit:.6f} (滑点: {sell_slippage:.3%})")
            print()
    
    # 3. 展示推荐设置
    print("3️⃣ 推荐滑点设置")
    print("-" * 30)
    print("💡 滑点控制建议:")
    print("   🟢 保守型: 0.05% (适合稳定币种)")
    print("   🟡 平衡型: 0.10% (推荐，适合大部分币种)")
    print("   🟠 激进型: 0.20% (适合波动较大的币种)")
    print("   🔴 高风险: 0.50% (仅在特殊情况下使用)")
    print()
    print("⚡ 系统默认使用 0.1% 滑点限制")
    
    # 4. 实际使用示例
    print("4️⃣ 实际使用示例")
    print("-" * 30)
    print("# 启动在线交易系统，滑点控制在0.1%以内")
    print("python start_online_trading.py --slippage-limit 0.001")
    print()
    print("# 更严格的滑点控制（0.05%）")
    print("python start_online_trading.py --slippage-limit 0.0005")
    print()
    print("# 宽松的滑点控制（0.2%）")
    print("python start_online_trading.py --slippage-limit 0.002")

def analyze_market_conditions():
    """分析市场条件，给出滑点建议"""
    print("\n🔍 市场条件分析")
    print("="*50)
    
    trader = EnhancedTrader(initial_capital=100)
    
    # 测试几个不同类型的币种
    test_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOGEUSDT"]
    
    print("币种分析（滑点风险评估）:")
    print(f"{'币种':<12} {'当前价格':<12} {'买卖价差':<12} {'建议滑点':<12}")
    print("-" * 55)
    
    for symbol in test_symbols:
        try:
            price = trader.get_symbol_price(symbol)
            order_book = trader.get_order_book(symbol)
            
            if price > 0 and order_book:
                best_bid = order_book['bids'][0][0] if order_book['bids'] else price
                best_ask = order_book['asks'][0][0] if order_book['asks'] else price
                spread = (best_ask - best_bid) / price
                
                # 根据价差推荐滑点设置
                if spread < 0.0005:
                    recommended_slippage = "0.05%"
                elif spread < 0.001:
                    recommended_slippage = "0.10%"
                elif spread < 0.002:
                    recommended_slippage = "0.15%"
                else:
                    recommended_slippage = "0.20%"
                
                print(f"{symbol:<12} ${price:<11.6f} {spread:<11.3%} {recommended_slippage:<12}")
            
        except Exception as e:
            print(f"{symbol:<12} 获取失败: {str(e)}")
    
    print("\n💡 动态滑点建议:")
    print("   • 主流币种(BTC/ETH): 使用较低滑点(0.05-0.1%)")
    print("   • 中等币种: 使用标准滑点(0.1-0.15%)")
    print("   • 小币种: 使用较高滑点(0.15-0.2%)")
    print("   • 根据实时价差动态调整")

def main():
    """主函数"""
    print("🌟 滑点控制系统演示")
    print("📊 控制交易滑点在千分之一内")
    print()
    
    try:
        # 演示滑点控制
        demo_slippage_control()
        
        # 分析市场条件
        analyze_market_conditions()
        
        print("\n✅ 演示完成!")
        print("\n🚀 开始使用:")
        print("   1. 根据市场条件选择合适的滑点限制")
        print("   2. 使用限价单替代市价单")
        print("   3. 监控实际滑点是否在控制范围内")
        print("   4. 根据交易结果调整滑点参数")
        
    except Exception as e:
        print(f"❌ 演示失败: {str(e)}")
        print("💡 请确保:")
        print("   1. API配置正确")
        print("   2. 网络连接正常")
        print("   3. 币安API权限足够")

if __name__ == '__main__':
    main()

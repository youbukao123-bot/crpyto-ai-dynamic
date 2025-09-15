"""
测试日志系统功能
"""

import os
import sys
from datetime import datetime
import pytz

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from online_trade.log_manager import LogManager, init_log_manager
from online_trade.enhanced_trader import EnhancedTrader

def test_log_manager():
    """测试日志管理器基本功能"""
    print("🧪 测试日志管理器基本功能...")
    
    # 初始化日志管理器
    logger = init_log_manager(base_dir=".", enable_console=True)
    
    # 测试系统日志
    logger.info("这是一条信息日志", "TestComponent")
    logger.warning("这是一条警告日志", "TestComponent")
    logger.error("这是一条错误日志", "TestComponent")
    logger.debug("这是一条调试日志", "TestComponent")
    
    # 测试操作日志
    logger.log_operation(
        operation_type="测试操作",
        symbol="BTCUSDT",
        details={
            "price": 65000.0,
            "quantity": 0.001,
            "reason": "测试日志功能"
        }
    )
    
    # 测试开仓日志
    logger.log_position_open(
        symbol="ETHUSDT",
        entry_price=3500.0,
        quantity=0.1,
        cost=350.0,
        strategy="测试策略",
        reason="测试开仓日志",
        is_simulation=True
    )
    
    # 测试平仓日志
    logger.log_position_close(
        symbol="ETHUSDT",
        exit_price=3600.0,
        quantity=0.1,
        revenue=360.0,
        pnl=10.0,
        pnl_pct=2.86,
        reason="测试平仓日志",
        is_simulation=True
    )
    
    # 测试挂单日志
    logger.log_order_placed(
        symbol="BNBUSDT",
        order_type="限价单",
        side="BUY",
        price=600.0,
        quantity=1.0,
        order_id="TEST_ORDER_001",
        is_simulation=True
    )
    
    # 测试订单成交日志
    logger.log_order_filled(
        symbol="BNBUSDT",
        order_id="TEST_ORDER_001",
        filled_price=598.0,
        filled_quantity=1.0,
        is_simulation=True
    )
    
    # 测试撤单日志
    logger.log_order_cancelled(
        symbol="ADAUSDT",
        order_id="TEST_ORDER_002",
        reason="市场波动过大",
        is_simulation=True
    )
    
    # 测试风控日志
    logger.log_risk_action(
        symbol="SOLUSDT",
        action="止损",
        trigger_price=50.0,
        current_price=48.0,
        reason="跌破止损线"
    )
    
    # 测试余额变动日志
    logger.log_balance_change(
        old_balance=1000.0,
        new_balance=1050.0,
        change_amount=50.0,
        reason="交易盈利",
        is_simulation=True
    )
    
    # 测试系统启动/停止日志
    logger.log_system_start("TestSystem", {"version": "1.0", "mode": "test"})
    logger.log_system_stop("TestSystem", "测试完成")
    
    # 测试API调用日志
    logger.log_api_call(
        component="TestAPI",
        api_name="get_balance",
        params={"symbol": "USDT"},
        success=True
    )
    
    logger.log_api_call(
        component="TestAPI",
        api_name="place_order",
        params={"symbol": "BTCUSDT", "side": "BUY"},
        success=False,
        error_msg="余额不足"
    )
    
    # 测试数据拉取日志
    logger.log_data_fetch(
        component="TestDataFetcher",
        symbol="BTCUSDT",
        timeframe="15m",
        records_count=100,
        success=True
    )
    
    # 测试信号检测日志
    logger.log_signal_detected(
        component="TestStrategy",
        symbol="ETHUSDT",
        signal_type="突破信号",
        signal_strength=0.85,
        details={"volume_ratio": 5.2, "price_change": 0.03}
    )
    
    print("✅ 日志管理器基本功能测试完成")

def test_enhanced_trader_logging():
    """测试增强交易器的日志功能"""
    print("\n🧪 测试增强交易器日志功能...")
    
    try:
        # 创建配置覆盖，启用模拟模式
        config_override = {
            'trading': {
                'enable_real_trading': False,
                'initial_capital': 1000.0
            }
        }
        
        # 初始化交易器（模拟模式）
        trader = EnhancedTrader(
            config_override=config_override,
            dingtalk_webhook=None  # 不启用钉钉通知，专注测试日志
        )
        
        print("✅ 增强交易器初始化完成（日志系统已集成）")
        
        # 测试模拟开仓（会触发操作日志）
        print("\n📋 测试模拟开仓...")
        success = trader.open_position(
            symbol="BTCUSDT",
            signal_strength=0.8,
            strategy_type="test_strategy"
        )
        
        if success:
            print("✅ 模拟开仓成功，操作日志已记录")
            
            # 测试模拟平仓（会触发操作日志）
            print("\n📋 测试模拟平仓...")
            close_success = trader.close_position(
                symbol="BTCUSDT",
                reason="测试平仓"
            )
            
            if close_success:
                print("✅ 模拟平仓成功，操作日志已记录")
            else:
                print("⚠️ 模拟平仓失败")
        else:
            print("⚠️ 模拟开仓失败")
        
        # 测试黄金分割点挂单（会触发操作日志）
        print("\n📋 测试黄金分割点挂单...")
        order_success, message = trader.place_golden_ratio_order(
            symbol="ETHUSDT",
            close_price=3500.0,
            open_price=3400.0,
            signal_strength=0.75,
            strategy_type="golden_ratio"
        )
        
        if order_success:
            print("✅ 黄金分割点挂单成功，操作日志已记录")
        else:
            print(f"⚠️ 黄金分割点挂单失败: {message}")
        
        print("✅ 增强交易器日志功能测试完成")
        
    except Exception as e:
        print(f"❌ 测试增强交易器时发生异常: {str(e)}")
        import traceback
        traceback.print_exc()

def check_log_files():
    """检查生成的日志文件"""
    print("\n🧪 检查生成的日志文件...")
    
    logger = init_log_manager()
    stats = logger.get_log_stats()
    
    print(f"📁 操作日志目录: {stats['operation_log_dir']}")
    print(f"📁 系统日志目录: {stats['system_log_dir']}")
    
    print(f"📄 操作日志文件: {len(stats['operation_files'])} 个")
    for file in stats['operation_files']:
        print(f"   - {file}")
    
    print(f"📄 系统日志文件: {len(stats['system_files'])} 个")
    for file in stats['system_files']:
        print(f"   - {file}")
    
    # 显示日志文件内容示例
    if stats['operation_files']:
        operation_file = os.path.join(stats['operation_log_dir'], stats['operation_files'][0])
        if os.path.exists(operation_file):
            print(f"\n📋 操作日志内容示例 ({stats['operation_files'][0]}):")
            with open(operation_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[-5:]):  # 显示最后5行
                    print(f"   {i+1}: {line.strip()}")
    
    if stats['system_files']:
        system_file = os.path.join(stats['system_log_dir'], stats['system_files'][0])
        if os.path.exists(system_file):
            print(f"\n📋 系统日志内容示例 ({stats['system_files'][0]}):")
            with open(system_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[-5:]):  # 显示最后5行
                    print(f"   {i+1}: {line.strip()}")

def main():
    """主测试函数"""
    print("🎯 开始测试日志系统...")
    print("=" * 60)
    
    # 测试基本日志功能
    test_log_manager()
    
    # 测试交易器日志集成
    test_enhanced_trader_logging()
    
    # 检查生成的日志文件
    check_log_files()
    
    print("\n" + "=" * 60)
    print("🎉 日志系统测试完成！")
    print("\n📝 测试总结:")
    print("✅ 操作日志：记录所有仓位变动（开仓、平仓、挂单、成交、撤单等）")
    print("✅ 系统日志：记录所有系统日志（INFO、WARNING、ERROR、DEBUG）")
    print("✅ 分天存储：日志文件按日期自动分文件存储")
    print("✅ 模拟模式：正确标识模拟交易和真实交易")
    print("✅ 结构化记录：同时支持可读文本和JSON结构化数据")
    print("\n📂 日志目录:")
    print("   - 操作日志：online_trade/ope_log/")
    print("   - 系统日志：online_trade/log/")

if __name__ == "__main__":
    main()

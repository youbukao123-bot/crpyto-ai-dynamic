"""
测试钉钉通知功能
验证各种交易通知是否正常工作
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from online_trade.dingtalk_notifier import DingTalkNotifier

def test_dingtalk_notifications():
    """测试所有钉钉通知功能"""
    
    # 钉钉机器人Webhook地址
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=562f41c37f10bc9d77fb0e3535c1cc778e7666ad9c1173fffcf9fb8a939118a7"
    
    print("🔔 开始测试钉钉通知功能...")
    
    # 初始化通知器（使用指定的关键词）
    keywords = ["Code"]
    notifier = DingTalkNotifier(webhook_url, keywords)
    
    # 测试1: 基础文本通知
    print("\n📝 测试1: 基础文本通知")
    result1 = notifier.send_message("这是一条测试消息，用于验证钉钉通知功能是否正常工作。", "系统测试")
    print(f"结果: {'✅ 成功' if result1 else '❌ 失败'}")
    
    # 测试2: 开仓通知
    print("\n🚀 测试2: 开仓通知")
    result2 = notifier.notify_position_opened(
        symbol="BTCUSDT",
        entry_price=65432.10,
        quantity=0.001523,
        cost=99.65,
        strategy_type="volume_breakout",
        signal_strength=7.5,
        reason="成交量突破，信号强度较高，使用限价单"
    )
    print(f"结果: {'✅ 成功' if result2 else '❌ 失败'}")
    
    # 测试3: 平仓通知（盈利）
    print("\n🎉 测试3: 平仓通知（盈利）")
    result3 = notifier.notify_position_closed(
        symbol="BTCUSDT",
        exit_price=67123.45,
        quantity=0.001523,
        revenue=102.24,
        cost=99.65,
        pnl=2.59,
        pnl_pct=0.026,
        reason="移动止盈 (2.6%)",
        holding_hours=12.5
    )
    print(f"结果: {'✅ 成功' if result3 else '❌ 失败'}")
    
    # 测试4: 平仓通知（亏损）
    print("\n😢 测试4: 平仓通知（亏损）")
    result4 = notifier.notify_position_closed(
        symbol="ETHUSDT",
        exit_price=2450.30,
        quantity=0.0408,
        revenue=99.97,
        cost=104.20,
        pnl=-4.23,
        pnl_pct=-0.041,
        reason="止损 (-4.1%)",
        holding_hours=6.2
    )
    print(f"结果: {'✅ 成功' if result4 else '❌ 失败'}")
    
    # 测试5: 挂单通知
    print("\n📋 测试5: 挂单通知")
    result5 = notifier.notify_order_placed(
        symbol="ADAUSDT",
        order_type="黄金分割点挂单",
        price=0.3456,
        quantity=290.5,
        amount=100.35,
        reason="黄金分割点策略，收盘价$0.3521，开盘价$0.3324"
    )
    print(f"结果: {'✅ 成功' if result5 else '❌ 失败'}")
    
    # 测试6: 挂单成交通知
    print("\n✅ 测试6: 挂单成交通知")
    result6 = notifier.notify_order_filled(
        symbol="ADAUSDT",
        order_type="黄金分割点挂单",
        fill_price=0.3456,
        quantity=290.5,
        amount=100.35
    )
    print(f"结果: {'✅ 成功' if result6 else '❌ 失败'}")
    
    # 测试7: 挂单取消通知
    print("\n🚫 测试7: 挂单取消通知")
    result7 = notifier.notify_order_cancelled(
        symbol="LINKUSDT",
        order_type="黄金分割点挂单",
        reason="订单超时"
    )
    print(f"结果: {'✅ 成功' if result7 else '❌ 失败'}")
    
    # 测试8: 风险警报通知
    print("\n⚠️ 测试8: 风险警报通知")
    result8 = notifier.notify_risk_alert(
        "总仓位已达到90%，接近风险上限",
        alert_level="WARNING"
    )
    print(f"结果: {'✅ 成功' if result8 else '❌ 失败'}")
    
    # 测试9: 系统状态通知
    print("\n🚀 测试9: 系统状态通知")
    result9 = notifier.notify_system_status(
        status="启动",
        message="在线交易系统已成功启动，钉钉通知功能正常"
    )
    print(f"结果: {'✅ 成功' if result9 else '❌ 失败'}")
    
    # 测试10: 投资组合摘要通知
    print("\n📊 测试10: 投资组合摘要通知")
    summary = {
        'usdt_balance': 850.75,
        'position_value': 320.45,
        'total_value': 1171.20,
        'position_count': 3,
        'pending_count': 1,
        'exposure': 0.274
    }
    result10 = notifier.notify_portfolio_summary(summary)
    print(f"结果: {'✅ 成功' if result10 else '❌ 失败'}")
    
    # 统计结果
    results = [result1, result2, result3, result4, result5, result6, result7, result8, result9, result10]
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📈 测试结果统计:")
    print(f"总测试数: {total_count}")
    print(f"成功数: {success_count}")
    print(f"失败数: {total_count - success_count}")
    print(f"成功率: {success_count/total_count:.1%}")
    
    if success_count == total_count:
        print(f"\n🎉 所有钉钉通知功能测试通过！")
        return True
    else:
        print(f"\n⚠️ 部分钉钉通知功能测试失败，请检查配置")
        return False


if __name__ == '__main__':
    test_dingtalk_notifications()

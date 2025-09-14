#!/usr/bin/env python3
"""
成交量突破监控策略测试脚本
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from monitor.volume_breakout_strategy import VolumeBreakoutMonitor

def test_basic_functionality():
    """测试基本功能"""
    print("=" * 50)
    print("测试基本功能")
    print("=" * 50)
    
    # 创建测试监控器
    monitor = VolumeBreakoutMonitor(
        data_dir="crypto/data/spot_min_binance",
        volume_multiplier=5.0,  # 降低阈值便于测试
        lookback_days=7
    )
    
    # 测试加载数据
    print("1. 测试数据加载...")
    df = monitor.load_coin_data("BTCUSDT")
    if df is not None and len(df) > 0:
        print(f"   ✅ 成功加载 BTCUSDT 数据，共 {len(df)} 条记录")
        print(f"   最新价格: {df.iloc[-1]['close']}")
        print(f"   最新成交量: {df.iloc[-1]['volumn']}")
    else:
        print("   ❌ 数据加载失败")
        return False
    
    # 测试成交量基准计算
    print("\n2. 测试成交量基准计算...")
    volumes = df['volumn'].values
    baseline = monitor.calculate_volume_baseline(volumes[:-1], datetime.now())
    print(f"   基准成交量: {baseline:.2f}")
    print(f"   当前成交量: {volumes[-1]:.2f}")
    print(f"   成交量比率: {volumes[-1]/baseline if baseline > 0 else 0:.2f}")
    
    # 测试突破检测
    print("\n3. 测试突破检测...")
    result = monitor.detect_volume_breakout("BTCUSDT", df)
    if result['detected']:
        print(f"   ✅ 检测到突破! 成交量倍数: {result['volume_ratio']:.1f}")
    else:
        print(f"   ❌ 未检测到突破，成交量倍数: {result.get('volume_ratio', 0):.1f}")
    
    return True

def test_multiple_coins():
    """测试多币种扫描"""
    print("\n" + "=" * 50)
    print("测试多币种扫描")
    print("=" * 50)
    
    monitor = VolumeBreakoutMonitor(
        data_dir="crypto/data/spot_min_binance",
        volume_multiplier=3.0,  # 进一步降低阈值
        lookback_days=7
    )
    
    # 测试几个主要币种
    test_coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT"]
    results = {}
    
    for coin in test_coins:
        print(f"\n检测 {coin}...")
        result = monitor.run_single_check(coin)
        results[coin] = result
        
        if result.get('detected', False):
            print(f"   ✅ 突破! 倍数: {result['volume_ratio']:.1f}")
        else:
            if 'volume_ratio' in result:
                print(f"   ❌ 无突破，倍数: {result['volume_ratio']:.1f}")
            else:
                print(f"   ❌ 数据不足或错误")
    
    # 统计结果
    detected_count = sum(1 for r in results.values() if r.get('detected', False))
    print(f"\n总结: 检测了 {len(test_coins)} 个币种，发现 {detected_count} 个突破")
    
    return results

def test_data_analysis():
    """分析数据质量"""
    print("\n" + "=" * 50)
    print("数据质量分析")
    print("=" * 50)
    
    monitor = VolumeBreakoutMonitor(data_dir="crypto/data/spot_min_binance")
    
    # 加载BTCUSDT数据进行分析
    df = monitor.load_coin_data("BTCUSDT")
    if df is None:
        print("❌ 无法加载数据")
        return
    
    print(f"数据概览:")
    print(f"  记录数量: {len(df)}")
    print(f"  时间范围: {df['openTime'].min()} 到 {df['openTime'].max()}")
    print(f"  价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
    print(f"  成交量范围: {df['volumn'].min():.2f} - {df['volumn'].max():.2f}")
    print(f"  平均成交量: {df['volumn'].mean():.2f}")
    print(f"  成交量标准差: {df['volumn'].std():.2f}")
    
    # 计算成交量分位数
    volume_percentiles = [50, 75, 90, 95, 99]
    print(f"\n成交量分位数:")
    for p in volume_percentiles:
        value = np.percentile(df['volumn'], p)
        print(f"  {p}%: {value:.2f}")
    
    # 分析最近的成交量
    recent_data = df.tail(100)  # 最近100个15分钟周期
    recent_avg = recent_data['volumn'].mean()
    overall_avg = df['volumn'].mean()
    
    print(f"\n最近vs整体成交量:")
    print(f"  最近100周期平均: {recent_avg:.2f}")
    print(f"  整体平均: {overall_avg:.2f}")
    print(f"  比率: {recent_avg/overall_avg:.2f}")

def run_mock_alert_test():
    """测试提醒功能(不实际发送)"""
    print("\n" + "=" * 50)
    print("测试提醒功能")
    print("=" * 50)
    
    monitor = VolumeBreakoutMonitor(
        data_dir="crypto/data/spot_min_binance",
        volume_multiplier=1.0,  # 极低阈值确保触发
        lookback_days=7
    )
    
    # 模拟突破信息
    mock_breakout_info = {
        'detected': True,
        'current_volume': 1000.0,
        'baseline_volume': 50.0,
        'volume_ratio': 20.0,
        'current_price': 45000.0,
        'current_time': datetime.now()
    }
    
    print("模拟突破信息:")
    print(f"  币种: TESTCOIN")
    print(f"  成交量倍数: {mock_breakout_info['volume_ratio']:.1f}")
    print(f"  当前价格: {mock_breakout_info['current_price']}")
    
    # 测试是否应该提醒
    should_alert_1 = monitor.should_alert("TESTCOIN")
    print(f"\n第一次检查是否应该提醒: {should_alert_1}")
    
    if should_alert_1:
        print("✅ 会发送提醒")
        # 模拟标记已提醒
        monitor.alerted_coins.add("TESTCOIN")
        
        # 再次检查
        should_alert_2 = monitor.should_alert("TESTCOIN")
        print(f"第二次检查是否应该提醒: {should_alert_2}")
        print("✅ 避免重复提醒功能正常")

def main():
    """主测试函数"""
    print("🧪 成交量突破监控策略测试")
    print("测试开始时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        # 1. 基本功能测试
        if not test_basic_functionality():
            print("❌ 基本功能测试失败，退出")
            return
        
        # 2. 多币种测试
        test_multiple_coins()
        
        # 3. 数据分析
        test_data_analysis()
        
        # 4. 提醒功能测试
        run_mock_alert_test()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 
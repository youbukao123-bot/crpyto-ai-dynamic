#!/usr/bin/env python3
"""
动量策略回测运行脚本
简化版本，专注于核心功能
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backtest.momentum_backtest import MomentumBacktest

def load_market_symbols():
    """从exchange_binance_market.txt加载所有币种"""
    try:
        with open('../data/exchange_binance_market.txt', 'r', encoding='utf-8') as f:
            symbols = [line.strip() for line in f.readlines() if line.strip()]
        print(f"📋 从市场币种库加载了 {len(symbols)} 个币种")
        return symbols
    except Exception as e:
        print(f"❌ 加载币种库失败: {str(e)}")
        # 备用币种列表
        return [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'DOTUSDT', 'AVAXUSDT', 'LINKUSDT', 'UNIUSDT', 'AAVEUSDT',
            'SHIBUSDT', 'DOGEUSDT', 'MATICUSDT', 'ATOMUSDT', 'FILUSDT'
        ]

def run_quick_backtest():
    """运行快速回测"""
    print("🚀 开始快速回测...")
    
    # 创建回测引擎
    backtest = MomentumBacktest(
        data_dir="../data/spot_min_binance",
        initial_capital=100000
    )
    
    # 设置回测时间范围（使用最近的数据）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # 最近30天
    
    print(f"📅 回测时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    
    # 加载所有市场币种
    all_symbols = load_market_symbols()
    
    # 对于快速回测，取前50个币种以控制运行时间
    test_symbols = all_symbols[:50]
    print(f"🎯 快速回测模式：使用前 {len(test_symbols)} 个币种")
    
    # 运行回测
    try:
        backtest.run_backtest(
            start_date=start_date,
            end_date=end_date,
            symbols=test_symbols
        )
        
        # 生成报告
        results = backtest.generate_report()
        
        # 保存结果
        backtest.save_results("quick_backtest")
        
        return results
        
    except Exception as e:
        print(f"❌ 回测过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def run_full_backtest():
    """运行完整回测"""
    print("🚀 开始完整回测...")
    
    # 创建回测引擎
    backtest = MomentumBacktest(
        data_dir="../data/spot_min_binance",
        initial_capital=100000
    )
    
    # 设置回测时间范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 最近25天
    
    print(f"📅 回测时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    
    # 加载所有市场币种
    all_symbols = load_market_symbols()
    print(f"🎯 完整回测模式：使用全部 {len(all_symbols)} 个币种")
    
    # 运行回测（使用所有市场币种）
    try:
        backtest.run_backtest(
            start_date=start_date,
            end_date=end_date,
            symbols=all_symbols  # 使用市场币种库中的所有币种
        )
        
        # 生成报告
        results = backtest.generate_report()
        
        # 保存结果
        backtest.save_results("full_backtest")
        
        return results
        
    except Exception as e:
        print(f"❌ 回测过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def analyze_strategy_performance(results):
    """分析策略表现"""
    if not results:
        return
    
    print(f"\n🔍 策略分析:")
    
    trades = results.get('trades', [])
    sell_trades = [t for t in trades if t['action'] == 'SELL']
    
    if not sell_trades:
        print("   暂无完成的交易")
        return
    
    # 按策略分析
    from collections import defaultdict
    strategy_performance = defaultdict(lambda: {'trades': [], 'total_pnl': 0, 'win_count': 0})
    
    for trade in sell_trades:
        strategy = trade.get('strategy', 'Unknown')
        pnl = trade.get('pnl_pct', 0)
        
        strategy_performance[strategy]['trades'].append(trade)
        strategy_performance[strategy]['total_pnl'] += pnl
        if pnl > 0:
            strategy_performance[strategy]['win_count'] += 1
    
    # 排序并显示
    sorted_strategies = sorted(strategy_performance.items(), 
                              key=lambda x: x[1]['total_pnl'], reverse=True)
    
    print(f"\n📊 各策略详细表现:")
    print(f"{'策略名称':<20} {'交易次数':<8} {'胜率':<8} {'总收益率':<10} {'平均收益率':<10}")
    print("-" * 70)
    
    for strategy, data in sorted_strategies:
        trade_count = len(data['trades'])
        win_rate = data['win_count'] / trade_count if trade_count > 0 else 0
        total_return = data['total_pnl']
        avg_return = total_return / trade_count if trade_count > 0 else 0
        
        print(f"{strategy:<20} {trade_count:<8} {win_rate:<8.2%} {total_return:<10.2%} {avg_return:<10.2%}")

def main():
    parser = argparse.ArgumentParser(description='动量策略回测系统')
    parser.add_argument('--mode', choices=['quick', 'full'], default='quick',
                        help='回测模式: quick(快速测试), full(完整回测)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("🚀           动量策略回测系统           🚀")
    print("="*80)
    print("📋 系统特性:")
    print("   • 基于advanced_momentum_strategy的多策略信号")
    print("   • 完整的仓位管理和风险控制")
    print("   • 自动止损止盈")
    print("   • 详细的性能分析报告")
    print("   • 使用exchange_binance_market.txt中的全部币种")
    print("="*80)
    
    if args.mode == 'quick':
        print(f"🔧 运行模式: 快速测试（前50个币种）")
        results = run_quick_backtest()
    else:
        print(f"🔧 运行模式: 完整回测（全部337个币种）")
        results = run_full_backtest()
    
    if results:
        analyze_strategy_performance(results)
        print(f"\n🎉 回测完成！详细结果已保存到CSV文件")
    else:
        print(f"\n❌ 回测失败")

if __name__ == '__main__':
    main()

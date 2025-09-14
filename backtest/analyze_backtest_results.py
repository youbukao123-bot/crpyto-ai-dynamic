#!/usr/bin/env python3
"""
回测结果分析脚本
分析和可视化动量策略回测结果
"""

import pandas as pd
import numpy as np
from datetime import datetime
import glob
import os

def load_latest_backtest_results():
    """加载最新的回测结果"""
    # 查找最新的回测文件
    trade_files = glob.glob("../data/*_trades_*.csv")
    portfolio_files = glob.glob("../data/*_portfolio_*.csv")
    
    if not trade_files or not portfolio_files:
        print("❌ 未找到回测结果文件")
        return None, None
    
    # 按时间排序，取最新的
    trade_files.sort()
    portfolio_files.sort()
    
    latest_trade_file = trade_files[-1]
    latest_portfolio_file = portfolio_files[-1]
    
    print(f"📊 加载回测结果:")
    print(f"   交易记录: {os.path.basename(latest_trade_file)}")
    print(f"   组合历史: {os.path.basename(latest_portfolio_file)}")
    
    trades_df = pd.read_csv(latest_trade_file)
    portfolio_df = pd.read_csv(latest_portfolio_file)
    
    return trades_df, portfolio_df

def analyze_trading_performance(trades_df):
    """分析交易表现"""
    print("\n📈 交易表现分析")
    print("="*60)
    
    if trades_df.empty:
        print("❌ 无交易记录")
        return
    
    # 基础统计
    total_trades = len(trades_df)
    buy_trades = trades_df[trades_df['action'] == 'BUY']
    sell_trades = trades_df[trades_df['action'] == 'SELL']
    
    print(f"总交易次数: {total_trades}")
    print(f"买入次数: {len(buy_trades)}")
    print(f"卖出次数: {len(sell_trades)}")
    
    if len(sell_trades) == 0:
        print("⚠️  暂无卖出交易，无法计算盈亏")
        return
    
    # 盈亏分析
    profitable_trades = sell_trades[sell_trades['pnl_value'] > 0]
    losing_trades = sell_trades[sell_trades['pnl_value'] <= 0]
    
    win_rate = len(profitable_trades) / len(sell_trades)
    avg_profit = profitable_trades['pnl_pct'].mean() if len(profitable_trades) > 0 else 0
    avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
    
    print(f"\n💰 盈亏统计:")
    print(f"   胜率: {win_rate:.2%}")
    print(f"   盈利交易: {len(profitable_trades)} 次")
    print(f"   亏损交易: {len(losing_trades)} 次")
    print(f"   平均盈利: {avg_profit:.2%}")
    print(f"   平均亏损: {avg_loss:.2%}")
    
    if avg_loss != 0:
        profit_loss_ratio = abs(avg_profit / avg_loss)
        print(f"   盈亏比: {profit_loss_ratio:.2f}")
    
    # 持仓时间分析
    avg_holding_time = sell_trades['holding_period'].mean()
    print(f"\n⏰ 持仓时间:")
    print(f"   平均持仓: {avg_holding_time:.1f} 小时")
    print(f"   最短持仓: {sell_trades['holding_period'].min():.1f} 小时")
    print(f"   最长持仓: {sell_trades['holding_period'].max():.1f} 小时")

def analyze_strategy_performance(trades_df):
    """分析各策略表现"""
    print("\n📊 策略表现分析")
    print("="*60)
    
    sell_trades = trades_df[trades_df['action'] == 'SELL']
    if sell_trades.empty:
        print("❌ 无卖出交易记录")
        return
    
    # 按策略分组分析
    strategy_stats = []
    
    for strategy in sell_trades['strategy'].unique():
        strategy_trades = sell_trades[sell_trades['strategy'] == strategy]
        
        total_trades = len(strategy_trades)
        profitable_trades = len(strategy_trades[strategy_trades['pnl_value'] > 0])
        win_rate = profitable_trades / total_trades
        
        total_pnl = strategy_trades['pnl_pct'].sum()
        avg_pnl = strategy_trades['pnl_pct'].mean()
        total_value = strategy_trades['pnl_value'].sum()
        
        avg_holding = strategy_trades['holding_period'].mean()
        
        strategy_stats.append({
            'strategy': strategy,
            'trades': total_trades,
            'win_rate': win_rate,
            'total_return': total_pnl,
            'avg_return': avg_pnl,
            'total_value': total_value,
            'avg_holding': avg_holding
        })
    
    # 排序并显示
    strategy_stats.sort(key=lambda x: x['total_return'], reverse=True)
    
    print(f"{'策略':<15} {'交易':<6} {'胜率':<8} {'总收益率':<10} {'平均收益':<10} {'总盈亏':<10} {'持仓时间':<8}")
    print("-" * 80)
    
    for stats in strategy_stats:
        print(f"{stats['strategy']:<15} "
              f"{stats['trades']:<6} "
              f"{stats['win_rate']:<8.1%} "
              f"{stats['total_return']:<10.2%} "
              f"{stats['avg_return']:<10.2%} "
              f"${stats['total_value']:<9.0f} "
              f"{stats['avg_holding']:<8.1f}h")

def analyze_exit_reasons(trades_df):
    """分析退出原因"""
    print("\n🚪 退出原因分析")
    print("="*60)
    
    sell_trades = trades_df[trades_df['action'] == 'SELL']
    if sell_trades.empty:
        print("❌ 无卖出交易记录")
        return
    
    # 按退出原因分组
    exit_reasons = sell_trades['reason'].value_counts()
    
    print("退出原因统计:")
    for reason, count in exit_reasons.items():
        percentage = count / len(sell_trades) * 100
        avg_pnl = sell_trades[sell_trades['reason'] == reason]['pnl_pct'].mean()
        print(f"   {reason}: {count} 次 ({percentage:.1f}%), 平均收益: {avg_pnl:.2%}")

def analyze_symbol_performance(trades_df):
    """分析各币种表现"""
    print("\n🪙 币种表现分析")
    print("="*60)
    
    sell_trades = trades_df[trades_df['action'] == 'SELL']
    if sell_trades.empty:
        print("❌ 无卖出交易记录")
        return
    
    # 按币种分组
    symbol_stats = []
    
    for symbol in sell_trades['symbol'].unique():
        symbol_trades = sell_trades[sell_trades['symbol'] == symbol]
        
        total_trades = len(symbol_trades)
        profitable_trades = len(symbol_trades[symbol_trades['pnl_value'] > 0])
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = symbol_trades['pnl_pct'].sum()
        total_value = symbol_trades['pnl_value'].sum()
        
        symbol_stats.append({
            'symbol': symbol,
            'trades': total_trades,
            'win_rate': win_rate,
            'total_return': total_pnl,
            'total_value': total_value
        })
    
    # 排序并显示前10
    symbol_stats.sort(key=lambda x: x['total_return'], reverse=True)
    
    print(f"{'币种':<12} {'交易次数':<8} {'胜率':<8} {'总收益率':<10} {'总盈亏':<10}")
    print("-" * 55)
    
    for stats in symbol_stats[:10]:
        print(f"{stats['symbol']:<12} "
              f"{stats['trades']:<8} "
              f"{stats['win_rate']:<8.1%} "
              f"{stats['total_return']:<10.2%} "
              f"${stats['total_value']:<9.0f}")

def analyze_portfolio_equity_curve(portfolio_df):
    """分析组合资金曲线"""
    print("\n📈 资金曲线分析")
    print("="*60)
    
    if portfolio_df.empty:
        print("❌ 无组合历史记录")
        return
    
    portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
    
    initial_value = portfolio_df['total_value'].iloc[0]
    final_value = portfolio_df['total_value'].iloc[-1]
    max_value = portfolio_df['total_value'].max()
    min_value = portfolio_df['total_value'].min()
    
    total_return = (final_value - initial_value) / initial_value
    max_gain = (max_value - initial_value) / initial_value
    max_drawdown = (min_value - max_value) / max_value
    
    print(f"初始资金: ${initial_value:,.0f}")
    print(f"最终资金: ${final_value:,.0f}")
    print(f"最高资金: ${max_value:,.0f}")
    print(f"最低资金: ${min_value:,.0f}")
    print(f"总收益率: {total_return:.2%}")
    print(f"最大收益: {max_gain:.2%}")
    print(f"最大回撤: {max_drawdown:.2%}")
    
    # 计算夏普比率
    portfolio_df['returns'] = portfolio_df['total_value'].pct_change()
    daily_return = portfolio_df['returns'].mean() * 96  # 15分钟 * 96 = 1天
    daily_vol = portfolio_df['returns'].std() * np.sqrt(96)
    
    annual_return = daily_return * 365
    annual_vol = daily_vol * np.sqrt(365)
    sharpe_ratio = annual_return / annual_vol if annual_vol != 0 else 0
    
    print(f"年化收益率: {annual_return:.2%}")
    print(f"年化波动率: {annual_vol:.2%}")
    print(f"夏普比率: {sharpe_ratio:.2f}")

def generate_summary_report(trades_df, portfolio_df):
    """生成总结报告"""
    print("\n📋 回测总结报告")
    print("="*60)
    
    if trades_df.empty or portfolio_df.empty:
        print("❌ 数据不完整，无法生成报告")
        return
    
    # 时间范围
    start_time = pd.to_datetime(trades_df['timestamp']).min()
    end_time = pd.to_datetime(trades_df['timestamp']).max()
    duration_days = (end_time - start_time).days
    
    # 基本统计
    sell_trades = trades_df[trades_df['action'] == 'SELL']
    total_signals = len(trades_df[trades_df['action'] == 'BUY'])
    
    if len(sell_trades) > 0:
        win_rate = len(sell_trades[sell_trades['pnl_value'] > 0]) / len(sell_trades)
        avg_return = sell_trades['pnl_pct'].mean()
    else:
        win_rate = 0
        avg_return = 0
    
    # 资金统计
    initial_capital = portfolio_df['total_value'].iloc[0]
    final_capital = portfolio_df['total_value'].iloc[-1]
    total_return = (final_capital - initial_capital) / initial_capital
    
    print(f"⏱️  回测周期: {duration_days} 天 ({start_time.strftime('%Y-%m-%d')} 至 {end_time.strftime('%Y-%m-%d')})")
    print(f"💰 资金变化: ${initial_capital:,.0f} → ${final_capital:,.0f} ({total_return:+.2%})")
    print(f"📊 交易统计: {total_signals} 次买入信号, {len(sell_trades)} 次卖出")
    print(f"🎯 策略效果: 胜率 {win_rate:.1%}, 平均收益 {avg_return:+.2%}")
    
    # 策略建议
    print(f"\n💡 策略建议:")
    if win_rate < 0.4:
        print("   • 胜率较低，建议优化入场信号质量")
    if avg_return < -0.02:
        print("   • 平均收益为负，建议调整止损止盈策略")
    if total_return < 0:
        print("   • 整体收益为负，建议重新评估策略参数")
    else:
        print("   • 策略表现良好，可考虑扩大资金规模")

def main():
    """主函数"""
    print("🔍 回测结果分析系统")
    print("="*60)
    
    # 加载数据
    trades_df, portfolio_df = load_latest_backtest_results()
    
    if trades_df is None or portfolio_df is None:
        return
    
    # 进行各项分析
    analyze_trading_performance(trades_df)
    analyze_strategy_performance(trades_df)
    analyze_exit_reasons(trades_df)
    analyze_symbol_performance(trades_df)
    analyze_portfolio_equity_curve(portfolio_df)
    generate_summary_report(trades_df, portfolio_df)
    
    print(f"\n✅ 分析完成!")

if __name__ == '__main__':
    main()

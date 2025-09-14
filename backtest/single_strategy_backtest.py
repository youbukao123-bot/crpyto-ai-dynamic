#!/usr/bin/env python3
"""
单策略回测程序
分别测试每个策略的单独效果
"""

import os
import sys
import pandas as pd
import numpy as np
import glob
from datetime import datetime, timedelta
from collections import defaultdict, deque
import warnings
import json
import argparse
import pytz
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def to_beijing_time(utc_time):
    """将UTC时间转换为北京时间"""
    if utc_time.tzinfo is None:
        utc_time = pytz.utc.localize(utc_time)
    elif utc_time.tzinfo != pytz.utc:
        utc_time = utc_time.astimezone(pytz.utc)
    return utc_time.astimezone(BEIJING_TZ)

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from monitor.advanced_momentum_strategy import AdvancedMomentumMonitor
from monitor.volume_breakout_strategy import VolumeBreakoutMonitor
from utils.log_utils import print_log
from backtest.momentum_backtest import Position, Portfolio, MomentumBacktest

class SingleStrategyBacktest(MomentumBacktest):
    """单策略回测引擎"""
    
    def __init__(self, strategy_name, data_dir="crypto/data/spot_min_binance", initial_capital=100000, timeframe="1h", buy_strategy="close"):
        super().__init__(data_dir, initial_capital)
        self.strategy_name = strategy_name
        self.timeframe = timeframe
        self.buy_strategy = buy_strategy
        
        # 使用指定的买入策略创建Portfolio
        self.portfolio = Portfolio(initial_capital, buy_strategy)
        
        self.volume_monitor = VolumeBreakoutMonitor(volume_multiplier=5.0, timeframe=timeframe)  # 使用新的放量突破条件
        
        # 性能优化：预聚合数据缓存
        self.pre_aggregated_data = {}
        
        # 支持的策略列表
        self.available_strategies = {
            'volume_breakout': '成交量突破策略',
            'multi_timeframe': '多时间框架共振策略', 
            'pullback': '突破回踩策略',
            'sector_rotation': '板块轮动策略'
        }
        
        if strategy_name not in self.available_strategies:
            raise ValueError(f"不支持的策略: {strategy_name}. 可用策略: {list(self.available_strategies.keys())}")
    
    def preprocess_data_for_strategy(self):
        """预处理数据以提高回测性能"""
        if self.strategy_name == 'volume_breakout':
            print("🔧 预处理成交量突破策略数据...")
            for symbol in self.all_data.keys():
                # 预先聚合所有数据
                if symbol != 'BTCUSDT':
                    aggregated_df = self.volume_monitor.get_aggregated_data(symbol, self.all_data[symbol])
                    self.pre_aggregated_data[symbol] = aggregated_df
            print(f"✅ 预处理完成，{len(self.pre_aggregated_data)}个币种")
    
    def calculate_signals_at_time(self, timestamp):
        """计算指定时间点的特定策略信号"""
        signals = []
        
        if self.strategy_name == 'volume_breakout':
            # 成交量突破策略
            signals = self._detect_volume_breakout_signals(timestamp)
            
        elif self.strategy_name == 'multi_timeframe':
            # 多时间框架共振策略
            signals = self._detect_multi_timeframe_signals(timestamp)
            
        elif self.strategy_name == 'pullback':
            # 突破回踩策略
            signals = self._detect_pullback_signals(timestamp)
            
        elif self.strategy_name == 'sector_rotation':
            # 板块轮动策略
            signals = self._detect_sector_rotation_signals(timestamp)
        
        return signals
    
    def _detect_volume_breakout_signals(self, timestamp):
        """检测成交量突破信号（性能优化版）"""
        signals = []
        
        for symbol in self.all_data.keys():
            if symbol == 'BTCUSDT':
                continue
            
            try:
                # 使用预聚合的数据或者原始数据
                if symbol in self.pre_aggregated_data:
                    # 使用预聚合数据，只需要检查当前时间点
                    aggregated_df = self.pre_aggregated_data[symbol]
                    if aggregated_df is None or len(aggregated_df) == 0:
                        continue
                    
                    # 找到当前时间点对应的聚合数据
                    mask = aggregated_df['openTime'] <= timestamp
                    if not mask.any():
                        continue
                    
                    current_data = aggregated_df[mask]
                    if len(current_data) < 2:
                        continue
                    
                    # 直接使用聚合数据检测信号
                    result = self._detect_volume_signal_fast(symbol, current_data, timestamp)
                else:
                    # 回退到原始方法
                    hist_data = self.get_historical_data_for_signal(timestamp, symbol)
                    if hist_data is None or len(hist_data) < self.lookback_window:
                        continue
                    result = self.volume_monitor.detect_volume_breakout(symbol, hist_data)
                
                if result.get('detected', False):
                    signal = {
                        'type': '成交量突破',
                        'coin': symbol,
                        'strength': result.get('quote_volume_ratio', 0),
                        'price': result.get('current_price', 0),
                        'details': result.get('reason', '成交量突破')
                    }
                    signals.append(signal)
                    
            except Exception as e:
                continue
                
        return signals
    
    def _detect_volume_signal_fast(self, symbol, aggregated_df, timestamp):
        """快速检测成交量信号（使用预聚合数据）"""
        try:
            if len(aggregated_df) < 2:
                return {'detected': False, 'reason': '数据不足'}
            
            # 获取最新的K线数据
            current_bar = aggregated_df.iloc[-1]
            current_quote_volume = current_bar['quote_volumn']
            current_price = current_bar['close']
            open_price = current_bar['open']
            
            # 检查价格上升
            price_change_pct = (current_price - open_price) / open_price
            if price_change_pct <= 0:
                return {'detected': False, 'reason': f'{self.volume_monitor.timeframe_name}价格下降或持平'}
            
            if price_change_pct >= 0.2:  # 涨幅过大
                return {'detected': False, 'reason': f'{self.volume_monitor.timeframe_name}涨幅超过20%'}
            
            # 计算成交额基准
            quote_volumes = aggregated_df['quote_volumn'].values
            if len(quote_volumes) < 2:
                return {'detected': False, 'reason': '基准数据不足'}
            
            baseline_quote_volume = np.mean(quote_volumes[:-1])  # 简化的基准计算
            if baseline_quote_volume <= 0:
                return {'detected': False, 'reason': '基准成交额为0'}
            
            quote_volume_ratio = current_quote_volume / baseline_quote_volume
            
            # 检查是否达到突破阈值
            volume_condition = quote_volume_ratio >= self.volume_monitor.volume_multiplier
            price_condition = (price_change_pct > 0) and (price_change_pct < 0.2)
            
            # 简化盘整检测（为了性能）
            consolidation_condition = True  # 暂时跳过盘整检测以提高性能
            
            detected = volume_condition and price_condition and consolidation_condition
            
            return {
                'detected': detected,
                'current_quote_volume': current_quote_volume,
                'baseline_quote_volume': baseline_quote_volume,
                'quote_volume_ratio': quote_volume_ratio,
                'current_price': current_price,
                'price_change_pct': price_change_pct,
                'reason': f"{self.volume_monitor.timeframe_name}成交额{quote_volume_ratio:.1f}倍, 涨幅{price_change_pct*100:.1f}%" if detected else "条件不满足"
            }
            
        except Exception as e:
            return {'detected': False, 'reason': f'检测错误: {str(e)}'}
    
    def _detect_multi_timeframe_signals(self, timestamp):
        """检测多时间框架共振信号"""
        signals = []
        
        for symbol in self.all_data.keys():
            if symbol == 'BTCUSDT':
                continue
                
            hist_data = self.get_historical_data_for_signal(timestamp, symbol)
            if hist_data is None or len(hist_data) < self.lookback_window:
                continue
            
            try:
                # 临时设置数据用于信号计算
                self.momentum_monitor.price_data = {symbol: hist_data, 'BTCUSDT': self.all_data.get('BTCUSDT')}
                
                momentum_signal = self.momentum_monitor.detect_multi_timeframe_momentum(symbol)
                if momentum_signal:
                    signals.append(momentum_signal)
                    
            except Exception as e:
                continue
                
        return signals
    
    def _detect_pullback_signals(self, timestamp):
        """检测突破回踩信号"""
        signals = []
        
        for symbol in self.all_data.keys():
            if symbol == 'BTCUSDT':
                continue
                
            hist_data = self.get_historical_data_for_signal(timestamp, symbol)
            if hist_data is None or len(hist_data) < self.lookback_window:
                continue
            
            try:
                # 临时设置数据用于信号计算
                self.momentum_monitor.price_data = {symbol: hist_data, 'BTCUSDT': self.all_data.get('BTCUSDT')}
                
                pullback_signal = self.momentum_monitor.detect_pullback_opportunity(symbol)
                if pullback_signal:
                    signals.append(pullback_signal)
                    
            except Exception as e:
                continue
                
        return signals
    
    def _detect_sector_rotation_signals(self, timestamp):
        """检测板块轮动信号"""
        signals = []
        
        try:
            if len(self.all_data) > 10:  # 确保有足够的数据
                # 临时设置数据用于信号计算
                temp_data = {}
                for symbol in self.all_data.keys():
                    hist_data = self.get_historical_data_for_signal(timestamp, symbol)
                    if hist_data is not None and len(hist_data) >= 14:
                        temp_data[symbol] = hist_data
                
                self.momentum_monitor.price_data = temp_data
                sector_signals = self.momentum_monitor.detect_sector_rotation()
                signals.extend(sector_signals)
        except Exception as e:
            pass
            
        return signals
    
    def run_single_strategy_backtest(self, start_date=None, end_date=None, symbols=None):
        """运行单策略回测"""
        strategy_display_name = self.available_strategies[self.strategy_name]
        print(f"🚀 开始运行【{strategy_display_name}】单独回测...")
        
        # 加载数据
        self.load_historical_data(start_date, end_date, symbols)
        
        if len(self.all_data) == 0:
            print("❌ 没有可用的历史数据")
            return
        
        # 预处理数据以提高性能
        self.preprocess_data_for_strategy()
        
        # 开始回测循环
        signal_count = 0
        trade_count = 0
        
        for i, timestamp in enumerate(self.timestamps):
            # 每N个时间点重新评估
            if i % self.rebalance_frequency != 0:
                continue
            
            # 获取当前价格数据
            current_prices = self.get_price_data_at_time(timestamp)
            
            # 更新持仓
            self.portfolio.update_positions(current_prices, timestamp)
            
            # 计算特定策略信号
            signals = self.calculate_signals_at_time(timestamp)
            signal_count += len(signals)
            
            # 处理信号
            for signal in signals:
                symbol = signal['coin']
                if symbol in current_prices:
                    entry_price = current_prices[symbol]
                    signal_strength = signal['strength']
                    strategy_type = signal['type']
                    
                    # 获取open价格用于黄金分割点计算
                    open_price = self.get_open_price_at_time(symbol, timestamp)
                    
                    # 获取下一根K线的低点，用于判断黄金分割点是否能成交
                    next_low_price = self.get_next_low_price_at_time(symbol, timestamp)
                    
                    # 尝试开仓
                    success, message = self.portfolio.open_position(
                        symbol, entry_price, signal_strength, timestamp, strategy_type, open_price, next_low_price
                    )
                    
                    if success:
                        trade_count += 1
                        beijing_time = to_beijing_time(timestamp)
                        print(f"[{beijing_time.strftime('%m-%d %H:%M')}] 开仓 {symbol} @ {entry_price:.6f} ({strategy_type})")
            
            # 记录组合价值
            self.portfolio.record_portfolio_value(timestamp)
            
            # 进度显示
            if i % (len(self.timestamps) // 10) == 0:
                progress = (i / len(self.timestamps)) * 100
                total_value = self.portfolio.get_total_value()
                position_count = len(self.portfolio.positions)
                print(f"⏳ 进度: {progress:.1f}% | 总资产: ${total_value:,.0f} | 持仓: {position_count} | 信号: {signal_count} | 交易: {trade_count}")
        
        # 强制平仓所有剩余持仓
        final_prices = self.get_price_data_at_time(self.timestamps[-1])
        for symbol in list(self.portfolio.positions.keys()):
            if symbol in final_prices:
                self.portfolio.close_position(symbol, final_prices[symbol], self.timestamps[-1], "回测结束")
        
        print("✅ 回测完成!")
        print(f"📊 【{strategy_display_name}】统计: 总信号 {signal_count}, 总交易 {trade_count}")
    
    def generate_strategy_report(self):
        """生成单策略回测报告"""
        strategy_display_name = self.available_strategies[self.strategy_name]
        
        print("\n" + "="*80)
        print(f"📈     【{strategy_display_name}】回测报告")
        print("="*80)
        
        # 基础统计
        initial_value = self.portfolio.initial_capital
        final_value = self.portfolio.get_total_value()
        total_return = (final_value - initial_value) / initial_value
        
        print(f"💰 资金统计:")
        print(f"   初始资金: ${initial_value:,.0f}")
        print(f"   最终资金: ${final_value:,.0f}")
        print(f"   总收益率: {total_return:.2%}")
        
        # 交易统计
        trades = self.portfolio.trade_history
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        
        print(f"\n📊 交易统计:")
        print(f"   总交易次数: {len(trades)}")
        print(f"   买入次数: {len(buy_trades)}")
        print(f"   卖出次数: {len(sell_trades)}")
        
        if sell_trades:
            profitable_trades = [t for t in sell_trades if t['pnl_value'] > 0]
            win_rate = len(profitable_trades) / len(sell_trades)
            avg_pnl = np.mean([t['pnl_pct'] for t in sell_trades])
            avg_holding_time = np.mean([t['holding_period'] for t in sell_trades])
            
            print(f"   胜率: {win_rate:.2%}")
            print(f"   平均收益率: {avg_pnl:.2%}")
            print(f"   平均持仓时间: {avg_holding_time:.1f}小时")
            
            # 最佳/最差交易
            best_trade = max(sell_trades, key=lambda x: x['pnl_pct'])
            worst_trade = min(sell_trades, key=lambda x: x['pnl_pct'])
            
            print(f"\n🏆 最佳交易: {best_trade['symbol']} ({best_trade['pnl_pct']:.2%})")
            print(f"💔 最差交易: {worst_trade['symbol']} ({worst_trade['pnl_pct']:.2%})")
        
        # 风险统计
        if len(self.portfolio.portfolio_history) > 1:
            portfolio_df = pd.DataFrame(self.portfolio.portfolio_history)
            portfolio_df['returns'] = portfolio_df['total_value'].pct_change()
            
            max_drawdown = self.calculate_max_drawdown(portfolio_df['total_value'])
            
            print(f"\n⚠️  风险指标:")
            print(f"   最大回撤: {max_drawdown:.2%}")
        
        # 绘制收益曲线图
        self.plot_equity_curve()
        
        return {
            'strategy_name': self.strategy_name,
            'strategy_display_name': strategy_display_name,
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': total_return,
            'trades': trades,
            'portfolio_history': self.portfolio.portfolio_history
        }
    
    def plot_equity_curve(self):
        """绘制收益曲线图"""
        if not self.portfolio.portfolio_history:
            print("⚠️  没有组合历史数据，跳过绘图")
            return
        
        try:
            # 准备数据
            portfolio_df = pd.DataFrame(self.portfolio.portfolio_history)
            portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
            portfolio_df['beijing_time'] = portfolio_df['timestamp'].apply(lambda x: to_beijing_time(x))
            
            # 计算收益率
            initial_value = self.portfolio.initial_capital
            portfolio_df['total_return'] = (portfolio_df['total_value'] - initial_value) / initial_value * 100
            
            # 创建图表
            plt.figure(figsize=(12, 8))
            
            # 子图1: 资产价值曲线
            plt.subplot(2, 1, 1)
            plt.plot(portfolio_df['beijing_time'], portfolio_df['total_value'], 
                    color='blue', linewidth=2, label='总资产价值')
            plt.axhline(y=initial_value, color='red', linestyle='--', alpha=0.7, label='初始资金')
            plt.title(f'【{self.available_strategies[self.strategy_name]}】资产价值变化', fontsize=14, fontweight='bold')
            plt.ylabel('资产价值 (USDT)', fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # 格式化x轴
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
            plt.xticks(rotation=45)
            
            # 子图2: 收益率曲线
            plt.subplot(2, 1, 2)
            plt.plot(portfolio_df['beijing_time'], portfolio_df['total_return'], 
                    color='green', linewidth=2, label='累计收益率')
            plt.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='盈亏平衡线')
            plt.title('累计收益率变化', fontsize=14, fontweight='bold')
            plt.xlabel('时间 (北京时间)', fontsize=12)
            plt.ylabel('收益率 (%)', fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # 格式化x轴
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
            plt.xticks(rotation=45)
            
            # 添加交易标记
            self.add_trade_markers(portfolio_df)
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_file = f"../data/{self.strategy_name}_equity_curve_{timestamp}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            print(f"\n📊 收益曲线图已保存: {chart_file}")
            
            # 显示图片
            plt.show()
            
        except Exception as e:
            print(f"⚠️  绘图失败: {str(e)}")
    
    def add_trade_markers(self, portfolio_df):
        """在收益曲线上添加交易标记"""
        try:
            if not self.portfolio.trade_history:
                return
            
            # 获取买入和卖出交易
            trades_df = pd.DataFrame(self.portfolio.trade_history)
            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
            trades_df['beijing_time'] = trades_df['timestamp'].apply(lambda x: to_beijing_time(x))
            
            buy_trades = trades_df[trades_df['action'] == 'BUY']
            sell_trades = trades_df[trades_df['action'] == 'SELL']
            
            # 为每个交易找到对应的组合价值
            for _, trade in buy_trades.iterrows():
                # 找到最接近的组合价值时间点
                closest_idx = (portfolio_df['timestamp'] - trade['timestamp']).abs().idxmin()
                if closest_idx in portfolio_df.index:
                    plt.scatter(trade['beijing_time'], 
                              portfolio_df.loc[closest_idx, 'total_return'],
                              color='green', marker='^', s=60, alpha=0.8, 
                              label='买入' if _ == buy_trades.index[0] else "")
            
            # 标记卖出交易
            for _, trade in sell_trades.iterrows():
                closest_idx = (portfolio_df['timestamp'] - trade['timestamp']).abs().idxmin()
                if closest_idx in portfolio_df.index:
                    color = 'red' if trade['pnl_pct'] < 0 else 'orange'
                    plt.scatter(trade['beijing_time'], 
                              portfolio_df.loc[closest_idx, 'total_return'],
                              color=color, marker='v', s=60, alpha=0.8,
                              label='卖出' if _ == sell_trades.index[0] else "")
            
        except Exception as e:
            print(f"⚠️  添加交易标记失败: {str(e)}")
    
    def save_strategy_results(self, results):
        """保存单策略回测结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_name = self.strategy_name
        
        # 保存交易记录
        trades_df = pd.DataFrame(self.portfolio.trade_history)
        trades_file = f"../data/{strategy_name}_backtest_trades_{timestamp}.csv"
        trades_df.to_csv(trades_file, index=False)
        
        # 保存组合历史
        portfolio_df = pd.DataFrame(self.portfolio.portfolio_history)
        portfolio_file = f"../data/{strategy_name}_backtest_portfolio_{timestamp}.csv"
        portfolio_df.to_csv(portfolio_file, index=False)
        
        print(f"\n💾 【{results['strategy_display_name']}】结果已保存:")
        print(f"   交易记录: {trades_file}")
        print(f"   组合历史: {portfolio_file}")

def run_all_strategies_comparison(start_date, end_date):
    """运行所有策略对比测试"""
    print("="*80)
    print("🔄        全策略对比回测        🔄")
    print("="*80)
    
    strategies = ['volume_breakout', 'multi_timeframe', 'pullback']
    results_summary = []
    
    # 统一的回测参数
   
    initial_capital = 100000
    
    print(f"📅 统一回测参数:")
    print(f"   时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    print(f"   初始资金: ${initial_capital:,.0f}")
    print("="*80)
    
    # 加载币种列表
    try:
        with open('../data/exchange_binance_market.txt', 'r', encoding='utf-8') as f:
            all_symbols = [line.strip() for line in f.readlines() if line.strip()]
        test_symbols = all_symbols  # 前50个币种
    except:
        test_symbols = None
    
    for i, strategy in enumerate(strategies, 1):
        print(f"\n[{i}/{len(strategies)}] 🧪 测试策略: {strategy}")
        print("-" * 60)
        
        try:
            # 创建单策略回测引擎
            backtest = SingleStrategyBacktest(
                strategy_name=strategy,
                data_dir="../data/spot_min_binance",
                initial_capital=initial_capital,
                timeframe="1h"  # 默认使用1小时周期
            )
            
            # 运行回测
            backtest.run_single_strategy_backtest(
                start_date=start_date,
                end_date=end_date,
                symbols=test_symbols
            )
            
            # 生成报告
            results = backtest.generate_strategy_report()
            
            # 保存结果
            backtest.save_strategy_results(results)
            
            # 收集汇总数据
            results_summary.append({
                'strategy': strategy,
                'display_name': results['strategy_display_name'],
                'total_return': results['total_return'],
                'trade_count': len([t for t in results['trades'] if t['action'] == 'SELL']),
                'final_value': results['final_value']
            })
            
        except Exception as e:
            print(f"❌ 策略 {strategy} 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 生成对比报告
    print("\n" + "="*80)
    print("📊           策略对比汇总           📊")
    print("="*80)
    
    if results_summary:
        # 按收益率排序
        results_summary.sort(key=lambda x: x['total_return'], reverse=True)
        
        print(f"{'排名':<4} {'策略名称':<20} {'总收益率':<10} {'交易次数':<8} {'最终资金':<12}")
        print("-" * 60)
        
        for rank, result in enumerate(results_summary, 1):
            print(f"{rank:<4} {result['display_name']:<20} {result['total_return']:<10.2%} "
                  f"{result['trade_count']:<8} ${result['final_value']:<11,.0f}")
        
        best_strategy = results_summary[0]
        print(f"\n🏆 最佳策略: {best_strategy['display_name']}")
        print(f"   收益率: {best_strategy['total_return']:.2%}")
        print(f"   交易次数: {best_strategy['trade_count']}")
    
    print(f"\n🎉 全策略对比测试完成!")

def main():
    parser = argparse.ArgumentParser(description='单策略回测系统')
    parser.add_argument('--strategy', choices=['volume_breakout', 'multi_timeframe', 'pullback', 'all'], 
                        default='all', help='要测试的策略类型')
    parser.add_argument('--days', type=int, default=90, help='回测天数')
    parser.add_argument('--timeframe', choices=['15m', '30m', '1h', '2h', '4h'], 
                        default='1h', help='成交量突破策略的时间周期')
    parser.add_argument('--buy-strategy', choices=['close', 'golden_ratio'], 
                        default='close', help='买入策略：close=收盘价买入，golden_ratio=黄金分割点买入')
    
    args = parser.parse_args()
    
    # 设置回测参数
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    if args.strategy == 'all':
        run_all_strategies_comparison(start_date, end_date)
    else:
        print("="*80)
        print("🧪        单策略回测系统        🧪")
        print("="*80)
        
        try:
            # 创建单策略回测引擎
            backtest = SingleStrategyBacktest(
                strategy_name=args.strategy,
                data_dir="../data/spot_min_binance",
                initial_capital=100000,
                timeframe=args.timeframe,
                buy_strategy=args.buy_strategy
            )
            
            # 加载币种
            try:
                with open('../data/exchange_binance_market.txt', 'r', encoding='utf-8') as f:
                    all_symbols = [line.strip() for line in f.readlines() if line.strip()]
                test_symbols = all_symbols
            except:
                test_symbols = None
            
            # 运行回测
            backtest.run_single_strategy_backtest(
                start_date=start_date,
                end_date=end_date,
                symbols=test_symbols
            )
            
            # 生成报告
            results = backtest.generate_strategy_report()
            
            # 保存结果
            backtest.save_strategy_results(results)
            
        except Exception as e:
            print(f"❌ 回测失败: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()

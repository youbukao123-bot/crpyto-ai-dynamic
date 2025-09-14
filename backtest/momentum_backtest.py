#!/usr/bin/env python3
"""
高级动量策略回测程序
基于advanced_momentum_strategy进行离线买卖模拟回测
包含完整的仓位管理、风险控制和性能评估
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
import matplotlib.pyplot as plt
import seaborn as sns
import pytz
warnings.filterwarnings('ignore')

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
from utils.log_utils import print_log

class Position:
    """单个持仓"""
    def __init__(self, symbol, entry_price, quantity, entry_time, strategy_type, open_price=None):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_time = entry_time
        self.strategy_type = strategy_type
        self.current_price = entry_price
        self.unrealized_pnl = 0
        self.max_profit = 0
        self.max_loss = 0
        
        # 移动止盈相关参数
        self.max_price = entry_price  # 记录最高价格
        self.trailing_stop_activated = False  # 移动止盈是否激活
        self.trailing_stop_price = entry_price  # 移动止盈触发价格
        self.trailing_stop_ratio = 0.68
        
    def update_price(self, current_price):
        """更新当前价格和未实现盈亏"""
        self.current_price = current_price
        self.unrealized_pnl = (current_price - self.entry_price) / self.entry_price
        
        # 更新最大盈利和亏损
        if self.unrealized_pnl > self.max_profit:
            self.max_profit = self.unrealized_pnl
        if self.unrealized_pnl < self.max_loss:
            self.max_loss = self.unrealized_pnl
        
        # 更新移动止盈逻辑
        self.update_trailing_stop(current_price)
    
    def update_trailing_stop(self, current_price):
        """更新移动止盈逻辑"""
        # 更新最高价格
        if current_price > self.max_price:
            self.max_price = current_price
        
        # 计算从最高点的盈利
        max_profit_pct = (self.max_price - self.entry_price) / self.entry_price
        
        # 当盈利达到20%时，激活移动止盈
        if max_profit_pct >= 0.20 and not self.trailing_stop_activated:
            self.trailing_stop_activated = True
            # 设置初始移动止盈价格为成本价上方15%
            self.trailing_stop_price = self.entry_price * 1.15
        
        # 如果移动止盈已激活，动态调整止盈价格
        if self.trailing_stop_activated:
            # 移动止盈策略：从最高点回撤不超过15%
            new_trailing_stop = self.max_price * self.trailing_stop_ratio
            
            # 止盈价格只能向上调整，不能向下
            if new_trailing_stop > self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_stop
    
    def should_trailing_stop(self):
        """判断是否应该触发移动止盈"""
        if not self.trailing_stop_activated:
            return False
        return self.current_price <= self.trailing_stop_price
    
    def get_market_value(self):
        """获取当前市值"""
        return self.quantity * self.current_price
    
    def get_cost_value(self):
        """获取成本价值"""
        return self.quantity * self.entry_price
    
    def get_holding_hours(self, current_time):
        """获取持有时间（小时）"""
        from datetime import datetime
        if isinstance(self.entry_time, str):
            entry_dt = datetime.fromisoformat(self.entry_time)
        else:
            entry_dt = self.entry_time
            
        if isinstance(current_time, str):
            current_dt = datetime.fromisoformat(current_time)
        else:
            current_dt = current_time
            
        time_diff = current_dt - entry_dt
        return time_diff.total_seconds() / 3600
    
    def should_time_exit(self, current_time):
        """判断是否应该基于时间退出
        
        退出规则：
        1. 持有超过7天（168小时）且盈利>=3% -> 获利了结
        2. 持有超过10天（240小时）且亏损<=-3% -> 止损离场
        3. 持有超过14天（336小时）无论盈亏 -> 强制平仓
        4. 持有超过3天（72小时）且盈利>=10% -> 快速获利了结
        """
        holding_hours = self.get_holding_hours(current_time)
        profit_pct = self.unrealized_pnl
        
        # 规则1: 3天且盈利>=10% -> 快速获利
        if holding_hours >= 72 and profit_pct >= 0.10:
            return f"时间止盈（持有{holding_hours:.0f}h，盈利{profit_pct:.1%}）"
        
        # 规则2: 7天且盈利>=3% -> 获利了结
        elif holding_hours >= 168 and profit_pct >= 0.03:
            return f"时间止盈（持有{holding_hours:.0f}h，盈利{profit_pct:.1%}）"
        
        # 规则3: 10天且亏损<=-3% -> 止损离场
        elif holding_hours >= 240 and profit_pct <= -0.03:
            return f"时间止损（持有{holding_hours:.0f}h，亏损{profit_pct:.1%}）"
        
        # 规则4: 14天强制平仓
        elif holding_hours >= 336:
            if profit_pct > 0:
                return f"强制止盈（持有{holding_hours:.0f}h，盈利{profit_pct:.1%}）"
            else:
                return f"强制止损（持有{holding_hours:.0f}h，亏损{profit_pct:.1%}）"
        
        return None

class Portfolio:
    """投资组合管理"""
    def __init__(self, initial_capital=100000, buy_strategy="close"):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # symbol -> Position
        self.trade_history = []
        self.portfolio_history = []
        self.daily_returns = []
        
        # 风险控制参数
        self.max_position_pct = 0.15 # 单个币种最大仓位比例
        self.max_total_exposure = 1.0  # 最大总仓位比例
        self.stop_loss_pct = -0.08  # 止损比例（-8%）
        self.max_profit_pct = 10.0  # 最大止盈比例（80%）
        
        # 买入策略配置
        self.buy_strategy = buy_strategy  # "close" 或 "golden_ratio"
        self.golden_ratio = 0.618  # 黄金分割比例
        
    def get_total_value(self):
        """获取总资产价值"""
        total_position_value = sum(pos.get_market_value() for pos in self.positions.values())
        return self.cash + total_position_value
    
    def get_position_exposure(self):
        """获取总仓位暴露度"""
        total_value = self.get_total_value()
        if total_value <= 0:
            return 0
        total_position_value = sum(pos.get_market_value() for pos in self.positions.values())
        return total_position_value / total_value
    
    def can_open_position(self, symbol, entry_price, signal_strength):
        """检查是否可以开仓"""
        # 检查是否已有该币种持仓
        if symbol in self.positions:
            return False, "已持有该币种"
        
        # 计算建议仓位大小（基于信号强度）
        position_size = self.calculate_position_size(entry_price, signal_strength)
        
        # 检查现金是否充足
        required_cash = position_size * entry_price
        if required_cash > self.cash:
            return False, "现金不足"
        
        # 检查总仓位限制
        current_exposure = self.get_position_exposure()
        new_exposure = required_cash / self.get_total_value()
        
        if current_exposure + new_exposure > self.max_total_exposure:
            return False, "总仓位超限"
        
        return True, "可以开仓"
    
    def calculate_position_size(self, entry_price, signal_strength):
        """计算仓位大小"""
        total_value = self.get_total_value()
        
        # 基础仓位比例（根据信号强度调整）
        base_position_pct = 0.05  # 5%基础仓位
        strength_multiplier = min(signal_strength / 5, 10.0)  # 信号强度倍数，最大2倍
        
        position_pct = min(base_position_pct * strength_multiplier, self.max_position_pct)
        position_value = total_value * position_pct
        
        return position_value / entry_price
    
    def calculate_buy_price(self, close_price, open_price=None, next_low_price=None):
        """根据买入策略计算实际买入价格
        
        策略说明：
        - close: 使用close价格立即买入（原策略）
        - golden_ratio: 使用黄金分割点挂单买入，需要检查下一根K线能否触及
          黄金分割点 = open + (close - open) * 0.618
          
        返回：(actual_price, can_execute)
        """
        if self.buy_strategy == "close":
            return close_price, True
        elif self.buy_strategy == "golden_ratio" and open_price is not None:
            # 黄金分割点买入：open + (close - open) * 0.618
            if close_price > open_price:  # 上涨K线
                price_range = close_price - open_price
                golden_point = open_price + price_range * self.golden_ratio
                
                # 检查下一根K线的低点是否能触及黄金分割点
                if next_low_price is not None:
                    can_execute = next_low_price <= golden_point
                    if can_execute:
                        return golden_point, True
                    else:
                        return None, False  # 无法成交，放弃开仓
                else:
                    # 没有下一根K线数据，假设能成交
                    return golden_point, True
            else:  # 下跌或平盘K线，使用close价格
                return close_price, True
        else:
            # 如果没有open价格，fallback到close价格
            return close_price, True
    
    def open_position(self, symbol, entry_price, signal_strength, entry_time, strategy_type, open_price=None, next_low_price=None):
        """开仓"""
        # 根据买入策略计算实际买入价格
        actual_buy_price, can_execute = self.calculate_buy_price(entry_price, open_price, next_low_price)
        
        # 如果是黄金分割点策略且无法成交，直接返回失败
        if not can_execute:
            if actual_buy_price is not None:
                return False, f"黄金分割点挂单无法成交：信号价{entry_price:.6f}，黄金分割点{actual_buy_price:.6f}，下根K线低点{next_low_price:.6f}"
            else:
                return False, f"黄金分割点挂单无法成交：信号价{entry_price:.6f}，下根K线低点{next_low_price:.6f}"
        
        can_open, reason = self.can_open_position(symbol, actual_buy_price, signal_strength)
        if not can_open:
            return False, reason
        
        quantity = self.calculate_position_size(actual_buy_price, signal_strength)
        cost = quantity * actual_buy_price
        
        # 扣除现金
        self.cash -= cost
        
        # 创建持仓
        position = Position(symbol, actual_buy_price, quantity, entry_time, strategy_type)
        self.positions[symbol] = position
        
        # 记录交易
        trade = {
            'timestamp': entry_time,
            'beijing_time': to_beijing_time(entry_time).strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'action': 'BUY',
            'price': actual_buy_price,
            'quantity': quantity,
            'value': cost,
            'strategy': strategy_type,
            'signal_strength': signal_strength,
            'buy_strategy': self.buy_strategy,  # 记录使用的买入策略
            'original_signal_price': entry_price  # 记录原始信号价格
        }
        self.trade_history.append(trade)
        
        return True, "开仓成功"
    
    def close_position(self, symbol, exit_price, exit_time, reason):
        """平仓"""
        if symbol not in self.positions:
            return False, "无持仓"
        
        position = self.positions[symbol]
        proceeds = position.quantity * exit_price
        
        # 增加现金
        self.cash += proceeds
        
        # 计算盈亏
        pnl_pct = (exit_price - position.entry_price) / position.entry_price
        pnl_value = proceeds - position.get_cost_value()
        
        # 记录交易
        trade = {
            'timestamp': exit_time,
            'beijing_time': to_beijing_time(exit_time).strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'action': 'SELL',
            'price': exit_price,
            'quantity': position.quantity,
            'value': proceeds,
            'strategy': position.strategy_type,
            'pnl_pct': pnl_pct,
            'pnl_value': pnl_value,
            'holding_period': (exit_time - position.entry_time).total_seconds() / 3600,  # 小时
            'reason': reason,
            'max_profit': position.max_profit,
            'max_loss': position.max_loss
        }
        self.trade_history.append(trade)
        
        # 删除持仓
        del self.positions[symbol]
        
        return True, "平仓成功"
    
    def update_positions(self, price_data, current_time):
        """更新所有持仓"""
        for symbol in list(self.positions.keys()):
            if symbol in price_data:
                current_price = price_data[symbol]
                position = self.positions[symbol]
                position.update_price(current_price)
                
                # 检查持有时间退出策略
                holding_hours = position.get_holding_hours(current_time)
                time_exit_reason = position.should_time_exit(current_time)
                if time_exit_reason:
                    self.close_position(symbol, current_price, current_time, time_exit_reason)
                # 检查止损：-8%
                elif position.unrealized_pnl <= self.stop_loss_pct:
                    self.close_position(symbol, current_price, current_time, "止损（-8%）")
                # 检查最高止盈：80%
                elif position.unrealized_pnl >= self.max_profit_pct:
                    self.close_position(symbol, current_price, current_time, "止盈（80%）")
                # 检查移动止盈
                elif position.should_trailing_stop():
                    profit_pct = position.unrealized_pnl
                    self.close_position(symbol, current_price, current_time, f"移动止盈（{profit_pct:.1%}）")
    
    def record_portfolio_value(self, timestamp):
        """记录组合价值"""
        total_value = self.get_total_value()
        position_value = sum(pos.get_market_value() for pos in self.positions.values())
        
        portfolio_record = {
            'timestamp': timestamp,
            'total_value': total_value,
            'cash': self.cash,
            'position_value': position_value,
            'position_count': len(self.positions),
            'exposure': self.get_position_exposure()
        }
        self.portfolio_history.append(portfolio_record)

class MomentumBacktest:
    """动量策略回测引擎"""
    
    def __init__(self, data_dir="crypto/data/spot_min_binance", initial_capital=100000):
        self.data_dir = data_dir
        self.portfolio = Portfolio(initial_capital)
        self.momentum_monitor = AdvancedMomentumMonitor(data_dir=data_dir)
        
        # 回测参数
        self.lookback_window = 500  # 计算信号所需的历史数据窗口
        self.rebalance_frequency = 4  # 每4个15分钟重新评估一次（1小时）
        
        # 数据存储
        self.all_data = {}
        self.timestamps = []
        
    def load_historical_data(self, start_date=None, end_date=None, symbols=None):
        """加载历史数据"""
        print("📊 加载历史数据...")
        
        # 获取所有数据文件
        pattern = f"{self.data_dir}/*_15m_*.csv"
        files = glob.glob(pattern)
        
        loaded_count = 0
        for file_path in files:
            if os.path.getsize(file_path) < 1000:
                continue
                
            filename = os.path.basename(file_path)
            symbol = filename.split('_')[0]
            
            # 如果指定了符号列表，只加载指定的符号
            if symbols and symbol not in symbols:
                continue
            
            try:
                df = pd.read_csv(file_path)
                df['openTime'] = pd.to_datetime(df['openTime'])
                df = df.sort_values('openTime')
                
                # 时间过滤
                if start_date:
                    df = df[df['openTime'] >= start_date]
                if end_date:
                    df = df[df['openTime'] <= end_date]
                
                if len(df) > self.lookback_window:
                    self.all_data[symbol] = df
                    loaded_count += 1
                    
            except Exception as e:
                print(f"⚠️  加载{symbol}数据失败: {str(e)}")
        
        print(f"✅ 成功加载 {loaded_count} 个币种的数据")
        
        # 创建统一的时间索引
        self.create_time_index()
        
    def create_time_index(self):
        """创建统一的时间索引"""
        all_timestamps = set()
        for symbol_data in self.all_data.values():
            all_timestamps.update(symbol_data['openTime'].tolist())
        
        self.timestamps = sorted(list(all_timestamps))
        print(f"📅 回测时间范围: {self.timestamps[0]} 到 {self.timestamps[-1]}")
        print(f"⏱️  总计 {len(self.timestamps)} 个时间点")
    
    def get_price_data_at_time(self, timestamp):
        """获取指定时间点的价格数据"""
        price_data = {}
        for symbol, df in self.all_data.items():
            # 找到最接近的时间点数据
            mask = df['openTime'] <= timestamp
            if mask.any():
                latest_data = df[mask].iloc[-1]
                price_data[symbol] = latest_data['close']
        return price_data
    
    def get_open_price_at_time(self, symbol, timestamp):
        """获取指定币种在指定时间的开盘价"""
        if symbol not in self.all_data:
            return None
        
        df = self.all_data[symbol]
        # 找到指定时间的数据
        mask = df['openTime'] <= timestamp
        if mask.any():
            latest_data = df[mask].iloc[-1]
            return latest_data['open']
        
        return None
    
    def get_next_low_price_at_time(self, symbol, current_timestamp):
        """获取指定币种在下一个时间点的最低价"""
        if symbol not in self.all_data:
            return None
        
        df = self.all_data[symbol]
        # 找到当前时间之后的第一根K线
        mask = df['openTime'] > current_timestamp
        if mask.any():
            next_data = df[mask].iloc[0]
            return next_data['low']
        
        return None
    
    def get_historical_data_for_signal(self, timestamp, symbol):
        """获取用于信号计算的历史数据"""
        if symbol not in self.all_data:
            return None
        
        df = self.all_data[symbol]
        mask = df['openTime'] <= timestamp
        
        if mask.sum() < self.lookback_window:
            return None
        
        return df[mask].tail(self.lookback_window)
    
    def calculate_signals_at_time(self, timestamp):
        """计算指定时间点的所有信号"""
        signals = []
        
        # 为每个币种计算信号
        for symbol in self.all_data.keys():
            if symbol == 'BTCUSDT':  # 跳过BTC作为基准
                continue
            
            hist_data = self.get_historical_data_for_signal(timestamp, symbol)
            if hist_data is None or len(hist_data) < self.lookback_window:
                continue
            
            # 临时设置数据用于信号计算
            self.momentum_monitor.price_data = {symbol: hist_data, 'BTCUSDT': self.all_data.get('BTCUSDT')}
            
            # 检测各种信号
            try:
                # 1. 成交量突破信号
                volume_signal = self.momentum_monitor.detect_volume_breakout(symbol)
                if volume_signal:
                    signals.append(volume_signal)
                
                # 2. 多时间框架共振信号
                momentum_signal = self.momentum_monitor.detect_multi_timeframe_momentum(symbol)
                if momentum_signal:
                    signals.append(momentum_signal)
                
                # 3. 突破回踩信号
                pullback_signal = self.momentum_monitor.detect_pullback_opportunity(symbol)
                if pullback_signal:
                    signals.append(pullback_signal)
                    
            except Exception as e:
                continue
        
        # 4. 板块轮动信号
        try:
            if len(self.all_data) > 10:  # 确保有足够的数据
                sector_signals = self.momentum_monitor.detect_sector_rotation()
                signals.extend(sector_signals)
        except Exception as e:
            pass
        
        return signals
    
    def run_backtest(self, start_date=None, end_date=None, symbols=None):
        """运行回测"""
        print("🚀 开始运行动量策略回测...")
        
        # 加载数据
        self.load_historical_data(start_date, end_date, symbols)
        
        if len(self.all_data) == 0:
            print("❌ 没有可用的历史数据")
            return
        
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
            
            # 计算信号
            signals = self.calculate_signals_at_time(timestamp)
            signal_count += len(signals)
            
            # 处理信号
            for signal in signals:
                symbol = signal['coin']
                if symbol in current_prices:
                    entry_price = current_prices[symbol]  # close价格
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
        print(f"📊 统计: 总信号 {signal_count}, 总交易 {trade_count}")
    
    def generate_report(self):
        """生成回测报告"""
        print("\n" + "="*80)
        print("📈           动量策略回测报告")
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
            
            # 按策略类型统计
            strategy_stats = defaultdict(list)
            for trade in sell_trades:
                strategy_stats[trade['strategy']].append(trade['pnl_pct'])
            
            print(f"\n📋 策略表现:")
            for strategy, pnls in strategy_stats.items():
                avg_return = np.mean(pnls)
                win_rate = len([p for p in pnls if p > 0]) / len(pnls)
                print(f"   {strategy}: 平均收益 {avg_return:.2%}, 胜率 {win_rate:.2%}, 交易数 {len(pnls)}")
        
        # 风险统计
        if len(self.portfolio.portfolio_history) > 1:
            portfolio_df = pd.DataFrame(self.portfolio.portfolio_history)
            portfolio_df['returns'] = portfolio_df['total_value'].pct_change()
            
            annual_return = total_return * (365 * 24 / ((self.timestamps[-1] - self.timestamps[0]).total_seconds() / 3600))
            volatility = portfolio_df['returns'].std() * np.sqrt(365 * 24 * 4)  # 年化波动率
            sharpe_ratio = annual_return / volatility if volatility > 0 else 0
            
            max_drawdown = self.calculate_max_drawdown(portfolio_df['total_value'])
            
            print(f"\n⚠️  风险指标:")
            print(f"   年化收益率: {annual_return:.2%}")
            print(f"   年化波动率: {volatility:.2%}")
            print(f"   夏普比率: {sharpe_ratio:.2f}")
            print(f"   最大回撤: {max_drawdown:.2%}")
        
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': total_return,
            'trades': trades,
            'portfolio_history': self.portfolio.portfolio_history
        }
    
    def calculate_max_drawdown(self, values):
        """计算最大回撤"""
        peak = values.expanding().max()
        drawdown = (values - peak) / peak
        return drawdown.min()
    
    def save_results(self, filename_prefix="momentum_backtest"):
        """保存回测结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存交易记录
        trades_df = pd.DataFrame(self.portfolio.trade_history)
        trades_file = f"../data/{filename_prefix}_trades_{timestamp}.csv"
        trades_df.to_csv(trades_file, index=False)
        
        # 保存组合历史
        portfolio_df = pd.DataFrame(self.portfolio.portfolio_history)
        portfolio_file = f"../data/{filename_prefix}_portfolio_{timestamp}.csv"
        portfolio_df.to_csv(portfolio_file, index=False)
        
        print(f"\n💾 结果已保存:")
        print(f"   交易记录: {trades_file}")
        print(f"   组合历史: {portfolio_file}")
    
    def calculate_max_drawdown(self, values):
        """计算最大回撤"""
        if len(values) < 2:
            return 0.0
        
        peak = values.iloc[0]
        max_drawdown = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
        
def main():
    """主函数"""
    print("="*80)
    print("🚀        高级动量策略回测系统        🚀")
    print("="*80)
    
    # 创建回测引擎
    backtest = MomentumBacktest(
        data_dir="../data/spot_min_binance",
        initial_capital=100000
    )
    
    # 设置回测参数
    start_date = datetime.now() - timedelta(days=25)  # 最近25天
    end_date = datetime.now()
    
    # 运行回测
    backtest.run_backtest(
        start_date=start_date,
        end_date=end_date,
        symbols=None  # 使用所有可用币种
    )
    
    # 生成报告
    results = backtest.generate_report()
    
    # 保存结果
    backtest.save_results()

if __name__ == '__main__':
    main()

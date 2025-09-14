"""
在线策略交易引擎
复用volume_breakout_strategy.py的逻辑，实现4小时周期的在线交易
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import schedule
import time

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from monitor.volume_breakout_strategy import VolumeBreakoutMonitor
from online_trade.enhanced_trader import EnhancedTrader
from online_trade.config_loader import get_config
from utils.log_utils import print_log
from utils.chat_robot import sent_msg

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class OnlineStrategyEngine:
    """在线策略交易引擎"""
    
    def __init__(self, config_override=None):
        """
        初始化在线策略引擎
        
        参数:
        - config_override: 配置覆盖字典（可选）
        """
        # 获取配置
        self.config = get_config()
        
        # 应用配置覆盖
        if config_override:
            for section, values in config_override.items():
                if hasattr(self.config, '_config') and section in self.config._config:
                    self.config._config[section].update(values)
        
        # 从配置读取参数
        self.data_dir = self.config.data_dir
        self.buy_strategy = self.config.buy_strategy
        self.slippage_limit = self.config.slippage_limit
        self.use_limit_order = self.config.use_limit_order
        
        # 初始化成交量突破监控器
        self.volume_monitor = VolumeBreakoutMonitor(
            data_dir=self.data_dir,
            volume_multiplier=self.config.volume_multiplier,
            timeframe=self.config.timeframe,
            lookback_days=7
        )
        
        # 初始化交易器
        self.trader = EnhancedTrader(config_override=config_override)
        
        # 交易记录
        self.signal_history = []
        self.last_check_time = None
        
        print(f"🚀 在线策略引擎初始化完成")
        print(f"   数据目录: {self.data_dir}")
        print(f"   交易周期: {self.config.timeframe}")
        print(f"   买入策略: {self.buy_strategy}")
        print(f"   成交量倍数: {self.config.volume_multiplier}x")
        print(f"   滑点限制: {self.slippage_limit:.3%}")
    
    def load_symbol_data(self, symbol):
        """加载单个币种的数据"""
        file_path = os.path.join(self.data_dir, f"{symbol}_15m.csv")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            df = pd.read_csv(file_path)
            df['openTime'] = pd.to_datetime(df['openTime'])
            df = df.sort_values('openTime').reset_index(drop=True)
            
            # 只保留最近30天的数据（优化性能）
            cutoff_time = datetime.now(BEIJING_TZ) - timedelta(days=30)
            df = df[df['openTime'] >= cutoff_time].reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"❌ 加载 {symbol} 数据失败: {str(e)}")
            return None
    
    def load_symbol_list(self):
        """加载币种列表"""
        symbol_file = os.path.join(os.path.dirname(self.data_dir), "exchange_binance_market.txt")
        
        try:
            with open(symbol_file, 'r', encoding='utf-8') as f:
                symbols = [line.strip() for line in f.readlines() if line.strip()]
            return symbols
        except Exception as e:
            print(f"❌ 加载币种列表失败: {str(e)}")
            return []
    
    def process_golden_ratio_signal(self, symbol, close_price, open_price, signal_strength, strategy_type):
        """
        处理黄金分割点信号（使用挂单管理）
        
        参数:
        - symbol: 币种
        - close_price: 信号K线收盘价
        - open_price: 信号K线开盘价
        - signal_strength: 信号强度
        - strategy_type: 策略类型
        
        返回: (success, message)
        """
        if self.buy_strategy != "golden_ratio":
            # 非黄金分割策略，直接市价买入
            return self.trader.open_position(
                symbol=symbol,
                signal_strength=signal_strength,
                strategy_type=strategy_type,
                use_limit_order=self.use_limit_order,
                slippage_limit=self.slippage_limit
            ), "市价买入"
        
        # 黄金分割策略，使用挂单管理
        return self.trader.place_golden_ratio_order(
            symbol=symbol,
            close_price=close_price,
            open_price=open_price,
            signal_strength=signal_strength,
            strategy_type=strategy_type
        )
    
    def detect_signals(self):
        """检测交易信号"""
        print("🔍 开始检测交易信号...")
        
        symbols = self.load_symbol_list()
        if not symbols:
            print("❌ 没有币种列表")
            return []
        
        signals = []
        current_time = datetime.now(BEIJING_TZ)
        
        for symbol in symbols:
            try:
                # 跳过已有持仓或挂单的币种
                if not self.trader.is_symbol_available_for_trading(symbol):
                    continue
                
                # 加载数据
                df = self.load_symbol_data(symbol)
                if df is None or len(df) < 288:  # 至少需要3天的数据
                    continue
                
                # 检测成交量突破信号
                result = self.volume_monitor.detect_volume_breakout(symbol, df)
                
                if result.get('detected', False):
                    # 获取信号相关的价格信息
                    latest_bar = df.iloc[-1]
                    close_price = latest_bar['close']
                    open_price = latest_bar['open']
                    
                    signal_info = {
                        'symbol': symbol,
                        'timestamp': current_time,
                        'signal_strength': result.get('quote_volume_ratio', 0),
                        'strategy_type': '成交量突破',
                        'close_price': close_price,
                        'open_price': open_price,
                        'volume_ratio': result.get('quote_volume_ratio', 0),
                        'price_change_pct': result.get('price_change_pct', 0),
                        'reason': result.get('reason', '')
                    }
                    signals.append(signal_info)
                    
                    print(f"🎯 发现信号: {symbol}")
                    print(f"   成交额倍数: {result.get('quote_volume_ratio', 0):.1f}")
                    print(f"   价格变化: {result.get('price_change_pct', 0):.2%}")
                    print(f"   买入策略: {self.buy_strategy}")
                
            except Exception as e:
                print(f"❌ 检测 {symbol} 信号时出错: {str(e)}")
        
        print(f"✅ 信号检测完成，发现 {len(signals)} 个信号")
        return signals
    
    def execute_trades(self, signals, risk_result=None):
        """执行交易 - 在风险管理释放资源后执行"""
        if not signals:
            print("💤 没有交易信号")
            return
        
        # 显示风险管理释放的资源
        if risk_result and (risk_result.get('positions_closed', 0) > 0 or risk_result.get('orders_processed', 0) > 0):
            print(f"💡 风险管理已释放资源，当前仓位暴露: {risk_result.get('exposure', 0):.1%}")
        
        print(f"⚡ 开始执行交易，共 {len(signals)} 个信号")
        
        # 按信号强度排序，优先执行强信号
        signals.sort(key=lambda x: x['signal_strength'], reverse=True)
        
        executed_count = 0
        for signal in signals:
            symbol = signal['symbol']
            signal_strength = signal['signal_strength']
            close_price = signal['close_price']
            open_price = signal['open_price']
            strategy_type = signal['strategy_type']
            
            try:
                # 检查是否可以开仓
                summary = self.trader.get_portfolio_summary()
                if summary['exposure'] >= self.trader.max_total_exposure:
                    print(f"⚠️  总仓位已达上限 ({summary['exposure']:.1%})，停止开仓")
                    break
                
                # 处理信号（根据买入策略决定市价买入还是挂单）
                success, message = self.process_golden_ratio_signal(
                    symbol=symbol,
                    close_price=close_price,
                    open_price=open_price,
                    signal_strength=signal_strength,
                    strategy_type=strategy_type
                )
                
                if success:
                    executed_count += 1
                    
                    # 记录信号历史
                    signal['executed'] = True
                    signal['execution_time'] = datetime.now(BEIJING_TZ)
                    signal['execution_method'] = message
                    self.signal_history.append(signal)
                    
                    # 发送通知
                    try:
                        if self.buy_strategy == "golden_ratio":
                            notification_message = f"📋 黄金分割点挂单: {symbol}\n"
                            notification_message += f"信号强度: {signal_strength:.1f}\n"
                            notification_message += f"挂单价格: ${(open_price + (close_price - open_price) * 0.618):.6f}\n"
                            notification_message += f"有效期: 48小时"
                        else:
                            notification_message = f"🎉 开仓成功: {symbol}\n"
                            notification_message += f"信号强度: {signal_strength:.1f}\n"
                            notification_message += f"执行价格: ${close_price:.6f}\n"
                            notification_message += f"买入策略: {self.buy_strategy}"
                        sent_msg(notification_message)
                    except:
                        pass  # 通知失败不影响交易
                else:
                    print(f"❌ {symbol} 执行失败: {message}")
                
                # 限制执行速度
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ 执行 {symbol} 交易失败: {str(e)}")
        
        print(f"✅ 交易执行完成，成功开仓 {executed_count} 个")
    
    def run_risk_management(self):
        """运行风险管理 - 优先级：释放资金和仓位空间"""
        print("🛡️  执行风险管理检查...")
        
        # 获取风险管理前的状态
        initial_positions = len(self.trader.positions)
        initial_pending = len(self.trader.pending_orders)
        
        print(f"📊 风险管理前状态:")
        print(f"   持仓数量: {initial_positions}")
        print(f"   挂单数量: {initial_pending}")
        
        # 执行风险管理（包含持仓管理和挂单状态检查）
        self.trader.check_risk_management()
        
        # 获取风险管理后的状态
        final_positions = len(self.trader.positions)
        final_pending = len(self.trader.pending_orders)
        
        # 计算释放的资源
        positions_closed = initial_positions - final_positions
        orders_processed = initial_pending - final_pending
        
        if positions_closed > 0 or orders_processed > 0:
            print(f"🔄 风险管理处理结果:")
            if positions_closed > 0:
                print(f"   平仓数量: {positions_closed}")
            if orders_processed > 0:
                print(f"   处理挂单: {orders_processed}")
        
        # 打印当前投资组合状态
        summary = self.trader.get_portfolio_summary()
        print(f"💰 投资组合状态:")
        print(f"   USDT余额: ${summary['usdt_balance']:.2f}")
        print(f"   持仓价值: ${summary['position_value']:.2f}")
        print(f"   挂单价值: ${summary['pending_value']:.2f}")
        print(f"   总价值: ${summary['total_value']:.2f}")
        print(f"   仓位暴露: {summary['exposure']:.1%}")
        
        # 显示活跃挂单详情
        if self.trader.pending_orders:
            print(f"📋 活跃挂单:")
            for symbol, order in self.trader.pending_orders.items():
                remaining_hours = (order['timeout_time'] - datetime.now(BEIJING_TZ)).total_seconds() / 3600
                print(f"   {symbol}: ${order['price']:.6f} (剩余{remaining_hours:.1f}小时)")
        
        # 如果没有持仓和挂单，提示系统状态
        if final_positions == 0 and final_pending == 0:
            print("💤 当前无持仓和挂单，系统处于空仓状态")
        
        return {
            'positions_closed': positions_closed,
            'orders_processed': orders_processed,
            'final_positions': final_positions,
            'final_pending': final_pending,
            'exposure': summary['exposure']
        }
    
    def run_strategy_cycle(self):
        """运行一次完整的策略周期"""
        print("\n" + "="*80)
        print(f"🔄 策略周期开始 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        try:
            # 1. 风险管理 - 优先处理现有持仓，释放资金和仓位空间
            risk_result = self.run_risk_management()
            
            # 2. 检测信号 - 在仓位释放后寻找新机会
            signals = self.detect_signals()
            
            # 3. 执行交易 - 利用释放的资源执行新交易
            self.execute_trades(signals, risk_result)
            
            # 4. 更新检查时间
            self.last_check_time = datetime.now(BEIJING_TZ)
            
            print("✅ 策略周期完成")
            
        except Exception as e:
            print(f"❌ 策略周期执行失败: {str(e)}")
            
            # 发送错误通知
            try:
                sent_msg(f"❌ 在线交易策略执行失败: {str(e)}")
            except:
                pass
        
        print("="*80)
    
    def start_trading(self):
        """启动在线交易"""
        print("🚀 启动在线交易系统...")
        print("⏰ 交易周期: 每4小时执行一次")
        print("🛡️  风险管理: 每30分钟检查一次")
        
        # 立即执行一次
        print("🔥 立即执行一次策略周期...")
        self.run_strategy_cycle()
        
        # 设置定时任务
        # 主策略：每4小时执行一次（在4的倍数小时执行，如0点、4点、8点、12点、16点、20点）
        schedule.every().day.at("00:00").do(self.run_strategy_cycle)
        schedule.every().day.at("04:00").do(self.run_strategy_cycle)
        schedule.every().day.at("08:00").do(self.run_strategy_cycle)
        schedule.every().day.at("12:00").do(self.run_strategy_cycle)
        schedule.every().day.at("16:00").do(self.run_strategy_cycle)
        schedule.every().day.at("20:00").do(self.run_strategy_cycle)
        
        # 风险管理：每30分钟检查一次
        schedule.every(30).minutes.do(self.run_risk_management)
        
        print("✅ 定时任务已设置，开始运行...")
        
        # 发送启动通知
        try:
            message = f"🚀 在线交易系统已启动\n"
            message += f"策略: 成交量突破 (4小时周期)\n"
            message += f"买入策略: {self.buy_strategy}\n"
            message += f"启动时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
            sent_msg(message)
        except:
            pass
        
        # 主循环
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                print("\n🛑 收到停止信号，正在关闭...")
                try:
                    sent_msg("🛑 在线交易系统已停止")
                except:
                    pass
                break
            except Exception as e:
                print(f"❌ 主循环错误: {str(e)}")
                time.sleep(60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='在线策略交易引擎')
    parser.add_argument('--capital', type=float, default=1000, help='初始资金（USDT）')
    parser.add_argument('--buy-strategy', choices=['close', 'golden_ratio'], 
                        default='golden_ratio', help='买入策略')
    parser.add_argument('--test', action='store_true', help='测试模式（仅检测信号，不执行交易）')
    
    args = parser.parse_args()
    
    # 创建策略引擎
    engine = OnlineStrategyEngine(
        initial_capital=args.capital,
        buy_strategy=args.buy_strategy
    )
    
    if args.test:
        print("🧪 测试模式：仅检测信号...")
        signals = engine.detect_signals()
        print(f"📊 检测到 {len(signals)} 个信号")
        for signal in signals:
            print(f"   {signal['symbol']}: 强度={signal['signal_strength']:.1f}, "
                  f"价格=${signal['actual_price']:.6f}")
    else:
        # 启动正式交易
        engine.start_trading()


if __name__ == '__main__':
    main()

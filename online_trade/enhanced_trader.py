"""
增强版动量策略交易器
基于mm_trader.py，增加了更多功能
"""

import sys
import os
import pandas as pd
from decimal import Decimal
import math
from datetime import datetime, timedelta
import pytz

# 添加项目路径
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.insert(0, src_dir)

from gateway.binance import BinanceSpotHttp, OrderStatus, OrderType, OrderSide
from utils.log_utils import print_log
from online_trade.config_loader import get_config

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class Position:
    """单个持仓（复制自回测系统）"""
    def __init__(self, symbol, entry_price, quantity, entry_time, strategy_type, cost, config=None):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_time = entry_time
        self.strategy_type = strategy_type
        self.cost = cost
        self.current_price = entry_price
        self.unrealized_pnl = 0
        self.max_profit = 0
        self.max_loss = 0
        
        # 从配置读取移动止盈参数
        if config:
            self.trailing_stop_activation = config.trailing_stop_activation
            self.trailing_stop_ratio = config.trailing_stop_ratio
        else:
            self.trailing_stop_activation = 0.20  # 默认20%激活
            self.trailing_stop_ratio = 0.68  # 默认68%（回撤32%）
        
        # 移动止盈相关参数
        self.max_price = entry_price  # 记录最高价格
        self.trailing_stop_activated = False  # 移动止盈是否激活
        self.trailing_stop_price = entry_price  # 移动止盈触发价格
        
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
        
        # 当盈利达到配置阈值时，激活移动止盈
        if max_profit_pct >= self.trailing_stop_activation and not self.trailing_stop_activated:
            self.trailing_stop_activated = True
            # 设置初始移动止盈价格为成本价上方15%
            self.trailing_stop_price = self.entry_price * 1.15
        
        # 如果移动止盈已激活，动态调整止盈价格
        if self.trailing_stop_activated:
            # 移动止盈策略：从最高点回撤不超过32%（trailing_stop_ratio=0.68）
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
        return self.cost
    
    def get_holding_hours(self, current_time):
        """获取持有时间（小时）"""
        if isinstance(self.entry_time, str):
            entry_dt = datetime.fromisoformat(self.entry_time.replace('Z', '+00:00'))
        else:
            entry_dt = self.entry_time
            
        if isinstance(current_time, str):
            current_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
        else:
            current_dt = current_time
            
        time_diff = current_dt - entry_dt
        return time_diff.total_seconds() / 3600
    
    def should_time_exit(self, current_time, config):
        """判断是否应该基于时间退出（从配置文件读取参数）
        
        退出规则：
        1. 持有超过quick_profit_hours且盈利>=quick_profit_threshold -> 快速获利
        2. 持有超过profit_taking_hours且盈利>=profit_taking_threshold -> 获利了结
        3. 持有超过stop_loss_hours且亏损<=stop_loss_threshold -> 止损离场
        4. 持有超过forced_close_hours无论盈亏 -> 强制平仓
        """
        if not config.enable_time_exit:
            return None
            
        holding_hours = self.get_holding_hours(current_time)
        profit_pct = self.unrealized_pnl
        
        # 规则1: 快速获利
        if holding_hours >= config.quick_profit_hours and profit_pct >= config.quick_profit_threshold:
            return f"时间止盈（持有{holding_hours:.0f}h，盈利{profit_pct:.1%}）"
        
        # 规则2: 获利了结
        elif holding_hours >= config.profit_taking_hours and profit_pct >= config.profit_taking_threshold:
            return f"时间止盈（持有{holding_hours:.0f}h，盈利{profit_pct:.1%}）"
        
        # 规则3: 止损离场
        elif holding_hours >= config.stop_loss_hours and profit_pct <= config.stop_loss_threshold:
            return f"时间止损（持有{holding_hours:.0f}h，亏损{profit_pct:.1%}）"
        
        # 规则4: 强制平仓
        elif holding_hours >= config.forced_close_hours:
            return f"时间强制平仓（持有{holding_hours:.0f}h，盈亏{profit_pct:.1%}）"
        
        return None

def round_to(value: float, target: float) -> float:
    """
    Round price to price tick value.
    """
    log10 = int(math.log(value, 10))
    target = target
    if log10 > 0:
        target = target * log10
        if target > 0.1:
            target = 0.1
        target = max(target, 0.1)
    if log10 < 0:
        target = min(target, pow(10, log10 - 2))

    value = Decimal(str(value))
    target = Decimal(str(target))
    rounded = float(int(round(value / target)) * target)
    return rounded


class EnhancedTrader:
    """增强版动量策略交易器"""
    
    def __init__(self, config_override=None):
        """
        初始化交易器
        
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
        
        # 使用配置中的API信息创建HTTP客户端
        self.http_client = BinanceSpotHttp(
            api_key=self.config.api_key,
            secret=self.config.api_secret,
            host=self.config.base_url,
            proxy_host=self.config.proxy_host,
            proxy_port=self.config.proxy_port,
            timeout=self.config.timeout
        )
        
        # 资金管理（从配置读取）
        self.initial_capital = self.config.initial_capital
        self.max_position_pct = self.config.max_position_pct
        self.max_total_exposure = self.config.max_total_exposure
        self.stop_loss_pct = self.config.stop_loss_pct
        self.take_profit_pct = self.config.take_profit_pct
        self.min_investment_amount = self.config.min_investment_amount
        self.use_limit_order = self.config.use_limit_order
        self.slippage_limit = self.config.slippage_limit
        
        # 持仓记录
        self.positions = {}  # symbol -> Position对象
        self.trade_history = []
        
        # 挂单管理
        self.pending_orders = {}  # symbol -> order_info
        self.order_timeout_hours = 48  # 挂单有效期48小时
        
        print(f"🚀 增强版交易器初始化完成")
        print(f"   初始资金: ${self.initial_capital:,}")
        print(f"   单仓位上限: {self.max_position_pct:.1%}")
        print(f"   总仓位上限: {self.max_total_exposure:.1%}")
        print(f"   止损比例: {self.stop_loss_pct:.1%}")
        print(f"   止盈比例: {self.take_profit_pct:.1%}")
        print(f"   滑点限制: {self.slippage_limit:.3%}")
    
    def get_account_balance(self):
        """获取账户余额"""
        try:
            account_info = self.http_client.get_account_info()
            if account_info:
                balances = {}
                for balance in account_info.get('balances', []):
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    if total > 0:
                        balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': total
                        }
                return balances
        except Exception as e:
            print(f"❌ 获取账户余额失败: {str(e)}")
        return {}
    
    def get_usdt_balance(self):
        """获取USDT余额"""
        balances = self.get_account_balance()
        usdt_info = balances.get('USDT', {})
        return usdt_info.get('free', 0)
    
    def get_symbol_price(self, symbol):
        """获取币种当前价格"""
        try:
            ticker = self.http_client.get_latest_price(symbol=symbol)
            if ticker:
                return float(ticker.get('price', 0))
        except Exception as e:
            print(f"❌ 获取 {symbol} 价格失败: {str(e)}")
        return 0
    
    def get_order_book(self, symbol, limit=5):
        """获取订单簿深度"""
        try:
            depth = self.http_client.get_order_book(symbol=symbol, limit=limit)
            if depth:
                bids = [[float(price), float(qty)] for price, qty in depth.get('bids', [])]
                asks = [[float(price), float(qty)] for price, qty in depth.get('asks', [])]
                return {'bids': bids, 'asks': asks}
        except Exception as e:
            print(f"❌ 获取 {symbol} 订单簿失败: {str(e)}")
        return None
    
    def calculate_limit_price(self, symbol, side, slippage_limit=0.001):
        """
        计算限价单价格，控制滑点
        
        参数:
        - symbol: 交易对
        - side: 买卖方向 ('BUY' 或 'SELL')
        - slippage_limit: 滑点限制，默认0.1%
        
        返回: 限价价格
        """
        current_price = self.get_symbol_price(symbol)
        if current_price <= 0:
            return None
        
        order_book = self.get_order_book(symbol)
        if not order_book:
            # 如果无法获取订单簿，使用当前价格±滑点限制
            if side.upper() == 'BUY':
                return current_price * (1 + slippage_limit)
            else:
                return current_price * (1 - slippage_limit)
        
        if side.upper() == 'BUY':
            # 买入：使用ask价格，加上滑点保护
            asks = order_book.get('asks', [])
            if asks:
                best_ask = asks[0][0]
                limit_price = min(best_ask * (1 + slippage_limit), current_price * (1 + slippage_limit))
                return limit_price
            else:
                return current_price * (1 + slippage_limit)
        else:
            # 卖出：使用bid价格，减去滑点保护
            bids = order_book.get('bids', [])
            if bids:
                best_bid = bids[0][0]
                limit_price = max(best_bid * (1 - slippage_limit), current_price * (1 - slippage_limit))
                return limit_price
            else:
                return current_price * (1 - slippage_limit)
    
    def calculate_position_size(self, symbol, entry_price, signal_strength=5.0):
        """
        计算仓位大小
        
        参数:
        - symbol: 交易对
        - entry_price: 入场价格
        - signal_strength: 信号强度（用于调整仓位大小）
        """
        # 获取可用USDT
        available_usdt = self.get_usdt_balance()
        
        # 基础仓位比例 (5%)
        base_position_pct = 0.05
        
        # 根据信号强度调整仓位（信号强度越高，仓位越大）
        strength_multiplier = min(signal_strength / 5.0, 2.0)  # 最大2倍
        
        # 计算目标仓位比例
        target_position_pct = min(base_position_pct * strength_multiplier, self.max_position_pct)
        
        # 计算目标投资金额
        target_investment = available_usdt * target_position_pct
        
        # 计算购买数量
        quantity = target_investment / entry_price
        
        print(f"📊 {symbol} 仓位计算:")
        print(f"   可用USDT: ${available_usdt:.2f}")
        print(f"   目标仓位比例: {target_position_pct:.2%}")
        print(f"   目标投资金额: ${target_investment:.2f}")
        print(f"   计算数量: {quantity:.6f}")
        
        return quantity, target_investment
    
    def buy_market(self, symbol, investment_amount):
        """
        市价买入
        
        参数:
        - symbol: 交易对
        - investment_amount: 投资金额（USDT）
        
        返回: (成交数量, 实际花费)
        """
        try:
            print(f"💰 正在买入 {symbol}，金额: ${investment_amount:.2f}")
            
            order = self.http_client.place_order(
                symbol=symbol.upper(),
                order_side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0.1,  # 占位符，实际使用quoteOrderQty
                price=0.1,     # 占位符
                quoteOrderQty=investment_amount
            )
            
            if order:
                print(f"✅ {symbol} 买入订单执行成功")
                print(f"📋 订单信息: {order}")
                
                executed_qty = float(order.get('executedQty', 0))
                cost = float(order.get('cummulativeQuoteQty', 0))
                avg_price = cost / executed_qty if executed_qty > 0 else 0
                
                # 记录交易
                trade_record = {
                    'timestamp': datetime.now(BEIJING_TZ),
                    'symbol': symbol,
                    'action': 'BUY',
                    'quantity': executed_qty,
                    'price': avg_price,
                    'cost': cost,
                    'order_id': order.get('orderId'),
                    'status': order.get('status')
                }
                self.trade_history.append(trade_record)
                
                return executed_qty, cost
            
        except Exception as e:
            print(f"❌ {symbol} 买入失败: {str(e)}")
        
        return 0.0, 0.0
    
    def buy_limit(self, symbol, quantity, limit_price, slippage_limit=0.001):
        """
        限价买入，控制滑点
        
        参数:
        - symbol: 交易对
        - quantity: 买入数量
        - limit_price: 限价价格
        - slippage_limit: 滑点限制
        
        返回: (成交数量, 实际花费)
        """
        try:
            # 计算限价价格
            if limit_price is None:
                limit_price = self.calculate_limit_price(symbol, 'BUY', slippage_limit)
            
            if limit_price is None:
                print(f"❌ 无法计算 {symbol} 限价价格")
                return 0.0, 0.0
            
            # 精度处理
            current_price = self.get_symbol_price(symbol)
            limit_price = round_to(limit_price, 0.000001)  # 6位小数精度
            quantity = round_to(quantity, 0.000001)
            
            print(f"💰 正在限价买入 {symbol}")
            print(f"   当前价格: ${current_price:.6f}")
            print(f"   限价价格: ${limit_price:.6f}")
            print(f"   买入数量: {quantity:.6f}")
            print(f"   预计滑点: {abs(limit_price - current_price) / current_price:.3%}")
            
            order = self.http_client.place_order(
                symbol=symbol.upper(),
                order_side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                price=limit_price
            )
            
            if order:
                order_id = order.get('orderId')
                print(f"✅ {symbol} 限价买入订单已提交，订单ID: {order_id}")
                
                # 等待订单成交或部分成交
                filled_qty, cost = self.wait_for_order_fill(symbol, order_id, timeout=30)
                
                if filled_qty > 0:
                    avg_price = cost / filled_qty if filled_qty > 0 else limit_price
                    actual_slippage = abs(avg_price - current_price) / current_price
                    
                    print(f"✅ {symbol} 限价买入成功")
                    print(f"   成交数量: {filled_qty:.6f}")
                    print(f"   平均价格: ${avg_price:.6f}")
                    print(f"   实际滑点: {actual_slippage:.3%}")
                    
                    # 记录交易
                    trade_record = {
                        'timestamp': datetime.now(BEIJING_TZ),
                        'symbol': symbol,
                        'action': 'BUY_LIMIT',
                        'quantity': filled_qty,
                        'price': avg_price,
                        'cost': cost,
                        'order_id': order_id,
                        'limit_price': limit_price,
                        'slippage': actual_slippage,
                        'status': 'FILLED'
                    }
                    self.trade_history.append(trade_record)
                    
                    return filled_qty, cost
                else:
                    print(f"⚠️  {symbol} 限价买入订单未成交，取消订单")
                    self.cancel_order(symbol, order_id)
            
        except Exception as e:
            print(f"❌ {symbol} 限价买入失败: {str(e)}")
        
        return 0.0, 0.0
    
    def sell_market(self, symbol, quantity):
        """
        市价卖出
        
        参数:
        - symbol: 交易对
        - quantity: 卖出数量
        
        返回: 实际收入（USDT）
        """
        try:
            print(f"💸 正在卖出 {symbol}，数量: {quantity:.6f}")
            
            order = self.http_client.place_order(
                symbol=symbol.upper(),
                order_side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=0.1  # 占位符
            )
            
            if order:
                print(f"✅ {symbol} 卖出订单执行成功")
                print(f"📋 订单信息: {order}")
                
                revenue = float(order.get('cummulativeQuoteQty', 0))
                executed_qty = float(order.get('executedQty', 0))
                avg_price = revenue / executed_qty if executed_qty > 0 else 0
                
                # 记录交易
                trade_record = {
                    'timestamp': datetime.now(BEIJING_TZ),
                    'symbol': symbol,
                    'action': 'SELL',
                    'quantity': executed_qty,
                    'price': avg_price,
                    'revenue': revenue,
                    'order_id': order.get('orderId'),
                    'status': order.get('status')
                }
                self.trade_history.append(trade_record)
                
                return revenue
            
        except Exception as e:
            print(f"❌ {symbol} 卖出失败: {str(e)}")
        
        return 0.0
    
    def sell_limit(self, symbol, quantity, limit_price=None, slippage_limit=0.001):
        """
        限价卖出，控制滑点
        
        参数:
        - symbol: 交易对
        - quantity: 卖出数量
        - limit_price: 限价价格
        - slippage_limit: 滑点限制
        
        返回: 实际收入（USDT）
        """
        try:
            # 计算限价价格
            if limit_price is None:
                limit_price = self.calculate_limit_price(symbol, 'SELL', slippage_limit)
            
            if limit_price is None:
                print(f"❌ 无法计算 {symbol} 限价价格")
                return 0.0
            
            # 精度处理
            current_price = self.get_symbol_price(symbol)
            limit_price = round_to(limit_price, 0.000001)
            quantity = round_to(quantity, 0.000001)
            
            print(f"💸 正在限价卖出 {symbol}")
            print(f"   当前价格: ${current_price:.6f}")
            print(f"   限价价格: ${limit_price:.6f}")
            print(f"   卖出数量: {quantity:.6f}")
            print(f"   预计滑点: {abs(limit_price - current_price) / current_price:.3%}")
            
            order = self.http_client.place_order(
                symbol=symbol.upper(),
                order_side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                price=limit_price
            )
            
            if order:
                order_id = order.get('orderId')
                print(f"✅ {symbol} 限价卖出订单已提交，订单ID: {order_id}")
                
                # 等待订单成交或部分成交
                filled_qty, revenue = self.wait_for_order_fill(symbol, order_id, timeout=30, is_sell=True)
                
                if filled_qty > 0:
                    avg_price = revenue / filled_qty if filled_qty > 0 else limit_price
                    actual_slippage = abs(avg_price - current_price) / current_price
                    
                    print(f"✅ {symbol} 限价卖出成功")
                    print(f"   成交数量: {filled_qty:.6f}")
                    print(f"   平均价格: ${avg_price:.6f}")
                    print(f"   实际滑点: {actual_slippage:.3%}")
                    
                    # 记录交易
                    trade_record = {
                        'timestamp': datetime.now(BEIJING_TZ),
                        'symbol': symbol,
                        'action': 'SELL_LIMIT',
                        'quantity': filled_qty,
                        'price': avg_price,
                        'revenue': revenue,
                        'order_id': order_id,
                        'limit_price': limit_price,
                        'slippage': actual_slippage,
                        'status': 'FILLED'
                    }
                    self.trade_history.append(trade_record)
                    
                    return revenue
                else:
                    print(f"⚠️  {symbol} 限价卖出订单未成交，取消订单")
                    self.cancel_order(symbol, order_id)
            
        except Exception as e:
            print(f"❌ {symbol} 限价卖出失败: {str(e)}")
        
        return 0.0
    
    def wait_for_order_fill(self, symbol, order_id, timeout=30, check_interval=2, is_sell=False):
        """
        等待订单成交
        
        参数:
        - symbol: 交易对
        - order_id: 订单ID
        - timeout: 超时时间（秒）
        - check_interval: 检查间隔（秒）
        - is_sell: 是否为卖出订单
        
        返回: (成交数量, 成交金额)
        """
        import time
        
        elapsed_time = 0
        while elapsed_time < timeout:
            try:
                order_status = self.http_client.get_order_by_id(symbol=symbol, orderId=order_id)
                if order_status:
                    status = order_status.get('status')
                    executed_qty = float(order_status.get('executedQty', 0))
                    
                    if status in ['FILLED', 'PARTIALLY_FILLED']:
                        if is_sell:
                            revenue = float(order_status.get('cummulativeQuoteQty', 0))
                            return executed_qty, revenue
                        else:
                            cost = float(order_status.get('cummulativeQuoteQty', 0))
                            return executed_qty, cost
                    elif status == 'CANCELED':
                        print(f"⚠️  订单 {order_id} 已取消")
                        break
                
                time.sleep(check_interval)
                elapsed_time += check_interval
                
            except Exception as e:
                print(f"❌ 检查订单状态失败: {str(e)}")
                break
        
        return 0.0, 0.0
    
    def cancel_order(self, symbol, order_id):
        """取消订单"""
        try:
            result = self.http_client.cancel_order_by_id(symbol=symbol, orderId=order_id)
            if result:
                print(f"✅ 订单 {order_id} 已取消")
                return True
        except Exception as e:
            print(f"❌ 取消订单失败: {str(e)}")
        return False
    
    def open_position(self, symbol, signal_strength, strategy_type="volume_breakout", use_limit_order=True, slippage_limit=0.001):
        """
        开仓
        
        参数:
        - symbol: 交易对
        - signal_strength: 信号强度
        - strategy_type: 策略类型
        - use_limit_order: 是否使用限价单
        - slippage_limit: 滑点限制
        """
        if symbol in self.positions:
            print(f"⚠️  {symbol} 已有持仓，跳过")
            return False
        
        # 获取当前价格
        current_price = self.get_symbol_price(symbol)
        if current_price <= 0:
            print(f"❌ 无法获取 {symbol} 价格")
            return False
        
        # 计算仓位大小
        quantity, investment_amount = self.calculate_position_size(symbol, current_price, signal_strength)
        
        if investment_amount < self.min_investment_amount:  # 最小投资金额限制
            print(f"⚠️  {symbol} 投资金额太小 (${investment_amount:.2f} < ${self.min_investment_amount:.2f})，跳过")
            return False
        
        # 执行买入
        if use_limit_order:
            # 使用限价单，精确控制滑点
            limit_price = self.calculate_limit_price(symbol, 'BUY', slippage_limit)
            if limit_price:
                buy_quantity = investment_amount / limit_price
                executed_qty, actual_cost = self.buy_limit(symbol, buy_quantity, limit_price, slippage_limit)
            else:
                print(f"⚠️  {symbol} 无法计算限价，回退到市价单")
                executed_qty, actual_cost = self.buy_market(symbol, investment_amount)
        else:
            # 使用市价单
            executed_qty, actual_cost = self.buy_market(symbol, investment_amount)
        
        if executed_qty > 0:
            # 记录持仓（使用Position对象）
            avg_price = actual_cost / executed_qty
            position = Position(
                symbol=symbol,
                entry_price=avg_price,
                quantity=executed_qty,
                entry_time=datetime.now(BEIJING_TZ),
                strategy_type=strategy_type,
                cost=actual_cost,
                config=self.config
            )
            self.positions[symbol] = position
            
            print(f"🎉 {symbol} 开仓成功!")
            print(f"   数量: {executed_qty:.6f}")
            print(f"   均价: ${avg_price:.6f}")
            print(f"   成本: ${actual_cost:.2f}")
            print(f"   订单类型: {'限价单' if use_limit_order else '市价单'}")
            
            return True
        
        return False
    
    def close_position(self, symbol, reason="manual", use_limit_order=True, slippage_limit=0.001):
        """
        平仓
        
        参数:
        - symbol: 交易对
        - reason: 平仓原因
        - use_limit_order: 是否使用限价单
        - slippage_limit: 滑点限制
        """
        if symbol not in self.positions:
            print(f"⚠️  {symbol} 没有持仓")
            return False
        
        position = self.positions[symbol]
        quantity = position.quantity
        
        # 执行卖出
        if use_limit_order:
            # 使用限价单
            revenue = self.sell_limit(symbol, quantity, slippage_limit=slippage_limit)
            if revenue <= 0:
                print(f"⚠️  {symbol} 限价卖出失败，回退到市价单")
                revenue = self.sell_market(symbol, quantity)
        else:
            # 使用市价单
            revenue = self.sell_market(symbol, quantity)
        
        if revenue > 0:
            # 计算盈亏
            cost = position.cost
            pnl = revenue - cost
            pnl_pct = pnl / cost
            
            print(f"🏁 {symbol} 平仓完成!")
            print(f"   卖出金额: ${revenue:.2f}")
            print(f"   盈亏: ${pnl:.2f} ({pnl_pct:.2%})")
            print(f"   平仓原因: {reason}")
            print(f"   订单类型: {'限价单' if use_limit_order else '市价单'}")
            
            # 删除持仓记录
            del self.positions[symbol]
            
            return True
        
        return False
    
    def place_golden_ratio_order(self, symbol, close_price, open_price, signal_strength, strategy_type):
        """
        黄金分割点限价挂单
        
        参数:
        - symbol: 币种
        - close_price: 信号K线收盘价
        - open_price: 信号K线开盘价
        - signal_strength: 信号强度
        - strategy_type: 策略类型
        
        返回: (success, message)
        """
        try:
            # 检查是否已有挂单或持仓
            if symbol in self.pending_orders:
                return False, f"{symbol} 已有挂单在等待"
            
            if symbol in self.positions:
                return False, f"{symbol} 已有持仓"
            
            # 计算黄金分割点价格
            if close_price <= open_price:
                golden_point = close_price  # 下跌或平盘，直接用收盘价
            else:
                price_range = close_price - open_price
                golden_point = open_price + price_range * self.config.golden_ratio
            
            # 计算投资金额
            max_position_value = self.initial_capital * self.max_position_pct
            quantity = max_position_value / golden_point
            
            # 检查最小投资金额
            investment_amount = quantity * golden_point
            if investment_amount < self.min_investment_amount:
                return False, f"{symbol} 投资金额过小: ${investment_amount:.2f}"
            
            # 下限价买单
            try:
                order_result = self.http_client.order_test_buy(
                    symbol=symbol.upper(),
                    type=OrderType.LIMIT,
                    quantity=f"{quantity:.6f}",
                    price=f"{golden_point:.6f}",
                    timeInForce="GTC"  # Good Till Cancelled
                )
                
                if order_result:
                    # 记录挂单信息
                    order_info = {
                        'symbol': symbol,
                        'order_id': order_result.get('orderId'),
                        'client_order_id': order_result.get('clientOrderId'),
                        'price': golden_point,
                        'quantity': quantity,
                        'signal_strength': signal_strength,
                        'strategy_type': strategy_type,
                        'close_price': close_price,
                        'open_price': open_price,
                        'create_time': datetime.now(BEIJING_TZ),
                        'timeout_time': datetime.now(BEIJING_TZ) + timedelta(hours=self.order_timeout_hours),
                        'status': 'PENDING'
                    }
                    
                    self.pending_orders[symbol] = order_info
                    
                    print(f"📋 {symbol} 黄金分割点挂单成功:")
                    print(f"   挂单价格: ${golden_point:.6f}")
                    print(f"   挂单数量: {quantity:.6f}")
                    print(f"   投资金额: ${investment_amount:.2f}")
                    print(f"   有效期: {self.order_timeout_hours}小时")
                    
                    return True, "挂单成功"
                else:
                    return False, "挂单失败"
                    
            except Exception as e:
                return False, f"下单异常: {str(e)}"
                
        except Exception as e:
            return False, f"挂单失败: {str(e)}"
    
    def check_pending_orders(self):
        """检查挂单状态"""
        current_time = datetime.now(BEIJING_TZ)
        completed_orders = []
        
        for symbol, order_info in list(self.pending_orders.items()):
            try:
                # 检查挂单是否超时
                if current_time > order_info['timeout_time']:
                    print(f"⏰ {symbol} 挂单超时，取消挂单")
                    self.cancel_pending_order(symbol, "超时")
                    continue
                
                # 查询订单状态
                order_id = order_info['order_id']
                if order_id:
                    order_status = self.http_client.get_order_by_id(symbol.upper(), order_id)
                    
                    if order_status:
                        status = order_status.get('status')
                        
                        if status == 'FILLED':
                            # 订单已成交，创建持仓
                            filled_qty = float(order_status.get('executedQty', 0))
                            filled_price = float(order_status.get('price', order_info['price']))
                            
                            if filled_qty > 0:
                                # 创建持仓
                                position = Position(
                                    symbol=symbol,
                                    entry_price=filled_price,
                                    quantity=filled_qty,
                                    entry_time=current_time,
                                    strategy_type=order_info['strategy_type'],
                                    cost=filled_qty * filled_price,
                                    config=self.config
                                )
                                self.positions[symbol] = position
                                
                                print(f"🎉 {symbol} 黄金分割点挂单成交!")
                                print(f"   成交价格: ${filled_price:.6f}")
                                print(f"   成交数量: {filled_qty:.6f}")
                                print(f"   成交金额: ${filled_qty * filled_price:.2f}")
                                
                                completed_orders.append(symbol)
                        
                        elif status in ['CANCELLED', 'REJECTED', 'EXPIRED']:
                            print(f"❌ {symbol} 挂单已取消/拒绝: {status}")
                            completed_orders.append(symbol)
                
            except Exception as e:
                print(f"❌ 检查 {symbol} 挂单状态失败: {str(e)}")
        
        # 清理已完成的挂单
        for symbol in completed_orders:
            if symbol in self.pending_orders:
                del self.pending_orders[symbol]
    
    def cancel_pending_order(self, symbol, reason="手动取消"):
        """取消挂单"""
        if symbol not in self.pending_orders:
            return False, f"{symbol} 没有挂单"
        
        order_info = self.pending_orders[symbol]
        order_id = order_info.get('order_id')
        
        try:
            if order_id:
                cancel_result = self.http_client.cancel_order_by_id(symbol.upper(), order_id)
                if cancel_result:
                    print(f"🚫 {symbol} 挂单已取消: {reason}")
                    del self.pending_orders[symbol]
                    return True, "取消成功"
            
            # 即使API取消失败，也要从本地记录中删除
            del self.pending_orders[symbol]
            return True, f"本地清理成功: {reason}"
            
        except Exception as e:
            print(f"❌ 取消 {symbol} 挂单失败: {str(e)}")
            # 仍然从本地删除，避免永久阻塞
            if symbol in self.pending_orders:
                del self.pending_orders[symbol]
            return False, f"取消失败: {str(e)}"
    
    def is_symbol_available_for_trading(self, symbol):
        """检查币种是否可以交易（没有持仓或挂单）"""
        return symbol not in self.positions and symbol not in self.pending_orders
    
    def check_risk_management(self):
        """检查风险管理，执行完整的止盈止损逻辑（复制自回测系统）"""
        current_time = datetime.now(BEIJING_TZ)
        
        # 1. 检查挂单状态
        self.check_pending_orders()
        
        # 2. 检查持仓风险管理
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            current_price = self.get_symbol_price(symbol)
            
            if current_price <= 0:
                continue
            
            # 更新持仓价格和相关指标
            position.update_price(current_price)
            
            # 按优先级检查退出条件
            
            # 1. 检查时间退出策略（最高优先级）
            time_exit_reason = position.should_time_exit(current_time, self.config)
            if time_exit_reason:
                print(f"⏰ {symbol} {time_exit_reason}")
                self.close_position(symbol, time_exit_reason, use_limit_order=self.use_limit_order, slippage_limit=self.slippage_limit)
                continue
            
            # 2. 检查基础止损
            elif position.unrealized_pnl <= self.stop_loss_pct:
                print(f"🛑 {symbol} 触发止损 ({position.unrealized_pnl:.2%})")
                self.close_position(symbol, f"止损 ({position.unrealized_pnl:.2%})", use_limit_order=self.use_limit_order, slippage_limit=self.slippage_limit)
                continue
            
            # 3. 检查最大止盈
            elif position.unrealized_pnl >= self.config.max_profit_pct:
                print(f"🎯 {symbol} 触发最大止盈 ({position.unrealized_pnl:.2%})")
                self.close_position(symbol, f"最大止盈 ({position.unrealized_pnl:.2%})", use_limit_order=self.use_limit_order, slippage_limit=self.slippage_limit)
                continue
            
            # 4. 检查移动止盈
            elif position.should_trailing_stop():
                print(f"📈 {symbol} 触发移动止盈 ({position.unrealized_pnl:.2%})")
                self.close_position(symbol, f"移动止盈 ({position.unrealized_pnl:.2%})", use_limit_order=self.use_limit_order, slippage_limit=self.slippage_limit)
                continue
    
    def get_portfolio_summary(self):
        """获取投资组合摘要"""
        balances = self.get_account_balance()
        usdt_balance = balances.get('USDT', {}).get('total', 0)
        
        total_position_value = 0
        for symbol, position in self.positions.items():
            current_price = self.get_symbol_price(symbol)
            if current_price > 0:
                position.update_price(current_price)
                total_position_value += position.get_market_value()
        
        total_value = usdt_balance + total_position_value
        
        # 计算挂单金额
        pending_value = sum(order['quantity'] * order['price'] for order in self.pending_orders.values())
        
        summary = {
            'usdt_balance': usdt_balance,
            'position_value': total_position_value,
            'total_value': total_value,
            'position_count': len(self.positions),
            'pending_count': len(self.pending_orders),
            'pending_value': pending_value,
            'exposure': total_position_value / total_value if total_value > 0 else 0
        }
        
        return summary


def test_trader():
    """测试交易器"""
    trader = EnhancedTrader(initial_capital=100)
    
    # 获取账户信息
    balances = trader.get_account_balance()
    print(f"💰 账户余额: {balances}")
    
    # 获取投资组合摘要
    summary = trader.get_portfolio_summary()
    print(f"📊 投资组合摘要: {summary}")


if __name__ == '__main__':
    test_trader()

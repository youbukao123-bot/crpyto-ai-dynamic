"""
高级动量策略监控系统
包含多种牛市动量策略：
1. 成交量突破策略
2. 多时间框架共振策略  
3. 相对强度策略
4. 突破回踩策略
5. 板块轮动策略
"""

import os
import sys
import pandas as pd
import numpy as np
import glob
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.chat_robot import sent_msg
from utils.log_utils import print_log
from monitor.volume_breakout_strategy import VolumeBreakoutMonitor

class AdvancedMomentumMonitor:
    """高级动量策略监控器"""
    
    def __init__(self, data_dir="crypto/data/spot_min_binance", log_file=None):
        self.data_dir = data_dir
        self.log_file = log_file
        
        # 各策略参数
        self.volume_multiplier = 8.0  # 成交量突破倍数
        self.rsi_oversold = 35        # RSI超卖线
        self.rsi_overbought = 70      # RSI超买线
        self.breakout_confirm_period = 3  # 突破确认周期
        
        # 币种分类（板块）
        self.sectors = {
            'DeFi': ['UNIUSDT', 'AAVEUSDT', 'COMPUSDT', 'MKRUSDT', 'CRVUSDT'],
            'Layer1': ['ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 'AVAXUSDT'],
            'Meme': ['DOGEUSDT', 'SHIBUSDT'],
            'Infrastructure': ['LINKUSDT', 'VETUSDT', 'FILUSDT'],
            'Exchange': ['BNBUSDT', 'FTTUSDT']
        }
        
        # 缓存数据
        self.price_data = {}
        self.volume_data = {}
        self.signals_cache = defaultdict(list)
        
        # 已提醒记录
        self.alerted_signals = set()
        self.last_reset_date = None
        
    def load_all_data(self):
        """加载所有币种数据"""
        try:
            pattern = f"{self.data_dir}/*_15m_*.csv"
            files = glob.glob(pattern)
            
            for file_path in files:
                if os.path.getsize(file_path) < 1000:  # 跳过小文件
                    continue
                    
                filename = os.path.basename(file_path)
                coin_symbol = filename.split('_')[0]
                
                df = pd.read_csv(file_path)
                df['openTime'] = pd.to_datetime(df['openTime'])
                df = df.sort_values('openTime').tail(500)  # 只保留最近500条记录
                
                self.price_data[coin_symbol] = df
                
            if self.log_file:
                print_log(f"[数据加载] 成功加载 {len(self.price_data)} 个币种数据", self.log_file)
                
        except Exception as e:
            if self.log_file:
                print_log(f"[数据加载错误]: {str(e)}", self.log_file)
    
    def calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        try:
            if len(prices) < period + 1:
                return None
                
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[:period])
            avg_loss = np.mean(losses[:period])
            
            if avg_loss == 0:
                return 100
                
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        except:
            return None
    
    def calculate_relative_strength(self, coin_symbol, period=14):
        """计算相对BTC的强度"""
        try:
            if coin_symbol not in self.price_data or 'BTCUSDT' not in self.price_data:
                return 0
                
            coin_df = self.price_data[coin_symbol]
            btc_df = self.price_data['BTCUSDT']
            
            if len(coin_df) < period or len(btc_df) < period:
                return 0
                
            # 计算收益率
            coin_returns = (coin_df['close'].iloc[-1] / coin_df['close'].iloc[-period] - 1)
            btc_returns = (btc_df['close'].iloc[-1] / btc_df['close'].iloc[-period] - 1)
            
            return coin_returns - btc_returns
            
        except Exception as e:
            return 0
    
    def detect_volume_breakout(self, coin_symbol):
        """检测成交量突破"""
        try:
            if coin_symbol not in self.price_data:
                return None
                
            df = self.price_data[coin_symbol]
            if len(df) < 100:  # 需要足够的历史数据
                return None
                
            # 使用之前的成交量突破逻辑
            volume_monitor = VolumeBreakoutMonitor(volume_multiplier=self.volume_multiplier)
            result = volume_monitor.detect_volume_breakout(coin_symbol, df)
            
            if result['detected']:
                return {
                    'type': '成交量突破',
                    'coin': coin_symbol,
                    'strength': result['volume_ratio'],
                    'price': result['current_price'],
                    'details': f"成交量{result['volume_ratio']:.1f}倍突破"
                }
            return None
            
        except Exception as e:
            return None
    
    def detect_multi_timeframe_momentum(self, coin_symbol):
        """多时间框架动量共振检测"""
        try:
            if coin_symbol not in self.price_data:
                return None
                
            df = self.price_data[coin_symbol]
            if len(df) < 50:
                return None
                
            # 检查多个时间框架的动量
            signals = []
            
            # 短期动量 (5周期)
            if len(df) >= 5:
                short_momentum = (df['close'].iloc[-1] / df['close'].iloc[-5] - 1)
                if short_momentum > 0.02:  # 5周期上涨超过2%
                    signals.append('短期上涨')
            
            # 中期动量 (20周期)
            if len(df) >= 20:
                mid_momentum = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1)
                if mid_momentum > 0.05:  # 20周期上涨超过5%
                    signals.append('中期上涨')
            
            # 成交量确认
            recent_volume = df['volumn'].tail(5).mean()
            historical_volume = df['volumn'].tail(50).mean()
            if recent_volume > historical_volume * 1.5:  # 最近成交量放大
                signals.append('成交量放大')
            
            # 相对强度
            rel_strength = self.calculate_relative_strength(coin_symbol)
            if rel_strength > 0.03:  # 相对BTC强势3%以上
                signals.append('相对强势')
            
            if len(signals) >= 3:  # 至少3个信号共振
                return {
                    'type': '多时间框架共振',
                    'coin': coin_symbol,
                    'strength': len(signals),
                    'price': df['close'].iloc[-1],
                    'details': f"共振信号: {', '.join(signals)}"
                }
            return None
            
        except Exception as e:
            return None
    
    def detect_pullback_opportunity(self, coin_symbol):
        """检测突破回踩机会"""
        try:
            if coin_symbol not in self.price_data:
                return None
                
            df = self.price_data[coin_symbol]
            if len(df) < 30:
                return None
                
            # 寻找最近的高点
            recent_high = df['high'].tail(20).max()
            current_price = df['close'].iloc[-1]
            
            # 检查是否从高点回调
            pullback_ratio = (recent_high - current_price) / recent_high
            
            # 理想的回调范围：3-8%
            if 0.03 <= pullback_ratio <= 0.08:
                # 检查是否有放量迹象
                recent_volume = df['volumn'].tail(3).mean()
                avg_volume = df['volumn'].tail(20).mean()
                
                if recent_volume > avg_volume * 1.2:  # 轻微放量
                    # 计算RSI，寻找超卖反弹
                    rsi = self.calculate_rsi(df['close'].values)
                    
                    if rsi and self.rsi_oversold <= rsi <= 50:  # RSI在合理范围
                        return {
                            'type': '突破回踩',
                            'coin': coin_symbol,
                            'strength': (0.08 - pullback_ratio) * 100,  # 回调越小评分越高
                            'price': current_price,
                            'details': f"从高点{recent_high:.4f}回调{pullback_ratio*100:.1f}%, RSI:{rsi:.1f}"
                        }
            return None
            
        except Exception as e:
            return None
    
    def detect_sector_rotation(self):
        """检测板块轮动机会"""
        try:
            sector_performance = {}
            
            for sector, coins in self.sectors.items():
                sector_returns = []
                for coin in coins:
                    if coin in self.price_data:
                        df = self.price_data[coin]
                        if len(df) >= 14:
                            # 计算14周期收益率
                            returns = (df['close'].iloc[-1] / df['close'].iloc[-14] - 1)
                            sector_returns.append(returns)
                
                if sector_returns:
                    sector_performance[sector] = np.mean(sector_returns)
            
            if not sector_performance:
                return []
            
            # 找出表现最好的板块
            best_sector = max(sector_performance, key=sector_performance.get)
            best_performance = sector_performance[best_sector]
            
            if best_performance > 0.1:  # 板块涨幅超过10%
                # 找出该板块内表现最好的币种
                sector_signals = []
                for coin in self.sectors[best_sector]:
                    if coin in self.price_data:
                        df = self.price_data[coin]
                        if len(df) >= 14:
                            coin_returns = (df['close'].iloc[-1] / df['close'].iloc[-14] - 1)
                            if coin_returns > best_performance * 0.8:  # 个股表现接近板块平均
                                sector_signals.append({
                                    'type': '板块轮动',
                                    'coin': coin,
                                    'strength': coin_returns * 100,
                                    'price': df['close'].iloc[-1],
                                    'details': f"{best_sector}板块领涨，个股涨幅{coin_returns*100:.1f}%"
                                })
                
                return sorted(sector_signals, key=lambda x: x['strength'], reverse=True)[:3]
            
            return []
            
        except Exception as e:
            return []
    
    def should_alert(self, signal_key):
        """判断是否应该发送提醒"""
        current_date = datetime.now().date()
        
        # 每天重置提醒记录
        if self.last_reset_date != current_date:
            self.alerted_signals.clear()
            self.last_reset_date = current_date
            
        return signal_key not in self.alerted_signals
    
    def send_alert(self, signals):
        """发送交易信号提醒"""
        try:
            if not signals:
                return
                
            # 按强度排序
            signals = sorted(signals, key=lambda x: x['strength'], reverse=True)
            
            message = "🚀 [牛市动量策略信号]\n\n"
            
            sent_count = 0
            for signal in signals[:5]:  # 最多发送5个信号
                signal_key = f"{signal['coin']}_{signal['type']}_{datetime.now().date()}"
                
                if self.should_alert(signal_key) and sent_count < 3:
                    message += f"📈 {signal['type']}: {signal['coin']}\n"
                    message += f"💰 价格: {signal['price']:.6f}\n"
                    message += f"⭐ 强度: {signal['strength']:.1f}\n"
                    message += f"📝 详情: {signal['details']}\n\n"
                    
                    self.alerted_signals.add(signal_key)
                    sent_count += 1
            
            if sent_count > 0:
                message += "💡 建议: 谨慎评估后考虑买入"
                sent_msg(message)
                
                if self.log_file:
                    print_log(f"[信号发送] 发送{sent_count}个动量信号", self.log_file)
            
        except Exception as e:
            if self.log_file:
                print_log(f"[发送提醒错误]: {str(e)}", self.log_file)
    
    def scan_all_strategies(self):
        """扫描所有策略信号"""
        try:
            if self.log_file:
                print_log(f"[开始扫描] 多策略动量信号检测", self.log_file)
            
            # 加载数据
            self.load_all_data()
            
            all_signals = []
            
            # 遍历所有币种，检测各种信号
            for coin_symbol in self.price_data.keys():
                if coin_symbol == 'BTCUSDT':  # 跳过BTC，作为基准
                    continue
                
                # 1. 成交量突破检测
                volume_signal = self.detect_volume_breakout(coin_symbol)
                if volume_signal:
                    all_signals.append(volume_signal)
                
                # 2. 多时间框架共振检测
                momentum_signal = self.detect_multi_timeframe_momentum(coin_symbol)
                if momentum_signal:
                    all_signals.append(momentum_signal)
                
                # 3. 突破回踩检测
                pullback_signal = self.detect_pullback_opportunity(coin_symbol)
                if pullback_signal:
                    all_signals.append(pullback_signal)
            
            # 4. 板块轮动检测
            sector_signals = self.detect_sector_rotation()
            all_signals.extend(sector_signals)
            
            # 发送信号
            if all_signals:
                self.send_alert(all_signals)
                
                if self.log_file:
                    for signal in all_signals:
                        print_log(f"[发现信号] {signal['type']} - {signal['coin']} - 强度{signal['strength']:.1f}", self.log_file)
            else:
                if self.log_file:
                    print_log(f"[扫描完成] 未发现符合条件的信号", self.log_file)
            
            return all_signals
            
        except Exception as e:
            if self.log_file:
                print_log(f"[扫描错误]: {str(e)}", self.log_file)
            return []
    
    def get_market_overview(self):
        """获取市场概况"""
        try:
            if 'BTCUSDT' not in self.price_data:
                return None
                
            btc_df = self.price_data['BTCUSDT']
            
            # BTC动量分析
            btc_momentum_1d = (btc_df['close'].iloc[-1] / btc_df['close'].iloc[-96] - 1) if len(btc_df) >= 96 else 0  # 24小时
            btc_momentum_3d = (btc_df['close'].iloc[-1] / btc_df['close'].iloc[-288] - 1) if len(btc_df) >= 288 else 0  # 3天
            
            # 市场参与度（通过成交量）
            recent_volume = btc_df['volumn'].tail(24).mean()  # 最近24个15分钟
            avg_volume = btc_df['volumn'].tail(96).mean()  # 最近4天平均
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            market_state = "中性"
            if btc_momentum_1d > 0.03 and volume_ratio > 1.2:
                market_state = "强势上涨"
            elif btc_momentum_1d > 0.01:
                market_state = "温和上涨"
            elif btc_momentum_1d < -0.03:
                market_state = "下跌"
            
            return {
                'btc_price': btc_df['close'].iloc[-1],
                'btc_1d_change': btc_momentum_1d * 100,
                'btc_3d_change': btc_momentum_3d * 100,
                'volume_ratio': volume_ratio,
                'market_state': market_state
            }
            
        except Exception as e:
            return None 
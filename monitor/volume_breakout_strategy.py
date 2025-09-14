"""
简单动量币监控策略
当15分钟K线的成交量突然是过去7天15分钟成交量的10倍时提示买入
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
from utils.time_utils import timestamp_to_str

class VolumeBreakoutMonitor:
    """成交量突破监控策略"""
    
    def __init__(self, data_dir="crypto/data/spot_min_binance", volume_multiplier=5, lookback_days=7, 
                 timeframe="1h", log_file=None):
        """
        初始化监控器
        
        参数:
        - data_dir: 数据文件目录
        - volume_multiplier: 成交量倍数阈值 (默认10倍)
        - lookback_days: 历史数据回看天数 (默认7天)
        - timeframe: 观测时间周期 (默认1h), 可选: 15m, 30m, 1h, 2h, 4h
        - log_file: 日志文件句柄
        """
        self.data_dir = data_dir
        self.volume_multiplier = volume_multiplier
        self.lookback_days = lookback_days
        self.timeframe = timeframe
        self.log_file = log_file
        
        # 时间周期配置
        self.timeframe_config = {
            '15m': {'periods': 1, 'name': '15分钟'},
            '30m': {'periods': 2, 'name': '30分钟'},
            '1h': {'periods': 4, 'name': '1小时'},
            '2h': {'periods': 8, 'name': '2小时'},
            '4h': {'periods': 16, 'name': '4小时'}
        }
        
        if timeframe not in self.timeframe_config:
            raise ValueError(f"不支持的时间周期: {timeframe}. 可选: {list(self.timeframe_config.keys())}")
        
        self.periods_per_timeframe = self.timeframe_config[timeframe]['periods']
        self.timeframe_name = self.timeframe_config[timeframe]['name']
        
        # 成交量历史数据缓存
        self.volume_history = defaultdict(list)
        self.price_history = defaultdict(list)
        
        # 聚合数据缓存 - 性能优化
        self.aggregated_data_cache = {}  # symbol -> aggregated_df
        self.cache_timestamp = {}  # symbol -> last_update_time
        
        # 已发送信号的币种(避免重复提醒)
        self.alerted_coins = set()
        
        # 每天重置提醒记录的时间
        self.last_reset_date = None
        
    def load_coin_data(self, coin_symbol):
        """
        加载指定币种的15分钟K线数据
        
        参数:
        - coin_symbol: 币种符号，如'BTCUSDT'
        
        返回:
        - DataFrame: K线数据
        """
        try:
            # 查找匹配的数据文件
            pattern = f"{self.data_dir}/{coin_symbol}_15m_*.csv"
            files = glob.glob(pattern)
            
            if not files:
                return None
                
            # 取最新的文件
            latest_file = max(files, key=os.path.getctime)
            
            # 读取数据
            df = pd.read_csv(latest_file)
            
            # 转换时间列
            df['openTime'] = pd.to_datetime(df['openTime'])
            df = df.sort_values('openTime')
            
            return df
            
        except Exception as e:
            if self.log_file:
                print_log(f"[load_data_error] {coin_symbol}: {str(e)}", self.log_file)
            return None
    
    def calculate_volume_baseline(self, volumes, current_time):
        """
        计算过去N天的成交量基准
        
        参数:
        - volumes: 成交量序列
        - current_time: 当前时间
        
        返回:
        - float: 成交量基准值
        """
        if len(volumes) < 2:
            return 0
            
        # 过去7天的15分钟周期数量 = 7 * 24 * 4 = 672
        lookback_periods = self.lookback_days * 24 * 4
        
        # 取最近N个周期的数据
        recent_volumes = volumes[-min(lookback_periods, len(volumes)):]
        
        if len(recent_volumes) < 10:  # 至少需要10个数据点
            return 0
            
        # 计算平均成交量
        avg_volume = np.mean(recent_volumes)
        
        return avg_volume
    
    def get_aggregated_data(self, coin_symbol, df):
        """
        获取聚合数据（带缓存优化）
        
        参数:
        - coin_symbol: 币种符号
        - df: 15分钟K线数据
        
        返回:
        - DataFrame: 聚合后的数据
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        # 获取最新数据时间
        latest_time = df.iloc[-1]['openTime']
        
        # 检查缓存是否有效
        if (coin_symbol in self.aggregated_data_cache and 
            coin_symbol in self.cache_timestamp and
            self.cache_timestamp[coin_symbol] == latest_time):
            return self.aggregated_data_cache[coin_symbol]
        
        # 重新聚合数据
        aggregated_df = self.aggregate_to_timeframe(df)
        
        # 更新缓存
        self.aggregated_data_cache[coin_symbol] = aggregated_df
        self.cache_timestamp[coin_symbol] = latest_time
        
        return aggregated_df
    
    def aggregate_to_timeframe(self, df):
        """
        将15分钟数据聚合到指定时间周期
        
        参数:
        - df: 15分钟K线数据
        
        返回:
        - DataFrame: 聚合后的数据
        """
        if self.timeframe == '15m':
            return df.copy()  # 直接返回原数据
        
        # 按照时间周期分组聚合
        periods = self.periods_per_timeframe
        
        # 确保数据按时间排序
        df_sorted = df.sort_values('openTime').copy()
        
        # 创建分组索引
        df_sorted['group'] = df_sorted.index // periods
        
        # 按组聚合数据
        aggregated_data = []
        for group_id, group_df in df_sorted.groupby('group'):
            if len(group_df) < periods:
                continue  # 跳过不完整的组
                
            # OHLC聚合
            open_price = group_df.iloc[0]['open']
            high_price = group_df['high'].max()
            low_price = group_df['low'].min()
            close_price = group_df.iloc[-1]['close']
            
            # 成交量和成交额求和
            volume = group_df['volumn'].sum()
            quote_volume = group_df['quote_volumn'].sum()
            
            # 时间使用组内第一个时间点
            open_time = group_df.iloc[0]['openTime']
            
            aggregated_data.append({
                'openTime': open_time,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volumn': volume,
                'quote_volumn': quote_volume
            })
        
        if not aggregated_data:
            return pd.DataFrame()
        
        return pd.DataFrame(aggregated_data)
    
    def detect_consolidation_phase(self, df, min_days=3, volatility_threshold=0.05):
        """
        检测盘整阶段
        
        参数:
        - df: K线数据
        - min_days: 最小盘整天数（默认3天）
        - volatility_threshold: 波动率阈值（默认5%）
        
        返回:
        - dict: 盘整信息 {'is_consolidating': bool, 'duration': int, 'volatility': float}
        """
        try:
            # 需要至少3天的数据
            min_periods = min_days * 24 * 4  # 15分钟周期数
            if len(df) < min_periods:
                return {'is_consolidating': False, 'reason': '数据不足'}
            
            # 获取最近3天的数据
            recent_data = df.iloc[-min_periods:].copy()
            
            # 计算价格波动率
            high_prices = recent_data['high'].values
            low_prices = recent_data['low'].values
            close_prices = recent_data['close'].values
            
            # 计算最高价和最低价的振幅
            max_high = np.max(high_prices)
            min_low = np.min(low_prices)
            price_range = (max_high - min_low) / min_low
            
            # 计算价格标准差
            price_std = np.std(close_prices) / np.mean(close_prices)
            
            # 判断是否为盘整：价格振幅和标准差都较小
            is_consolidating = (price_range <= volatility_threshold * 2) and (price_std <= volatility_threshold)
            
            # 如果满足基本盘整条件，检查是否持续了足够长时间
            if is_consolidating:
                # 检查更长时间的盘整（最多检查7天）
                max_check_periods = min(7 * 24 * 4, len(df))
                consolidation_duration = 0
                
                for i in range(min_periods, max_check_periods, 96):  # 每天检查一次
                    check_data = df.iloc[-i:].copy()
                    if len(check_data) < min_periods:
                        break
                        
                    check_high = np.max(check_data['high'].values)
                    check_low = np.min(check_data['low'].values)
                    check_range = (check_high - check_low) / check_low
                    check_std = np.std(check_data['close'].values) / np.mean(check_data['close'].values)
                    
                    if check_range <= volatility_threshold * 2 and check_std <= volatility_threshold:
                        consolidation_duration = i // 96  # 转换为天数
                    else:
                        break
                
                return {
                    'is_consolidating': True,
                    'duration_periods': min_periods,
                    'duration_days': consolidation_duration if consolidation_duration > 0 else min_days,
                    'price_range': price_range,
                    'volatility': price_std,
                    'reason': f'盘整{consolidation_duration if consolidation_duration > 0 else min_days}天'
                }
            else:
                return {
                    'is_consolidating': False,
                    'price_range': price_range,
                    'volatility': price_std,
                    'reason': f'波动过大(振幅{price_range:.1%}, 标准差{price_std:.1%})'
                }
                
        except Exception as e:
            return {'is_consolidating': False, 'reason': f'检测错误: {str(e)}'}
    
    def detect_volume_breakout(self, coin_symbol, df):
        """
        检测成交量突破
        新条件：
        a. 成交量是过去一周指定时间周期成交额的10倍
        b. 该时间周期内的涨幅小于10%，且必须是价格上升
        c. 处于盘整阶段后的放量，盘整时间>=3天
        
        参数:
        - coin_symbol: 币种符号
        - df: 15分钟K线数据
        
        返回:
        - dict: 突破信息 {'detected': bool, 'current_volume': float, 'baseline': float, 'ratio': float}
        """
        if df is None or len(df) < 288:  # 需要至少3天的数据 (3*24*4=288个15分钟周期)
            return {'detected': False, 'reason': '数据不足'}
            
        try:
            # 使用缓存的聚合数据
            aggregated_df = self.get_aggregated_data(coin_symbol, df)
            
            if aggregated_df is None or len(aggregated_df) < 2:
                return {'detected': False, 'reason': '聚合后数据不足'}
            
            # 获取最新的K线数据（已聚合）
            current_bar = aggregated_df.iloc[-1]
            current_volume = current_bar['volumn']  # 成交量
            current_quote_volume = current_bar['quote_volumn']  # 成交额（USDT）
            current_time = current_bar['openTime']
            current_price = current_bar['close']
            open_price = current_bar['open']
            
            # 条件b：检查该时间周期内涨幅是否小于10%，且必须是价格上升
            price_change_pct = (current_price - open_price) / open_price
            if price_change_pct >= 0.2:  # 涨幅>=10%，不符合条件
                return {'detected': False, 'reason': f'{self.timeframe_name}涨幅超过10%'}
            
            if price_change_pct <= 0:  # 新增：必须是价格上升
                return {'detected': False, 'reason': f'{self.timeframe_name}价格下降或持平'}
            
            # 条件c：检查盘整阶段（使用原始15分钟数据）
            consolidation_result = self.detect_consolidation_phase(df)
            if not consolidation_result['is_consolidating']:
                return {'detected': False, 'reason': '不在盘整阶段'}
            
            # 条件a：计算过去一周成交额基准（使用聚合后的数据）
            # 获取历史成交额数据（quote_volumn是USDT成交额）
            quote_volumes = aggregated_df['quote_volumn'].values
            
            # 计算成交额基准（过去一周平均）
            baseline_quote_volume = self.calculate_volume_baseline(quote_volumes[:-1], current_time)
            
            if baseline_quote_volume <= 0:
                return {'detected': False, 'reason': '基准成交额为0'}
                
            # 计算成交额倍数
            quote_volume_ratio = current_quote_volume / baseline_quote_volume
            
            # 检查是否达到突破阈值（成交额10倍）
            volume_condition = quote_volume_ratio >= self.volume_multiplier
            price_condition = (price_change_pct > 0) and (price_change_pct < 0.10)  # 价格上升且涨幅<10%
            consolidation_condition = consolidation_result['is_consolidating']
            
            detected = volume_condition and price_condition and consolidation_condition
            
            result = {
                'detected': detected,
                'current_volume': current_volume,
                'current_quote_volume': current_quote_volume,
                'baseline_quote_volume': baseline_quote_volume,
                'quote_volume_ratio': quote_volume_ratio,
                'volume_ratio': quote_volume_ratio,  # 保持兼容性
                'current_price': current_price,
                'open_price': open_price,
                'price_change_pct': price_change_pct,
                'current_time': current_time,
                'timeframe': self.timeframe,
                'timeframe_name': self.timeframe_name,
                'consolidation_info': consolidation_result,
                'reason': f"{self.timeframe_name}成交额{quote_volume_ratio:.1f}倍, 涨幅{price_change_pct*100:.1f}%, {consolidation_result.get('reason', '')}" if detected else "条件不满足"
            }
            
            return result
            
        except Exception as e:
            if self.log_file:
                print_log(f"[breakout_detection_error] {coin_symbol}: {str(e)}", self.log_file)
            return {'detected': False}
    
    def should_alert(self, coin_symbol):
        """
        判断是否应该发送提醒
        避免同一币种在短时间内重复提醒
        """
        current_date = datetime.now().date()
        
        # 每天重置提醒记录
        if self.last_reset_date != current_date:
            self.alerted_coins.clear()
            self.last_reset_date = current_date
            
        return coin_symbol not in self.alerted_coins
    
    def send_alert(self, coin_symbol, breakout_info):
        """
        发送买入提醒
        
        参数:
        - coin_symbol: 币种符号
        - breakout_info: 突破信息
        """
        try:
            volume_ratio = breakout_info['volume_ratio']
            current_price = breakout_info['current_price']
            current_time = breakout_info['current_time']
            
            message = f"🚀 [成交量突破提醒] {coin_symbol}\n"
            message += f"💰 当前价格: {current_price:.6f}\n"
            message += f"📈 成交量倍数: {volume_ratio:.1f}倍\n"
            message += f"⏰ 时间: {current_time}\n"
            message += f"💡 建议: 考虑买入"
            
            # 发送钉钉通知
            sent_msg(message)
            
            # 记录日志
            if self.log_file:
                log_msg = f"[VOLUME_BREAKOUT] {coin_symbol} - 成交量{volume_ratio:.1f}倍突破 - 价格{current_price}"
                print_log(log_msg, self.log_file)
            
            # 标记已提醒
            self.alerted_coins.add(coin_symbol)
            
        except Exception as e:
            if self.log_file:
                print_log(f"[alert_error] {coin_symbol}: {str(e)}", self.log_file)
    
    def scan_all_coins(self):
        """
        扫描所有币种，检测成交量突破
        """
        try:
            # 获取所有数据文件
            pattern = f"{self.data_dir}/*_15m_*.csv"
            files = glob.glob(pattern)
            
            if not files:
                if self.log_file:
                    print_log("[scan_error] 未找到数据文件", self.log_file)
                return
            
            detected_breakouts = []
            
            for file_path in files:
                # 从文件名提取币种符号
                filename = os.path.basename(file_path)
                coin_symbol = filename.split('_')[0]
                
                # 跳过过小的文件(可能是空数据)
                if os.path.getsize(file_path) < 1000:
                    continue
                
                # 加载数据并检测
                df = self.load_coin_data(coin_symbol)
                breakout_info = self.detect_volume_breakout(coin_symbol, df)
                
                if breakout_info['detected']:
                    detected_breakouts.append((coin_symbol, breakout_info))
                    
                    if self.log_file:
                        print_log(f"[detection] {coin_symbol} 成交量突破检测: {breakout_info['volume_ratio']:.1f}倍", self.log_file)
            
            # 按成交量倍数排序，优先提醒最强的突破
            detected_breakouts.sort(key=lambda x: x[1]['volume_ratio'], reverse=True)
            
            # 发送提醒
            alert_count = 0
            for coin_symbol, breakout_info in detected_breakouts:
                if self.should_alert(coin_symbol) and alert_count < 5:  # 限制每次扫描最多提醒5个币种
                    self.send_alert(coin_symbol, breakout_info)
                    alert_count += 1
            
            if self.log_file:
                print_log(f"[scan_complete] 扫描完成，发现{len(detected_breakouts)}个突破，发送{alert_count}个提醒", self.log_file)
                
        except Exception as e:
            if self.log_file:
                print_log(f"[scan_error]: {str(e)}", self.log_file)
    
    def run_single_check(self, coin_symbol):
        """
        对单个币种进行检测
        
        参数:
        - coin_symbol: 币种符号，如'BTCUSDT'
        
        返回:
        - dict: 检测结果
        """
        df = self.load_coin_data(coin_symbol)
        return self.detect_volume_breakout(coin_symbol, df) 
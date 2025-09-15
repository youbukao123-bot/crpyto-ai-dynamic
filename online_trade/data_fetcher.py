"""
在线交易数据拉取器
每小时定时拉取最新的K线数据
"""

import os
import sys
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import pytz
import schedule
from enum import Enum

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.log_utils import print_log
from online_trade.config_loader import get_config
from online_trade.log_manager import get_log_manager

class DataType(Enum):
    SPOT = "spot"

# 时区设置
CHINA_TZ = pytz.timezone('Asia/Shanghai')

# API配置
BINANCE_API_URL = "https://api.binance.com"
REQUEST_TIMEOUT = 30

# 设置pandas选项
pd.set_option('display.float_format', '{:.8f}'.format)

class OnlineDataFetcher:
    """在线数据拉取器"""
    
    def __init__(self, data_dir="../online_data", lookback_days=21):
        """
        初始化数据拉取器
        
        参数:
        - data_dir: 数据存储目录
        - lookback_days: 回看天数，用于初始化和补充数据
        """
        self.data_dir = data_dir
        self.lookback_days = lookback_days
        self.spot_data_dir = os.path.join(data_dir, "spot_klines")
        
        # 确保目录存在
        os.makedirs(self.spot_data_dir, exist_ok=True)
        
        # 初始化数据拉取专用日志管理器
        from online_trade.log_manager import LogManager
        self.logger = LogManager(base_dir="dat_log", enable_console=True)
        self.logger.log_system_start("OnlineDataFetcher", {
            "data_dir": self.data_dir,
            "lookback_days": self.lookback_days
        })
        
        print(f"📂 数据拉取器初始化完成")
        print(f"   数据目录: {self.data_dir}")
        print(f"   现货数据目录: {self.spot_data_dir}")
    
    def format_timestamp(self, date_time):
        """格式化时间戳"""
        return date_time.strftime('%Y-%m-%d_%H_%M')
    
    def parse_time_str(self, time_str):
        """解析时间字符串"""
        return datetime.strptime(time_str, '%Y-%m-%d_%H_%M').replace(tzinfo=CHINA_TZ)
    
    def get_klines_from_api(self, symbol, interval="15m", start_time=None, end_time=None, limit=5000):
        """
        从币安API获取K线数据
        """
        url = f"{BINANCE_API_URL}/api/v3/klines"
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            if isinstance(start_time, datetime):
                start_time = int(start_time.timestamp() * 1000)
            params['startTime'] = start_time
            
        if end_time:
            if isinstance(end_time, datetime):
                end_time = int(end_time.timestamp() * 1000)
            params['endTime'] = end_time
        
        try:
            # 记录API调用
            self.logger.log_api_call("OnlineDataFetcher", f"get_klines/{symbol}", params, success=True)
            
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                self.logger.warning(f"API返回空数据: {symbol}", "OnlineDataFetcher")
                return None
                
            # 转换为DataFrame
            df = pd.DataFrame(data, columns=[
                'openTime', 'open', 'high', 'low', 'close', 'volumn',
                'closeTime', 'quote_volumn', 'count', 'taker_buy_volumn',
                'taker_buy_quote_volumn', 'ignore'
            ])
            
            # 数据类型转换
            df['openTime'] = pd.to_datetime(df['openTime'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volumn', 'quote_volumn']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 记录数据拉取成功
            self.logger.log_data_fetch("OnlineDataFetcher", symbol, interval, len(df), success=True)
            
            return df
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 获取 {symbol} K线数据失败: {error_msg}")
            self.logger.log_api_call("OnlineDataFetcher", f"get_klines/{symbol}", params, success=False, error_msg=error_msg)
            self.logger.log_data_fetch("OnlineDataFetcher", symbol, interval, 0, success=False, error_msg=error_msg)
            return None
    
    def load_existing_data(self, symbol):
        """加载现有的数据文件"""
        file_path = os.path.join(self.spot_data_dir, f"{symbol}_15m.csv")
        
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                df['openTime'] = pd.to_datetime(df['openTime'])
                return df
            except Exception as e:
                print(f"⚠️  加载 {symbol} 现有数据失败: {str(e)}")
                return None
        
        return None
    
    def save_data(self, symbol, df):
        """保存数据到文件"""
        if df is None or len(df) == 0:
            return False
            
        file_path = os.path.join(self.spot_data_dir, f"{symbol}_15m.csv")
        
        try:
            # 按时间排序并去重
            df = df.sort_values('openTime').drop_duplicates(subset=['openTime'], keep='last')
            df.to_csv(file_path, index=False)
            return True
        except Exception as e:
            print(f"❌ 保存 {symbol} 数据失败: {str(e)}")
            return False
    
    def update_symbol_data(self, symbol):
        """更新单个币种的数据"""
        print(f"🔄 更新 {symbol} 数据...")
        
        # 加载现有数据
        existing_df = self.load_existing_data(symbol)
        
        if existing_df is not None and len(existing_df) > 0:
            # 从最后一条数据的时间开始拉取
            last_time = existing_df['openTime'].max()
            start_time = last_time + timedelta(minutes=15)  # 避免重复
        else:
            # 没有现有数据，拉取最近30天的数据
            start_time = datetime.now(CHINA_TZ) - timedelta(days=self.lookback_days)
        
        # 拉取最新数据
        new_df = self.get_klines_from_api(symbol, "15m", start_time=start_time)
        
        if new_df is None or len(new_df) == 0:
            print(f"⚠️  {symbol} 没有新数据")
            return False
        
        # 合并数据
        if existing_df is not None and len(existing_df) > 0:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # 保存数据
        success = self.save_data(symbol, combined_df)
        if success:
            print(f"✅ {symbol} 数据更新成功，共 {len(combined_df)} 条记录")
        
        return success
    
    def load_symbol_list(self):
        """加载币种列表"""
        symbol_file = os.path.join(self.data_dir, "exchange_binance_market.txt")
        
        try:
            with open(symbol_file, 'r', encoding='utf-8') as f:
                symbols = [line.strip() for line in f.readlines() if line.strip()]
            print(f"📋 加载了 {len(symbols)} 个币种")
            return symbols
        except Exception as e:
            print(f"❌ 加载币种列表失败: {str(e)}")
            return []
    
    def fetch_all_data(self):
        """拉取所有币种的数据"""
        print("🚀 开始拉取所有币种数据...")
        
        symbols = self.load_symbol_list()
        if not symbols:
            print("❌ 没有找到币种列表")
            return
        
        success_count = 0
        failed_symbols = []
        
        for i, symbol in enumerate(symbols):
            try:
                success = self.update_symbol_data(symbol)
                if success:
                    success_count += 1
                else:
                    failed_symbols.append(symbol)
                
                # 进度显示
                if (i + 1) % 10 == 0:
                    print(f"📊 进度: {i + 1}/{len(symbols)} ({(i + 1)/len(symbols)*100:.1f}%)")
                
                # API限制，适当延迟
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 处理 {symbol} 时出错: {str(e)}")
                failed_symbols.append(symbol)
        
        print("\n" + "="*60)
        print("🎉 数据拉取完成!")
        print("="*60)
        print(f"📊 统计结果:")
        print(f"   ✅ 成功: {success_count} 个币种")
        print(f"   ❌ 失败: {len(failed_symbols)} 个币种")
        
        if failed_symbols:
            print(f"❌ 失败币种: {', '.join(failed_symbols[:10])}")
            if len(failed_symbols) > 10:
                print(f"   ... 还有 {len(failed_symbols) - 10} 个")
    
    def start_scheduler(self):
        """启动定时任务"""
        self.logger.info("启动数据拉取定时任务", "OnlineDataFetcher")
        print("⏰ 启动数据拉取定时任务...")
        print("📅 调度规则: 每小时执行一次")
        
        # 立即执行一次
        print("🔥 立即执行一次数据拉取...")
        self.logger.info("立即执行数据拉取", "OnlineDataFetcher")
        self.fetch_all_data()
        
        # 设置定时任务：每小时执行一次
        schedule.every().hour.do(self.fetch_all_data)
        
        print("✅ 定时任务已启动，等待执行...")
        self.logger.info("定时任务已启动", "OnlineDataFetcher")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                self.logger.info("数据拉取器停止：用户中断", "OnlineDataFetcher")
                print("\n⏹️  数据拉取器已停止")
                break
            except Exception as e:
                self.logger.error(f"定时任务执行异常: {str(e)}", "OnlineDataFetcher", exc_info=True)
                print(f"❌ 定时任务执行异常: {str(e)}")
                time.sleep(60)  # 等待一分钟后继续


def run_data_fetcher():
    """运行数据拉取器"""
    fetcher = OnlineDataFetcher()
    fetcher.fetch_all_data()


def start_scheduler():
    """启动定时任务"""
    print("⏰ 启动数据拉取定时任务...")
    print("📅 调度规则: 每小时执行一次")
    
    # 立即执行一次
    print("🔥 立即执行一次数据拉取...")
    run_data_fetcher()
    
    # 设置定时任务：每小时执行一次
    schedule.every().hour.do(run_data_fetcher)
    
    print("✅ 定时任务已启动，等待执行...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='在线数据拉取器')
    parser.add_argument('--mode', choices=['once', 'schedule'], 
                        default='once', help='运行模式：once=单次执行，schedule=定时执行')
    
    args = parser.parse_args()
    
    if args.mode == 'schedule':
        start_scheduler()
    else:
        run_data_fetcher()

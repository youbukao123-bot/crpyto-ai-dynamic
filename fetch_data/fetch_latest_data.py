#!/usr/bin/env python3
"""
拉取最新的加密货币数据
"""

import requests
import pytz
import time
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class DataType(Enum):
    SPOT = 'spot' # 现货
    FUTURE = 'future' # 合约
    COINE_FUTURE = 'coin_future' # 币本位合约

BASE_URL_S = 'https://api.binance.com' # 现货
KLINE_URL_S = '/api/v3/klines' # K线数据

BINANCE_SPOT_LIMIT = 500

# 单位 ms
MIN_INTERVAL = 60 * 1000
MIN_15_INTERVAL = 60 * 15 * 1000
HOUR_INTERVAL = MIN_INTERVAL * 60
DAY_INTERVAL = HOUR_INTERVAL * 24

interval_dict = {
    "1m": MIN_INTERVAL,
    "1h": HOUR_INTERVAL, 
    "1d": DAY_INTERVAL,
    "15m": MIN_15_INTERVAL,
}

BINANCE_SPOT_DAT_COL=['openTime', 'open', 'high', 'low', 'close', 'volumn', 'closeTime', 'quote_volumn', 'trades', 'taker_base_volumn', 'taker_quote_volumn', 'ignore']
proxies = None

CHINA_TZ = pytz.timezone("Asia/Shanghai")
pd.set_option('expand_frame_repr', False)
pd.set_option('display.max_rows', 5000)

def format_timestamp(date_time):
    return date_time.strftime('%Y-%m-%d_%H_%M')

def parse_time_str(time_str):
    """解析时间字符串，格式: 2025-08-30_22_42"""
    return datetime.strptime(time_str, '%Y-%m-%d_%H_%M').replace(tzinfo=CHINA_TZ)

def get_klines(data_type, symbol, interval, start_time_str, end_time_str, output_path):
    """
    获取K线数据
    """
    print(f"正在获取 {symbol} {interval} 数据...")
    
    interval_int = interval_dict[interval]
    limit = BINANCE_SPOT_LIMIT
    
    start_time = parse_time_str(start_time_str)
    end_time = parse_time_str(end_time_str)
    
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    total_data = pd.DataFrame()
    
    current_timestamp = start_timestamp
    
    while current_timestamp < end_timestamp:
        next_timestamp = min(current_timestamp + limit * interval_int, end_timestamp)
        
        if data_type == DataType.SPOT:
            url = BASE_URL_S + KLINE_URL_S
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_timestamp,
                'endTime': next_timestamp,
                'limit': limit
            }
        
        try:
            response = requests.get(url, params=params, proxies=proxies, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data, columns=BINANCE_SPOT_DAT_COL)
                    df['openTime'] = pd.to_datetime(df['openTime'], unit='ms')
                    
                    numeric_columns = ['open', 'high', 'low', 'close', 'volumn', 'quote_volumn', 'trades', 'taker_base_volumn', 'taker_quote_volumn']
                    for col in numeric_columns:
                        df[col] = pd.to_numeric(df[col])
                    
                    total_data = pd.concat([total_data, df], ignore_index=True)
                    print(f"  获取了 {len(df)} 条记录, 时间范围: {df['openTime'].iloc[0]} - {df['openTime'].iloc[-1]}")
                else:
                    print(f"  {symbol} 在 {current_timestamp} 时间段没有数据")
            else:
                print(f"  请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"  请求异常: {str(e)}")
            
        current_timestamp = next_timestamp
        time.sleep(0.1)  # 避免频率限制
    
    if not total_data.empty:
        total_data = total_data.drop_duplicates(subset=['openTime'])
        total_data = total_data.sort_values('openTime')
        
        # 确保输出目录存在
        output_dir = f'../data/spot_{output_path}_binance'
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = f'{output_dir}/{symbol}_{interval}_{start_time_str}_{end_time_str}.csv'
        total_data.to_csv(output_file, index=False)
        print(f"✅ {symbol} 数据已保存到 {output_file}, 共 {len(total_data)} 条记录")
    else:
        print(f"❌ {symbol} 没有获取到任何数据")

def get_current_time_range():
    """
    获取当前时间范围（最近5天到现在）
    """
    now = datetime.now(CHINA_TZ)
    start_time = now - timedelta(days=5)  # 最近5天的数据
    
    start_str = format_timestamp(start_time)
    end_str = format_timestamp(now)
    
    return start_str, end_str

def get_latest_batch():
    """
    批量获取最新数据
    """
    print("🚀 开始拉取最新加密货币数据...")
    
    start_str, end_str = get_current_time_range()
    print(f"📅 时间范围: {start_str} 到 {end_str}")
    
    # 从更新后的市值币种库读取
    symbols = []
    market_file = '../data/exchange_binance_market.txt'
    
    try:
        with open(market_file, 'r', encoding='utf-8') as f:
            symbols = [line.strip() for line in f.readlines() if line.strip()]
        print(f"📋 从 {market_file} 读取到 {len(symbols)} 个币种")
    except Exception as e:
        print(f"⚠️  读取币种库失败: {str(e)}，使用默认币种列表")
        # 备用币种列表
        symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT', 
            'SOLUSDT', 'DOTUSDT', 'AVAXUSDT', 'LINKUSDT',
            'UNIUSDT', 'AAVEUSDT', 'COMPUSDT', 'MKRUSDT', 'CRVUSDT',
            'SHIBUSDT', 'VETUSDT', 'FILUSDT', 'FTTUSDT', 'LTCUSDT',
            'ETCUSDT', 'ICPUSDT', 'LUNAUSDT', 'AXSUSDT', 'AUDIOUSDT'
        ]
    
    # 限制数量避免太多请求
    if len(symbols) > 50:
        print(f"⚠️  币种数量较多({len(symbols)})，仅处理前50个以避免API限制")
        symbols = symbols[:50]
    
    success_count = 0
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] 处理 {symbol}...")
        try:
            get_klines(DataType.SPOT, symbol, "15m", start_str, end_str, 'min')
            success_count += 1
        except Exception as e:
            print(f"❌ {symbol} 获取失败: {str(e)}")
        
        # 避免频率限制
        if i % 5 == 0:
            print("⏱️  暂停2秒...")
            time.sleep(2)
    
    print(f"\n🎉 数据拉取完成! 成功获取 {success_count}/{len(symbols)} 个币种的数据")

def main():
    try:
        get_latest_batch()
    except KeyboardInterrupt:
        print("\n⛔ 用户中断了数据拉取")
    except Exception as e:
        print(f"❌ 拉取数据时发生错误: {str(e)}")

if __name__ == '__main__':
    main()

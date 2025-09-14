#!/usr/bin/env python3
"""
批量拉取exchange_binance_market.txt中所有币种最近一个月的15分钟数据
"""

import requests
import pytz
import time
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class DataType(Enum):
    SPOT = 'spot'
    FUTURE = 'future'
    COINE_FUTURE = 'coin_future'

BASE_URL_S = 'https://api.binance.com'
KLINE_URL_S = '/api/v3/klines'

BINANCE_SPOT_LIMIT = 1000  # 增加单次请求限制

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

def get_one_month_time_range():
    """
    获取最近一个月的时间范围
    """
    now = datetime.now(CHINA_TZ)
    start_time = now - timedelta(days=8)  # 最近30天的数据
    
    start_str = format_timestamp(start_time)

    end_time = now - timedelta(days=0)
    end_str = format_timestamp(end_time)
    
    return start_str, end_str

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
    request_count = 0
    
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
            response = requests.get(url, params=params, proxies=proxies, timeout=15)
            request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data, columns=BINANCE_SPOT_DAT_COL)
                    df['openTime'] = pd.to_datetime(df['openTime'], unit='ms')
                    
                    numeric_columns = ['open', 'high', 'low', 'close', 'volumn', 'quote_volumn', 'trades', 'taker_base_volumn', 'taker_quote_volumn']
                    for col in numeric_columns:
                        df[col] = pd.to_numeric(df[col])
                    
                    total_data = pd.concat([total_data, df], ignore_index=True)
                    print(f"  ✓ 获取 {len(df)} 条记录 [{df['openTime'].iloc[0].strftime('%m-%d %H:%M')} - {df['openTime'].iloc[-1].strftime('%m-%d %H:%M')}]")
                else:
                    print(f"  - 时间段无数据")
            elif response.status_code == 429:
                print(f"  ⚠️  API限制，等待60秒...")
                time.sleep(60)
                continue
            else:
                print(f"  ❌ 请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ 请求异常: {str(e)}")
            
        current_timestamp = next_timestamp
        
        # 控制请求频率，避免触发限制
        if request_count % 10 == 0:
            time.sleep(1)  # 每10个请求暂停1秒
        else:
            time.sleep(0.1)  # 每个请求暂停0.1秒
    
    if not total_data.empty:
        total_data = total_data.drop_duplicates(subset=['openTime'])
        total_data = total_data.sort_values('openTime')
        
        # 确保输出目录存在
        output_dir = f'../data/spot_{output_path}_binance'
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = f'{output_dir}/{symbol}_{interval}_{start_time_str}_{end_time_str}.csv'
        total_data.to_csv(output_file, index=False)
        print(f"✅ {symbol} 数据已保存: {len(total_data)} 条记录")
        return True
    else:
        print(f"❌ {symbol} 没有获取到任何数据")
        return False

def load_symbols_from_file():
    """从文件加载币种列表"""
    symbols = []
    market_file = '../data/exchange_binance_market.txt'
    
    try:
        with open(market_file, 'r', encoding='utf-8') as f:
            symbols = [line.strip() for line in f.readlines() if line.strip()]
        print(f"📋 从 {market_file} 读取到 {len(symbols)} 个币种")
    except Exception as e:
        print(f"❌ 读取币种库失败: {str(e)}")
        return []
    
    return symbols

def save_progress(completed_symbols, failed_symbols, progress_file):
    """保存进度到文件"""
    progress_data = {
        'completed': completed_symbols,
        'failed': failed_symbols,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存进度失败: {str(e)}")

def load_progress(progress_file):
    """加载之前的进度"""
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        return progress_data.get('completed', []), progress_data.get('failed', [])
    except:
        return [], []

def get_monthly_batch():
    """
    批量获取最近一个月的数据
    """
    print("🚀 开始批量拉取最近一个月的15分钟数据...")
    
    start_str, end_str = get_one_month_time_range()
    print(f"📅 时间范围: {start_str} 到 {end_str}")
    
    # 加载币种列表
    symbols = load_symbols_from_file()
    if not symbols:
        print("❌ 无法加载币种列表，程序退出")
        return
    
    print(f"📊 总共需要处理 {len(symbols)} 个币种")
    
    # 进度文件
    progress_file = '../data/fetch_progress.json'
    completed_symbols, failed_symbols = load_progress(progress_file)
    
    if completed_symbols:
        print(f"📝 发现之前的进度: 已完成 {len(completed_symbols)} 个，失败 {len(failed_symbols)} 个")
        
        # 过滤掉已完成的币种
        remaining_symbols = [s for s in symbols if s not in completed_symbols]
        symbols = remaining_symbols
        print(f"📋 剩余需要处理: {len(symbols)} 个币种")
    
    success_count = len(completed_symbols)
    fail_count = len(failed_symbols)
    
    print("\n" + "="*80)
    print("开始数据拉取...")
    print("="*80)
    
    for i, symbol in enumerate(symbols, 1):
        total_progress = len(completed_symbols) + i
        print(f"\n[{total_progress}/{len(symbols) + len(completed_symbols)}] 处理 {symbol}...")
        
        try:
            success = get_klines(DataType.SPOT, symbol, "15m", start_str, end_str, 'min')
            
            if success:
                completed_symbols.append(symbol)
                success_count += 1
                print(f"  ✅ 成功")
            else:
                failed_symbols.append(symbol)
                fail_count += 1
                print(f"  ❌ 失败")
                
        except KeyboardInterrupt:
            print(f"\n⛔ 用户中断，保存当前进度...")
            save_progress(completed_symbols, failed_symbols, progress_file)
            print(f"📊 当前进度: 成功 {success_count}, 失败 {fail_count}")
            return
            
        except Exception as e:
            failed_symbols.append(symbol)
            fail_count += 1
            print(f"  ❌ 处理失败: {str(e)}")
        
        # 每处理10个币种保存一次进度
        if i % 10 == 0:
            save_progress(completed_symbols, failed_symbols, progress_file)
            print(f"📝 已保存进度: 成功 {success_count}, 失败 {fail_count}")
        
        # 每处理5个币种暂停一下，避免频率限制
        if i % 5 == 0:
            print("⏱️  暂停3秒...")
            time.sleep(3)
    
    # 保存最终进度
    save_progress(completed_symbols, failed_symbols, progress_file)
    
    print("\n" + "="*80)
    print("🎉 数据拉取完成!")
    print("="*80)
    print(f"📊 最终统计:")
    print(f"   ✅ 成功: {success_count} 个币种")
    print(f"   ❌ 失败: {fail_count} 个币种")
    print(f"   📁 数据保存目录: ../data/spot_min_binance/")
    
    if failed_symbols:
        print(f"\n❌ 失败的币种:")
        for symbol in failed_symbols:
            print(f"   - {symbol}")
        print(f"\n💡 提示: 可以重新运行程序继续处理失败的币种")

def main():
    try:
        print("=" * 80)
        print("🚀        批量数据拉取工具 - 一个月15分钟数据        🚀")
        print("=" * 80)
        print("📋 功能: 拉取exchange_binance_market.txt中所有币种的最近一个月15分钟数据")
        print("📅 时间范围: 最近30天")
        print("⏱️  数据间隔: 15分钟")
        print("=" * 80)
        
        get_monthly_batch()
        
    except KeyboardInterrupt:
        print("\n⛔ 用户中断了数据拉取")
    except Exception as e:
        print(f"❌ 拉取数据时发生错误: {str(e)}")

if __name__ == '__main__':
    main()

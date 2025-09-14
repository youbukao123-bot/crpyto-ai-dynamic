#!/usr/bin/env python3
"""
获取币安现货交易对信息，并筛选市值大于3000万的现货
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime
import os

def get_binance_exchange_info():
    """获取币安现货交易对信息"""
    try:
        print("🔍 获取币安现货交易对信息...")
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            symbols = data['symbols']
            
            # 只筛选USDT交易对且状态为TRADING的现货
            usdt_symbols = []
            for symbol in symbols:
                if (symbol['quoteAsset'] == 'USDT' and 
                    symbol['status'] == 'TRADING' and
                    symbol['isSpotTradingAllowed']):
                    usdt_symbols.append(symbol['symbol'])
            
            print(f"✅ 获取到 {len(usdt_symbols)} 个USDT现货交易对")
            return usdt_symbols
        else:
            print(f"❌ 获取交易对信息失败: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ 获取交易对信息异常: {str(e)}")
        return []

def get_24hr_ticker():
    """获取24小时ticker统计"""
    try:
        print("📊 获取24小时ticker统计...")
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            ticker_dict = {}
            for item in data:
                if item['symbol'].endswith('USDT'):
                    ticker_dict[item['symbol']] = {
                        'price': float(item['lastPrice']),
                        'volume': float(item['volume']),
                        'quoteVolume': float(item['quoteVolume']),
                        'priceChangePercent': float(item['priceChangePercent'])
                    }
            
            print(f"✅ 获取到 {len(ticker_dict)} 个USDT交易对的价格数据")
            return ticker_dict
        else:
            print(f"❌ 获取ticker统计失败: {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"❌ 获取ticker统计异常: {str(e)}")
        return {}

def get_coinmarketcap_data():
    """
    从CoinGecko获取市值数据（免费API）
    注意：这是一个简化版本，实际中可能需要API key
    """
    try:
        print("💰 获取市值数据...")
        
        # 使用CoinGecko的免费API
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 250,
            'page': 1,
            'sparkline': 'false'
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            market_cap_dict = {}
            
            for coin in data:
                symbol = coin['symbol'].upper() + 'USDT'
                market_cap_dict[symbol] = {
                    'market_cap': coin.get('market_cap', 0),
                    'name': coin.get('name', ''),
                    'rank': coin.get('market_cap_rank', 999)
                }
            
            print(f"✅ 获取到 {len(market_cap_dict)} 个币种的市值数据")
            return market_cap_dict
        else:
            print(f"❌ 获取市值数据失败: {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"❌ 获取市值数据异常: {str(e)}")
        return {}

def calculate_market_cap_from_volume(ticker_data):
    """
    基于交易量估算市值（备用方法）
    这是一个粗略的估算，仅作为后备方案
    """
    estimated_caps = {}
    
    # 获取一些已知的大币种作为基准
    btc_volume = ticker_data.get('BTCUSDT', {}).get('quoteVolume', 1000000000)
    
    for symbol, data in ticker_data.items():
        quote_volume = data.get('quoteVolume', 0)
        price = data.get('price', 0)
        
        # 粗略估算：基于交易量相对比例
        if quote_volume > 0 and price > 0:
            # 假设市值与交易量有一定相关性
            estimated_cap = quote_volume * 50  # 简化的估算倍数
            estimated_caps[symbol] = max(estimated_cap, quote_volume)
    
    return estimated_caps

def filter_by_market_cap(symbols_data, min_market_cap=30000000):
    """
    根据市值筛选币种
    min_market_cap: 最小市值（默认3000万美元）
    """
    filtered_symbols = []
    
    for symbol, data in symbols_data.items():
        market_cap = data.get('market_cap', 0)
        if market_cap >= min_market_cap:
            filtered_symbols.append({
                'symbol': symbol,
                'market_cap': market_cap,
                'name': data.get('name', ''),
                'rank': data.get('rank', 999),
                'price': data.get('price', 0),
                'volume_24h': data.get('quoteVolume', 0),
                'price_change_24h': data.get('priceChangePercent', 0)
            })
    
    # 按市值排序
    filtered_symbols.sort(key=lambda x: x['market_cap'], reverse=True)
    return filtered_symbols

def save_symbols_to_file(symbols_data, filename):
    """保存符合条件的币种到文件"""
    try:
        # 确保目录存在
        data_dir = "../data"
        os.makedirs(data_dir, exist_ok=True)
        
        filepath = os.path.join(data_dir, filename)
        
        # 保存为简单的symbol列表
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in symbols_data:
                f.write(f"{item['symbol']}\n")
        
        print(f"✅ 币种列表已保存到: {filepath}")
        
        # 同时保存详细信息到CSV
        csv_filename = filename.replace('.txt', '_details.csv')
        csv_filepath = os.path.join(data_dir, csv_filename)
        
        df = pd.DataFrame(symbols_data)
        df['market_cap_millions'] = df['market_cap'] / 1000000  # 转换为百万美元
        df = df[['symbol', 'name', 'rank', 'market_cap_millions', 'price', 'volume_24h', 'price_change_24h']]
        df.to_csv(csv_filepath, index=False)
        
        print(f"✅ 详细信息已保存到: {csv_filepath}")
        
    except Exception as e:
        print(f"❌ 保存文件失败: {str(e)}")

def main():
    print("=" * 60)
    print("🚀    币安现货信息更新工具    🚀")
    print("=" * 60)
    print("📋 功能: 获取市值≥3000万美元的币安现货")
    print("=" * 60)
    
    # 1. 获取币安交易对信息
    binance_symbols = get_binance_exchange_info()
    if not binance_symbols:
        print("❌ 无法获取币安交易对信息，程序退出")
        return
    
    # 2. 获取价格和交易量数据
    ticker_data = get_24hr_ticker()
    if not ticker_data:
        print("❌ 无法获取价格数据，程序退出")
        return
    
    # 3. 获取市值数据
    market_cap_data = get_coinmarketcap_data()
    
    # 4. 合并数据
    combined_data = {}
    for symbol in binance_symbols:
        if symbol in ticker_data:
            combined_data[symbol] = ticker_data[symbol].copy()
            
            # 添加市值信息
            if symbol in market_cap_data:
                combined_data[symbol].update(market_cap_data[symbol])
            else:
                # 如果没有市值数据，使用交易量估算
                estimated_caps = calculate_market_cap_from_volume({symbol: ticker_data[symbol]})
                combined_data[symbol]['market_cap'] = estimated_caps.get(symbol, 0)
                combined_data[symbol]['name'] = symbol.replace('USDT', '')
                combined_data[symbol]['rank'] = 999
    
    print(f"\n📊 数据统计:")
    print(f"   币安USDT交易对: {len(binance_symbols)}")
    print(f"   有价格数据: {len(ticker_data)}")
    print(f"   有市值数据: {len(market_cap_data)}")
    print(f"   合并后数据: {len(combined_data)}")
    
    # 5. 按市值筛选
    min_market_cap = 30000000  # 3000万美元
    filtered_symbols = filter_by_market_cap(combined_data, min_market_cap)
    
    print(f"\n🎯 筛选结果:")
    print(f"   市值≥{min_market_cap/1000000:.0f}M美元的币种: {len(filtered_symbols)}")
    
    # 6. 显示前20个
    print(f"\n📈 市值前20名:")
    print("-" * 80)
    print(f"{'排名':<4} {'币种':<12} {'名称':<15} {'市值(M)':<10} {'价格':<10} {'24h涨跌':<8}")
    print("-" * 80)
    
    for i, item in enumerate(filtered_symbols[:20], 1):
        market_cap_m = item['market_cap'] / 1000000
        print(f"{i:<4} {item['symbol']:<12} {item['name']:<15} ${market_cap_m:<9.0f} ${item['price']:<9.4f} {item['price_change_24h']:>+6.2f}%")
    
    if len(filtered_symbols) > 20:
        print(f"... 还有 {len(filtered_symbols) - 20} 个币种")
    
    # 7. 保存到文件
    current_time = datetime.now().strftime("%Y%m%d")
    filename = f"exchange_binance_market_cap_{current_time}.txt"
    save_symbols_to_file(filtered_symbols, filename)
    
    # 8. 同时更新通用文件
    save_symbols_to_file(filtered_symbols, "exchange_binance_market.txt")
    
    print(f"\n🎉 处理完成！共筛选出 {len(filtered_symbols)} 个符合条件的现货交易对")

if __name__ == '__main__':
    main()

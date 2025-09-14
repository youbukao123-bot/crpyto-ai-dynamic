#!/usr/bin/env python3
"""
成交量突破监控运行脚本
支持实时监控和单次扫描两种模式
"""

import os
import sys
import time
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from monitor.volume_breakout_strategy import VolumeBreakoutMonitor
from utils.log_utils import print_log

def create_log_file():
    """创建日志文件"""
    log_dir = "crypto/data/log"
    os.makedirs(log_dir, exist_ok=True)
    
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{log_dir}/volume_monitor_{current_time}.log"
    
    return open(log_filename, 'a', encoding='utf-8')

def run_single_scan(data_dir, volume_multiplier, lookback_days):
    """运行单次扫描"""
    log_file = create_log_file()
    
    try:
        print_log(f"[开始] 成交量突破监控 - 单次扫描模式", log_file)
        print_log(f"[参数] 数据目录: {data_dir}", log_file)
        print_log(f"[参数] 成交量倍数阈值: {volume_multiplier}", log_file)
        print_log(f"[参数] 回看天数: {lookback_days}", log_file)
        
        # 创建监控器
        monitor = VolumeBreakoutMonitor(
            data_dir=data_dir,
            volume_multiplier=volume_multiplier,
            lookback_days=lookback_days,
            log_file=log_file
        )
        
        # 执行扫描
        monitor.scan_all_coins()
        
        print_log(f"[完成] 单次扫描完成", log_file)
        print("扫描完成，请查看日志文件和钉钉通知")
        
    except Exception as e:
        print_log(f"[错误] 扫描过程中发生错误: {str(e)}", log_file)
        print(f"扫描过程中发生错误: {str(e)}")
    finally:
        log_file.close()

def run_continuous_monitor(data_dir, volume_multiplier, lookback_days, interval_minutes):
    """运行连续监控模式"""
    log_file = create_log_file()
    
    try:
        print_log(f"[开始] 成交量突破监控 - 连续监控模式", log_file)
        print_log(f"[参数] 数据目录: {data_dir}", log_file)
        print_log(f"[参数] 成交量倍数阈值: {volume_multiplier}", log_file)
        print_log(f"[参数] 回看天数: {lookback_days}", log_file)
        print_log(f"[参数] 扫描间隔: {interval_minutes}分钟", log_file)
        
        # 创建监控器
        monitor = VolumeBreakoutMonitor(
            data_dir=data_dir,
            volume_multiplier=volume_multiplier,
            lookback_days=lookback_days,
            log_file=log_file
        )
        
        print(f"开始连续监控，每{interval_minutes}分钟扫描一次...")
        print("按 Ctrl+C 停止监控")
        
        scan_count = 0
        while True:
            try:
                scan_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print_log(f"[第{scan_count}次扫描] 开始时间: {current_time}", log_file)
                print(f"[{current_time}] 开始第{scan_count}次扫描...")
                
                # 执行扫描
                monitor.scan_all_coins()
                
                # 等待下次扫描
                print(f"等待{interval_minutes}分钟后进行下次扫描...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print_log(f"[停止] 用户手动停止监控", log_file)
                print("\n监控已停止")
                break
            except Exception as e:
                print_log(f"[错误] 扫描过程中发生错误: {str(e)}", log_file)
                print(f"扫描过程中发生错误: {str(e)}")
                print(f"等待{interval_minutes}分钟后重试...")
                time.sleep(interval_minutes * 60)
                
    except Exception as e:
        print_log(f"[错误] 监控程序发生严重错误: {str(e)}", log_file)
        print(f"监控程序发生严重错误: {str(e)}")
    finally:
        log_file.close()

def run_single_coin_check(data_dir, coin_symbol, volume_multiplier, lookback_days):
    """检查单个币种"""
    log_file = create_log_file()
    
    try:
        print_log(f"[开始] 单币种检测: {coin_symbol}", log_file)
        
        # 创建监控器
        monitor = VolumeBreakoutMonitor(
            data_dir=data_dir,
            volume_multiplier=volume_multiplier,
            lookback_days=lookback_days,
            log_file=log_file
        )
        
        # 检测单个币种
        result = monitor.run_single_check(coin_symbol)
        
        if result['detected']:
            print(f"✅ {coin_symbol} 检测到成交量突破!")
            print(f"   成交量倍数: {result['volume_ratio']:.1f}倍")
            print(f"   当前价格: {result['current_price']}")
            print(f"   当前成交量: {result['current_volume']}")
            print(f"   基准成交量: {result['baseline_volume']}")
            
            # 发送提醒
            if monitor.should_alert(coin_symbol):
                monitor.send_alert(coin_symbol, result)
                print(f"   已发送提醒通知")
        else:
            print(f"❌ {coin_symbol} 未检测到成交量突破")
            
    except Exception as e:
        print_log(f"[错误] 单币种检测错误: {str(e)}", log_file)
        print(f"检测过程中发生错误: {str(e)}")
    finally:
        log_file.close()

def main():
    parser = argparse.ArgumentParser(description='成交量突破监控策略')
    parser.add_argument('--mode', choices=['scan', 'monitor', 'single'], default='scan',
                        help='运行模式: scan(单次扫描), monitor(连续监控), single(单币种检测)')
    parser.add_argument('--data-dir', default='crypto/data/spot_min_binance',
                        help='数据文件目录 (默认: crypto/data/spot_min_binance)')
    parser.add_argument('--volume-multiplier', type=float, default=10.0,
                        help='成交量突破倍数阈值 (默认: 10)')
    parser.add_argument('--lookback-days', type=int, default=7,
                        help='历史数据回看天数 (默认: 7)')
    parser.add_argument('--interval', type=int, default=15,
                        help='连续监控模式下的扫描间隔(分钟) (默认: 15)')
    parser.add_argument('--coin', type=str,
                        help='单币种检测模式下的币种符号 (如: BTCUSDT)')
    
    args = parser.parse_args()
    
    # 检查数据目录
    if not os.path.exists(args.data_dir):
        print(f"错误: 数据目录不存在: {args.data_dir}")
        return
    
    print("=" * 60)
    print("      成交量突破监控策略")
    print("=" * 60)
    print(f"运行模式: {args.mode}")
    print(f"数据目录: {args.data_dir}")
    print(f"成交量倍数阈值: {args.volume_multiplier}")
    print(f"回看天数: {args.lookback_days}")
    if args.mode == 'monitor':
        print(f"扫描间隔: {args.interval}分钟")
    if args.mode == 'single':
        print(f"目标币种: {args.coin}")
    print("=" * 60)
    
    # 根据模式运行
    if args.mode == 'scan':
        run_single_scan(args.data_dir, args.volume_multiplier, args.lookback_days)
    elif args.mode == 'monitor':
        run_continuous_monitor(args.data_dir, args.volume_multiplier, args.lookback_days, args.interval)
    elif args.mode == 'single':
        if not args.coin:
            print("错误: 单币种检测模式需要指定 --coin 参数")
            return
        run_single_coin_check(args.data_dir, args.coin, args.volume_multiplier, args.lookback_days)

if __name__ == '__main__':
    main() 
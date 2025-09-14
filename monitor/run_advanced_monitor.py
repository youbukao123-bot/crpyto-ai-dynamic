#!/usr/bin/env python3
"""
高级动量策略监控运行脚本
包含多种牛市动量策略
"""

import os
import sys
import time
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from monitor.advanced_momentum_strategy import AdvancedMomentumMonitor
from utils.log_utils import print_log

def create_log_file():
    """创建日志文件"""
    log_dir = "crypto/data/log"
    os.makedirs(log_dir, exist_ok=True)
    
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{log_dir}/advanced_momentum_{current_time}.log"
    
    return open(log_filename, 'a', encoding='utf-8')

def run_single_scan(data_dir):
    """运行单次扫描"""
    log_file = create_log_file()
    
    try:
        print_log(f"[开始] 高级动量策略监控 - 单次扫描模式", log_file)
        print_log(f"[参数] 数据目录: {data_dir}", log_file)
        
        # 创建监控器
        monitor = AdvancedMomentumMonitor(data_dir=data_dir, log_file=log_file)
        
        # 获取市场概况
        market_overview = monitor.get_market_overview()
        if market_overview:
            print_log(f"[市场概况] BTC价格: {market_overview['btc_price']:.2f}, "
                     f"24h涨幅: {market_overview['btc_1d_change']:.2f}%, "
                     f"市场状态: {market_overview['market_state']}", log_file)
            
            print(f"📊 市场概况:")
            print(f"   BTC价格: ${market_overview['btc_price']:.2f}")
            print(f"   24小时涨幅: {market_overview['btc_1d_change']:+.2f}%")
            print(f"   3天涨幅: {market_overview['btc_3d_change']:+.2f}%")
            print(f"   成交量比率: {market_overview['volume_ratio']:.2f}")
            print(f"   市场状态: {market_overview['market_state']}")
            print("-" * 50)
        
        # 执行扫描
        signals = monitor.scan_all_strategies()
        
        # 显示结果
        if signals:
            print(f"🎯 发现 {len(signals)} 个动量信号:")
            for i, signal in enumerate(signals[:10], 1):  # 显示前10个
                print(f"{i}. {signal['type']} - {signal['coin']}")
                print(f"   💰 价格: {signal['price']:.6f}")
                print(f"   ⭐ 强度: {signal['strength']:.1f}")
                print(f"   📝 {signal['details']}")
                print()
        else:
            print("❌ 未发现符合条件的动量信号")
        
        print_log(f"[完成] 单次扫描完成，发现{len(signals)}个信号", log_file)
        print("扫描完成，请查看日志文件和钉钉通知")
        
    except Exception as e:
        print_log(f"[错误] 扫描过程中发生错误: {str(e)}", log_file)
        print(f"扫描过程中发生错误: {str(e)}")
    finally:
        log_file.close()

def run_continuous_monitor(data_dir, interval_minutes):
    """运行连续监控模式"""
    log_file = create_log_file()
    
    try:
        print_log(f"[开始] 高级动量策略监控 - 连续监控模式", log_file)
        print_log(f"[参数] 数据目录: {data_dir}", log_file)
        print_log(f"[参数] 扫描间隔: {interval_minutes}分钟", log_file)
        
        # 创建监控器
        monitor = AdvancedMomentumMonitor(data_dir=data_dir, log_file=log_file)
        
        print(f"🚀 开始高级动量策略监控")
        print(f"⏰ 每{interval_minutes}分钟扫描一次")
        print("按 Ctrl+C 停止监控")
        print("=" * 60)
        
        scan_count = 0
        while True:
            try:
                scan_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print_log(f"[第{scan_count}次扫描] 开始时间: {current_time}", log_file)
                print(f"\n[{current_time}] 第{scan_count}次扫描...")
                
                # 获取市场概况
                market_overview = monitor.get_market_overview()
                if market_overview:
                    print(f"📊 BTC: ${market_overview['btc_price']:.0f} "
                          f"({market_overview['btc_1d_change']:+.1f}%) "
                          f"- {market_overview['market_state']}")
                
                # 执行扫描
                signals = monitor.scan_all_strategies()
                
                if signals:
                    print(f"✅ 发现 {len(signals)} 个信号，已发送通知")
                else:
                    print("⭕ 未发现信号")
                
                # 等待下次扫描
                print(f"💤 等待{interval_minutes}分钟...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print_log(f"[停止] 用户手动停止监控", log_file)
                print("\n🛑 监控已停止")
                break
            except Exception as e:
                print_log(f"[错误] 扫描过程中发生错误: {str(e)}", log_file)
                print(f"❌ 扫描错误: {str(e)}")
                print(f"💤 等待{interval_minutes}分钟后重试...")
                time.sleep(interval_minutes * 60)
                
    except Exception as e:
        print_log(f"[错误] 监控程序发生严重错误: {str(e)}", log_file)
        print(f"❌ 严重错误: {str(e)}")
    finally:
        log_file.close()

def analyze_signals(data_dir):
    """分析历史信号质量"""
    log_file = create_log_file()
    
    try:
        print("🔍 分析历史信号质量...")
        
        monitor = AdvancedMomentumMonitor(data_dir=data_dir, log_file=log_file)
        monitor.load_all_data()
        
        # 统计各策略信号数量
        strategy_stats = {
            '成交量突破': 0,
            '多时间框架共振': 0,
            '突破回踩': 0,
            '板块轮动': 0
        }
        
        total_coins = len(monitor.price_data)
        print(f"📊 分析了 {total_coins} 个币种")
        print("-" * 50)
        
        # 分析每个币种
        for coin_symbol in monitor.price_data.keys():
            if coin_symbol == 'BTCUSDT':
                continue
                
            # 检测各种信号
            volume_signal = monitor.detect_volume_breakout(coin_symbol)
            if volume_signal:
                strategy_stats['成交量突破'] += 1
                
            momentum_signal = monitor.detect_multi_timeframe_momentum(coin_symbol)
            if momentum_signal:
                strategy_stats['多时间框架共振'] += 1
                
            pullback_signal = monitor.detect_pullback_opportunity(coin_symbol)
            if pullback_signal:
                strategy_stats['突破回踩'] += 1
        
        # 板块轮动
        sector_signals = monitor.detect_sector_rotation()
        strategy_stats['板块轮动'] = len(sector_signals)
        
        # 显示统计结果
        print("📈 策略信号统计:")
        for strategy, count in strategy_stats.items():
            percentage = (count / total_coins) * 100 if total_coins > 0 else 0
            print(f"   {strategy}: {count} 个信号 ({percentage:.1f}%)")
        
        total_signals = sum(strategy_stats.values())
        print(f"\n🎯 总计: {total_signals} 个信号")
        
        # 市场分析
        market_overview = monitor.get_market_overview()
        if market_overview:
            print(f"\n📊 市场状态: {market_overview['market_state']}")
            if market_overview['market_state'] in ['强势上涨', '温和上涨']:
                print("💡 建议: 当前市场环境适合动量策略")
            else:
                print("⚠️  建议: 当前市场环境需谨慎操作")
        
    except Exception as e:
        print(f"分析过程中发生错误: {str(e)}")
    finally:
        log_file.close()

def main():
    parser = argparse.ArgumentParser(description='高级动量策略监控系统')
    parser.add_argument('--mode', choices=['scan', 'monitor', 'analyze'], default='scan',
                        help='运行模式: scan(单次扫描), monitor(连续监控), analyze(信号分析)')
    parser.add_argument('--data-dir', default='crypto/data/spot_min_binance',
                        help='数据文件目录 (默认: crypto/data/spot_min_binance)')
    parser.add_argument('--interval', type=int, default=15,
                        help='连续监控模式下的扫描间隔(分钟) (默认: 15)')
    
    args = parser.parse_args()
    
    # 检查数据目录
    if not os.path.exists(args.data_dir):
        print(f"❌ 错误: 数据目录不存在: {args.data_dir}")
        return
    
    print("=" * 60)
    print("🚀     高级动量策略监控系统     🚀")
    print("=" * 60)
    print("📋 包含策略:")
    print("   1. 成交量突破策略")
    print("   2. 多时间框架共振策略")
    print("   3. 相对强度策略")
    print("   4. 突破回踩策略")
    print("   5. 板块轮动策略")
    print("=" * 60)
    print(f"🔧 运行模式: {args.mode}")
    print(f"📁 数据目录: {args.data_dir}")
    if args.mode == 'monitor':
        print(f"⏰ 扫描间隔: {args.interval}分钟")
    print("=" * 60)
    
    # 根据模式运行
    if args.mode == 'scan':
        run_single_scan(args.data_dir)
    elif args.mode == 'monitor':
        run_continuous_monitor(args.data_dir, args.interval)
    elif args.mode == 'analyze':
        analyze_signals(args.data_dir)

if __name__ == '__main__':
    main() 
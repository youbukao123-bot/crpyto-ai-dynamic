"""
在线交易系统启动脚本
整合数据拉取器和交易引擎
"""

import os
import sys
import time
import threading
import argparse
from datetime import datetime
import pytz

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from online_trade.data_fetcher import OnlineDataFetcher
from online_trade.online_strategy_engine import OnlineStrategyEngine
from online_trade.config_loader import get_config
from online_trade.log_manager import init_log_manager

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class OnlineTradingSystem:
    """在线交易系统管理器"""
    
    def __init__(self, config_override=None, dingtalk_webhook=None):
        """
        初始化在线交易系统
        
        参数:
        - config_override: 配置覆盖字典（可选）
        - dingtalk_webhook: 钉钉Webhook地址（可选）
        """
        # 获取配置
        self.config = get_config()
        
        # 应用配置覆盖
        if config_override:
            for section, values in config_override.items():
                if hasattr(self.config, '_config') and section in self.config._config:
                    self.config._config[section].update(values)
        
        # 初始化日志管理器
        self.logger = init_log_manager(base_dir=".", enable_console=True)
        self.logger.log_system_start("OnlineTradingSystem", {
            "config_override": config_override,
            "dingtalk_enabled": dingtalk_webhook is not None
        })
        
        # 初始化组件
        self.data_fetcher = OnlineDataFetcher()
        self.strategy_engine = OnlineStrategyEngine(config_override=config_override, dingtalk_webhook=dingtalk_webhook)
        self.dingtalk_webhook = dingtalk_webhook
        
        # 运行状态
        self.running = False
        self.data_thread = None
        self.strategy_thread = None
        
        print(f"🚀 在线交易系统初始化完成")
        print(f"   初始资金: ${self.config.initial_capital:,}")
        print(f"   买入策略: {self.config.buy_strategy}")
        print(f"   滑点限制: {self.config.slippage_limit:.3%}")
        print(f"   交易周期: {self.config.trade_cycle_hours}小时")
    
    def start_data_fetcher(self):
        """启动数据拉取器线程"""
        def run_data_fetcher():
            try:
                print("📊 数据拉取器线程启动...")
                self.data_fetcher.start_scheduler()
            except Exception as e:
                print(f"❌ 数据拉取器线程异常: {str(e)}")
        
        self.data_thread = threading.Thread(target=run_data_fetcher, daemon=True)
        self.data_thread.start()
        print("✅ 数据拉取器已启动")
    
    def start_strategy_engine(self):
        """启动策略引擎线程"""
        def run_strategy_engine():
            try:
                print("⚡ 策略引擎线程启动...")
                # 等待数据拉取器先运行一会儿
                time.sleep(30)
                self.strategy_engine.start_trading()
            except Exception as e:
                print(f"❌ 策略引擎线程异常: {str(e)}")
        
        self.strategy_thread = threading.Thread(target=run_strategy_engine, daemon=True)
        self.strategy_thread.start()
        print("✅ 策略引擎已启动")
    
    def start_system(self):
        """启动完整系统"""
        print("🚀 启动在线交易系统...")
        print(f"⏰ 启动时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        
        self.running = True
        
        try:
            # 1. 先启动数据拉取器
            print("📊 第一步: 启动数据拉取器...")
            self.start_data_fetcher()
            
            # 2. 等待一段时间让数据拉取器初始化
            print("⏳ 等待数据拉取器初始化...")
            time.sleep(60)
            
            # 3. 启动策略引擎
            print("⚡ 第二步: 启动策略引擎...")
            self.start_strategy_engine()
            
            print("✅ 系统启动完成！")
            print("-" * 60)
            print("🔧 系统组件状态:")
            print("   📊 数据拉取器: 每小时自动拉取最新数据")
            print("   ⚡ 策略引擎: 每4小时检测信号并执行交易")
            print("   🛡️  风险管理: 每30分钟检查止盈止损")
            print("-" * 60)
            
            # 主循环：监控系统状态
            while self.running:
                try:
                    # 检查线程状态
                    if self.data_thread and not self.data_thread.is_alive():
                        print("❌ 数据拉取器线程异常退出，尝试重启...")
                        self.start_data_fetcher()
                    
                    if self.strategy_thread and not self.strategy_thread.is_alive():
                        print("❌ 策略引擎线程异常退出，尝试重启...")
                        self.start_strategy_engine()
                    
                    # 定期打印系统状态
                    current_time = datetime.now(BEIJING_TZ)
                    if current_time.minute == 0:  # 每小时打印一次状态
                        self.print_system_status()
                    
                    time.sleep(60)  # 每分钟检查一次
                    
                except KeyboardInterrupt:
                    print("\n🛑 收到停止信号...")
                    self.stop_system()
                    break
                except Exception as e:
                    print(f"❌ 系统监控异常: {str(e)}")
                    time.sleep(60)
        
        except Exception as e:
            print(f"❌ 系统启动失败: {str(e)}")
            self.stop_system()
    
    def stop_system(self):
        """停止系统"""
        print("🛑 正在停止在线交易系统...")
        self.running = False
        
        print("✅ 系统已停止")
    
    def print_system_status(self):
        """打印系统状态"""
        current_time = datetime.now(BEIJING_TZ)
        print(f"\n📊 系统状态报告 - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        # 数据拉取器状态
        data_status = "运行中" if self.data_thread and self.data_thread.is_alive() else "异常"
        print(f"📊 数据拉取器: {data_status}")
        
        # 策略引擎状态
        strategy_status = "运行中" if self.strategy_thread and self.strategy_thread.is_alive() else "异常"
        print(f"⚡ 策略引擎: {strategy_status}")
        
        # 投资组合状态
        try:
            summary = self.strategy_engine.trader.get_portfolio_summary()
            print(f"💰 投资组合:")
            print(f"   总价值: ${summary['total_value']:.2f}")
            print(f"   持仓数: {summary['position_count']}")
            print(f"   仓位暴露: {summary['exposure']:.1%}")
        except:
            print(f"💰 投资组合: 无法获取状态")
        
        print("-" * 50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='在线交易系统启动器')
    parser.add_argument('--capital', type=float, default=1000, help='初始资金（USDT）')
    parser.add_argument('--buy-strategy', choices=['close', 'golden_ratio'], 
                        default='golden_ratio', help='买入策略')
    parser.add_argument('--slippage-limit', type=float, default=0.001, 
                        help='滑点限制（默认0.1%）')
    parser.add_argument('--data-only', action='store_true', help='仅启动数据拉取器')
    parser.add_argument('--strategy-only', action='store_true', help='仅启动策略引擎')
    parser.add_argument('--dingtalk-webhook', type=str, 
                        default='https://oapi.dingtalk.com/robot/send?access_token=562f41c37f10bc9d77fb0e3535c1cc778e7666ad9c1173fffcf9fb8a939118a7',
                        help='钉钉机器人Webhook地址')
    parser.add_argument('--disable-dingtalk', action='store_true', help='禁用钉钉通知')
    parser.add_argument('--enable-real-trading', action='store_true', help='启用真实交易（默认为模拟模式）')
    
    args = parser.parse_args()
    
    # 确定钉钉通知设置
    dingtalk_webhook = None if args.disable_dingtalk else args.dingtalk_webhook
    
    # 确定交易模式
    trading_mode = "真实交易" if args.enable_real_trading else "模拟交易"
    mode_emoji = "💰" if args.enable_real_trading else "🎮"
    
    print("🌟 欢迎使用在线交易系统!")
    print("="*60)
    print("⚡ 功能特性:")
    print("   📊 自动数据拉取 (每小时)")
    print("   🎯 成交量突破策略 (4小时周期)")
    print("   🛡️  智能风险管理 (止盈止损)")
    print("   💎 黄金分割点买入")
    print(f"   {mode_emoji} 交易模式: {trading_mode}")
    print(f"   🔔 钉钉通知: {'✅ 已启用' if dingtalk_webhook else '❌ 已禁用'}")
    print("="*60)
    
    if args.data_only:
        # 仅启动数据拉取器
        print("📊 启动模式: 仅数据拉取器")
        fetcher = OnlineDataFetcher()
        fetcher.start_scheduler()
    
    elif args.strategy_only:
        # 仅启动策略引擎
        print("⚡ 启动模式: 仅策略引擎")
        config_override = {
            'trading': {
                'initial_capital': args.capital,
                'buy_strategy': args.buy_strategy,
                'enable_real_trading': args.enable_real_trading
            }
        }
        engine = OnlineStrategyEngine(config_override=config_override, dingtalk_webhook=dingtalk_webhook)
        engine.start_trading()
    
    else:
        # 启动完整系统
        print("🚀 启动模式: 完整系统")
        config_override = {
            'trading': {
                'initial_capital': args.capital,
                'buy_strategy': args.buy_strategy,
                'slippage_limit': args.slippage_limit,
                'enable_real_trading': args.enable_real_trading
            }
        }
        system = OnlineTradingSystem(config_override=config_override, dingtalk_webhook=dingtalk_webhook)
        system.start_system()


if __name__ == '__main__':
    main()

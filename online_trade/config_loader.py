"""
配置加载器
统一管理所有系统参数
"""

import json
import os
from typing import Dict, Any

class TradingConfig:
    """交易配置管理器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        
        参数:
        - config_path: 配置文件路径，默认为 ../online_data/config/config.json
        """
        if config_path is None:
            config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../online_data/config/config.json'))
        
        self.config_path = config_path
        self._config = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            print(f"✅ 配置文件加载成功: {self.config_path}")
        except Exception as e:
            print(f"❌ 加载配置文件失败: {str(e)}")
            raise
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置文件保存成功: {self.config_path}")
        except Exception as e:
            print(f"❌ 保存配置文件失败: {str(e)}")
            raise
    
    def get(self, section: str, key: str = None, default=None):
        """
        获取配置值
        
        参数:
        - section: 配置段名 (api, trading, strategy, system, backtest, time_exit)
        - key: 配置键名，如果为None则返回整个段
        - default: 默认值
        """
        try:
            section_config = self._config.get(section, {})
            if key is None:
                return section_config
            return section_config.get(key, default)
        except Exception:
            return default
    
    def set(self, section: str, key: str, value: Any):
        """
        设置配置值
        
        参数:
        - section: 配置段名
        - key: 配置键名
        - value: 配置值
        """
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
    
    def update_section(self, section: str, updates: Dict[str, Any]):
        """
        批量更新配置段
        
        参数:
        - section: 配置段名
        - updates: 更新的键值对
        """
        if section not in self._config:
            self._config[section] = {}
        self._config[section].update(updates)
    
    # API配置属性
    @property
    def api_key(self) -> str:
        return self.get('api', 'api_key', '')
    
    @property
    def api_secret(self) -> str:
        return self.get('api', 'api_secret', '')
    
    @property
    def base_url(self) -> str:
        return self.get('api', 'base_url', 'https://api.binance.com')
    
    @property
    def proxy_host(self) -> str:
        return self.get('api', 'proxy_host')
    
    @property
    def proxy_port(self) -> int:
        return self.get('api', 'proxy_port', 0)
    
    @property
    def timeout(self) -> int:
        return self.get('api', 'timeout', 5)
    
    # 交易配置属性
    @property
    def enable_real_trading(self) -> bool:
        return self.get('trading', 'enable_real_trading', False)
    
    @property
    def initial_capital(self) -> float:
        return self.get('trading', 'initial_capital', 1000)
    
    @property
    def max_position_pct(self) -> float:
        return self.get('trading', 'max_position_pct', 0.15)
    
    @property
    def max_total_exposure(self) -> float:
        return self.get('trading', 'max_total_exposure', 0.80)
    
    @property
    def stop_loss_pct(self) -> float:
        return self.get('trading', 'stop_loss_pct', -0.08)
    
    @property
    def take_profit_pct(self) -> float:
        return self.get('trading', 'take_profit_pct', 0.15)
    
    @property
    def max_profit_pct(self) -> float:
        return self.get('trading', 'max_profit_pct', 0.80)
    
    @property
    def trailing_stop_activation(self) -> float:
        return self.get('trading', 'trailing_stop_activation', 0.20)
    
    @property
    def trailing_stop_ratio(self) -> float:
        return self.get('trading', 'trailing_stop_ratio', 0.15)
    
    @property
    def buy_strategy(self) -> str:
        return self.get('trading', 'buy_strategy', 'golden_ratio')
    
    @property
    def golden_ratio(self) -> float:
        return self.get('trading', 'golden_ratio', 0.618)
    
    @property
    def use_limit_order(self) -> bool:
        return self.get('trading', 'use_limit_order', True)
    
    @property
    def slippage_limit(self) -> float:
        return self.get('trading', 'slippage_limit', 0.001)
    
    @property
    def min_investment_amount(self) -> float:
        return self.get('trading', 'min_investment_amount', 10.0)
    
    # 策略配置属性
    @property
    def volume_multiplier(self) -> float:
        return self.get('strategy', 'volume_multiplier', 5.0)
    
    @property
    def timeframe(self) -> str:
        return self.get('strategy', 'timeframe', '4h')
    
    @property
    def price_change_max(self) -> float:
        return self.get('strategy', 'price_change_max', 0.20)
    
    @property
    def consolidation_min_days(self) -> int:
        return self.get('strategy', 'consolidation_min_days', 3)
    
    @property
    def signal_strength_base(self) -> float:
        return self.get('strategy', 'signal_strength_base', 5.0)
    
    # 系统配置属性
    @property
    def data_dir(self) -> str:
        return self.get('system', 'data_dir', '../online_data/spot_klines')
    
    @property
    def market_file(self) -> str:
        return self.get('system', 'market_file', '../online_data/exchange_binance_market.txt')
    
    @property
    def interval(self) -> str:
        return self.get('system', 'interval', '15m')
    
    @property
    def trade_cycle_hours(self) -> int:
        return self.get('system', 'trade_cycle_hours', 4)
    
    @property
    def risk_check_interval_minutes(self) -> int:
        return self.get('system', 'risk_check_interval_minutes', 30)
    
    # 时间退出配置属性
    @property
    def enable_time_exit(self) -> bool:
        return self.get('time_exit', 'enable_time_exit', True)
    
    @property
    def quick_profit_hours(self) -> int:
        return self.get('time_exit', 'quick_profit_hours', 72)
    
    @property
    def quick_profit_threshold(self) -> float:
        return self.get('time_exit', 'quick_profit_threshold', 0.10)
    
    @property
    def profit_taking_hours(self) -> int:
        return self.get('time_exit', 'profit_taking_hours', 168)
    
    @property
    def profit_taking_threshold(self) -> float:
        return self.get('time_exit', 'profit_taking_threshold', 0.03)
    
    @property
    def stop_loss_hours(self) -> int:
        return self.get('time_exit', 'stop_loss_hours', 240)
    
    @property
    def stop_loss_threshold(self) -> float:
        return self.get('time_exit', 'stop_loss_threshold', -0.03)
    
    @property
    def forced_close_hours(self) -> int:
        return self.get('time_exit', 'forced_close_hours', 336)
    
    def print_config_summary(self):
        """打印配置摘要"""
        print("📋 交易系统配置摘要")
        print("=" * 50)
        
        print("🔑 API配置:")
        print(f"   基础URL: {self.base_url}")
        print(f"   API密钥: {self.api_key[:8]}...{self.api_key[-8:] if len(self.api_key) > 16 else '***'}")
        print(f"   超时设置: {self.timeout}秒")
        
        print("\n💰 交易配置:")
        print(f"   真实交易: {'✅ 启用' if self.enable_real_trading else '❌ 模拟模式'}")
        print(f"   初始资金: ${self.initial_capital:,}")
        print(f"   单仓位上限: {self.max_position_pct:.1%}")
        print(f"   总仓位上限: {self.max_total_exposure:.1%}")
        print(f"   止损比例: {self.stop_loss_pct:.1%}")
        print(f"   止盈比例: {self.take_profit_pct:.1%}")
        print(f"   最大止盈: {self.max_profit_pct:.1%}")
        print(f"   买入策略: {self.buy_strategy}")
        print(f"   滑点限制: {self.slippage_limit:.3%}")
        
        print("\n📊 策略配置:")
        print(f"   成交量倍数: {self.volume_multiplier}x")
        print(f"   时间框架: {self.timeframe}")
        print(f"   最大涨幅: {self.price_change_max:.1%}")
        print(f"   盘整最小天数: {self.consolidation_min_days}天")
        
        print("\n⚙️  系统配置:")
        print(f"   数据目录: {self.data_dir}")
        print(f"   交易周期: {self.trade_cycle_hours}小时")
        print(f"   风险检查: {self.risk_check_interval_minutes}分钟")
        
        print("\n⏰ 时间退出:")
        print(f"   启用状态: {'✅' if self.enable_time_exit else '❌'}")
        print(f"   快速止盈: {self.quick_profit_hours}小时 / {self.quick_profit_threshold:.1%}")
        print(f"   强制平仓: {self.forced_close_hours}小时")

# 全局配置实例
_global_config = None

def get_config() -> TradingConfig:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = TradingConfig()
    return _global_config

def reload_config():
    """重新加载配置"""
    global _global_config
    _global_config = None
    return get_config()

if __name__ == '__main__':
    # 测试配置加载器
    config = TradingConfig()
    config.print_config_summary()

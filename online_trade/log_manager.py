"""
日志管理器模块
支持操作日志和系统日志的分天存储
"""

import logging
import os
from datetime import datetime
import pytz
from typing import Optional, Dict, Any
import json
from pathlib import Path

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class LogManager:
    """日志管理器"""
    
    def __init__(self, base_dir: str = ".", enable_console: bool = True):
        """
        初始化日志管理器
        
        Args:
            base_dir: 基础目录路径
            enable_console: 是否启用控制台输出
        """
        self.base_dir = Path(base_dir)
        self.enable_console = enable_console
        
        # 创建日志目录
        self.operation_log_dir = self.base_dir / "ope_log"
        self.system_log_dir = self.base_dir / "log"
        
        self.operation_log_dir.mkdir(exist_ok=True)
        self.system_log_dir.mkdir(exist_ok=True)
        
        # 日志器字典
        self.loggers: Dict[str, logging.Logger] = {}
        
        # 初始化日志器
        self._setup_loggers()
        
        print(f"📝 日志管理器初始化完成")
        print(f"   操作日志目录: {self.operation_log_dir}")
        print(f"   系统日志目录: {self.system_log_dir}")
        print(f"   控制台输出: {'✅ 启用' if enable_console else '❌ 禁用'}")
    
    def _setup_loggers(self):
        """设置日志器"""
        # 操作日志器
        self.operation_logger = self._create_logger(
            name="operation",
            log_dir=self.operation_log_dir,
            format_str="%(asctime)s [%(levelname)s] %(message)s",
            level=logging.INFO
        )
        
        # 系统日志器
        self.system_logger = self._create_logger(
            name="system", 
            log_dir=self.system_log_dir,
            format_str="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            level=logging.DEBUG
        )
        
        self.loggers["operation"] = self.operation_logger
        self.loggers["system"] = self.system_logger
    
    def _create_logger(self, name: str, log_dir: Path, format_str: str, level: int) -> logging.Logger:
        """创建日志器"""
        logger = logging.getLogger(f"trading_{name}")
        logger.setLevel(level)
        
        # 清除已有的处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 文件处理器（按日期分文件）
        today = datetime.now(BEIJING_TZ).strftime('%Y%m%d')
        log_file = log_dir / f"{name}_{today}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        
        # 格式器
        formatter = logging.Formatter(
            format_str,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 控制台处理器（可选）
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                f"[{name.upper()}] %(asctime)s %(levelname)s: %(message)s",
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # 防止日志向上传播
        logger.propagate = False
        
        return logger
    
    def _get_beijing_time(self) -> str:
        """获取北京时间字符串"""
        return datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    def log_operation(self, operation_type: str, symbol: str = "", details: Dict[str, Any] = None, **kwargs):
        """
        记录操作日志
        
        Args:
            operation_type: 操作类型 (开仓/平仓/挂单/撤单等)
            symbol: 交易对
            details: 操作详情
            **kwargs: 其他参数
        """
        if details is None:
            details = {}
        
        # 合并kwargs到details
        details.update(kwargs)
        
        # 构建日志消息
        log_data = {
            "time": self._get_beijing_time(),
            "operation": operation_type,
            "symbol": symbol,
            "details": details
        }
        
        # 格式化消息
        msg_parts = [f"操作类型: {operation_type}"]
        if symbol:
            msg_parts.append(f"交易对: {symbol}")
        
        for key, value in details.items():
            if key not in ['time', 'operation', 'symbol']:
                msg_parts.append(f"{key}: {value}")
        
        message = " | ".join(msg_parts)
        
        # 记录到操作日志
        self.operation_logger.info(message)
        
        # 同时记录结构化数据（JSON格式）
        json_message = json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))
        self.operation_logger.debug(f"JSON: {json_message}")
    
    def log_position_open(self, symbol: str, entry_price: float, quantity: float, 
                         cost: float, strategy: str, reason: str = "", is_simulation: bool = False):
        """记录开仓操作"""
        self.log_operation(
            operation_type="开仓",
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            cost=cost,
            strategy=strategy,
            reason=reason,
            trading_mode="模拟" if is_simulation else "真实"
        )
    
    def log_position_close(self, symbol: str, exit_price: float, quantity: float,
                          revenue: float, pnl: float, pnl_pct: float, reason: str = "", 
                          is_simulation: bool = False):
        """记录平仓操作"""
        self.log_operation(
            operation_type="平仓",
            symbol=symbol,
            exit_price=exit_price,
            quantity=quantity,
            revenue=revenue,
            pnl=pnl,
            pnl_pct=f"{pnl_pct:.2f}%",
            reason=reason,
            trading_mode="模拟" if is_simulation else "真实"
        )
    
    def log_order_placed(self, symbol: str, order_type: str, side: str, price: float, 
                        quantity: float, order_id: str = "", is_simulation: bool = False):
        """记录挂单操作"""
        self.log_operation(
            operation_type="挂单",
            symbol=symbol,
            order_type=order_type,
            side=side,
            price=price,
            quantity=quantity,
            order_id=order_id,
            trading_mode="模拟" if is_simulation else "真实"
        )
    
    def log_order_filled(self, symbol: str, order_id: str, filled_price: float, 
                        filled_quantity: float, is_simulation: bool = False):
        """记录订单成交"""
        self.log_operation(
            operation_type="订单成交",
            symbol=symbol,
            order_id=order_id,
            filled_price=filled_price,
            filled_quantity=filled_quantity,
            trading_mode="模拟" if is_simulation else "真实"
        )
    
    def log_order_cancelled(self, symbol: str, order_id: str, reason: str = "", 
                           is_simulation: bool = False):
        """记录撤单操作"""
        self.log_operation(
            operation_type="撤单",
            symbol=symbol,
            order_id=order_id,
            reason=reason,
            trading_mode="模拟" if is_simulation else "真实"
        )
    
    def log_risk_action(self, symbol: str, action: str, trigger_price: float, 
                       current_price: float, reason: str = ""):
        """记录风控操作"""
        self.log_operation(
            operation_type="风控操作",
            symbol=symbol,
            action=action,
            trigger_price=trigger_price,
            current_price=current_price,
            reason=reason
        )
    
    def log_balance_change(self, old_balance: float, new_balance: float, 
                          change_amount: float, reason: str = "", is_simulation: bool = False):
        """记录余额变动"""
        self.log_operation(
            operation_type="余额变动",
            old_balance=old_balance,
            new_balance=new_balance,
            change_amount=change_amount,
            reason=reason,
            trading_mode="模拟" if is_simulation else "真实"
        )
    
    # 系统日志方法
    def debug(self, message: str, component: str = "system"):
        """调试日志"""
        logger = self.loggers.get("system", self.system_logger)
        logger.debug(f"[{component}] {message}")
    
    def info(self, message: str, component: str = "system"):
        """信息日志"""
        logger = self.loggers.get("system", self.system_logger)
        logger.info(f"[{component}] {message}")
    
    def warning(self, message: str, component: str = "system"):
        """警告日志"""
        logger = self.loggers.get("system", self.system_logger)
        logger.warning(f"[{component}] {message}")
    
    def error(self, message: str, component: str = "system", exc_info: bool = False):
        """错误日志"""
        logger = self.loggers.get("system", self.system_logger)
        logger.error(f"[{component}] {message}", exc_info=exc_info)
    
    def critical(self, message: str, component: str = "system", exc_info: bool = False):
        """严重错误日志"""
        logger = self.loggers.get("system", self.system_logger)
        logger.critical(f"[{component}] {message}", exc_info=exc_info)
    
    def log_system_start(self, component: str, config: Dict[str, Any] = None):
        """记录系统启动"""
        self.info(f"{component} 系统启动", component)
        if config:
            self.debug(f"{component} 配置: {json.dumps(config, ensure_ascii=False, indent=2)}", component)
    
    def log_system_stop(self, component: str, reason: str = ""):
        """记录系统停止"""
        self.info(f"{component} 系统停止: {reason}", component)
    
    def log_api_call(self, component: str, api_name: str, params: Dict[str, Any] = None, 
                    success: bool = True, error_msg: str = ""):
        """记录API调用"""
        if success:
            self.debug(f"API调用成功: {api_name}", component)
            if params:
                self.debug(f"API参数: {json.dumps(params, ensure_ascii=False)}", component)
        else:
            self.error(f"API调用失败: {api_name} - {error_msg}", component)
    
    def log_data_fetch(self, component: str, symbol: str, timeframe: str, 
                      records_count: int, success: bool = True, error_msg: str = ""):
        """记录数据拉取"""
        if success:
            self.info(f"数据拉取成功: {symbol} {timeframe} ({records_count}条)", component)
        else:
            self.error(f"数据拉取失败: {symbol} {timeframe} - {error_msg}", component)
    
    def log_signal_detected(self, component: str, symbol: str, signal_type: str, 
                           signal_strength: float, details: Dict[str, Any] = None):
        """记录信号检测"""
        msg = f"信号检测: {symbol} {signal_type} 强度:{signal_strength:.3f}"
        self.info(msg, component)
        if details:
            self.debug(f"信号详情: {json.dumps(details, ensure_ascii=False)}", component)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        stats = {
            "operation_log_dir": str(self.operation_log_dir),
            "system_log_dir": str(self.system_log_dir),
            "operation_files": [],
            "system_files": []
        }
        
        # 操作日志文件
        if self.operation_log_dir.exists():
            stats["operation_files"] = [f.name for f in self.operation_log_dir.glob("*.log")]
        
        # 系统日志文件  
        if self.system_log_dir.exists():
            stats["system_files"] = [f.name for f in self.system_log_dir.glob("*.log")]
        
        return stats
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """清理旧日志文件"""
        import glob
        from datetime import timedelta
        
        cutoff_date = datetime.now(BEIJING_TZ) - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime('%Y%m%d')
        
        cleaned_count = 0
        
        # 清理操作日志
        for log_file in self.operation_log_dir.glob("operation_*.log"):
            try:
                date_part = log_file.stem.split('_')[-1]  # 获取日期部分
                if date_part < cutoff_str:
                    log_file.unlink()
                    cleaned_count += 1
                    self.info(f"清理旧操作日志: {log_file.name}")
            except (ValueError, IndexError):
                continue
        
        # 清理系统日志
        for log_file in self.system_log_dir.glob("system_*.log"):
            try:
                date_part = log_file.stem.split('_')[-1]  # 获取日期部分
                if date_part < cutoff_str:
                    log_file.unlink()
                    cleaned_count += 1
                    self.info(f"清理旧系统日志: {log_file.name}")
            except (ValueError, IndexError):
                continue
        
        if cleaned_count > 0:
            self.info(f"日志清理完成，共清理 {cleaned_count} 个文件")
        
        return cleaned_count


# 全局日志管理器实例
_global_log_manager: Optional[LogManager] = None

def get_log_manager() -> LogManager:
    """获取全局日志管理器实例"""
    global _global_log_manager
    if _global_log_manager is None:
        _global_log_manager = LogManager()
    return _global_log_manager

def init_log_manager(base_dir: str = ".", enable_console: bool = True) -> LogManager:
    """初始化全局日志管理器"""
    global _global_log_manager
    _global_log_manager = LogManager(base_dir=base_dir, enable_console=enable_console)
    return _global_log_manager

# 便捷函数
def log_operation(*args, **kwargs):
    """记录操作日志的便捷函数"""
    return get_log_manager().log_operation(*args, **kwargs)

def log_info(message: str, component: str = "system"):
    """记录信息日志的便捷函数"""
    return get_log_manager().info(message, component)

def log_warning(message: str, component: str = "system"):
    """记录警告日志的便捷函数"""
    return get_log_manager().warning(message, component)

def log_error(message: str, component: str = "system", exc_info: bool = False):
    """记录错误日志的便捷函数"""
    return get_log_manager().error(message, component, exc_info)

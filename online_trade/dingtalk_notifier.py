"""
钉钉通知器
用于发送交易相关的通知到钉钉群
"""

import json
import requests
from datetime import datetime
import pytz
from typing import Dict, Any, Optional

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class DingTalkNotifier:
    """钉钉通知器"""
    
    def __init__(self, webhook_url: str, keywords: list = None):
        """
        初始化钉钉通知器
        
        参数:
        - webhook_url: 钉钉机器人Webhook地址
        - keywords: 关键词列表，用于满足钉钉机器人的关键词限制
        """
        self.webhook_url = webhook_url
        self.keywords = keywords or ["Code"]  # 默认关键词
        self.headers = {
            'Content-Type': 'application/json'
        }
        
        print(f"🔔 钉钉通知器初始化完成")
        print(f"   Webhook URL: {webhook_url[:50]}...")
        print(f"   关键词: {', '.join(self.keywords)}")
    
    def _add_keywords(self, content: str) -> str:
        """在内容中添加关键词以满足钉钉机器人要求"""
        # 检查是否已包含任何关键词
        for keyword in self.keywords:
            if keyword in content:
                return content  # 已包含关键词，直接返回
        
        # 如果没有包含任何关键词，添加第一个关键词
        return f"[{self.keywords[0]}] {content}"
    
    def send_message(self, message: str, title: str = "交易通知") -> bool:
        """
        发送文本消息到钉钉
        
        参数:
        - message: 消息内容
        - title: 消息标题
        
        返回: 是否发送成功
        """
        try:
            # 添加关键词并构建消息体
            full_message = f"【{title}】\n{message}"
            full_message = self._add_keywords(full_message)
            
            data = {
                "msgtype": "text",
                "text": {
                    "content": full_message
                }
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                headers=self.headers,
                data=json.dumps(data),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print(f"✅ 钉钉通知发送成功")
                    return True
                else:
                    print(f"❌ 钉钉通知发送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                print(f"❌ 钉钉通知发送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 发送钉钉通知异常: {str(e)}")
            return False
    
    def send_markdown(self, markdown_text: str, title: str = "交易通知") -> bool:
        """
        发送Markdown消息到钉钉
        
        参数:
        - markdown_text: Markdown格式的消息内容
        - title: 消息标题
        
        返回: 是否发送成功
        """
        try:
            # 添加关键词并构建消息体
            markdown_text = self._add_keywords(markdown_text)
            
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": markdown_text
                }
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                headers=self.headers,
                data=json.dumps(data),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print(f"✅ 钉钉Markdown通知发送成功")
                    return True
                else:
                    print(f"❌ 钉钉Markdown通知发送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                print(f"❌ 钉钉Markdown通知发送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 发送钉钉Markdown通知异常: {str(e)}")
            return False
    
    def notify_position_opened(self, symbol: str, entry_price: float, quantity: float, 
                             cost: float, strategy_type: str, signal_strength: float,
                             reason: str = "", is_simulation: bool = False) -> bool:
        """
        发送开仓通知
        
        参数:
        - symbol: 交易对
        - entry_price: 开仓价格
        - quantity: 开仓数量
        - cost: 开仓成本
        - strategy_type: 策略类型
        - signal_strength: 信号强度
        - reason: 开仓理由
        """
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        mode_emoji = "🎮" if is_simulation else "💰"
        mode_text = "模拟" if is_simulation else "真实"
        
        markdown_text = f"""# {mode_emoji} 开仓通知

**交易模式**: {mode_text}交易
**交易对**: {symbol}
**开仓时间**: {current_time}
**开仓价格**: ${entry_price:.6f}
**开仓数量**: {quantity:.6f}
**投资金额**: ${cost:.2f}
**策略类型**: {strategy_type}
**信号强度**: {signal_strength:.1f}

**开仓理由**: {reason if reason else '成交量突破信号'}

---
*系统自动通知*"""
        
        return self.send_markdown(markdown_text, "开仓通知")
    
    def notify_position_closed(self, symbol: str, exit_price: float, quantity: float,
                              revenue: float, cost: float, pnl: float, pnl_pct: float,
                              reason: str, holding_hours: float = 0, is_simulation: bool = False) -> bool:
        """
        发送平仓通知
        
        参数:
        - symbol: 交易对
        - exit_price: 平仓价格
        - quantity: 平仓数量
        - revenue: 平仓收入
        - cost: 原始成本
        - pnl: 盈亏金额
        - pnl_pct: 盈亏百分比
        - reason: 平仓原因
        - holding_hours: 持仓时长（小时）
        """
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 根据盈亏设置不同的emoji
        if pnl > 0:
            status_emoji = "🎉"
            pnl_color = "green"
        else:
            status_emoji = "😢"
            pnl_color = "red"
        
        mode_prefix = "🎮" if is_simulation else "💰"
        mode_text = "模拟" if is_simulation else "真实"
        
        markdown_text = f"""# {mode_prefix}{status_emoji} 平仓通知

**交易模式**: {mode_text}交易
**交易对**: {symbol}
**平仓时间**: {current_time}
**平仓价格**: ${exit_price:.6f}
**平仓数量**: {quantity:.6f}
**平仓收入**: ${revenue:.2f}
**原始成本**: ${cost:.2f}
**盈亏金额**: <font color="{pnl_color}">${pnl:+.2f}</font>
**盈亏比例**: <font color="{pnl_color}">{pnl_pct:+.2%}</font>
**持仓时长**: {holding_hours:.1f}小时

**平仓原因**: {reason}

---
*系统自动通知*"""
        
        return self.send_markdown(markdown_text, "平仓通知")
    
    def notify_order_placed(self, symbol: str, order_type: str, price: float, 
                           quantity: float, amount: float, reason: str = "") -> bool:
        """
        发送挂单通知
        
        参数:
        - symbol: 交易对
        - order_type: 订单类型（如："黄金分割点挂单"）
        - price: 挂单价格
        - quantity: 挂单数量
        - amount: 挂单金额
        - reason: 挂单理由
        """
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        markdown_text = f"""# 📋 挂单通知

**交易对**: {symbol}
**挂单时间**: {current_time}
**订单类型**: {order_type}
**挂单价格**: ${price:.6f}
**挂单数量**: {quantity:.6f}
**挂单金额**: ${amount:.2f}

**挂单理由**: {reason if reason else '黄金分割点策略'}

---
*系统自动通知*"""
        
        return self.send_markdown(markdown_text, "挂单通知")
    
    def notify_order_filled(self, symbol: str, order_type: str, fill_price: float,
                           quantity: float, amount: float) -> bool:
        """
        发送挂单成交通知
        
        参数:
        - symbol: 交易对
        - order_type: 订单类型
        - fill_price: 成交价格
        - quantity: 成交数量
        - amount: 成交金额
        """
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        markdown_text = f"""# ✅ 挂单成交通知

**交易对**: {symbol}
**成交时间**: {current_time}
**订单类型**: {order_type}
**成交价格**: ${fill_price:.6f}
**成交数量**: {quantity:.6f}
**成交金额**: ${amount:.2f}

**状态**: 挂单已成交，已自动创建持仓

---
*系统自动通知*"""
        
        return self.send_markdown(markdown_text, "挂单成交通知")
    
    def notify_order_cancelled(self, symbol: str, order_type: str, reason: str) -> bool:
        """
        发送挂单取消通知
        
        参数:
        - symbol: 交易对
        - order_type: 订单类型
        - reason: 取消原因
        """
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        markdown_text = f"""# 🚫 挂单取消通知

**交易对**: {symbol}
**取消时间**: {current_time}
**订单类型**: {order_type}
**取消原因**: {reason}

---
*系统自动通知*"""
        
        return self.send_markdown(markdown_text, "挂单取消通知")
    
    def notify_risk_alert(self, message: str, alert_level: str = "WARNING") -> bool:
        """
        发送风险警报通知
        
        参数:
        - message: 警报消息
        - alert_level: 警报级别（INFO, WARNING, ERROR）
        """
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 根据警报级别设置emoji
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "🚨"
        }
        emoji = emoji_map.get(alert_level, "⚠️")
        
        markdown_text = f"""# {emoji} 风险警报

**警报时间**: {current_time}
**警报级别**: {alert_level}
**警报内容**: {message}

---
*系统自动通知*"""
        
        return self.send_markdown(markdown_text, "风险警报")
    
    def notify_system_status(self, status: str, message: str) -> bool:
        """
        发送系统状态通知
        
        参数:
        - status: 系统状态（启动、停止、错误等）
        - message: 状态消息
        """
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 根据状态设置emoji
        emoji_map = {
            "启动": "🚀",
            "停止": "🛑",
            "错误": "❌",
            "恢复": "✅"
        }
        emoji = emoji_map.get(status, "🔔")
        
        markdown_text = f"""# {emoji} 系统状态通知

**时间**: {current_time}
**状态**: {status}
**详情**: {message}

---
*系统自动通知*"""
        
        return self.send_markdown(markdown_text, "系统状态")
    
    def notify_portfolio_summary(self, summary: Dict[str, Any]) -> bool:
        """
        发送投资组合摘要通知
        
        参数:
        - summary: 投资组合摘要数据
        """
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        markdown_text = f"""# 📊 投资组合摘要

**统计时间**: {current_time}
**USDT余额**: ${summary.get('usdt_balance', 0):.2f}
**持仓价值**: ${summary.get('position_value', 0):.2f}
**总资产**: ${summary.get('total_value', 0):.2f}
**持仓数量**: {summary.get('position_count', 0)}个
**挂单数量**: {summary.get('pending_count', 0)}个
**仓位占比**: {summary.get('exposure', 0):.1%}

---
*系统自动通知*"""
        
        return self.send_markdown(markdown_text, "投资组合摘要")


# 全局通知器实例
_global_notifier = None

def get_notifier(webhook_url: str = None, keywords: list = None) -> Optional[DingTalkNotifier]:
    """获取全局通知器实例"""
    global _global_notifier
    
    if webhook_url:
        _global_notifier = DingTalkNotifier(webhook_url, keywords)
    
    return _global_notifier

def init_notifier(webhook_url: str, keywords: list = None) -> DingTalkNotifier:
    """初始化全局通知器"""
    return get_notifier(webhook_url, keywords)


if __name__ == '__main__':
    # 测试钉钉通知器
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=0ade599901a68fe52c268fcb3172513714e26ef8bbd11db70ba1d78a5afea1ec"
    notifier = DingTalkNotifier(webhook_url)
    
    # 测试发送消息
    notifier.send_message("这是一条测试消息", "测试通知")
    
    # 测试发送开仓通知
    notifier.notify_position_opened(
        symbol="BTCUSDT",
        entry_price=65432.10,
        quantity=0.001523,
        cost=99.65,
        strategy_type="volume_breakout",
        signal_strength=7.5,
        reason="成交量突破，信号强度较高"
    )

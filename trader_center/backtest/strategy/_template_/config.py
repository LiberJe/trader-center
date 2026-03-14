"""
策略配置

定义策略参数和回测配置
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class TemplateConfig:
    """策略配置类

    Attributes:
        param1: 参数1说明（默认10）
        param2: 参数2说明（默认0.5）
        initial_cash: 初始资金（默认100000）
        commission: 佣金费率（默认万2.5）
        stake: 每次交易股数（默认100）
    """

    # 策略参数
    param1: int = 10
    param2: float = 0.5

    # 回测参数
    initial_cash: float = 100000.0
    commission: float = 0.00025  # 万2.5
    stake: int = 100  # 每次交易股数

    def to_params(self) -> Dict[str, Any]:
        """转换为 backtrader params 格式"""
        return {
            'param1': self.param1,
            'param2': self.param2,
        }

    def to_cerebro_config(self) -> Dict[str, Any]:
        """转换为 Cerebro 配置"""
        return {
            'cash': self.initial_cash,
            'commission': self.commission,
        }


# 默认配置
DEFAULT_CONFIG = TemplateConfig()

# 优化参数范围（用于参数优化）
PARAM_RANGES = {
    'param1': range(5, 50, 5),
    'param2': [0.1, 0.2, 0.3, 0.5, 0.8],
}

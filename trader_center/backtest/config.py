"""
回测配置

管理回测的默认参数和配置选项。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class BacktestConfig:
    """
    回测配置

    Attributes:
        initial_cash: 初始资金（默认10万）
        commission_rate: 佣金率（默认万2.5）
        stamp_duty_rate: 印花税率（默认千1）
        min_commission: 最低佣金（默认5元）
        limit_up_pct: 涨停幅度（默认10%）
        limit_down_pct: 跌停幅度（默认10%）
        max_workers: 并行进程数（默认None=CPU核心数）
        output_dir: 结果输出目录
    """

    # 资金配置
    initial_cash: float = 100000.0

    # 手续费配置
    commission_rate: float = 0.00025  # 万2.5
    stamp_duty_rate: float = 0.001     # 千1
    min_commission: float = 5.0        # 最低5元

    # 交易限制
    limit_up_pct: float = 0.10    # 涨停10%
    limit_down_pct: float = 0.10  # 跌停10%

    # 执行配置
    max_workers: Optional[int] = None

    # 输出配置
    output_dir: Path = field(default_factory=lambda: Path.home() / ".trader_center" / "backtest_results")

    def __post_init__(self):
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            'initial_cash': self.initial_cash,
            'commission_rate': self.commission_rate,
            'stamp_duty_rate': self.stamp_duty_rate,
            'min_commission': self.min_commission,
            'limit_up_pct': self.limit_up_pct,
            'limit_down_pct': self.limit_down_pct,
            'max_workers': self.max_workers,
            'output_dir': str(self.output_dir),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'BacktestConfig':
        """从字典创建配置"""
        config = cls(**d)
        if 'output_dir' in d:
            config.output_dir = Path(d['output_dir'])
        return config

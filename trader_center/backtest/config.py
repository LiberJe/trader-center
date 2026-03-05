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
        auto_save_trades: 是否自动保存交易日志
        trade_log_format: 交易日志格式（csv/json）
        auto_save_plot: 是否自动保存图表（启用可视化时）
    """

    initial_cash: float = 100000.0

    commission_rate: float = 0.00025
    stamp_duty_rate: float = 0.001
    min_commission: float = 5.0

    limit_up_pct: float = 0.10
    limit_down_pct: float = 0.10

    max_workers: Optional[int] = None

    output_dir: Path = field(default_factory=lambda: Path.cwd() / "logs" / "backtest_results")

    trade_log_dir: Path = field(default_factory=lambda: Path.cwd() / "logs" / "backtest")
    auto_save_trades: bool = True
    trade_log_format: str = "csv"
    auto_save_plot: bool = True

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trade_log_dir.mkdir(parents=True, exist_ok=True)

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
            'trade_log_dir': str(self.trade_log_dir),
            'auto_save_trades': self.auto_save_trades,
            'trade_log_format': self.trade_log_format,
            'auto_save_plot': self.auto_save_plot,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'BacktestConfig':
        """从字典创建配置"""
        if 'output_dir' in d:
            d['output_dir'] = Path(d['output_dir'])
        if 'trade_log_dir' in d:
            d['trade_log_dir'] = Path(d['trade_log_dir'])
        d.pop('plot_output_dir', None)
        return cls(**d)

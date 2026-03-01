# trader_center/backtest/result.py
"""Backtest result encapsulation."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd


@dataclass
class BacktestResult:
    """回测结果封装类.

    Attributes:
        start_date: 回测开始日期
        end_date: 回测结束日期
        duration: 回测持续时间
        metrics: 绩效指标字典
        trades: 交易记录 DataFrame
        daily_values: 每日资金曲线
        positions: 每日持仓 DataFrame
    """
    start_date: datetime
    end_date: datetime
    duration: timedelta
    metrics: Dict[str, float]
    trades: pd.DataFrame
    daily_values: pd.DataFrame
    positions: pd.DataFrame

    def report(self) -> str:
        """生成文字报告."""
        lines = [
            "=" * 50,
            "Backtest Report",
            "=" * 50,
            f"Period: {self.start_date.date()} to {self.end_date.date()}",
            f"Duration: {self.duration.days} days",
            "-" * 50,
            "Performance Metrics:",
            f"  Total Return:      {self.metrics.get('total_return_pct', 0):.2f}%",
            f"  CAGR:              {self.metrics.get('cagr_pct', 0):.2f}%",
            f"  Max Drawdown:      {self.metrics.get('max_drawdown_pct', 0):.2f}%",
            f"  Sharpe Ratio:      {self.metrics.get('sharpe_ratio', 0):.2f}",
            f"  Volatility:        {self.metrics.get('volatility_pct', 0):.2f}%",
            f"  Calmar Ratio:      {self.metrics.get('calmar_ratio', 0):.2f}",
            "-" * 50,
            f"Total Trades: {len(self.trades)}",
            "=" * 50,
        ]
        return "\n".join(lines)

    def save_trades(self, path: str) -> None:
        """保存交易记录到 CSV."""
        self.trades.to_csv(path, index=False)

    def save(self, path_prefix: str) -> None:
        """保存所有结果.

        Args:
            path_prefix: 文件路径前缀，如 "results/backtest_001"
                      会生成 backtest_001_trades.csv, backtest_001_daily.csv 等
        """
        import os
        base = path_prefix.replace('.csv', '').replace('.json', '')

        self.trades.to_csv(f"{base}_trades.csv", index=False)
        self.daily_values.to_csv(f"{base}_daily.csv", index=True)
        self.positions.to_csv(f"{base}_positions.csv", index=True)

        # 保存指标为 JSON
        import json
        with open(f"{base}_metrics.json", 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def plot(self, path: Optional[str] = None) -> None:
        """生成回测图表.

        Args:
            path: 图表保存路径，若为 None 则显示图表
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for plotting")

        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                  gridspec_kw={'height_ratios': [3, 1]})

        # 资金曲线
        ax1 = axes[0]
        ax1.plot(self.daily_values.index, self.daily_values['value'], label='Portfolio Value')
        ax1.set_ylabel('Value')
        ax1.set_title('Backtest Result')
        ax1.legend()
        ax1.grid(True)

        # 每日收益
        ax2 = axes[1]
        returns = self.daily_values['value'].pct_change() * 100
        ax2.bar(self.daily_values.index, returns, label='Daily Return %', alpha=0.6)
        ax2.set_ylabel('Return %')
        ax2.set_xlabel('Date')
        ax2.legend()
        ax2.grid(True)

        plt.tight_layout()

        if path:
            plt.savefig(path)
        else:
            plt.show()

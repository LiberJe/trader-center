"""
回测结果封装

定义回测结果的数据结构和绩效指标计算。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Optional, Any
import pandas as pd


@dataclass
class BacktestResult:
    """
    回测结果

    包含回测的所有输出数据和绩效指标。

    Attributes:
        strategy_name: 策略名称
        initial_cash: 初始资金
        final_value: 最终资产价值
        trades: 交易记录列表
        daily_values: 每日资产价值序列
        start_date: 回测开始日期
        end_date: 回测结束日期
        logs: 日志记录
        params: 策略参数
    """

    strategy_name: str
    initial_cash: float
    final_value: float
    start_date: date
    end_date: date

    trades: List[Dict[str, Any]] = field(default_factory=list)
    daily_values: List[Dict[str, Any]] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    params: Optional[Dict[str, Any]] = None

    # 运行时信息
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None

    @property
    def return_pct(self) -> float:
        """总收益率"""
        if self.initial_cash == 0:
            return 0.0
        return (self.final_value - self.initial_cash) / self.initial_cash

    @property
    def total_trades(self) -> int:
        """总交易次数"""
        return len(self.trades)

    @property
    def win_rate(self) -> float:
        """胜率"""
        if not self.trades:
            return 0.0
        winning_trades = sum(1 for t in self.trades if t.get('pnl', 0) > 0)
        return winning_trades / len(self.trades)

    @property
    def profit_factor(self) -> float:
        """盈亏比"""
        gross_profit = sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) < 0))
        if gross_loss == 0:
            return gross_profit if gross_profit > 0 else 1.0
        return gross_profit / gross_loss

    def calculate_max_drawdown(self) -> float:
        """
        计算最大回撤

        Returns:
            最大回撤百分比（负数）
        """
        if not self.daily_values:
            return 0.0

        df = pd.DataFrame(self.daily_values)
        if 'value' not in df.columns:
            return 0.0

        df['peak'] = df['value'].cummax()
        df['drawdown'] = (df['value'] - df['peak']) / df['peak']
        return df['drawdown'].min()

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率（简化版，假设252个交易日）

        Args:
            risk_free_rate: 无风险利率（年化）

        Returns:
            夏普比率
        """
        if not self.daily_values or len(self.daily_values) < 2:
            return 0.0

        df = pd.DataFrame(self.daily_values)
        if 'value' not in df.columns:
            return 0.0

        # 计算日收益率
        df['return'] = df['value'].pct_change()

        # 年化收益率
        excess_return = df['return'].mean() * 252 - risk_free_rate
        volatility = df['return'].std() * (252 ** 0.5)

        if volatility == 0:
            return 0.0

        return excess_return / volatility

    def to_summary(self) -> Dict[str, Any]:
        """生成摘要字典"""
        return {
            'strategy_name': self.strategy_name,
            'params': self.params,
            'period': f"{self.start_date} ~ {self.end_date}",
            'initial_cash': self.initial_cash,
            'final_value': self.final_value,
            'return_pct': f"{self.return_pct:.2%}",
            'total_trades': self.total_trades,
            'win_rate': f"{self.win_rate:.2%}",
            'profit_factor': f"{self.profit_factor:.2f}",
            'max_drawdown': f"{self.calculate_max_drawdown():.2%}",
            'sharpe_ratio': f"{self.calculate_sharpe_ratio():.2f}",
            'duration_seconds': self.duration_seconds,
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame（一行）"""
        return pd.DataFrame([self.to_summary()])

    def save(self, filepath: str):
        """
        保存结果到文件

        Args:
            filepath: 文件路径，支持 .json, .csv, .html
        """
        import json

        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                json.dump({
                    'summary': self.to_summary(),
                    'trades': self.trades,
                    'daily_values': self.daily_values,
                    'logs': self.logs,
                }, f, indent=2, default=str)

        elif filepath.endswith('.csv'):
            self.to_dataframe().to_csv(filepath, index=False)

        elif filepath.endswith('.html'):
            # 生成简单的 HTML 报告
            html = f"""
            <html>
            <head><title>{self.strategy_name} Backtest Result</title></head>
            <body>
                <h1>{self.strategy_name} 回测结果</h1>
                <pre>{pd.DataFrame([self.to_summary()]).to_html()}</pre>
            </body>
            </html>
            """
            with open(filepath, 'w') as f:
                f.write(html)

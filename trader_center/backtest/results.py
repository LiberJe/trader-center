"""
回测结果封装

定义回测结果的数据结构和绩效指标计算。
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import pandas as pd
import json
import hashlib


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
        logs: 日志记录
        params: 策略参数
        analyzer_results: 分析器结果
        run_id: 唯一运行ID
        signal_log: 信号日志
        capital_log: 资金日志
        position_log: 持仓日志
        order_log: 订单日志
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
    analyzer_results: Dict[str, Any] = field(default_factory=dict)

    signal_log: List[Dict[str, Any]] = field(default_factory=list)
    capital_log: List[Dict[str, Any]] = field(default_factory=list)
    position_log: List[Dict[str, Any]] = field(default_factory=list)
    order_log: List[Dict[str, Any]] = field(default_factory=list)

    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None

    run_id: Optional[str] = None
    log_files: Dict[str, str] = field(default_factory=dict)

    def generate_run_id(self) -> str:
        """
        生成唯一运行ID

        Returns:
            格式为 {timestamp}_{hash} 的运行ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content = f"{self.strategy_name}_{timestamp}_{self.params or {}}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:6]
        return f"{timestamp}_{hash_val}"

    def get_run_dir(self, base_dir: Path) -> Path:
        """
        获取本次回测的输出目录

        Args:
            base_dir: 基础输出目录

        Returns:
            本次回测的输出目录路径
        """
        if not self.run_id:
            self.run_id = self.generate_run_id()
        run_dir = base_dir / self.strategy_name / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

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
        summary = {
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
        # 添加分析器结果（如果有）
        if self.analyzer_results:
            summary['analyzer'] = self.analyzer_results
        return summary

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame（一行）"""
        return pd.DataFrame([self.to_summary()])

    def save_trades(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存交易日志

        Args:
            output_dir: 输出目录
            format: 格式（csv/json）

        Returns:
            保存的文件路径，如果无交易则返回 None
        """
        if not self.trades:
            return None

        run_dir = self.get_run_dir(output_dir)

        if format == "json":
            filepath = run_dir / "trades.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.trades, f, indent=2, default=str, ensure_ascii=False)
        else:
            filepath = run_dir / "trades.csv"
            df = pd.DataFrame(self.trades)
            df.to_csv(filepath, index=False, encoding='utf-8')

        self.log_files['trades'] = str(filepath)
        return filepath

    def save_daily_values(self, output_dir: Path) -> Optional[Path]:
        """
        保存每日资产价值

        Args:
            output_dir: 输出目录

        Returns:
            保存的文件路径，如果无数据则返回 None
        """
        if not self.daily_values:
            return None

        run_dir = self.get_run_dir(output_dir)

        filepath = run_dir / "daily_values.csv"
        df = pd.DataFrame(self.daily_values)
        df.to_csv(filepath, index=False, encoding='utf-8')

        self.log_files['daily_values'] = str(filepath)
        return filepath

    def save_summary(self, output_dir: Path) -> Path:
        """
        保存回测摘要

        Args:
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        run_dir = self.get_run_dir(output_dir)

        filepath = run_dir / "summary.json"
        summary_data = {
            'run_id': self.run_id,
            'summary': self.to_summary(),
            'params': self.params,
            'error_message': self.error_message,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, default=str, ensure_ascii=False)

        self.log_files['summary'] = str(filepath)
        return filepath

    def save_plot(self, output_dir: Path, plot_path: Optional[Path] = None) -> Optional[Path]:
        """
        保存图表文件路径记录

        Args:
            output_dir: 输出目录
            plot_path: 图表文件路径（如果已保存）

        Returns:
            图表文件路径
        """
        if plot_path:
            self.log_files['plot'] = str(plot_path)
            return plot_path
        return None

    def save_signal_log(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存信号日志

        Args:
            output_dir: 输出目录
            format: 格式（csv/json）

        Returns:
            保存的文件路径，如果无数据则返回 None
        """
        if not self.signal_log:
            return None

        run_dir = self.get_run_dir(output_dir)

        if format == "json":
            filepath = run_dir / "signals.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.signal_log, f, indent=2, default=str, ensure_ascii=False)
        else:
            filepath = run_dir / "signals.csv"
            df = pd.DataFrame(self.signal_log)
            df.to_csv(filepath, index=False, encoding='utf-8')

        self.log_files['signals'] = str(filepath)
        return filepath

    def save_capital_log(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存资金日志

        Args:
            output_dir: 输出目录
            format: 格式（csv/json）

        Returns:
            保存的文件路径，如果无数据则返回 None
        """
        if not self.capital_log:
            return None

        run_dir = self.get_run_dir(output_dir)

        if format == "json":
            filepath = run_dir / "capitals.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.capital_log, f, indent=2, default=str, ensure_ascii=False)
        else:
            filepath = run_dir / "capitals.csv"
            df = pd.DataFrame(self.capital_log)
            df.to_csv(filepath, index=False, encoding='utf-8')

        self.log_files['capitals'] = str(filepath)
        return filepath

    def save_position_log(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存持仓日志

        Args:
            output_dir: 输出目录
            format: 格式（csv/json）

        Returns:
            保存的文件路径，如果无数据则返回 None
        """
        if not self.position_log:
            return None

        run_dir = self.get_run_dir(output_dir)

        if format == "json":
            filepath = run_dir / "positions.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.position_log, f, indent=2, default=str, ensure_ascii=False)
        else:
            filepath = run_dir / "positions.csv"
            df = pd.DataFrame(self.position_log)
            df.to_csv(filepath, index=False, encoding='utf-8')

        self.log_files['positions'] = str(filepath)
        return filepath

    def save_order_log(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存订单日志

        Args:
            output_dir: 输出目录
            format: 格式（csv/json）

        Returns:
            保存的文件路径，如果无数据则返回 None
        """
        if not self.order_log:
            return None

        run_dir = self.get_run_dir(output_dir)

        if format == "json":
            filepath = run_dir / "orders.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.order_log, f, indent=2, default=str, ensure_ascii=False)
        else:
            filepath = run_dir / "orders.csv"
            df = pd.DataFrame(self.order_log)
            df.to_csv(filepath, index=False, encoding='utf-8')

        self.log_files['orders'] = str(filepath)
        return filepath

    def save_all_logs(self, output_dir: Path, format: str = "csv") -> Dict[str, str]:
        """
        保存所有日志文件

        Args:
            output_dir: 输出目录
            format: 交易日志格式

        Returns:
            保存的文件路径字典
        """
        saved_files = {}

        trades_path = self.save_trades(output_dir, format)
        if trades_path:
            saved_files['trades'] = str(trades_path)

        daily_path = self.save_daily_values(output_dir)
        if daily_path:
            saved_files['daily_values'] = str(daily_path)

        summary_path = self.save_summary(output_dir)
        saved_files['summary'] = str(summary_path)

        signals_path = self.save_signal_log(output_dir, format)
        if signals_path:
            saved_files['signals'] = str(signals_path)

        capitals_path = self.save_capital_log(output_dir, format)
        if capitals_path:
            saved_files['capitals'] = str(capitals_path)

        positions_path = self.save_position_log(output_dir, format)
        if positions_path:
            saved_files['positions'] = str(positions_path)

        orders_path = self.save_order_log(output_dir, format)
        if orders_path:
            saved_files['orders'] = str(orders_path)

        return saved_files

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

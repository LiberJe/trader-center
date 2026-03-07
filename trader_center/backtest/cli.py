"""
回测 CLI

命令行入口用于执行回测任务。
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
import logging

from trader_center.backtest.runner import BacktestRunner
from trader_center.backtest.config import BacktestConfig


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """创建参数解析器"""
    parser = argparse.ArgumentParser(
        prog='backtest',
        description='Trader Center 量化回测系统'
    )

    parser.add_argument(
        '--strategy', '-s',
        help='策略模块路径，如 examples.sma_cross'
    )

    parser.add_argument(
        '--symbol', '-sym',
        action='append',
        help='股票代码，可多次指定'
    )

    parser.add_argument(
        '--start', '-f',
        help='开始日期 (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end', '-t',
        help='结束日期 (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--cash', '-c',
        type=float,
        default=100000.0,
        help='初始资金（默认10万）'
    )

    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=1,
        help='并行进程数（默认1）'
    )

    parser.add_argument(
        '--output', '-o',
        help='输出文件路径 (.json, .csv, .html)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )

    parser.add_argument(
        '--plot', '-p',
        action='store_true',
        help='显示可视化图表'
    )

    parser.add_argument(
        '--plot-style',
        choices=['candle', 'line', 'bar'],
        default='candle',
        help='图表样式（默认candle）'
    )

    parser.add_argument(
        '--plot-file',
        help='保存图表到文件（支持 .png, .pdf, .svg）'
    )

    parser.add_argument(
        '--log-dir',
        help='交易日志输出目录'
    )

    parser.add_argument(
        '--no-auto-save',
        action='store_true',
        help='禁用自动保存交易日志'
    )

    parser.add_argument(
        '--log-format',
        choices=['csv', 'json'],
        default='csv',
        help='交易日志格式（默认csv）'
    )

    parser.add_argument(
        '--no-auto-save-plot',
        action='store_true',
        help='禁用自动保存图表（启用可视化时）'
    )

    parser.add_argument(
        '--benchmark', '-b',
        default='000300.SH',
        help='基准指数代码（默认沪深300: 000300.SH）'
    )

    parser.add_argument(
        '--no-quantstats',
        action='store_true',
        help='禁用 QuantStats 绩效分析'
    )

    parser.add_argument(
        '--no-report',
        action='store_true',
        help='禁用自动保存 HTML 绩效报告'
    )

    parser.add_argument(
        '--open-report',
        action='store_true',
        help='回测完成后自动打开浏览器展示绩效报告'
    )

    return parser


def main(args: Optional[list] = None) -> int:
    """
    CLI 入口

    Returns:
        退出码，0 表示成功
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    if parsed.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not parsed.strategy:
        logger.error("请指定策略 --strategy")
        return 1

    if not parsed.symbol:
        logger.error("请指定至少一个股票代码 --symbol")
        return 1

    end_date = parsed.end or date.today().isoformat()
    if not parsed.start:
        end = date.fromisoformat(end_date)
        start = end - timedelta(days=365)
        start_date = start.isoformat()
    else:
        start_date = parsed.start

    try:
        strategy = load_strategy(parsed.strategy)
        if strategy is None:
            logger.error(f"无法加载策略: {parsed.strategy}")
            return 1

        config = BacktestConfig(
            max_workers=parsed.workers,
            auto_save_trades=not parsed.no_auto_save,
            trade_log_format=parsed.log_format,
            auto_save_plot=not parsed.no_auto_save_plot,
            enable_quantstats=not parsed.no_quantstats,
            benchmark_symbol=parsed.benchmark,
            auto_save_report=not parsed.no_report,
            auto_open_report=parsed.open_report,
        )
        if parsed.log_dir:
            config.trade_log_dir = Path(parsed.log_dir)

        runner = BacktestRunner(
            max_workers=parsed.workers,
            enable_plot=parsed.plot,
            plot_style=parsed.plot_style,
            plot_file=parsed.plot_file,
            config=config,
        )
        result = runner.run(
            strategy=strategy,
            symbols=parsed.symbol,
            start=start_date,
            end=end_date,
            initial_cash=parsed.cash,
        )

        print_result(result, verbose=parsed.verbose)

        if result.log_files:
            print("\n【日志文件】")
            for log_type, log_path in result.log_files.items():
                print(f"  {log_type}: {log_path}")

        if parsed.output:
            result.save(parsed.output)
            logger.info(f"结果已保存到: {parsed.output}")

        return 0 if result.error_message is None else 1

    except Exception as e:
        logger.error(f"回测执行失败: {e}")
        return 1


def load_strategy(strategy_path: str):
    """
    动态加载策略类

    Args:
        strategy_path: 模块路径，如 "examples.sma_cross"

    Returns:
        策略类或 None
    """
    try:
        parts = strategy_path.split('.')
        module_path = '.'.join(parts[:-1])
        class_name = parts[-1]

        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except Exception as e:
        logger.error(f"加载策略失败: {e}")
        return None


def print_result(result, verbose: bool = False):
    """打印回测结果"""
    print("\n" + "=" * 60)
    print(f"策略: {result.strategy_name}")
    print(f"周期: {result.start_date} ~ {result.end_date}")
    print("-" * 60)
    
    print("【资金概况】")
    print(f"  初始资金: {result.initial_cash:,.2f}")
    print(f"  最终资产: {result.final_value:,.2f}")
    print(f"  总收益:   {result.final_value - result.initial_cash:+,.2f}")
    print(f"  收益率:   {result.return_pct:+.2%}")
    
    print("\n【风险指标】")
    max_dd = result.calculate_max_drawdown()
    sharpe = result.calculate_sharpe_ratio()
    print(f"  最大回撤: {max_dd:.2%}")
    print(f"  夏普比率: {sharpe:.2f}")
    
    extended_metrics = result.get_extended_metrics()
    if extended_metrics:
        print("\n【扩展绩效指标】")
        if 'sortino' in extended_metrics:
            print(f"  Sortino比率: {extended_metrics['sortino']:.2f}")
        if 'calmar' in extended_metrics:
            print(f"  Calmar比率:  {extended_metrics['calmar']:.2f}")
        if 'volatility' in extended_metrics:
            print(f"  年化波动率:  {extended_metrics['volatility']:.2%}")
        if 'cagr' in extended_metrics:
            print(f"  年化收益:    {extended_metrics['cagr']:.2%}")
        if 'omega' in extended_metrics and extended_metrics['omega']:
            print(f"  Omega比率:   {extended_metrics['omega']:.2f}")
        if 'var_95' in extended_metrics and extended_metrics['var_95']:
            print(f"  VaR(95%):    {extended_metrics['var_95']:.2%}")
    
    print("\n【交易统计】")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  胜率:       {result.win_rate:.1%}")
    print(f"  盈亏比:     {result.profit_factor:.2f}")
    
    if result.analyzer_results:
        print("\n【分析器结果】")
        for key, value in result.analyzer_results.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
    
    if verbose and result.trades:
        print("\n【交易记录】")
        trades_df = __import__('pandas').DataFrame(result.trades)
        if not trades_df.empty:
            print(trades_df.to_string(index=False))
    
    if verbose and result.daily_values:
        print(f"\n【每日资产】共 {len(result.daily_values)} 条记录")
        dv_df = __import__('pandas').DataFrame(result.daily_values)
        print(dv_df.head(10).to_string(index=False))
        print("...")
        print(dv_df.tail(5).to_string(index=False))
    
    print("=" * 60 + "\n")


if __name__ == '__main__':
    sys.exit(main())

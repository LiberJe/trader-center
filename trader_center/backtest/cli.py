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

    # 参数验证
    if not parsed.strategy:
        logger.error("请指定策略 --strategy")
        return 1

    if not parsed.symbol:
        logger.error("请指定至少一个股票代码 --symbol")
        return 1

    # 默认日期
    end_date = parsed.end or date.today().isoformat()
    if not parsed.start:
        # 默认回测1年
        end = date.fromisoformat(end_date)
        start = end - timedelta(days=365)
        start_date = start.isoformat()
    else:
        start_date = parsed.start

    try:
        # 动态导入策略
        strategy = load_strategy(parsed.strategy)
        if strategy is None:
            logger.error(f"无法加载策略: {parsed.strategy}")
            return 1

        # 执行回测
        runner = BacktestRunner(max_workers=parsed.workers)
        result = runner.run(
            strategy=strategy,
            symbols=parsed.symbol,
            start=start_date,
            end=end_date,
            initial_cash=parsed.cash,
        )

        # 打印结果
        print_result(result)

        # 保存结果
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


def print_result(result):
    """打印回测结果"""
    print("\n" + "=" * 50)
    print(f"策略: {result.strategy_name}")
    print(f"周期: {result.start_date} ~ {result.end_date}")
    print("-" * 50)
    print(f"初始资金: {result.initial_cash:,.2f}")
    print(f"最终资产: {result.final_value:,.2f}")
    print(f"收益率:   {result.return_pct:+.2%}")
    print(f"交易次数: {result.total_trades}")
    print(f"胜率:     {result.win_rate:.1%}")
    print(f"盈亏比:   {result.profit_factor:.2f}")
    print("=" * 50 + "\n")


if __name__ == '__main__':
    sys.exit(main())

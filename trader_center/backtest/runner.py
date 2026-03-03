"""
回测运行器

支持单策略回测和多策略并行回测。
"""

import backtrader as bt
from datetime import date, datetime
from typing import Type, List, Dict, Any, Optional, Union
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
import time

from trader_center.backtest.strategy.base import BaseStrategy
from trader_center.backtest.data_feed import PandasDataFeed
from trader_center.backtest.broker import configure_astock_broker
from trader_center.backtest.results import BacktestResult
from trader_center.backtest.account import StrategyAccount

# 导入 DataHub
try:
    import trader_center.data_hub as dh
except ImportError:
    dh = None


logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    回测运行器

    负责：
    - 从 DataHub 加载数据
    - 配置 backtrader Cerebro
    - 执行回测
    - 收集结果

    Example:
        >>> runner = BacktestRunner()
        >>> result = runner.run(
        ...     strategy=SmaStrategy,
        ...     symbols=["000001.SZ"],
        ...     start="2024-01-01",
        ...     end="2024-12-31",
        ...     initial_cash=100000
        ... )
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Args:
            max_workers: 多进程并行时的最大进程数，None 表示使用 CPU 核心数
        """
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)

    def run(
        self,
        strategy: Type[BaseStrategy],
        symbols: Union[str, List[str]],
        start: Union[str, date],
        end: Union[str, date],
        initial_cash: float = 100000.0,
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> BacktestResult:
        """
        运行单策略回测

        Args:
            strategy: 策略类（继承 BaseStrategy）
            symbols: 股票代码或列表
            start: 开始日期
            end: 结束日期
            initial_cash: 初始资金
            strategy_params: 策略参数

        Returns:
            BacktestResult 回测结果
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        start_time = time.time()
        strategy_name = getattr(strategy, 'name', strategy.__name__)

        try:
            # 创建 Cerebro
            cerebro = bt.Cerebro()

            # 添加策略
            if strategy_params:
                cerebro.addstrategy(strategy, **strategy_params)
            else:
                cerebro.addstrategy(strategy)

            # 加载数据
            for symbol in symbols:
                data = self._load_data(symbol, start, end)
                if data:
                    cerebro.adddata(data)

            if not cerebro.datas:
                return BacktestResult(
                    strategy_name=strategy_name,
                    initial_cash=initial_cash,
                    final_value=initial_cash,
                    start_date=self._parse_date(start),
                    end_date=self._parse_date(end),
                    error_message="No data loaded",
                )

            # 配置 Broker
            configure_astock_broker(cerebro, cash=initial_cash)

            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

            # 运行回测
            self.logger.info(f"Running backtest for {strategy_name}")
            results = cerebro.run()

            # 收集结果
            strat = results[0]
            final_value = cerebro.broker.getvalue()

            # 提取交易记录
            trades = strat.get_trades_df().to_dict('records') if hasattr(strat, 'get_trades_df') else []

            return BacktestResult(
                strategy_name=strategy_name,
                initial_cash=initial_cash,
                final_value=final_value,
                trades=trades,
                start_date=self._parse_date(start),
                end_date=self._parse_date(end),
                params=strategy_params,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return BacktestResult(
                strategy_name=strategy_name,
                initial_cash=initial_cash,
                final_value=initial_cash,
                start_date=self._parse_date(start),
                end_date=self._parse_date(end),
                params=strategy_params,
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            )

    def run_multiple(
        self,
        strategies: List[Dict[str, Any]],
        symbols: Union[str, List[str]],
        start: Union[str, date],
        end: Union[str, date],
        initial_cash: float = 100000.0,
    ) -> List[BacktestResult]:
        """
        并行运行多策略回测

        Args:
            strategies: 策略配置列表，每项包含 'class', 'params', 'name'
            symbols: 股票代码或列表
            start: 开始日期
            end: 结束日期
            initial_cash: 初始资金

        Returns:
            BacktestResult 列表
        """
        if self.max_workers == 1:
            # 单进程模式
            results = []
            for config in strategies:
                result = self.run(
                    strategy=config['class'],
                    symbols=symbols,
                    start=start,
                    end=end,
                    initial_cash=initial_cash,
                    strategy_params=config.get('params'),
                )
                results.append(result)
            return results

        # 多进程并行
        workers = self.max_workers or 4
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = []
            for config in strategies:
                future = executor.submit(
                    self._run_single_worker,
                    config,
                    symbols,
                    start,
                    end,
                    initial_cash,
                )
                futures.append(future)

            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
                    results.append(BacktestResult(
                        strategy_name="unknown",
                        initial_cash=initial_cash,
                        final_value=initial_cash,
                        start_date=self._parse_date(start),
                        end_date=self._parse_date(end),
                        error_message=str(e),
                    ))

            return results

    def _run_single_worker(
        self,
        config: Dict[str, Any],
        symbols: List[str],
        start: Union[str, date],
        end: Union[str, date],
        initial_cash: float,
    ) -> BacktestResult:
        """工作进程执行的函数（必须是静态方法或模块函数）"""
        runner = BacktestRunner(max_workers=1)
        return runner.run(
            strategy=config['class'],
            symbols=symbols,
            start=start,
            end=end,
            initial_cash=initial_cash,
            strategy_params=config.get('params'),
        )

    def _load_data(
        self,
        symbol: str,
        start: Union[str, date],
        end: Union[str, date],
    ) -> Optional[PandasDataFeed]:
        """
        从 DataHub 加载数据

        Args:
            symbol: 股票代码
            start: 开始日期
            end: 结束日期

        Returns:
            PandasDataFeed 或 None
        """
        if dh is None:
            self.logger.error("DataHub not available")
            return None

        try:
            df = dh.get_daily_bars(symbol, start, end)
            if df.empty:
                self.logger.warning(f"No data for {symbol}")
                return None

            return PandasDataFeed.from_datahub(symbol, df)

        except Exception as e:
            self.logger.error(f"Failed to load data for {symbol}: {e}")
            return None

    def _parse_date(self, d: Union[str, date]) -> date:
        """解析日期"""
        if isinstance(d, str):
            return datetime.strptime(d, '%Y-%m-%d').date()
        return d

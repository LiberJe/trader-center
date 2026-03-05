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
from trader_center.backtest.config import BacktestConfig

# 导入 DataHub
try:
    import trader_center.data_hub as dh
except ImportError:
    dh = None


logger = logging.getLogger(__name__)


class DailyValueObserver(bt.Observer):
    """
    每日资产价值观察器
    
    记录每个交易日的资产价值，用于计算最大回撤和夏普比率。
    """
    lines = ('value', 'cash')
    
    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue()
        self.lines.cash[0] = self._owner.broker.getcash()


def _run_single_worker(
    strategy_class: Type[BaseStrategy],
    symbols: List[str],
    start: Union[str, date],
    end: Union[str, date],
    initial_cash: float,
    strategy_params: Optional[Dict[str, Any]] = None,
) -> BacktestResult:
    """
    工作进程执行的函数（模块级函数，支持 pickle 序列化）
    
    Args:
        strategy_class: 策略类
        symbols: 股票代码列表
        start: 开始日期
        end: 结束日期
        initial_cash: 初始资金
        strategy_params: 策略参数
        
    Returns:
        BacktestResult 回测结果
    """
    runner = BacktestRunner(max_workers=1)
    return runner.run(
        strategy=strategy_class,
        symbols=symbols,
        start=start,
        end=end,
        initial_cash=initial_cash,
        strategy_params=strategy_params,
    )


class BacktestRunner:
    """
    回测运行器

    负责：
    - 从 DataHub 加载数据
    - 配置 backtrader Cerebro
    - 执行回测
    - 收集结果
    - 可视化输出

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

    def __init__(
        self,
        max_workers: Optional[int] = None,
        enable_plot: bool = False,
        plot_style: str = "candle",
        plot_file: Optional[str] = None,
        config: Optional[BacktestConfig] = None,
    ):
        """
        Args:
            max_workers: 多进程并行时的最大进程数，None 表示使用 CPU 核心数
            enable_plot: 是否启用可视化图表
            plot_style: 图表样式 (candle, line, bar)
            plot_file: 保存图表到文件路径
            config: 回测配置，如果为 None 则使用默认配置
        """
        self.config = config or BacktestConfig()
        self.max_workers = max_workers or self.config.max_workers
        self.enable_plot = enable_plot
        self.plot_style = plot_style
        self.plot_file = plot_file
        self.logger = logging.getLogger(__name__)
        self._cerebro = None

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
                if data is not None:
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

            # 添加观察器（记录每日资产价值）
            cerebro.addobserver(DailyValueObserver)

            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.03)
            cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
            cerebro.addanalyzer(bt.analyzers.PeriodStats, _name='period_stats')

            # 保存 cerebro 引用用于可视化
            self._cerebro = cerebro

            # 运行回测
            self.logger.info(f"Running backtest for {strategy_name}")
            results = cerebro.run()

            # 收集结果
            strat = results[0]
            final_value = cerebro.broker.getvalue()

            # 提取每日资产价值
            daily_values = []
            if hasattr(strat, 'observers') and len(strat.observers) > 0:
                for obs in strat.observers:
                    if isinstance(obs, DailyValueObserver):
                        # 获取日期和数据
                        data = cerebro.datas[0]
                        for i in range(len(data)):
                            try:
                                dt = data.datetime.date(-i)
                                val = obs.lines.value[-i]
                                cash = obs.lines.cash[-i]
                                daily_values.append({
                                    'date': dt,
                                    'value': val,
                                    'cash': cash,
                                })
                            except IndexError:
                                break
                        daily_values.reverse()  # 按时间正序排列
                        break

            # 提取交易记录
            trades = strat.get_trades_df().to_dict('records') if hasattr(strat, 'get_trades_df') else []

            # 提取分析器结果
            analyzer_results = {}
            try:
                if hasattr(strat, 'analyzers'):
                    returns = strat.analyzers.returns.get_analysis()
                    drawdown = strat.analyzers.drawdown.get_analysis()
                    trade_analyzer = strat.analyzers.trades.get_analysis()
                    sqn = strat.analyzers.sqn.get_analysis()
                    sharpe = strat.analyzers.sharpe.get_analysis()
                    annual_return = strat.analyzers.annual_return.get_analysis()
                    period_stats = strat.analyzers.period_stats.get_analysis()
                    
                    analyzer_results = {
                        'total_return': returns.get('rtot', 0),
                        'average_return': returns.get('ravg', 0),
                        'max_drawdown': drawdown.get('max', {}).get('drawdown', 0),
                        'max_drawdown_len': drawdown.get('max', {}).get('len', 0),
                        'total_trades': trade_analyzer.get('total', {}).get('total', 0),
                        'sqn': sqn.get('sqn', 0),
                        'sharpe_ratio': sharpe.get('sharperatio', 0),
                        'average_win': trade_analyzer.get('won', {}).get('pnl', {}).get('average', 0) if trade_analyzer.get('won') else 0,
                        'average_loss': trade_analyzer.get('lost', {}).get('pnl', {}).get('average', 0) if trade_analyzer.get('lost') else 0,
                        'max_win': trade_analyzer.get('won', {}).get('pnl', {}).get('max', 0) if trade_analyzer.get('won') else 0,
                        'max_loss': trade_analyzer.get('lost', {}).get('pnl', {}).get('max', 0) if trade_analyzer.get('lost') else 0,
                        'average_period': period_stats.get('average', 0),
                        'stddev_period': period_stats.get('stddev', 0),
                    }
                    
                    if annual_return:
                        analyzer_results['annual_returns'] = {str(k): v for k, v in annual_return.items()}
            except Exception as e:
                self.logger.warning(f"Failed to extract analyzer results: {e}")

            result = BacktestResult(
                strategy_name=strategy_name,
                initial_cash=initial_cash,
                final_value=final_value,
                trades=trades,
                daily_values=daily_values,
                start_date=self._parse_date(start),
                end_date=self._parse_date(end),
                params=strategy_params,
                duration_seconds=time.time() - start_time,
                analyzer_results=analyzer_results,
            )

            if self.config.auto_save_trades:
                try:
                    saved_files = result.save_all_logs(
                        self.config.trade_log_dir,
                        self.config.trade_log_format
                    )
                    if saved_files:
                        self.logger.info(f"交易日志已保存: {saved_files}")
                except Exception as e:
                    self.logger.warning(f"保存交易日志失败: {e}")

            if self.enable_plot:
                self._plot_result(cerebro, strat, result)

            return result

        except Exception as e:
            import traceback
            self.logger.error(f"Backtest failed: {e}")
            self.logger.error(traceback.format_exc())
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
                    _run_single_worker,
                    config['class'],
                    symbols,
                    start,
                    end,
                    initial_cash,
                    config.get('params'),
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

    def _plot_result(self, cerebro, strat, result: BacktestResult):
        """
        绘制回测结果图表
        
        Args:
            cerebro: backtrader Cerebro 实例
            strat: 策略实例
            result: 回测结果
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            
            # 设置中文字体
            chinese_fonts = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC']
            font_found = False
            for font_name in chinese_fonts:
                try:
                    font_path = fm.findfont(font_name)
                    if 'generic' not in font_path.lower():
                        plt.rcParams['font.sans-serif'] = [font_name]
                        font_found = True
                        break
                except:
                    continue
            
            if not font_found:
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
            
            plt.rcParams['axes.unicode_minus'] = False
            
            # 创建图表
            fig = plt.figure(figsize=(14, 10))
            fig.suptitle(f'{result.strategy_name} 回测结果', fontsize=14, fontweight='bold')
            
            # 子图1: 资产曲线
            ax1 = fig.add_subplot(2, 2, 1)
            if result.daily_values:
                import pandas as pd
                df = pd.DataFrame(result.daily_values)
                ax1.plot(df['date'], df['value'], 'b-', label='资产价值', linewidth=1.5)
                ax1.axhline(y=result.initial_cash, color='gray', linestyle='--', label='初始资金')
                ax1.set_title('资产曲线')
                ax1.set_xlabel('日期')
                ax1.set_ylabel('资产价值')
                ax1.legend(loc='upper left')
                ax1.grid(True, alpha=0.3)
                ax1.tick_params(axis='x', rotation=45)
            
            # 子图2: 回撤曲线
            ax2 = fig.add_subplot(2, 2, 2)
            if result.daily_values:
                import pandas as pd
                df = pd.DataFrame(result.daily_values)
                df['peak'] = df['value'].cummax()
                df['drawdown'] = (df['value'] - df['peak']) / df['peak'] * 100
                ax2.fill_between(df['date'], df['drawdown'], 0, color='red', alpha=0.3)
                ax2.plot(df['date'], df['drawdown'], 'r-', linewidth=1)
                ax2.set_title('回撤曲线')
                ax2.set_xlabel('日期')
                ax2.set_ylabel('回撤 (%)')
                ax2.grid(True, alpha=0.3)
                ax2.tick_params(axis='x', rotation=45)
            
            # 子图3: 收益分布
            ax3 = fig.add_subplot(2, 2, 3)
            if result.trades:
                import pandas as pd
                trades_df = pd.DataFrame(result.trades)
                if 'pnl' in trades_df.columns:
                    wins = trades_df[trades_df['pnl'] > 0]['pnl']
                    losses = trades_df[trades_df['pnl'] < 0]['pnl']
                    ax3.hist(wins, bins=20, color='green', alpha=0.6, label=f'盈利 ({len(wins)})')
                    ax3.hist(losses, bins=20, color='red', alpha=0.6, label=f'亏损 ({len(losses)})')
                    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
                    ax3.set_title('交易收益分布')
                    ax3.set_xlabel('盈亏')
                    ax3.set_ylabel('次数')
                    ax3.legend()
                    ax3.grid(True, alpha=0.3)
            
            # 子图4: 绩效摘要
            ax4 = fig.add_subplot(2, 2, 4)
            ax4.axis('off')
            
            summary_text = f"""
Performance Summary
========================
Strategy: {result.strategy_name}
Period: {result.start_date} ~ {result.end_date}
========================
Initial Cash: {result.initial_cash:,.2f}
Final Value: {result.final_value:,.2f}
Total PnL: {result.final_value - result.initial_cash:+,.2f}
Return: {result.return_pct:+.2%}
========================
Max Drawdown: {result.calculate_max_drawdown():.2%}
Sharpe Ratio: {result.calculate_sharpe_ratio():.2f}
========================
Total Trades: {result.total_trades}
Win Rate: {result.win_rate:.1%}
Profit Factor: {result.profit_factor:.2f}
"""
            if result.analyzer_results:
                sqn = result.analyzer_results.get('sqn', 0)
                sharpe = result.analyzer_results.get('sharpe_ratio', 0)
                summary_text += f"SQN:        {sqn:.2f}\n"
                summary_text += f"BT夏普:     {sharpe:.2f}\n" if sharpe else ""
            
            ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, 
                    fontsize=10, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            plt.tight_layout()
            
            if self.plot_file:
                plt.savefig(self.plot_file, dpi=150, bbox_inches='tight')
                self.logger.info(f"图表已保存到: {self.plot_file}")
            elif self.config.auto_save_plot:
                run_dir = result.get_run_dir(self.config.trade_log_dir)
                plot_path = run_dir / "plot.png"
                plt.savefig(plot_path, dpi=150, bbox_inches='tight')
                self.logger.info(f"图表已保存到: {plot_path}")
                result.log_files['plot'] = str(plot_path)
            else:
                plt.show()
            
        except ImportError:
            self.logger.warning("matplotlib 未安装，跳过可视化")
        except Exception as e:
            self.logger.warning(f"可视化失败: {e}")

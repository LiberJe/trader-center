"""
绩效分析模块

集成 QuantStats 提供专业级绩效分析能力。
"""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import pandas as pd
import numpy as np

try:
    import quantstats as qs
    HAS_QUANTSTATS = True
except ImportError:
    HAS_QUANTSTATS = False

logger = logging.getLogger(__name__)


class PerformanceAnalytics:
    """
    绩效分析器
    
    提供专业的策略绩效分析，包括风险指标、收益指标、风险调整收益等。
    
    Args:
        returns: 日收益率序列 (pd.Series, index为日期)
        benchmark: 基准日收益率序列 (可选)
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.03], 
        ...                     index=pd.date_range('2024-01-01', periods=3))
        >>> analytics = PerformanceAnalytics(returns)
        >>> metrics = analytics.metrics()
        >>> report_path = analytics.report('report.html')
    """
    
    def __init__(
        self, 
        returns: pd.Series, 
        benchmark: Optional[pd.Series] = None
    ):
        self.returns = self._validate_returns(returns)
        self.benchmark = self._validate_benchmark(benchmark) if benchmark is not None else None
        
    def _validate_returns(self, returns: pd.Series) -> pd.Series:
        """验证并标准化收益率序列"""
        if not isinstance(returns, pd.Series):
            raise ValueError("returns 必须是 pd.Series")
            
        if returns.empty:
            raise ValueError("returns 不能为空")
            
        if not isinstance(returns.index, pd.DatetimeIndex):
            try:
                returns.index = pd.to_datetime(returns.index)
            except Exception as e:
                raise ValueError(f"无法将 returns.index 转换为 DatetimeIndex: {e}")
                
        returns = returns.sort_index()
        returns.name = 'strategy'
        
        return returns
    
    def _validate_benchmark(self, benchmark: pd.Series) -> pd.Series:
        """验证并标准化基准收益率序列"""
        if not isinstance(benchmark, pd.Series):
            raise ValueError("benchmark 必须是 pd.Series")
            
        if not isinstance(benchmark.index, pd.DatetimeIndex):
            try:
                benchmark.index = pd.to_datetime(benchmark.index)
            except Exception as e:
                raise ValueError(f"无法将 benchmark.index 转换为 DatetimeIndex: {e}")
                
        benchmark = benchmark.sort_index()
        benchmark.name = 'benchmark'
        
        return benchmark
    
    def metrics(self, periods: int = 252) -> Dict[str, Any]:
        """
        计算完整绩效指标
        
        Args:
            periods: 年化交易日数 (默认252)
            
        Returns:
            绩效指标字典
        """
        if HAS_QUANTSTATS:
            return self._metrics_quantstats(periods)
        else:
            return self._metrics_basic(periods)
    
    def _metrics_quantstats(self, periods: int = 252) -> Dict[str, Any]:
        """使用 QuantStats 计算绩效指标"""
        metrics = {}
        
        try:
            metrics['start_date'] = str(self.returns.index[0].date())
            metrics['end_date'] = str(self.returns.index[-1].date())
            metrics['total_days'] = len(self.returns)
            
            metrics['total_return'] = float(qs.stats.comp(self.returns))
            metrics['cagr'] = float(qs.stats.cagr(self.returns, periods=periods))
            metrics['expected_return'] = float(self.returns.mean() * periods)
            
            metrics['volatility'] = float(qs.stats.volatility(self.returns, periods=periods))
            metrics['max_drawdown'] = float(qs.stats.max_drawdown(self.returns))
            
            try:
                metrics['var_95'] = float(qs.stats.var(self.returns, sigma=1.65))
                metrics['cvar_95'] = float(qs.stats.cvar(self.returns, sigma=1.65))
            except:
                metrics['var_95'] = None
                metrics['cvar_95'] = None
            
            metrics['downside_deviation'] = float(qs.stats.volatility(
                self.returns[self.returns < 0], periods=periods
            )) if (self.returns < 0).any() else 0.0
            
            metrics['sharpe'] = float(qs.stats.sharpe(self.returns, periods=periods))
            metrics['sortino'] = float(qs.stats.sortino(self.returns, periods=periods))
            metrics['calmar'] = float(qs.stats.calmar(self.returns, periods=periods))
            
            try:
                metrics['omega'] = float(qs.stats.omega(self.returns))
            except:
                metrics['omega'] = None
                
            try:
                metrics['tail_ratio'] = float(qs.stats.tail_ratio(self.returns))
            except:
                metrics['tail_ratio'] = None
            
            metrics['skew'] = float(self.returns.skew())
            metrics['kurtosis'] = float(self.returns.kurtosis())
            
            metrics['best_day'] = float(self.returns.max())
            metrics['worst_day'] = float(self.returns.min())
            metrics['avg_win'] = float(self.returns[self.returns > 0].mean()) if (self.returns > 0).any() else 0
            metrics['avg_loss'] = float(self.returns[self.returns < 0].mean()) if (self.returns < 0).any() else 0
            
            win_days = (self.returns > 0).sum()
            loss_days = (self.returns < 0).sum()
            metrics['win_days'] = int(win_days)
            metrics['loss_days'] = int(loss_days)
            metrics['win_rate'] = float(win_days / len(self.returns)) if len(self.returns) > 0 else 0
            
            if self.benchmark is not None:
                try:
                    aligned_benchmark = self.benchmark.reindex(
                        self.returns.index, method='ffill'
                    ).dropna()
                    aligned_returns = self.returns.reindex(aligned_benchmark.index)
                    
                    if len(aligned_returns) > 0:
                        greeks = qs.stats.greeks(aligned_returns, aligned_benchmark, periods=periods)
                        metrics['alpha'] = float(greeks['alpha'])
                        metrics['beta'] = float(greeks['beta'])
                        metrics['r_squared'] = float(qs.stats.r_squared(
                            aligned_returns, aligned_benchmark
                        ))
                        metrics['information_ratio'] = float(qs.stats.information_ratio(
                            aligned_returns, aligned_benchmark
                        ))
                except Exception as e:
                    logger.warning(f"计算基准相关指标失败: {e}")
                    metrics['alpha'] = None
                    metrics['beta'] = None
                    metrics['r_squared'] = None
                    metrics['information_ratio'] = None
                    
        except Exception as e:
            logger.error(f"QuantStats 计算失败: {e}")
            return self._metrics_basic(periods)
            
        return metrics
    
    def _metrics_basic(self, periods: int = 252) -> Dict[str, Any]:
        """基础绩效指标计算（无 QuantStats 时使用）"""
        metrics = {}
        
        metrics['start_date'] = str(self.returns.index[0].date())
        metrics['end_date'] = str(self.returns.index[-1].date())
        metrics['total_days'] = len(self.returns)
        
        total_return = (1 + self.returns).prod() - 1
        metrics['total_return'] = float(total_return)
        
        years = len(self.returns) / periods
        if years > 0 and total_return > -1:
            metrics['cagr'] = float((1 + total_return) ** (1 / years) - 1)
        else:
            metrics['cagr'] = 0.0
            
        metrics['expected_return'] = float(self.returns.mean() * periods)
        metrics['volatility'] = float(self.returns.std() * np.sqrt(periods))
        
        cum_returns = (1 + self.returns).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        metrics['max_drawdown'] = float(drawdown.min())
        
        excess_return = self.returns.mean() * periods - 0.03
        volatility = self.returns.std() * np.sqrt(periods)
        metrics['sharpe'] = float(excess_return / volatility) if volatility > 0 else 0.0
        
        downside_returns = self.returns[self.returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std() * np.sqrt(periods)
            metrics['sortino'] = float(excess_return / downside_std) if downside_std > 0 else 0.0
        else:
            metrics['sortino'] = 0.0
            
        if metrics['max_drawdown'] != 0:
            metrics['calmar'] = float(metrics['cagr'] / abs(metrics['max_drawdown']))
        else:
            metrics['calmar'] = 0.0
            
        metrics['skew'] = float(self.returns.skew())
        metrics['kurtosis'] = float(self.returns.kurtosis())
        
        metrics['best_day'] = float(self.returns.max())
        metrics['worst_day'] = float(self.returns.min())
        
        win_days = (self.returns > 0).sum()
        loss_days = (self.returns < 0).sum()
        metrics['win_days'] = int(win_days)
        metrics['loss_days'] = int(loss_days)
        metrics['win_rate'] = float(win_days / len(self.returns)) if len(self.returns) > 0 else 0
        
        return metrics
    
    def report(
        self, 
        output_path: Optional[Union[str, Path]] = None,
        title: str = "Strategy Performance Report",
        benchmark_name: str = "Benchmark"
    ) -> Optional[str]:
        """
       生成 HTML 绩效报告
        
        Args:
            output_path: 输出文件路径
            title: 报告标题
            benchmark_name: 基准名称
            
        Returns:
            报告文件路径，如果 QuantStats 未安装则返回 None
        """
        if not HAS_QUANTSTATS:
            logger.warning("QuantStats 未安装，无法生成 HTML 报告")
            return None
            
        if output_path is None:
            output_path = "performance_report.html"
        output_path = Path(output_path)
        
        try:
            if self.benchmark is not None:
                aligned_benchmark = self.benchmark.reindex(
                    self.returns.index, method='ffill'
                )
                qs.reports.html(
                    self.returns,
                    benchmark=aligned_benchmark,
                    output=str(output_path),
                    title=title,
                    benchmark_title=benchmark_name
                )
            else:
                qs.reports.html(
                    self.returns,
                    output=str(output_path),
                    title=title
                )
            
            logger.info(f"绩效报告已保存到: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"生成 HTML 报告失败: {e}")
            return None
    
    def plot_snapshot(
        self, 
        output_path: Optional[Union[str, Path]] = None,
        title: str = "Strategy Snapshot"
    ) -> Optional[str]:
        """
        生成快照图表
        
        Args:
            output_path: 输出文件路径
            title: 图表标题
            
        Returns:
            图表文件路径，如果 QuantStats 未安装则返回 None
        """
        if not HAS_QUANTSTATS:
            logger.warning("QuantStats 未安装，无法生成快照图表")
            return None
            
        if output_path is None:
            output_path = "snapshot.png"
        output_path = Path(output_path)
        
        try:
            qs.plots.snapshot(
                self.returns, 
                title=title, 
                savefig=str(output_path),
                show=False
            )
            logger.info(f"快照图表已保存到: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"生成快照图表失败: {e}")
            return None
    
    def monthly_returns(self) -> pd.DataFrame:
        """
        计算月度收益
        
        Returns:
            月度收益 DataFrame
        """
        if HAS_QUANTSTATS:
            try:
                return qs.stats.monthly_returns(self.returns)
            except:
                pass
        
        monthly = self.returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
        monthly_df = monthly.to_frame('return')
        monthly_df.index = pd.to_datetime(monthly_df.index)
        return monthly_df
    
    def yearly_returns(self) -> pd.DataFrame:
        """
        计算年度收益
        
        Returns:
            年度收益 DataFrame
        """
        if HAS_QUANTSTATS:
            try:
                return qs.stats.yearly_returns(self.returns)
            except:
                pass
        
        yearly = self.returns.resample('YE').apply(lambda x: (1 + x).prod() - 1)
        yearly_df = yearly.to_frame('return')
        yearly_df.index = pd.to_datetime(yearly_df.index)
        return yearly_df
    
    def drawdown_details(self) -> pd.DataFrame:
        """
        获取回撤详情
        
        Returns:
            回撤详情 DataFrame
        """
        if HAS_QUANTSTATS:
            try:
                return qs.stats.drawdown_details(self.returns)
            except:
                pass
        
        cum_returns = (1 + self.returns).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        
        details = []
        in_drawdown = False
        dd_start = None
        dd_max = 0
        
        for i, (date, dd) in enumerate(drawdown.items()):
            if dd < 0 and not in_drawdown:
                in_drawdown = True
                dd_start = date
                dd_max = dd
            elif dd < 0 and in_drawdown:
                dd_max = min(dd_max, dd)
            elif dd == 0 and in_drawdown:
                details.append({
                    'start': dd_start,
                    'end': date,
                    'max_drawdown': dd_max
                })
                in_drawdown = False
                dd_max = 0
        
        if in_drawdown:
            details.append({
                'start': dd_start,
                'end': drawdown.index[-1],
                'max_drawdown': dd_max
            })
        
        return pd.DataFrame(details)


def create_returns_series(
    daily_values: List[Dict[str, Any]]
) -> pd.Series:
    """
    从每日资产价值列表创建收益率序列
    
    Args:
        daily_values: 每日资产价值列表，每个元素包含 'date' 和 'value'
        
    Returns:
        日收益率序列
    """
    if not daily_values:
        raise ValueError("daily_values 不能为空")
    
    df = pd.DataFrame(daily_values)
    
    if 'date' not in df.columns or 'value' not in df.columns:
        raise ValueError("daily_values 必须包含 'date' 和 'value' 字段")
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    returns = df['value'].pct_change().dropna()
    
    return returns


def load_benchmark_returns(
    symbol: str,
    start: Union[str, date],
    end: Union[str, date]
) -> Optional[pd.Series]:
    """
    加载基准收益率序列
    
    Args:
        symbol: 基准代码 (如 "000300.SH")
        start: 开始日期
        end: 结束日期
        
    Returns:
        基准日收益率序列，如果加载失败返回 None
    """
    try:
        import trader_center.data_hub as dh
        
        df = dh.get_daily_bars(symbol, start, end)
        if df.empty:
            logger.warning(f"无法加载基准数据: {symbol}")
            return None
        
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            elif 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df = df.set_index('trade_date')
        
        df = df.sort_index()
        returns = df['close'].pct_change().dropna()
        returns.name = 'benchmark'
        
        return returns
        
    except ImportError:
        logger.warning("DataHub 不可用，无法加载基准数据")
        return None
    except Exception as e:
        logger.error(f"加载基准数据失败: {e}")
        return None

"""
因子分析流水线

提供一键式因子分析功能，整合因子计算、预处理、分析和报告生成。
"""

from typing import Optional, Dict, List, Union
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
import warnings

from trader_center.factor.library import FactorRegistry
from trader_center.factor.mining.engine import FactorEngine
from trader_center.factor.mining.preprocessing.winsorization import winsorize_cross_sectional
from trader_center.factor.mining.preprocessing.standardization import standardize_cross_sectional
from trader_center.factor.mining.alphalens_adapter import AlphalensAdapter, check_alphalens_available
from trader_center.factor.mining.visualization import FactorVisualizer
from trader_center.factor.mining.scoring import FactorScorer, compute_monotonicity
from trader_center.factor.mining.report import FactorReport
from trader_center.factor.mining.turnover import TurnoverAnalyzer
from trader_center.factor.mining.grouped_ic import GroupedICAnalyzer
from trader_center.factor.mining.decay import DecayAnalyzer
from trader_center.factor.mining.robustness import RobustnessTester
from trader_center.factor.mining.alpha_beta import AlphaBetaAnalyzer

logger = logging.getLogger(__name__)


class FactorAnalysisPipeline:
    """
    因子分析流水线
    
    一键完成因子全流程分析，包括：
    1. 因子计算
    2. 数据预处理
    3. IC分析
    4. 分层回测
    5. 因子评分
    6. 可视化
    7. 报告生成
    
    Example:
        pipeline = FactorAnalysisPipeline()
        
        # 单因子分析
        result = pipeline.run(
            factor_name='momentum',
            factor_df=momentum_values,
            price_df=close_prices,
            visualize=True,
            generate_report=True,
        )
        
        # 批量分析
        results = pipeline.run_batch(
            factor_names=['momentum', 'rsi', 'macd'],
            factor_data_dict=factor_dict,
            price_df=close_prices,
        )
    """
    
    def __init__(
        self,
        registry: FactorRegistry = None,
        preprocessing_config: Dict = None,
        analysis_config: Dict = None,
        output_dir: str = './factor_analysis_output',
        use_alphalens: bool = True,
        use_timestamp_subdir: bool = True,
    ):
        """
        初始化因子分析流水线
        
        Args:
            registry: 因子注册器
            preprocessing_config: 预处理配置
            analysis_config: 分析配置
            output_dir: 输出目录
            use_alphalens: 是否使用Alphalens进行分析
            use_timestamp_subdir: 是否使用时间戳子目录存储结果
        """
        self.registry = registry or FactorRegistry()
        self.engine = FactorEngine(registry=self.registry)
        
        self.preprocessing_config = preprocessing_config or {
            'winsorize': {'method': 'mad', 'threshold': 3.0},
            'standardize': {'method': 'zscore'},
            'neutralize': None,
        }
        
        self.analysis_config = analysis_config or {
            'periods': [1, 5, 10, 20],
            'quantiles': 5,
            'ic_method': 'spearman',
        }
        
        self.output_dir = Path(output_dir)
        
        if use_timestamp_subdir:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.run_dir = self.output_dir / timestamp
        else:
            self.run_dir = self.output_dir
        
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_alphalens = use_alphalens and check_alphalens_available()
        
        if self.use_alphalens:
            self.alphalens_adapter = AlphalensAdapter(
                periods=self.analysis_config['periods'],
                quantiles=self.analysis_config['quantiles'],
            )
        
        self.visualizer = FactorVisualizer()
        self.scorer = FactorScorer()
        self.reporter = FactorReport(str(self.run_dir / 'reports'))
        
        self._results_cache: Dict[str, Dict] = {}
    
    def run(
        self,
        factor_name: str,
        factor_df: pd.DataFrame,
        price_df: pd.DataFrame,
        preprocessing: bool = True,
        use_alphalens_analysis: bool = None,
        scoring: bool = True,
        visualize: bool = True,
        generate_report: bool = False,
        show_plots: bool = False,
        save_figures: bool = True,
        metadata: Dict = None,
    ) -> Dict:
        """
        运行因子分析流水线
        
        Args:
            factor_name: 因子名称
            factor_df: 因子值DataFrame，index为日期，columns为资产代码
            price_df: 价格DataFrame，index为日期，columns为资产代码
            preprocessing: 是否进行预处理
            use_alphalens_analysis: 是否使用Alphalens分析（默认使用初始化配置）
            scoring: 是否进行评分
            visualize: 是否生成可视化
            generate_report: 是否生成报告
            show_plots: 是否显示图表
            save_figures: 是否保存图表
            metadata: 因子元数据
        
        Returns:
            分析结果字典
        
        Example:
            result = pipeline.run(
                factor_name='momentum_20',
                factor_df=momentum_values,
                price_df=close_prices,
                visualize=True,
            )
            print(f"IC均值: {result['summary']['ic_mean']:.4f}")
            print(f"评分: {result['score']['total_score']:.2f}")
        """
        logger.info(f"开始分析因子: {factor_name}")
        
        result = {
            'factor_name': factor_name,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
        }
        
        if preprocessing:
            factor_processed = self._preprocess(factor_df)
        else:
            factor_processed = factor_df.copy()
        
        result['factor_processed'] = factor_processed
        
        use_al = use_alphalens_analysis if use_alphalens_analysis is not None else self.use_alphalens
        
        if use_al:
            analysis_result = self._analyze_with_alphalens(
                factor_processed, price_df, show_plots
            )
            # 添加额外的分析
            additional_analysis = self._analyze_additional(
                factor_processed, price_df
            )
            analysis_result.update(additional_analysis)
        else:
            analysis_result = self._analyze_with_builtin(
                factor_processed, price_df
            )
        
        result.update(analysis_result)
        
        if scoring:
            score = self.scorer.score(analysis_result)
            result['score'] = score
            logger.info(f"因子评分: {score['total_score']:.2f} ({score['grade']})")
        
        figures = {}
        if visualize:
            figures = self._generate_visualizations(
                factor_name, result, save_figures
            )
            result['figures'] = figures
        
        if generate_report:
            report_path = self.reporter.generate(
                factor_name=factor_name,
                analysis_result=result,
                figures=figures,
                score=result.get('score'),
                metadata=metadata,
            )
            result['report_path'] = report_path
            logger.info(f"报告已生成: {report_path}")
        
        self._results_cache[factor_name] = result
        
        logger.info(f"因子分析完成: {factor_name}")
        
        return result
    
    def run_with_factor(
        self,
        factor: Union[str, 'BaseFactor'],
        price_df: pd.DataFrame,
        volume_df: pd.DataFrame = None,
        open_df: pd.DataFrame = None,
        high_df: pd.DataFrame = None,
        low_df: pd.DataFrame = None,
        factor_params: Dict = None,
        preprocessing: bool = True,
        scoring: bool = True,
        visualize: bool = True,
        generate_report: bool = False,
        metadata: Dict = None,
        **kwargs,
    ) -> Dict:
        """
        使用 BaseFactor 实例运行因子分析
        
        支持直接传入 BaseFactor 实例或因子名称，自动处理数据格式转换。
        
        Args:
            factor: 因子名称（字符串）或 BaseFactor 实例
            price_df: 价格数据（宽表格式，index=日期，columns=股票代码）
            volume_df: 成交量数据（可选）
            open_df: 开盘价数据（可选）
            high_df: 最高价数据（可选）
            low_df: 最低价数据（可选）
            factor_params: 因子参数（当 factor 为字符串时使用）
            preprocessing: 是否进行预处理
            scoring: 是否进行评分
            visualize: 是否生成可视化
            generate_report: 是否生成报告
            metadata: 因子元数据
            **kwargs: 其他参数
        
        Returns:
            分析结果字典
        
        Example:
            >>> from trader_center.factor.library.technical.momentum import MomentumFactor
            >>> pipeline = FactorAnalysisPipeline()
            >>> 
            >>> # 使用因子实例
            >>> factor = MomentumFactor(period=20)
            >>> result = pipeline.run_with_factor(factor, price_df)
            >>> 
            >>> # 使用因子名称（需先注册）
            >>> result = pipeline.run_with_factor('momentum', price_df, factor_params={'period': 20})
        """
        from trader_center.factor.library.base import BaseFactor
        from trader_center.factor.mining.data_adapter import wide_to_dict
        
        if isinstance(factor, str):
            factor_instance = self.registry.get(factor)
            if factor_params:
                factor_instance.set_params(**factor_params)
        elif isinstance(factor, BaseFactor):
            factor_instance = factor
        else:
            raise ValueError(
                f"factor 参数必须是字符串或 BaseFactor 实例，当前类型: {type(factor)}"
            )
        
        required_data = factor_instance.required_data
        include_volume = 'volume' in required_data
        
        data_dict = wide_to_dict(
            price_df=price_df,
            include_ohlcv=True,
            open_df=open_df,
            high_df=high_df,
            low_df=low_df,
            volume_df=volume_df if include_volume else None,
        )
        
        logger.info(f"使用因子 {factor_instance.name} 计算 {len(data_dict)} 个资产的因子值")
        
        factor_values = {}
        for symbol, data in data_dict.items():
            try:
                factor_values[symbol] = factor_instance.compute(data)
            except Exception as e:
                logger.warning(f"计算因子 {factor_instance.name} 失败 (symbol={symbol}): {e}")
                factor_values[symbol] = pd.Series(dtype=float)
        
        factor_df = pd.DataFrame(factor_values)
        
        params_str = '_'.join(f"{k}{v}" for k, v in factor_instance.params.items())
        factor_name = f"{factor_instance.name}_{params_str}" if params_str else factor_instance.name
        
        full_metadata = factor_instance.get_metadata()
        if metadata:
            full_metadata.update(metadata)
        
        return self.run(
            factor_name=factor_name,
            factor_df=factor_df,
            price_df=price_df,
            preprocessing=preprocessing,
            scoring=scoring,
            visualize=visualize,
            generate_report=generate_report,
            metadata=full_metadata,
            **kwargs,
        )
    
    def _preprocess(
        self,
        factor_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        预处理步骤
        
        Args:
            factor_df: 原始因子数据
        
        Returns:
            处理后的因子数据
        """
        result = factor_df.copy()
        
        winsorize_config = self.preprocessing_config.get('winsorize')
        if winsorize_config:
            result = winsorize_cross_sectional(
                result,
                method=winsorize_config.get('method', 'mad'),
                threshold=winsorize_config.get('threshold', 3.0),
            )
            logger.debug("去极值完成")
        
        standardize_config = self.preprocessing_config.get('standardize')
        if standardize_config:
            result = standardize_cross_sectional(
                result,
                method=standardize_config.get('method', 'zscore'),
            )
            logger.debug("标准化完成")
        
        return result
    
    def _analyze_with_alphalens(
        self,
        factor_df: pd.DataFrame,
        price_df: pd.DataFrame,
        show_plots: bool = False,
    ) -> Dict:
        """
        使用Alphalens进行分析
        
        Args:
            factor_df: 因子数据
            price_df: 价格数据
            show_plots: 是否显示图表
        
        Returns:
            分析结果字典
        """
        factor_data = self.alphalens_adapter.create_factor_data(factor_df, price_df)
        
        analysis_result = self.alphalens_adapter.run_full_analysis(factor_data)
        
        quantile_returns = self.alphalens_adapter.compute_quantile_returns(factor_data)
        monotonicity = compute_monotonicity(quantile_returns[0])
        analysis_result['monotonicity'] = monotonicity
        
        if show_plots:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.alphalens_adapter.create_tear_sheet(factor_data)
        
        return analysis_result
    
    def _analyze_additional(
        self,
        factor_df: pd.DataFrame,
        price_df: pd.DataFrame,
    ) -> Dict:
        """
        添加额外的分析结果
        
        Args:
            factor_df: 因子数据
            price_df: 价格数据
        
        Returns:
            额外分析结果字典
        """
        forward_returns = price_df.pct_change().shift(-1)
        
        # 换手率分析
        turnover_analyzer = TurnoverAnalyzer()
        turnover_result = turnover_analyzer.compute_factor_turnover(factor_df)
        
        # 分组IC分析
        grouped_ic_analyzer = GroupedICAnalyzer()
        # 由于没有行业数据，这里跳过分组IC分析
        grouped_ic_result = {}
        
        # 因子衰减分析
        decay_analyzer = DecayAnalyzer()
        decay_result = decay_analyzer.compute_ic_decay(factor_df, forward_returns)
        
        # 稳健性测试
        robustness_tester = RobustnessTester()
        # 使用时间周期测试作为稳健性测试
        robustness_result = robustness_tester.test_by_time_period(factor_df, forward_returns)
        
        # Alpha/Beta分析
        alpha_beta_analyzer = AlphaBetaAnalyzer()
        # 计算因子收益
        factor_returns = alpha_beta_analyzer.compute_factor_returns(factor_df, forward_returns)
        # 创建简单的基准收益（市场平均）
        benchmark_returns = forward_returns.mean(axis=1)
        # 计算Alpha和Beta
        alpha_beta_result = alpha_beta_analyzer.compute_factor_alpha_beta(factor_returns, benchmark_returns)
        
        return {
            'turnover': turnover_result,
            'grouped_ic': grouped_ic_result,
            'decay': decay_result,
            'robustness': robustness_result,
            'alpha_beta': alpha_beta_result,
        }
    
    def _analyze_with_builtin(
        self,
        factor_df: pd.DataFrame,
        price_df: pd.DataFrame,
    ) -> Dict:
        """
        使用内置分析器进行分析
        
        Args:
            factor_df: 因子数据
            price_df: 价格数据
        
        Returns:
            分析结果字典
        """
        from trader_center.factor.mining.ic_analysis import ICAnalyzer
        from trader_center.factor.mining.layering import LayeringAnalyzer
        
        forward_returns = price_df.pct_change().shift(-1)
        
        ic_analyzer = ICAnalyzer()
        ic_result = ic_analyzer.compute(
            factor_df, forward_returns,
            method=self.analysis_config.get('ic_method', 'spearman')
        )
        
        layering_analyzer = LayeringAnalyzer(
            n_groups=self.analysis_config.get('quantiles', 5)
        )
        layering_result = layering_analyzer.compute(factor_df, forward_returns)
        
        # 添加额外分析
        additional_analysis = self._analyze_additional(factor_df, price_df)
        
        summary = {
            'ic_mean': ic_result['ic_mean'],
            'ic_std': ic_result['ic_std'],
            'icir': ic_result['icir'],
            'ic_positive_ratio': ic_result['ic_positive_ratio'],
            'ic_skew': ic_result['ic_series'].skew(),
        }
        
        if not layering_result['long_short_returns'].empty:
            ls_returns = layering_result['long_short_returns']
            summary['factor_return_mean'] = ls_returns.mean()
            summary['factor_return_std'] = ls_returns.std()
            if ls_returns.std() > 0:
                summary['factor_sharpe'] = ls_returns.mean() / ls_returns.std()
        
        result = {
            'ic': ic_result,
            'layering': layering_result,
            'summary': summary,
            'monotonicity': layering_analyzer.compute_monotonicity(),
        }
        result.update(additional_analysis)
        
        return result
    
    def _generate_visualizations(
        self,
        factor_name: str,
        result: Dict,
        save_figures: bool,
    ) -> Dict:
        """
        生成可视化图表
        
        Args:
            factor_name: 因子名称
            result: 分析结果
            save_figures: 是否保存图表
        
        Returns:
            图表字典
        """
        figures = {}
        figure_dir = self.run_dir / 'figures'
        figure_dir.mkdir(parents=True, exist_ok=True)
        
        factor_data = result.get('factor_processed')
        if factor_data is not None:
            factor_series = factor_data.stack()
            factor_series.index.names = ['date', 'asset']
            
            save_path = str(figure_dir / f'{factor_name}_distribution.png') if save_figures else None
            fig = self.visualizer.plot_factor_distribution(
                factor_series, save_path=save_path
            )
            figures['distribution'] = fig
        
        # IC分析图表
        ic_result = result.get('ic')
        if ic_result:
            save_path = str(figure_dir / f'{factor_name}_ic_series.png') if save_figures else None
            fig = self.visualizer.plot_ic_series(
                ic_result.get('ic_series', []), save_path=save_path
            )
            figures['ic_series'] = fig
        
        # 分层回测图表
        layering_result = result.get('layering')
        if layering_result:
            save_path = str(figure_dir / f'{factor_name}_layering_returns.png') if save_figures else None
            fig = self.visualizer.plot_layering_returns(
                layering_result.get('group_returns', {}),
                layering_result.get('long_short_returns', []),
                save_path=save_path
            )
            figures['layering_returns'] = fig
        
        # 换手率图表
        turnover_result = result.get('turnover')
        if turnover_result is not None:
            # 检查turnover_series是否存在
            turnover_series = turnover_result.get('turnover_series') if isinstance(turnover_result, dict) else turnover_result
            if turnover_series is not None and not (hasattr(turnover_series, 'empty') and turnover_series.empty):
                save_path = str(figure_dir / f'{factor_name}_turnover.png') if save_figures else None
                fig = self.visualizer.plot_turnover_series(
                    turnover_series,
                    save_path=save_path
                )
                figures['turnover'] = fig
        
        # 因子衰减图表
        decay_result = result.get('decay')
        if decay_result is not None:
            # 检查decay_curve是否存在
            decay_curve = decay_result.get('decay_curve') if isinstance(decay_result, dict) else decay_result
            if decay_curve is not None and not (hasattr(decay_curve, 'empty') and decay_curve.empty):
                save_path = str(figure_dir / f'{factor_name}_decay.png') if save_figures else None
                fig = self.visualizer.plot_decay_curve(
                    decay_curve,
                    save_path=save_path
                )
                figures['decay'] = fig
        
        # 稳健性测试图表
        robustness_result = result.get('robustness')
        if robustness_result is not None:
            # 检查regime_results是否存在
            regime_results = robustness_result.get('regime_results') if isinstance(robustness_result, dict) else robustness_result
            if regime_results is not None and isinstance(regime_results, dict) and regime_results:
                save_path = str(figure_dir / f'{factor_name}_robustness.png') if save_figures else None
                fig = self.visualizer.plot_robustness_analysis(
                    regime_results,
                    save_path=save_path
                )
                figures['robustness'] = fig
        
        # Alpha/Beta分析图表
        alpha_beta_result = result.get('alpha_beta')
        if alpha_beta_result is not None and isinstance(alpha_beta_result, dict):
            save_path = str(figure_dir / f'{factor_name}_alpha_beta.png') if save_figures else None
            fig = self.visualizer.plot_alpha_beta_analysis(
                alpha_beta_result.get('alpha', 0),
                alpha_beta_result.get('beta', 0),
                alpha_beta_result.get('information_ratio', 0),
                save_path=save_path
            )
            figures['alpha_beta'] = fig
        
        return figures
    
    def run_batch(
        self,
        factor_names: List[str],
        factor_data_dict: Dict[str, pd.DataFrame],
        price_df: pd.DataFrame,
        parallel: bool = False,
        **kwargs,
    ) -> Dict[str, Dict]:
        """
        批量运行因子分析
        
        Args:
            factor_names: 因子名称列表
            factor_data_dict: 因子数据字典 {factor_name: DataFrame}
            price_df: 价格数据
            parallel: 是否并行执行
            **kwargs: 传递给run方法的参数
        
        Returns:
            分析结果字典 {factor_name: result}
        
        Example:
            results = pipeline.run_batch(
                factor_names=['momentum', 'rsi', 'macd'],
                factor_data_dict={
                    'momentum': momentum_df,
                    'rsi': rsi_df,
                    'macd': macd_df,
                },
                price_df=close_prices,
            )
        """
        results = {}
        
        for factor_name in factor_names:
            if factor_name not in factor_data_dict:
                logger.warning(f"因子数据不存在: {factor_name}")
                continue
            
            try:
                result = self.run(
                    factor_name=factor_name,
                    factor_df=factor_data_dict[factor_name],
                    price_df=price_df,
                    **kwargs,
                )
                results[factor_name] = result
            except Exception as e:
                logger.error(f"分析因子 {factor_name} 时出错: {e}")
                results[factor_name] = {'error': str(e)}
        
        logger.info(f"批量分析完成，共 {len(results)} 个因子")
        
        return results
    
    def get_ranking(
        self,
        factor_names: List[str] = None,
    ) -> pd.DataFrame:
        """
        获取因子排名
        
        Args:
            factor_names: 要排名的因子列表，默认为所有已分析的因子
        
        Returns:
            排名DataFrame
        """
        if factor_names is None:
            factor_names = list(self._results_cache.keys())
        
        results_to_rank = {
            name: self._results_cache[name]
            for name in factor_names
            if name in self._results_cache
        }
        
        if not results_to_rank:
            logger.warning("没有可排名的因子结果")
            return pd.DataFrame()
        
        return self.scorer.rank_factors(results_to_rank)
    
    def get_summary(
        self,
        factor_names: List[str] = None,
    ) -> pd.DataFrame:
        """
        获取分析摘要
        
        Args:
            factor_names: 因子列表，默认为所有
        
        Returns:
            摘要DataFrame
        """
        if factor_names is None:
            factor_names = list(self._results_cache.keys())
        
        summaries = []
        for name in factor_names:
            if name not in self._results_cache:
                continue
            
            result = self._results_cache[name]
            summary = result.get('summary', {})
            summary['factor'] = name
            
            if 'score' in result:
                summary['total_score'] = result['score']['total_score']
                summary['grade'] = result['score']['grade']
            
            summaries.append(summary)
        
        return pd.DataFrame(summaries).set_index('factor')
    
    def generate_multi_factor_report(
        self,
        factor_names: List[str] = None,
    ) -> str:
        """
        生成多因子对比报告
        
        Args:
            factor_names: 因子列表，默认为所有已分析的因子
        
        Returns:
            报告路径
        """
        if factor_names is None:
            factor_names = list(self._results_cache.keys())
        
        results = {
            name: self._results_cache[name]
            for name in factor_names
            if name in self._results_cache
        }
        
        ranking = self.get_ranking(factor_names)
        
        figures = {}
        if len(ranking) > 1:
            fig = self.visualizer.plot_score_summary(ranking)
            figures['score_summary'] = fig
        
        return self.reporter.generate_multi_factor_report(
            analysis_results=results,
            ranking_df=ranking,
            figures=figures,
        )
    
    def clear_cache(self) -> None:
        """清空结果缓存"""
        self._results_cache.clear()
        logger.info("缓存已清空")


def quick_analyze(
    factor_df: pd.DataFrame,
    price_df: pd.DataFrame,
    factor_name: str = 'factor',
    show_tear_sheet: bool = True,
) -> Dict:
    """
    快速因子分析
    
    便捷函数，一键完成因子分析。
    
    Args:
        factor_df: 因子值DataFrame
        price_df: 价格DataFrame
        factor_name: 因子名称
        show_tear_sheet: 是否显示Alphalens完整报告
    
    Returns:
        分析结果字典
    
    Example:
        result = quick_analyze(momentum_df, close_df, 'momentum')
        print(f"IC均值: {result['summary']['ic_mean']:.4f}")
        print(f"评级: {result['score']['grade']}")
    """
    pipeline = FactorAnalysisPipeline()
    
    return pipeline.run(
        factor_name=factor_name,
        factor_df=factor_df,
        price_df=price_df,
        preprocessing=True,
        scoring=True,
        visualize=False,
        generate_report=False,
        show_plots=show_tear_sheet,
    )

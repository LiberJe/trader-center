"""
因子可视化模块

提供Alphalens未提供的补充可视化功能，
包括因子分布图、多因子对比图、评分汇总图等。
"""

from typing import Optional, Dict, List, Tuple
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FactorVisualizer:
    """
    因子可视化器
    
    提供Alphalens未提供的可视化功能。
    
    Example:
        visualizer = FactorVisualizer()
        
        # 因子分布图
        fig = visualizer.plot_factor_distribution(factor_data)
        
        # 多因子对比图
        fig = visualizer.plot_multi_factor_comparison(analysis_results)
        
        # 评分汇总图
        fig = visualizer.plot_score_summary(scores_df)
    """
    
    def __init__(
        self,
        style: str = 'whitegrid',
        figsize_scale: float = 1.0,
        color_palette: str = 'husl',
        language: str = 'zh',  # 'zh' for Chinese, 'en' for English
    ):
        """
        初始化可视化器
        
        Args:
            style: matplotlib样式
            figsize_scale: 图表大小缩放因子
            color_palette: seaborn颜色主题
            language: 语言设置 ('zh' 中文, 'en' 英文)
        """
        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'ggplot')
        sns.set_theme(style=style, palette=color_palette)
        self.figsize_scale = figsize_scale
        self.color_palette = color_palette
        self.language = language
        
        # 语言映射
        self.labels = {
            'zh': {
                'factor_value': '因子值',
                'frequency': '频次',
                'density': '密度',
                'date': '日期',
                'ic': 'IC',
                'cumulative_ic': '累计IC',
                'return': '收益',
                'cumulative_return': '累计收益',
                'turnover': '换手率',
                'group': '分组',
                'sector': '行业',
                'market_cap': '市值',
                'period': '时期',
                'performance': '表现',
                'robustness': '稳健性',
                'decay': '衰减',
                'alpha': 'Alpha',
                'beta': 'Beta',
                'risk': '风险',
                'score': '评分',
                'total_score': '总评分',
                'factor': '因子',
                'distribution': '分布',
                'comparison': '对比',
                'correlation': '相关性',
                'heatmap': '热力图',
                'time_series': '时间序列',
                'rolling': '滚动',
                'grouped': '分组',
                'quantile': '分位数',
                'summary': '汇总',
                'dashboard': '仪表盘',
                'breakdown': '分解',
                'matrix': '矩阵',
                'mean': '均值',
                'median': '中位数',
                'std': '标准差',
                'min': '最小值',
                'max': '最大值',
                'skew': '偏度',
                'kurtosis': '峰度',
                'good': '良好',
                'excellent': '优秀',
            },
            'en': {
                'factor_value': 'Factor Value',
                'frequency': 'Frequency',
                'density': 'Density',
                'date': 'Date',
                'ic': 'IC',
                'cumulative_ic': 'Cumulative IC',
                'return': 'Return',
                'cumulative_return': 'Cumulative Return',
                'turnover': 'Turnover',
                'group': 'Group',
                'sector': 'Sector',
                'market_cap': 'Market Cap',
                'period': 'Period',
                'performance': 'Performance',
                'robustness': 'Robustness',
                'decay': 'Decay',
                'alpha': 'Alpha',
                'beta': 'Beta',
                'risk': 'Risk',
                'score': 'Score',
                'total_score': 'Total Score',
                'factor': 'Factor',
                'distribution': 'Distribution',
                'comparison': 'Comparison',
                'correlation': 'Correlation',
                'heatmap': 'Heatmap',
                'time_series': 'Time Series',
                'rolling': 'Rolling',
                'grouped': 'Grouped',
                'quantile': 'Quantile',
                'summary': 'Summary',
                'dashboard': 'Dashboard',
                'breakdown': 'Breakdown',
                'matrix': 'Matrix',
                'mean': 'Mean',
                'median': 'Median',
                'std': 'Std',
                'min': 'Min',
                'max': 'Max',
                'skew': 'Skew',
                'kurtosis': 'Kurtosis',
                'good': 'Good',
                'excellent': 'Excellent',
            }
        }
    
    def _get_label(self, key: str) -> str:
        """
        获取标签
        
        Args:
            key: 标签键
        
        Returns:
            标签值
        """
        return self.labels.get(self.language, self.labels['zh']).get(key, key)
    
    def _setup_figure(
        self,
        figsize: Tuple[float, float],
        nrows: int = 1,
        ncols: int = 1,
    ) -> plt.Figure:
        """
        创建图表
        
        Args:
            figsize: 图表大小
            nrows: 行数
            ncols: 列数
        
        Returns:
            Figure对象
        """
        fig = plt.figure(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        return fig
    
    def _save_figure(
        self,
        fig: plt.Figure,
        save_path: Optional[str],
    ) -> None:
        """
        保存图表
        
        Args:
            fig: Figure对象
            save_path: 保存路径
        """
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"图表已保存: {save_path}")
    
    def plot_factor_distribution(
        self,
        factor_data: pd.Series,
        figsize: Tuple[float, float] = (12, 5),
        bins: int = 50,
        show_stats: bool = True,
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制因子分布图
        
        包含直方图和箱线图，展示因子的分布特征。
        
        Args:
            factor_data: 因子值Series
            figsize: 图表大小
            bins: 直方图分箱数
            show_stats: 是否显示统计信息
            save_path: 保存路径
        
        Returns:
            Figure对象
        
        Example:
            fig = visualizer.plot_factor_distribution(factor_series)
            plt.show()
        """
        fig, axes = plt.subplots(1, 2, figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax1 = axes[0]
        ax1.hist(factor_data.dropna(), bins=bins, alpha=0.7, edgecolor='black')
        ax1.axvline(factor_data.mean(), color='red', linestyle='--', label=f'Mean: {factor_data.mean():.4f}')
        ax1.axvline(factor_data.median(), color='green', linestyle='--', label=f'Median: {factor_data.median():.4f}')
        ax1.set_xlabel('Factor Value')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Factor Distribution (Histogram)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2 = axes[1]
        box = ax2.boxplot(factor_data.dropna(), vert=True, patch_artist=True)
        box['boxes'][0].set_facecolor('lightblue')
        ax2.set_ylabel('Factor Value')
        ax2.set_title('Factor Distribution (Boxplot)')
        ax2.grid(True, alpha=0.3, axis='y')
        
        if show_stats:
            stats_text = (
                f"Mean: {factor_data.mean():.4f}\n"
                f"Std: {factor_data.std():.4f}\n"
                f"Min: {factor_data.min():.4f}\n"
                f"Max: {factor_data.max():.4f}\n"
                f"Skew: {factor_data.skew():.4f}\n"
                f"Kurtosis: {factor_data.kurtosis():.4f}"
            )
            ax2.text(
                0.98, 0.98, stats_text,
                transform=ax2.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                fontsize=9,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            )
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_factor_distribution_by_quantile(
        self,
        factor_data: pd.DataFrame,
        figsize: Tuple[float, float] = (14, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制各分位数下的因子分布
        
        Args:
            factor_data: Alphalens格式的因子数据，包含factor和group列
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, axes = plt.subplots(1, 2, figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        factor_values = factor_data['factor'].dropna()
        quantiles = factor_data['factor_quantile'].dropna()
        
        ax1 = axes[0]
        for q in sorted(quantiles.unique()):
            data = factor_values[quantiles == q]
            ax1.hist(data, bins=30, alpha=0.5, label=f'Q{int(q)}', density=True)
        ax1.set_xlabel('Factor Value')
        ax1.set_ylabel('Density')
        ax1.set_title('Factor Distribution by Quantile')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2 = axes[1]
        data_by_quantile = [
            factor_values[quantiles == q].values
            for q in sorted(quantiles.unique())
        ]
        bp = ax2.boxplot(data_by_quantile, patch_artist=True)
        colors = sns.color_palette(self.color_palette, len(data_by_quantile))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
        ax2.set_xlabel('Quantile')
        ax2.set_ylabel('Factor Value')
        ax2.set_title('Factor Distribution by Quantile (Boxplot)')
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_multi_factor_comparison(
        self,
        analysis_results: Dict[str, Dict],
        metrics: List[str] = None,
        figsize: Tuple[float, float] = (14, 8),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制多因子对比图
        
        包含雷达图和柱状图，展示多个因子的综合表现。
        
        Args:
            analysis_results: 分析结果字典 {factor_name: result}
            metrics: 要对比的指标列表
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        
        Example:
            results = {
                'momentum': {'ic_mean': 0.05, 'icir': 0.8, ...},
                'rsi': {'ic_mean': 0.03, 'icir': 0.5, ...},
            }
            fig = visualizer.plot_multi_factor_comparison(results)
        """
        if metrics is None:
            metrics = ['ic_mean', 'icir', 'factor_return_mean', 'factor_sharpe']
        
        factor_names = list(analysis_results.keys())
        
        fig = plt.figure(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax1 = fig.add_subplot(121, polar=True)
        
        n_metrics = len(metrics)
        angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
        angles += angles[:1]
        
        for i, factor_name in enumerate(factor_names):
            values = []
            for metric in metrics:
                val = analysis_results[factor_name].get(metric, {}).get(
                    'mean', 
                    analysis_results[factor_name].get(metric, 0)
                )
                values.append(val)
            
            max_val = max(abs(v) for v in values) if values else 1
            normalized = [v / max_val if max_val != 0 else 0 for v in values]
            normalized += normalized[:1]
            
            ax1.plot(angles, normalized, 'o-', linewidth=2, label=factor_name)
            ax1.fill(angles, normalized, alpha=0.1)
        
        ax1.set_xticks(angles[:-1])
        ax1.set_xticklabels(metrics)
        ax1.set_title('Factor Comparison (Radar)', pad=20)
        ax1.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        ax2 = fig.add_subplot(122)
        
        metric_to_show = metrics[0]
        x = np.arange(len(factor_names))
        width = 0.6
        
        values = [
            analysis_results[fn].get(metric_to_show, {}).get('mean', 0)
            for fn in factor_names
        ]
        
        colors = ['green' if v > 0 else 'red' for v in values]
        ax2.bar(x, values, width, color=colors, alpha=0.7)
        ax2.set_xlabel('Factor')
        ax2.set_ylabel(metric_to_show)
        ax2.set_title(f'Factor {metric_to_show} Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(factor_names, rotation=45, ha='right')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_factor_correlation_heatmap(
        self,
        corr_matrix: pd.DataFrame,
        figsize: Tuple[float, float] = (10, 8),
        cmap: str = 'RdYlGn',
        annot: bool = True,
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制因子相关性热力图
        
        Args:
            corr_matrix: 相关性矩阵
            figsize: 图表大小
            cmap: 颜色映射
            annot: 是否显示数值
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        
        sns.heatmap(
            corr_matrix,
            mask=mask,
            annot=annot,
            fmt='.2f',
            cmap=cmap,
            center=0,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
            ax=ax
        )
        
        ax.set_title('Factor Correlation Heatmap', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_score_summary(
        self,
        scores_df: pd.DataFrame,
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制因子评分汇总图
        
        展示各因子的综合评分和各维度得分。
        
        Args:
            scores_df: 评分DataFrame，index为因子名称
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        
        Example:
            scores_df = pd.DataFrame({
                'ic_score': [0.8, 0.6],
                'return_score': [0.7, 0.5],
                'total_score': [0.75, 0.55],
            }, index=['momentum', 'rsi'])
            
            fig = visualizer.plot_score_summary(scores_df)
        """
        fig, axes = plt.subplots(1, 2, figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax1 = axes[0]
        
        score_cols = [col for col in scores_df.columns if 'score' in col.lower()]
        
        if 'total_score' in score_cols:
            score_cols.remove('total_score')
        
        if score_cols:
            scores_df[score_cols].plot(
                kind='bar',
                ax=ax1,
                alpha=0.7,
                width=0.8
            )
            ax1.set_xlabel('Factor')
            ax1.set_ylabel('Score')
            ax1.set_title('Factor Score by Dimension')
            ax1.set_xticklabels(scores_df.index, rotation=45, ha='right')
            ax1.legend(loc='upper right')
            ax1.grid(True, alpha=0.3, axis='y')
            ax1.set_ylim(0, 1.1)
        
        ax2 = axes[1]
        
        if 'total_score' in scores_df.columns:
            colors = []
            for score in scores_df['total_score']:
                if score >= 0.8:
                    colors.append('darkgreen')
                elif score >= 0.6:
                    colors.append('green')
                elif score >= 0.4:
                    colors.append('yellow')
                elif score >= 0.2:
                    colors.append('orange')
                else:
                    colors.append('red')
            
            scores_df['total_score'].plot(
                kind='bar',
                ax=ax2,
                color=colors,
                alpha=0.8,
                width=0.6
            )
            ax2.set_xlabel('Factor')
            ax2.set_ylabel('Total Score')
            ax2.set_title('Factor Total Score Ranking')
            ax2.set_xticklabels(scores_df.index, rotation=45, ha='right')
            ax2.axhline(y=0.6, color='green', linestyle='--', alpha=0.5, label='Good (0.6)')
            ax2.axhline(y=0.8, color='darkgreen', linestyle='--', alpha=0.5, label='Excellent (0.8)')
            ax2.legend()
            ax2.grid(True, alpha=0.3, axis='y')
            ax2.set_ylim(0, 1.1)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_ic_comparison(
        self,
        ic_results: Dict[str, pd.Series],
        figsize: Tuple[float, float] = (14, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制多因子IC时间序列对比图
        
        Args:
            ic_results: IC结果字典 {factor_name: ic_series}
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, axes = plt.subplots(2, 1, figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax1 = axes[0]
        for factor_name, ic_series in ic_results.items():
            (1 + ic_series).cumprod().plot(
                ax=ax1,
                label=factor_name,
                linewidth=1.5
            )
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Cumulative IC')
        ax1.set_title('IC Cumulative Comparison')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2 = axes[1]
        width = 0.8 / len(ic_results)
        x = np.arange(len(ic_results))
        
        for i, (factor_name, ic_series) in enumerate(ic_results.items()):
            ax2.bar(
                x + i * width - 0.4 + width/2,
                ic_series.mean(),
                width,
                yerr=ic_series.std(),
                label=factor_name,
                alpha=0.7,
                capsize=3
            )
        
        ax2.set_xlabel('Factor')
        ax2.set_ylabel('IC Mean')
        ax2.set_title('IC Mean Comparison (with Std)')
        ax2.set_xticks(x)
        ax2.set_xticklabels(ic_results.keys(), rotation=45, ha='right')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_quantile_returns_heatmap(
        self,
        quantile_returns: pd.DataFrame,
        figsize: Tuple[float, float] = (10, 6),
        cmap: str = 'RdYlGn',
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制分层收益热力图
        
        Args:
            quantile_returns: 分层收益DataFrame
            figsize: 图表大小
            cmap: 颜色映射
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        sns.heatmap(
            quantile_returns.T,
            annot=True,
            fmt='.4f',
            cmap=cmap,
            center=0,
            square=False,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
            ax=ax
        )
        
        ax.set_title('Quantile Returns Heatmap', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Quantile')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # IC相关图表
    def plot_ic_rolling(
        self,
        ic_series: pd.Series,
        window: int = 20,
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制滚动IC图
        
        Args:
            ic_series: IC时间序列
            window: 滚动窗口大小
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        rolling_ic = ic_series.rolling(window=window).mean()
        
        ax.plot(ic_series.index, ic_series.values, alpha=0.5, label='IC')
        ax.plot(rolling_ic.index, rolling_ic.values, linewidth=2, label=f'Rolling {window}D IC')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.axhline(y=ic_series.mean(), color='red', linestyle='--', label='Mean IC')
        
        ax.set_title(f'Rolling {window}D IC')
        ax.set_xlabel(self._get_label('date'))
        ax.set_ylabel(self._get_label('ic'))
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_ic_by_period(
        self,
        ic_by_period: Dict[str, float],
        figsize: Tuple[float, float] = (10, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制分时期IC对比
        
        Args:
            ic_by_period: 分时期IC字典
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        periods = list(ic_by_period.keys())
        values = list(ic_by_period.values())
        
        colors = ['green' if v > 0 else 'red' for v in values]
        ax.bar(periods, values, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax.set_title('IC by Period')
        ax.set_xlabel(self._get_label('period'))
        ax.set_ylabel(self._get_label('ic'))
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_ic_grouped_heatmap(
        self,
        group_ic: pd.DataFrame,
        figsize: Tuple[float, float] = (12, 8),
        cmap: str = 'RdYlGn',
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制分组IC热力图
        
        Args:
            group_ic: 分组IC DataFrame
            figsize: 图表大小
            cmap: 颜色映射
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        sns.heatmap(
            group_ic,
            annot=True,
            fmt='.4f',
            cmap=cmap,
            center=0,
            square=False,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
            ax=ax
        )
        
        ax.set_title('Grouped IC Heatmap')
        ax.set_xlabel(self._get_label('group'))
        ax.set_ylabel(self._get_label('period'))
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_ic_cumulative(
        self,
        ic_series: pd.Series,
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制累计IC图
        
        Args:
            ic_series: IC时间序列
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        cumulative_ic = ic_series.cumsum()
        
        ax.plot(cumulative_ic.index, cumulative_ic.values, linewidth=2)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax.set_title('Cumulative IC')
        ax.set_xlabel(self._get_label('date'))
        ax.set_ylabel(self._get_label('cumulative_ic'))
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 分层回测图表
    def plot_cumulative_returns(
        self,
        returns_by_quantile: pd.DataFrame,
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制累计收益图（各分组）
        
        Args:
            returns_by_quantile: 各分组收益DataFrame
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        cumulative_returns = (1 + returns_by_quantile).cumprod() - 1
        
        for col in cumulative_returns.columns:
            ax.plot(cumulative_returns.index, cumulative_returns[col], label=col)
        
        ax.set_title('Cumulative Returns by Quantile')
        ax.set_xlabel(self._get_label('date'))
        ax.set_ylabel(self._get_label('cumulative_return'))
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_quantile_returns_bar(
        self,
        quantile_returns: pd.DataFrame,
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制分组收益柱状图
        
        Args:
            quantile_returns: 分组收益DataFrame
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        mean_returns = quantile_returns.mean()
        std_returns = quantile_returns.std()
        
        mean_returns.plot(kind='bar', yerr=std_returns, capsize=3, alpha=0.7, ax=ax)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax.set_title('Quantile Returns')
        ax.set_xlabel('Quantile')
        ax.set_ylabel(self._get_label('return'))
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_turnover_series(
        self,
        turnover_series: pd.Series,
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制换手率时间序列
        
        Args:
            turnover_series: 换手率时间序列
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax.plot(turnover_series.index, turnover_series.values, linewidth=2)
        ax.axhline(y=turnover_series.mean(), color='red', linestyle='--', label='Mean Turnover')
        
        ax.set_title('Turnover Time Series')
        ax.set_xlabel(self._get_label('date'))
        ax.set_ylabel(self._get_label('turnover'))
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_group_performance_radar(
        self,
        group_metrics: pd.DataFrame,
        figsize: Tuple[float, float] = (10, 8),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制分组表现雷达图
        
        Args:
            group_metrics: 分组指标DataFrame
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ), polar=True)
        
        metrics = group_metrics.columns
        n_metrics = len(metrics)
        angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
        angles += angles[:1]
        
        for group in group_metrics.index:
            values = group_metrics.loc[group].values.tolist()
            values += values[:1]
            ax.plot(angles, values, 'o-', linewidth=2, label=group)
            ax.fill(angles, values, alpha=0.1)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_title('Group Performance Radar')
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 衰减分析图表
    def plot_ic_decay_curve(
        self,
        ic_decay: pd.Series,
        figsize: Tuple[float, float] = (10, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制IC衰减曲线
        
        Args:
            ic_decay: IC衰减曲线
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax.plot(ic_decay.index, ic_decay.values, 'o-', linewidth=2, markersize=8)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        if not ic_decay.isna().all():
            max_period = ic_decay.idxmax()
            max_ic = ic_decay.max()
            ax.annotate(f'Max: {max_ic:.4f} at {max_period}d',
                        xy=(max_period, max_ic),
                        xytext=(max_period + 2, max_ic + 0.01),
                        arrowprops=dict(facecolor='black', shrink=0.05))
        
        ax.set_title('IC Decay Curve')
        ax.set_xlabel('Holding Period (days)')
        ax.set_ylabel(self._get_label('ic'))
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_return_decay_curve(
        self,
        return_decay: pd.Series,
        figsize: Tuple[float, float] = (10, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制收益衰减曲线
        
        Args:
            return_decay: 收益衰减曲线
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax.plot(return_decay.index, return_decay.values, 'o-', linewidth=2, markersize=8)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        if not return_decay.isna().all():
            max_period = return_decay.idxmax()
            max_return = return_decay.max()
            ax.annotate(f'Max: {max_return:.4f} at {max_period}d',
                        xy=(max_period, max_return),
                        xytext=(max_period + 2, max_return + 0.001),
                        arrowprops=dict(facecolor='black', shrink=0.05))
        
        ax.set_title('Return Decay Curve')
        ax.set_xlabel('Holding Period (days)')
        ax.set_ylabel(self._get_label('return'))
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_decay_comparison(
        self,
        decay_dict: Dict[str, pd.Series],
        figsize: Tuple[float, float] = (12, 8),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制多因子衰减对比
        
        Args:
            decay_dict: 因子衰减字典
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        for factor_name, decay_series in decay_dict.items():
            ax.plot(decay_series.index, decay_series.values, 'o-', linewidth=2, markersize=6, label=factor_name)
        
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax.set_title('Factor Decay Comparison')
        ax.set_xlabel('Holding Period (days)')
        ax.set_ylabel(self._get_label('ic'))
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 稳健性测试图表
    def plot_period_comparison(
        self,
        period_results: Dict[str, Dict[str, float]],
        metric: str = 'ic_mean',
        figsize: Tuple[float, float] = (10, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制分时期表现对比
        
        Args:
            period_results: 分时期测试结果
            metric: 要显示的指标
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        periods = list(period_results.keys())
        values = [period_results[p][metric] for p in periods]
        
        colors = ['green' if v > 0 else 'red' for v in values]
        ax.bar(periods, values, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax.set_title('Performance by Time Period')
        ax.set_xlabel(self._get_label('period'))
        ax.set_ylabel(metric)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_sector_performance(
        self,
        sector_results: Dict[str, Dict[str, float]],
        metric: str = 'ic_mean',
        figsize: Tuple[float, float] = (12, 8),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制分行业表现
        
        Args:
            sector_results: 分行业测试结果
            metric: 要显示的指标
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        sectors = list(sector_results.keys())
        values = [sector_results[s][metric] for s in sectors]
        
        colors = ['green' if v > 0 else 'red' for v in values]
        ax.barh(sectors, values, color=colors, alpha=0.7)
        ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        
        ax.set_title('Performance by Sector')
        ax.set_xlabel(metric)
        ax.set_ylabel(self._get_label('sector'))
        ax.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_robustness_heatmap(
        self,
        results: Dict[str, Dict[str, float]],
        figsize: Tuple[float, float] = (12, 8),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制稳健性热力图
        
        Args:
            results: 测试结果
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        # 准备数据
        data = []
        for group, metrics in results.items():
            row = {'group': group}
            row.update(metrics)
            data.append(row)
        
        df = pd.DataFrame(data).set_index('group')
        
        # 选择要显示的指标
        metrics_to_show = ['ic_mean', 'icir', 'positive_ratio']
        df_subset = df[metrics_to_show]
        
        sns.heatmap(df_subset, annot=True, cmap='RdYlGn', center=0, fmt='.4f', ax=ax)
        
        ax.set_title('Robustness Heatmap')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 综合仪表盘
    def plot_factor_dashboard(
        self,
        factor_results: Dict[str, float],
        figsize: Tuple[float, float] = (14, 10),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制因子综合仪表盘
        
        Args:
            factor_results: 因子分析结果
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig = plt.figure(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        # 创建子图
        gs = fig.add_gridspec(3, 2)
        
        # 1. IC相关指标
        ax1 = fig.add_subplot(gs[0, 0])
        ic_metrics = ['ic_mean', 'icir', 'ic_positive_ratio']
        ic_values = [factor_results.get(m, 0) for m in ic_metrics]
        ax1.bar(ic_metrics, ic_values, alpha=0.7)
        ax1.set_title('IC Metrics')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 2. 收益相关指标
        ax2 = fig.add_subplot(gs[0, 1])
        return_metrics = ['annualized_return', 'sharpe_ratio', 'max_drawdown']
        return_values = [factor_results.get(m, 0) for m in return_metrics]
        ax2.bar(return_metrics, return_values, alpha=0.7)
        ax2.set_title('Return Metrics')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 3. 风险相关指标
        ax3 = fig.add_subplot(gs[1, 0])
        risk_metrics = ['beta', 'tracking_error', 'downside_risk']
        risk_values = [factor_results.get(m, 0) for m in risk_metrics]
        ax3.bar(risk_metrics, risk_values, alpha=0.7)
        ax3.set_title('Risk Metrics')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. 其他指标
        ax4 = fig.add_subplot(gs[1, 1])
        other_metrics = ['turnover', 'half_life', 'robustness_score']
        other_values = [factor_results.get(m, 0) for m in other_metrics]
        ax4.bar(other_metrics, other_values, alpha=0.7)
        ax4.set_title('Other Metrics')
        ax4.grid(True, alpha=0.3, axis='y')
        
        # 5. 总评分
        ax5 = fig.add_subplot(gs[2, :])
        if 'total_score' in factor_results:
            score = factor_results['total_score']
            ax5.bar(['Total Score'], [score], color='green' if score >= 0.6 else 'red', alpha=0.8)
            ax5.axhline(y=0.6, color='green', linestyle='--', label='Good')
            ax5.axhline(y=0.8, color='darkgreen', linestyle='--', label='Excellent')
            ax5.set_ylim(0, 1.1)
            ax5.legend()
        ax5.set_title('Total Score')
        ax5.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_score_breakdown(
        self,
        scores: Dict[str, float],
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制评分分解图
        
        Args:
            scores: 各维度评分
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        categories = list(scores.keys())
        values = list(scores.values())
        
        colors = sns.color_palette(self.color_palette, len(categories))
        ax.bar(categories, values, color=colors, alpha=0.7)
        ax.axhline(y=0.6, color='green', linestyle='--', label='Good')
        ax.axhline(y=0.8, color='darkgreen', linestyle='--', label='Excellent')
        
        ax.set_title('Score Breakdown')
        ax.set_xlabel('Dimension')
        ax.set_ylabel(self._get_label('score'))
        ax.set_ylim(0, 1.1)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    def plot_factor_comparison_matrix(
        self,
        factors_data: Dict[str, Dict[str, float]],
        figsize: Tuple[float, float] = (14, 10),
        cmap: str = 'RdYlGn',
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制多因子对比矩阵
        
        Args:
            factors_data: 多因子数据
            figsize: 图表大小
            cmap: 颜色映射
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        # 转换为DataFrame
        df = pd.DataFrame(factors_data).T
        
        sns.heatmap(df, annot=True, cmap=cmap, center=0, fmt='.4f', ax=ax)
        
        ax.set_title('Factor Comparison Matrix')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 缺失的方法：plot_ic_series
    def plot_ic_series(
        self,
        ic_series: pd.Series,
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制IC时间序列
        
        Args:
            ic_series: IC时间序列
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax.bar(ic_series.index, ic_series.values, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.axhline(y=ic_series.mean(), color='red', linestyle='--', label='Mean IC')
        
        ax.set_title('IC Time Series')
        ax.set_xlabel(self._get_label('date'))
        ax.set_ylabel(self._get_label('ic'))
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 缺失的方法：plot_layering_returns
    def plot_layering_returns(
        self,
        group_returns: pd.DataFrame,
        long_short_returns: pd.Series,
        figsize: Tuple[float, float] = (12, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制分层回测收益
        
        Args:
            group_returns: 分组收益DataFrame
            long_short_returns: 多空收益Series
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        # 绘制各分组累计收益
        cumulative_returns = (1 + group_returns).cumprod() - 1
        for col in cumulative_returns.columns:
            ax.plot(cumulative_returns.index, cumulative_returns[col], label=col)
        
        # 绘制多空收益
        if not long_short_returns.empty:
            ls_cumulative = (1 + long_short_returns).cumprod() - 1
            ax.plot(ls_cumulative.index, ls_cumulative, 'k--', linewidth=2, label='Long-Short')
        
        ax.set_title('Layering Backtest Returns')
        ax.set_xlabel(self._get_label('date'))
        ax.set_ylabel(self._get_label('cumulative_return'))
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 缺失的方法：plot_decay_curve
    def plot_decay_curve(
        self,
        decay_curve: pd.Series,
        figsize: Tuple[float, float] = (10, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制衰减曲线
        
        Args:
            decay_curve: 衰减曲线
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        ax.plot(decay_curve.index, decay_curve.values, 'o-', linewidth=2, markersize=8)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        if not decay_curve.isna().all():
            max_period = decay_curve.idxmax()
            max_value = decay_curve.max()
            ax.annotate(f'Max: {max_value:.4f} at {max_period}d',
                        xy=(max_period, max_value),
                        xytext=(max_period + 2, max_value + 0.01),
                        arrowprops=dict(facecolor='black', shrink=0.05))
        
        ax.set_title('Decay Curve')
        ax.set_xlabel('Holding Period (days)')
        ax.set_ylabel(self._get_label('ic'))
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 缺失的方法：plot_robustness_analysis
    def plot_robustness_analysis(
        self,
        regime_results: Dict[str, Dict[str, float]],
        figsize: Tuple[float, float] = (12, 8),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制稳健性分析
        
        Args:
            regime_results: 市场状态测试结果
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        regimes = list(regime_results.keys())
        ic_means = [regime_results[r]['ic_mean'] for r in regimes]
        icirs = [regime_results[r]['icir'] for r in regimes]
        
        x = np.arange(len(regimes))
        width = 0.35
        
        ax.bar(x - width/2, ic_means, width, label='IC Mean', alpha=0.7)
        ax.bar(x + width/2, icirs, width, label='ICIR', alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax.set_title('Robustness Analysis by Market Regime')
        ax.set_xlabel('Market Regime')
        ax.set_ylabel('Value')
        ax.set_xticks(x)
        ax.set_xticklabels(regimes)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig
    
    # 缺失的方法：plot_alpha_beta_analysis
    def plot_alpha_beta_analysis(
        self,
        alpha: float,
        beta: float,
        information_ratio: float,
        figsize: Tuple[float, float] = (10, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        绘制Alpha/Beta分析
        
        Args:
            alpha: Alpha值
            beta: Beta值
            information_ratio: 信息比率
            figsize: 图表大小
            save_path: 保存路径
        
        Returns:
            Figure对象
        """
        fig, ax = plt.subplots(figsize=(
            figsize[0] * self.figsize_scale,
            figsize[1] * self.figsize_scale
        ))
        
        metrics = ['Alpha', 'Beta', 'Information Ratio']
        values = [alpha, beta, information_ratio]
        colors = ['green' if v > 0 else 'red' for v in values]
        
        ax.bar(metrics, values, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.axhline(y=1, color='blue', linestyle='--', linewidth=0.5, label='Beta=1')
        
        ax.set_title('Alpha/Beta Analysis')
        ax.set_ylabel('Value')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        self._save_figure(fig, save_path)
        
        return fig


def plot_ic_ts(
    ic_series: pd.Series,
    figsize: Tuple[float, float] = (12, 4),
    show_mean: bool = True,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    绘制IC时间序列图
    
    便捷函数。
    
    Args:
        ic_series: IC时间序列
        figsize: 图表大小
        show_mean: 是否显示均值线
        save_path: 保存路径
    
    Returns:
        Figure对象
    """
    visualizer = FactorVisualizer()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    ax.bar(ic_series.index, ic_series.values, alpha=0.7)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    if show_mean:
        mean_ic = ic_series.mean()
        ax.axhline(y=mean_ic, color='red', linestyle='--', 
                   label=f'Mean: {mean_ic:.4f}')
        ax.legend()
    
    ax.set_xlabel('Date')
    ax.set_ylabel('IC')
    ax.set_title('IC Time Series')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig

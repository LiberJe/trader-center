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
    ):
        """
        初始化可视化器
        
        Args:
            style: matplotlib样式
            figsize_scale: 图表大小缩放因子
            color_palette: seaborn颜色主题
        """
        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'ggplot')
        sns.set_theme(style=style, palette=color_palette)
        self.figsize_scale = figsize_scale
        self.color_palette = color_palette
    
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

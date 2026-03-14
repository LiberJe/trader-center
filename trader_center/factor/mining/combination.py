"""
因子组合优化

提供因子正交化、权重优化和组合功能。
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
import logging
from scipy import stats
from scipy.linalg import qr

logger = logging.getLogger(__name__)


@dataclass
class CombinationResult:
    """组合结果"""
    weights: pd.Series
    combined_factor: pd.Series
    factor_contributions: pd.DataFrame
    method: str


class FactorCombiner:
    """
    因子组合优化器
    
    提供因子正交化、权重优化和组合功能。
    
    Example:
        combiner = FactorCombiner()
        
        # 正交化
        orthogonal_factors = combiner.orthogonalize(factors_df)
        
        # 优化权重
        weights = combiner.optimize_weights(factors_df, forward_returns)
        
        # 合成因子
        combined = combiner.combine(factors_df, weights)
    """
    
    def __init__(
        self,
        orthogonalize_method: str = 'schmidt',
        weight_method: str = 'icir',
    ):
        """
        初始化因子组合优化器
        
        Args:
            orthogonalize_method: 正交化方法 ('schmidt', 'pca', 'none')
            weight_method: 权重优化方法 ('icir', 'equal', 'ic', 'max_sharpe')
        """
        self.orthogonalize_method = orthogonalize_method
        self.weight_method = weight_method
    
    def orthogonalize(
        self,
        factors: pd.DataFrame,
        method: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        因子正交化
        
        Args:
            factors: 因子DataFrame，每列为一个因子
            method: 正交化方法 ('schmidt', 'pca', 'none')
        
        Returns:
            正交化后的因子DataFrame
        """
        method = method or self.orthogonalize_method
        
        if method == 'none':
            return factors
        
        if method == 'schmidt':
            return self._schmidt_orthogonalize(factors)
        elif method == 'pca':
            return self._pca_orthogonalize(factors)
        else:
            raise ValueError(f"未知的正交化方法: {method}")
    
    def _schmidt_orthogonalize(self, factors: pd.DataFrame) -> pd.DataFrame:
        """
        施密特正交化
        
        Args:
            factors: 因子DataFrame
        
        Returns:
            正交化后的因子
        """
        factors_clean = factors.dropna()
        
        factor_matrix = factors_clean.values
        n_factors = factor_matrix.shape[1]
        
        orthogonal_matrix = np.zeros_like(factor_matrix)
        
        for i in range(n_factors):
            current_factor = factor_matrix[:, i].copy()
            
            for j in range(i):
                projection = np.dot(orthogonal_matrix[:, j], current_factor) / \
                            np.dot(orthogonal_matrix[:, j], orthogonal_matrix[:, j])
                current_factor = current_factor - projection * orthogonal_matrix[:, j]
            
            orthogonal_matrix[:, i] = current_factor
        
        std = np.std(orthogonal_matrix, axis=0)
        std[std == 0] = 1
        orthogonal_matrix = orthogonal_matrix / std
        
        result = pd.DataFrame(
            orthogonal_matrix,
            index=factors_clean.index,
            columns=[f"{col}_ortho" for col in factors.columns],
        )
        
        return result
    
    def _pca_orthogonalize(self, factors: pd.DataFrame) -> pd.DataFrame:
        """
        PCA正交化
        
        Args:
            factors: 因子DataFrame
        
        Returns:
            正交化后的因子
        """
        from sklearn.decomposition import PCA
        
        factors_clean = factors.dropna()
        
        pca = PCA(n_components=factors_clean.shape[1])
        orthogonal_matrix = pca.fit_transform(factors_clean.values)
        
        result = pd.DataFrame(
            orthogonal_matrix,
            index=factors_clean.index,
            columns=[f"PC{i+1}" for i in range(factors_clean.shape[1])],
        )
        
        return result
    
    def optimize_weights(
        self,
        factors: pd.DataFrame,
        forward_returns: pd.Series,
        method: Optional[str] = None,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> pd.Series:
        """
        优化因子权重
        
        Args:
            factors: 因子DataFrame
            forward_returns: 未来收益
            method: 优化方法 ('icir', 'equal', 'ic', 'max_sharpe')
            min_weight: 最小权重
            max_weight: 最大权重
        
        Returns:
            权重Series
        """
        method = method or self.weight_method
        
        if method == 'equal':
            return self._equal_weights(factors)
        elif method == 'ic':
            return self._ic_weights(factors, forward_returns)
        elif method == 'icir':
            return self._icir_weights(factors, forward_returns)
        elif method == 'max_sharpe':
            return self._max_sharpe_weights(factors, forward_returns, min_weight, max_weight)
        else:
            raise ValueError(f"未知的权重优化方法: {method}")
    
    def _equal_weights(self, factors: pd.DataFrame) -> pd.Series:
        """等权重"""
        n = len(factors.columns)
        return pd.Series(1.0 / n, index=factors.columns)
    
    def _ic_weights(self, factors: pd.DataFrame, forward_returns: pd.Series) -> pd.Series:
        """IC加权"""
        ic_values = {}
        
        for col in factors.columns:
            factor_series = factors[col].dropna()
            common_index = factor_series.index.intersection(forward_returns.dropna().index)
            
            if len(common_index) < 10:
                ic_values[col] = 0
                continue
            
            ic, _ = stats.spearmanr(
                factor_series.loc[common_index],
                forward_returns.loc[common_index]
            )
            ic_values[col] = ic if not np.isnan(ic) else 0
        
        ic_series = pd.Series(ic_values)
        
        abs_ic = ic_series.abs()
        weights = abs_ic / abs_ic.sum()
        
        for col in ic_series.index:
            if ic_series[col] < 0:
                weights[col] = -weights[col]
        
        return weights
    
    def _icir_weights(self, factors: pd.DataFrame, forward_returns: pd.Series) -> pd.Series:
        """ICIR加权"""
        from .ic_analysis import ICAnalyzer
        
        icir_values = {}
        
        for col in factors.columns:
            factor_series = factors[col].dropna()
            common_index = factor_series.index.intersection(forward_returns.dropna().index)
            
            if len(common_index) < 20:
                icir_values[col] = 0
                continue
            
            analyzer = ICAnalyzer()
            
            factor_df = factor_series.to_frame()
            returns_df = forward_returns.to_frame()
            
            result = analyzer.compute(factor_df.T, returns_df.T)
            icir = result.get('icir', 0)
            icir_values[col] = icir if not np.isnan(icir) else 0
        
        icir_series = pd.Series(icir_values)
        
        abs_icir = icir_series.abs()
        weights = abs_icir / abs_icir.sum()
        
        for col in icir_series.index:
            if icir_series[col] < 0:
                weights[col] = -weights[col]
        
        return weights
    
    def _max_sharpe_weights(
        self,
        factors: pd.DataFrame,
        forward_returns: pd.Series,
        min_weight: float,
        max_weight: float,
    ) -> pd.Series:
        """最大化夏普比率权重"""
        try:
            from scipy.optimize import minimize
            
            factor_returns = factors.pct_change().dropna()
            
            mean_returns = factor_returns.mean().values
            cov_matrix = factor_returns.cov().values
            
            n = len(mean_returns)
            
            def neg_sharpe(w):
                port_return = np.dot(w, mean_returns)
                port_std = np.sqrt(np.dot(w, np.dot(cov_matrix, w)))
                return -port_return / port_std if port_std > 0 else 0
            
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
            ]
            
            bounds = [(min_weight, max_weight) for _ in range(n)]
            
            initial_weights = np.ones(n) / n
            
            result = minimize(
                neg_sharpe,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
            )
            
            return pd.Series(result.x, index=factors.columns)
        
        except Exception as e:
            logger.warning(f"最大化夏普优化失败: {e}，使用等权重")
            return self._equal_weights(factors)
    
    def combine(
        self,
        factors: pd.DataFrame,
        weights: pd.Series,
        orthogonalize_first: bool = False,
    ) -> CombinationResult:
        """
        合成复合因子
        
        Args:
            factors: 因子DataFrame
            weights: 权重Series
            orthogonalize_first: 是否先正交化
        
        Returns:
            组合结果
        """
        if orthogonalize_first:
            factors = self.orthogonalize(factors)
        
        common_cols = factors.columns.intersection(weights.index)
        factors = factors[common_cols]
        weights = weights[common_cols]
        
        weights = weights / weights.abs().sum()
        
        combined = factors.mul(weights, axis=1).sum(axis=1)
        
        contributions = factors.mul(weights, axis=1)
        contributions.columns = [f"{col}_contrib" for col in contributions.columns]
        
        return CombinationResult(
            weights=weights,
            combined_factor=combined,
            factor_contributions=contributions,
            method=self.weight_method,
        )
    
    def compute_factor_correlation(
        self,
        factors: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        计算因子相关性矩阵
        
        Args:
            factors: 因子DataFrame
        
        Returns:
            相关性矩阵
        """
        return factors.corr()
    
    def remove_redundant_factors(
        self,
        factors: pd.DataFrame,
        threshold: float = 0.7,
        keep_metric: Optional[pd.Series] = None,
    ) -> List[str]:
        """
        移除冗余因子
        
        Args:
            factors: 因子DataFrame
            threshold: 相关性阈值
            keep_metric: 保留指标（值大的优先保留）
        
        Returns:
            保留的因子名称列表
        """
        corr_matrix = factors.corr().abs()
        
        n = len(factors.columns)
        keep = [True] * n
        
        if keep_metric is not None:
            order = keep_metric.abs().sort_values(ascending=False).index.tolist()
        else:
            order = factors.columns.tolist()
        
        for i, col_i in enumerate(order):
            if not keep[factors.columns.get_loc(col_i)]:
                continue
            
            for j, col_j in enumerate(order[i+1:], i+1):
                if not keep[factors.columns.get_loc(col_j)]:
                    continue
                
                if corr_matrix.loc[col_i, col_j] > threshold:
                    keep[factors.columns.get_loc(col_j)] = False
        
        return [col for col, k in zip(factors.columns, keep) if k]


def create_factor_portfolio(
    factors: pd.DataFrame,
    forward_returns: pd.Series,
    n_factors: int = 5,
    method: str = 'icir',
) -> Tuple[pd.Series, pd.Series]:
    """
    创建因子组合
    
    Args:
        factors: 因子DataFrame
        forward_returns: 未来收益
        n_factors: 选择的因子数量
        method: 权重方法
    
    Returns:
        (组合因子, 权重)
    """
    combiner = FactorCombiner(weight_method=method)
    
    weights = combiner.optimize_weights(factors, forward_returns, method)
    
    top_factors = weights.abs().nlargest(n_factors).index
    selected_factors = factors[top_factors]
    selected_weights = weights[top_factors]
    
    result = combiner.combine(selected_factors, selected_weights)
    
    return result.combined_factor, result.weights


def evaluate_factor_combination(
    factors: pd.DataFrame,
    forward_returns: pd.Series,
    weights: pd.Series,
) -> Dict[str, float]:
    """
    评估因子组合效果
    
    Args:
        factors: 因子DataFrame
        forward_returns: 未来收益
        weights: 权重
    
    Returns:
        评估指标字典
    """
    combiner = FactorCombiner()
    result = combiner.combine(factors, weights)
    
    combined = result.combined_factor.dropna()
    returns = forward_returns.dropna()
    
    common_index = combined.index.intersection(returns.index)
    
    if len(common_index) < 10:
        return {'ic': np.nan, 'icir': np.nan}
    
    ic, _ = stats.spearmanr(combined.loc[common_index], returns.loc[common_index])
    
    ic_series = []
    for i in range(len(common_index) - 1):
        date = common_index[i]
        if date in combined.index and date in returns.index:
            single_ic, _ = stats.spearmanr(
                [combined.loc[date]],
                [returns.loc[date]]
            )
            ic_series.append(single_ic)
    
    icir = np.mean(ic_series) / np.std(ic_series) if len(ic_series) > 1 and np.std(ic_series) > 0 else 0
    
    return {
        'ic': ic,
        'icir': icir,
        'mean_combined': combined.mean(),
        'std_combined': combined.std(),
    }

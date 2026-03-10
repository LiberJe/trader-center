"""
多因子打分器

负责管理多个因子、计算因子值、标准化和加权合成综合得分。
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging

from trader_center.factor.library import FactorRegistry, register_factor
from trader_center.factor.library.technical.momentum import MomentumFactor, RSIFactor
from trader_center.factor.library.technical.trend import TrendStrengthFactor
from trader_center.factor.library.technical.volatility import ATRFactor, HistoricalVolatilityFactor


logger = logging.getLogger(__name__)


DEFAULT_FACTOR_CONFIGS = {
    'momentum': {
        'weight': 0.30,
        'direction': 'positive',
        'params': {'period': 20},
    },
    'trend_strength': {
        'weight': 0.25,
        'direction': 'positive',
        'params': {'period': 20},
    },
    'rsi': {
        'weight': 0.15,
        'direction': 'negative',
        'params': {'period': 14},
    },
    'historical_volatility': {
        'weight': 0.15,
        'direction': 'negative',
        'params': {'period': 20},
    },
    'atr': {
        'weight': 0.15,
        'direction': 'negative',
        'params': {'period': 14},
    },
}


class FactorScorer:
    """
    多因子打分器
    
    管理多个因子，计算因子值，标准化后加权合成综合得分。
    
    Example:
        scorer = FactorScorer({
            'momentum': {'weight': 0.3, 'direction': 'positive', 'params': {'period': 20}},
            'rsi': {'weight': 0.2, 'direction': 'negative', 'params': {'period': 14}},
        })
        
        data_dict = {
            '510300.SH': df1,
            '518880.SH': df2,
        }
        
        scores = scorer.compute_scores(data_dict)
        # {'510300.SH': 0.85, '518880.SH': -0.32}
    """
    
    def __init__(self, factor_configs: Optional[Dict[str, Dict]] = None):
        """
        初始化因子打分器
        
        Args:
            factor_configs: 因子配置字典，格式如下：
                {
                    'factor_name': {
                        'weight': 0.3,           # 因子权重
                        'direction': 'positive', # 因子方向: 'positive' 或 'negative'
                        'params': {'period': 20} # 因子参数
                    }
                }
                如果为 None，使用默认配置
        """
        self.factor_configs = factor_configs or DEFAULT_FACTOR_CONFIGS
        self.registry = FactorRegistry()
        self._validate_configs()
        self._register_factors()
    
    def _validate_configs(self):
        """验证因子配置"""
        total_weight = sum(cfg['weight'] for cfg in self.factor_configs.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"因子权重总和不为1: {total_weight:.2f}")
        
        for name, cfg in self.factor_configs.items():
            if 'weight' not in cfg:
                raise ValueError(f"因子 {name} 缺少 'weight' 配置")
            if 'direction' not in cfg:
                raise ValueError(f"因子 {name} 缺少 'direction' 配置")
            if cfg['direction'] not in ['positive', 'negative']:
                raise ValueError(f"因子 {name} 的 direction 必须是 'positive' 或 'negative'")
    
    def _register_factors(self):
        """注册因子到注册器"""
        factor_classes = {
            'momentum': MomentumFactor,
            'rsi': RSIFactor,
            'trend_strength': TrendStrengthFactor,
            'historical_volatility': HistoricalVolatilityFactor,
            'atr': ATRFactor,
        }
        
        for factor_name, cfg in self.factor_configs.items():
            if factor_name not in factor_classes:
                logger.warning(f"因子 {factor_name} 未找到对应的因子类，跳过")
                continue
            
            try:
                params = cfg.get('params', {})
                factor_class = factor_classes[factor_name]
                factor = factor_class(**params)
                self.registry.register(factor)
                logger.debug(f"注册因子: {factor_name}, 参数: {params}")
            except Exception as e:
                logger.error(f"注册因子 {factor_name} 失败: {e}")
    
    def compute_scores(
        self,
        data_dict: Dict[str, pd.DataFrame],
        lookback: int = 60,
    ) -> Dict[str, float]:
        """
        计算所有资产的综合得分
        
        Args:
            data_dict: 资产代码到数据的映射 {symbol: DataFrame}
            lookback: 计算因子时使用的历史数据长度
        
        Returns:
            资产代码到综合得分的映射 {symbol: score}
        """
        factor_values = self._compute_factor_values(data_dict, lookback)
        
        standardized = self._standardize_cross_sectional(factor_values)
        
        scores = self._aggregate_scores(standardized)
        
        return scores
    
    def _compute_factor_values(
        self,
        data_dict: Dict[str, pd.DataFrame],
        lookback: int,
    ) -> Dict[str, Dict[str, float]]:
        """
        计算每个资产的每个因子值
        
        Args:
            data_dict: 资产数据字典
            lookback: 历史数据长度
        
        Returns:
            {symbol: {factor_name: latest_factor_value}}
        """
        factor_values = {}
        
        for symbol, data in data_dict.items():
            if len(data) < lookback:
                logger.warning(f"资产 {symbol} 数据不足 {lookback} 天，跳过")
                continue
            
            data_slice = data.tail(lookback).copy()
            
            factor_values[symbol] = {}
            
            for factor_name, cfg in self.factor_configs.items():
                try:
                    factor = self.registry.get(factor_name)
                    params = cfg.get('params', {})
                    if params:
                        factor.set_params(**params)
                    
                    values = factor.compute(data_slice)
                    
                    latest_value = values.iloc[-1]
                    
                    if pd.isna(latest_value):
                        latest_value = 0.0
                    
                    factor_values[symbol][factor_name] = latest_value
                    
                except Exception as e:
                    logger.error(f"计算因子 {factor_name} 失败 (symbol={symbol}): {e}")
                    factor_values[symbol][factor_name] = 0.0
        
        return factor_values
    
    def _standardize_cross_sectional(
        self,
        factor_values: Dict[str, Dict[str, float]],
    ) -> Dict[str, Dict[str, float]]:
        """
        横截面标准化因子值
        
        对每个因子，在所有资产间进行 Z-score 标准化。
        
        Args:
            factor_values: {symbol: {factor_name: value}}
        
        Returns:
            标准化后的 {symbol: {factor_name: standardized_value}}
        """
        symbols = list(factor_values.keys())
        factor_names = list(self.factor_configs.keys())
        
        factor_matrix = pd.DataFrame(index=symbols, columns=factor_names)
        for symbol in symbols:
            for factor_name in factor_names:
                factor_matrix.loc[symbol, factor_name] = factor_values[symbol].get(factor_name, 0.0)
        
        factor_matrix = factor_matrix.astype(float)
        
        standardized = pd.DataFrame(index=symbols, columns=factor_names)
        for factor_name in factor_names:
            values = factor_matrix[factor_name]
            
            mean = values.mean()
            std = values.std()
            
            if std == 0 or pd.isna(std):
                standardized[factor_name] = 0.0
            else:
                standardized[factor_name] = (values - mean) / std
        
        result = {}
        for symbol in symbols:
            result[symbol] = {}
            for factor_name in factor_names:
                result[symbol][factor_name] = standardized.loc[symbol, factor_name]
        
        return result
    
    def _aggregate_scores(
        self,
        standardized: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        """
        加权合成综合得分
        
        Args:
            standardized: 标准化后的因子值
        
        Returns:
            {symbol: composite_score}
        """
        scores = {}
        
        for symbol, factor_scores in standardized.items():
            composite = 0.0
            
            for factor_name, value in factor_scores.items():
                cfg = self.factor_configs[factor_name]
                weight = cfg['weight']
                direction = cfg['direction']
                
                if direction == 'negative':
                    value = -value
                
                composite += weight * value
            
            scores[symbol] = composite
        
        return scores
    
    def get_factor_info(self) -> pd.DataFrame:
        """
        获取因子配置信息
        
        Returns:
            因子配置的 DataFrame
        """
        rows = []
        for name, cfg in self.factor_configs.items():
            rows.append({
                'factor': name,
                'weight': cfg['weight'],
                'direction': cfg['direction'],
                'params': str(cfg.get('params', {})),
            })
        return pd.DataFrame(rows)
    
    def __repr__(self) -> str:
        return f"FactorScorer(factors={len(self.factor_configs)})"

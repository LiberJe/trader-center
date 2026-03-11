"""
多因子轮动策略

基于多因子打分的资产轮动策略，演示如何使用因子库进行资产配置。
"""

import backtrader as bt
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging

from .base import BaseStrategy
from .factor_scorer import FactorScorer, DEFAULT_FACTOR_CONFIGS
from .asset_allocation import ASSET_CONFIG


logger = logging.getLogger(__name__)


class MultiFactorRotationStrategy(BaseStrategy):
    """
    多因子轮动策略
    
    基于多个因子综合评分进行资产轮动：
    1. 计算每个资产的多个因子值
    2. 横截面标准化因子值
    3. 加权合成综合得分
    4. 选择得分最高的N个资产
    5. 定期再平衡
    
    策略特点:
    - 因子驱动: 基于多因子综合评分进行资产选择
    - 动态轮动: 根据因子得分动态调整持仓
    - 风险分散: 持有多只资产，降低单一资产风险
    - 可扩展: 易于添加新因子或调整因子权重
    
    Params:
        rebalance_freq: 再平衡频率（交易日），默认20天
        top_n: 持仓资产数量，默认3
        factor_configs: 因子配置字典
        min_score: 最低得分阈值，低于此值的资产不持有
        lookback: 因子计算的历史数据长度
        exec_type: 订单执行类型，'open'为次日开盘价，'close'为次日收盘价
    """
    
    name = "multi_factor_rotation"
    description = "基于多因子打分的资产轮动策略"
    
    params = (
        ('rebalance_freq', 20),
        ('top_n', 3),
        ('factor_configs', None),
        ('min_score', -np.inf),
        ('lookback', 60),
        ('exec_type', 'open'),
    )
    
    def __init__(self):
        super().__init__()
        
        factor_configs = self.p.factor_configs or DEFAULT_FACTOR_CONFIGS
        self.scorer = FactorScorer(factor_configs)
        
        self.data_cache: Dict[str, List[Dict]] = {}
        self.data_dfs: Dict[str, pd.DataFrame] = {}
        
        self.last_rebalance_day: Optional[int] = None
        self.initialized = False
        self.data_names: List[str] = []
        
        self.max_cache_size = self.p.lookback + 20
        
        for data in self.datas:
            name = data._name if hasattr(data, '_name') else 'unknown'
            self.data_names.append(name)
            self.data_cache[name] = []
        
        self.log(f"策略初始化: 资产数量={len(self.datas)}, 持仓数量={self.p.top_n}")
        self.log(f"因子配置: {list(self.scorer.factor_configs.keys())}")
        self.log(f"订单执行类型: {self.p.exec_type} ({'次日开盘价' if self.p.exec_type == 'open' else '次日收盘价'})")
    
    def _order_target_percent(self, data, target: float):
        """
        下单调整仓位到目标百分比
        
        Args:
            data: 数据对象
            target: 目标仓位百分比 (0.0 ~ 1.0)
        
        Returns:
            订单对象
        """
        if self.p.exec_type == 'close':
            return self.order_target_percent(data=data, target=target, exectype=bt.Order.Close)
        else:
            return self.order_target_percent(data=data, target=target)
    
    def prenext(self):
        """预热期 - 缓存数据"""
        self._update_data_cache()
    
    def nextstart(self):
        """第一个有效交易日 - 开始缓存数据"""
        self._update_data_cache()
        self.log(f"数据预热完成，开始等待足够数据计算因子")
    
    def next(self):
        """每日执行"""
        self._log_daily_state()
        
        self._update_data_cache()
        
        if not self._has_enough_data():
            return
        
        if not self.initialized:
            self._initial_rebalance()
            self.initialized = True
            self.last_rebalance_day = len(self.datas[0])
            return
        
        if self._should_rebalance():
            self._rebalance()
            self.last_rebalance_day = len(self.datas[0])
    
    def _update_data_cache(self):
        """更新数据缓存"""
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            
            bar_data = {
                'open': data.open[0],
                'high': data.high[0],
                'low': data.low[0],
                'close': data.close[0],
                'volume': data.volume[0],
            }
            
            self.data_cache[symbol].append(bar_data)
            
            if len(self.data_cache[symbol]) > self.max_cache_size:
                self.data_cache[symbol] = self.data_cache[symbol][-self.max_cache_size:]
    
    def _has_enough_data(self) -> bool:
        """检查是否有足够的数据计算因子"""
        for symbol in self.data_names:
            if len(self.data_cache[symbol]) < self.p.lookback:
                return False
        return True
    
    def _get_data_dfs(self) -> Dict[str, pd.DataFrame]:
        """将缓存数据转换为 DataFrame"""
        data_dfs = {}
        
        for symbol in self.data_names:
            cache = self.data_cache[symbol][-self.p.lookback:]
            
            df = pd.DataFrame(cache)
            
            if len(df) >= self.p.lookback:
                data_dfs[symbol] = df
        
        return data_dfs
    
    def _should_rebalance(self) -> bool:
        """
        判断是否需要再平衡
        
        条件: 达到再平衡频率
        
        Returns:
            bool: 是否需要再平衡
        """
        if self.last_rebalance_day is None:
            return True
        
        current_day = len(self.datas[0])
        days_since_rebalance = current_day - self.last_rebalance_day
        
        if days_since_rebalance >= self.p.rebalance_freq:
            self.log(f"触发定期再平衡: 距上次 {days_since_rebalance} 天")
            return True
        
        return False
    
    def _compute_scores(self) -> Dict[str, float]:
        """
        计算所有资产的因子得分
        
        Returns:
            {symbol: score}
        """
        data_dfs = self._get_data_dfs()
        
        if not data_dfs:
            return {}
        
        scores = self.scorer.compute_scores(data_dfs, lookback=self.p.lookback)
        
        return scores
    
    def _select_assets(self, scores: Dict[str, float]) -> List[str]:
        """
        选择得分最高的N个资产
        
        Args:
            scores: {symbol: score}
        
        Returns:
            选中的资产代码列表
        """
        sorted_assets = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        selected = []
        for symbol, score in sorted_assets[:self.p.top_n]:
            if score >= self.p.min_score:
                selected.append(symbol)
            else:
                self.log(f"资产 {symbol} 得分 {score:.4f} 低于阈值 {self.p.min_score}, 跳过")
        
        return selected
    
    def _initial_rebalance(self):
        """初始建仓"""
        self.log("开始初始建仓...")
        
        scores = self._compute_scores()
        
        if not scores:
            self.log("无法计算因子得分，跳过初始建仓")
            return
        
        selected = self._select_assets(scores)
        
        if not selected:
            self.log("没有符合条件的资产，跳过初始建仓")
            return
        
        self.log(f"初始选中资产: {selected}")
        
        weight_per_asset = 0.95 / len(selected)
        
        for symbol in selected:
            score = scores[symbol]
            asset_info = ASSET_CONFIG.get(symbol, {})
            asset_name = asset_info.get('name', symbol)
            
            self.log_signal(
                signal_type='buy',
                data=self._get_data_by_symbol(symbol),
                trigger_condition=f'初始建仓: {asset_name} 得分 {score:.4f}',
                indicator_values={
                    'score': score,
                    'target_weight': weight_per_asset,
                },
                confidence=min(1.0, (score + 2) / 4),
            )
        
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            
            if symbol in selected:
                self._order_target_percent(data=data, target=weight_per_asset)
            else:
                position = self.getposition(data)
                if position.size > 0:
                    self._order_target_percent(data=data, target=0)
        
        self.log(f"初始建仓完成，选中 {len(selected)} 个资产，每个权重 {weight_per_asset:.2%}")
    
    def _rebalance(self):
        """执行再平衡"""
        self.log("开始执行再平衡...")
        
        scores = self._compute_scores()
        
        if not scores:
            self.log("无法计算因子得分，跳过再平衡")
            return
        
        self.log(f"因子得分: {scores}")
        
        selected = self._select_assets(scores)
        
        if not selected:
            self.log("没有符合条件的资产，清仓")
            for data in self.datas:
                position = self.getposition(data)
                if position.size > 0:
                    self._order_target_percent(data=data, target=0)
            return
        
        weight_per_asset = 0.95 / len(selected)
        
        rebalance_info = []
        
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            position = self.getposition(data)
            
            current_weight = 0.0
            if position.size > 0:
                total_value = self.broker.getvalue()
                market_value = position.size * data.close[0]
                current_weight = market_value / total_value
            
            if symbol in selected:
                target_weight = weight_per_asset
                score = scores[symbol]
            else:
                target_weight = 0.0
                score = scores.get(symbol, 0)
            
            asset_info = ASSET_CONFIG.get(symbol, {})
            asset_name = asset_info.get('name', symbol)
            
            rebalance_info.append({
                'symbol': symbol,
                'name': asset_name,
                'current_weight': current_weight,
                'target_weight': target_weight,
                'score': score,
            })
            
            if abs(current_weight - target_weight) > 0.01:
                self.log_signal(
                    signal_type='rebalance',
                    data=data,
                    trigger_condition=f'再平衡: {asset_name} 权重 {current_weight:.2%} -> {target_weight:.2%}',
                    indicator_values={
                        'score': score,
                        'current_weight': current_weight,
                        'target_weight': target_weight,
                    },
                    confidence=min(1.0, (score + 2) / 4) if score else 0.5,
                )
                
                self._order_target_percent(data=data, target=target_weight)
        
        self.log("再平衡执行完成")
        
        for info in rebalance_info:
            if info['target_weight'] > 0 or info['current_weight'] > 0:
                self.log(
                    f"  {info['name']}: 得分={info['score']:.4f}, "
                    f"权重 {info['current_weight']:.2%} -> {info['target_weight']:.2%}"
                )
    
    def _get_data_by_symbol(self, symbol: str):
        """根据 symbol 获取 data 对象"""
        for data in self.datas:
            name = data._name if hasattr(data, '_name') else 'unknown'
            if name == symbol:
                return data
        return None
    
    def stop(self):
        """回测结束"""
        self._log_daily_state()
        
        portfolio_value = self.broker.getvalue()
        cash = self.broker.getcash()
        
        self.log(f"回测结束: 总资产={portfolio_value:.2f}, 现金={cash:.2f}")
        
        self.log("最终持仓:")
        for data in self.datas:
            position = self.getposition(data)
            if position.size > 0:
                symbol = data._name if hasattr(data, '_name') else 'unknown'
                asset_info = ASSET_CONFIG.get(symbol, {})
                asset_name = asset_info.get('name', symbol)
                market_value = position.size * data.close[0]
                weight = market_value / portfolio_value
                
                self.log(
                    f"  {asset_name}: 数量={int(position.size)}, "
                    f"市值={market_value:.2f}, 权重={weight:.2%}"
                )

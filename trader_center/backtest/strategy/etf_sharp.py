"""
ETF夏普比率轮动策略

基于四因子综合评分的ETF轮动策略，核心因子包括：
- 夏普比率因子（核心）
- 动量因子
- 波动率因子
- 最大回撤因子
"""

import backtrader as bt
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging

from .base import BaseStrategy
from .factor_scorer import FactorScorer, ETF_SHARP_FACTOR_CONFIGS, DEFAULT_NORMALIZATION_CONFIG
from .asset_allocation import ASSET_CONFIG


logger = logging.getLogger(__name__)


class ETFSharpStrategy(BaseStrategy):
    """
    ETF夏普比率轮动策略
    
    基于四因子综合评分进行ETF资产选择和轮动：
    1. 计算每个ETF的四个因子值
    2. 极端值处理 (Winsorize)
    3. 横截面标准化 (Z-score)
    4. 方向调整
    5. 加权合成综合得分
    6. 选择得分最高的N个ETF
    7. 定期再平衡
    
    因子配置:
    - sharpe_ratio: 权重 0.40, 方向 positive
    - momentum: 权重 0.25, 方向 positive
    - historical_volatility: 权重 0.20, 方向 negative
    - max_drawdown: 权重 0.15, 方向 negative
    
    策略特点:
    - 风险调整收益导向：以夏普比率为核心因子
    - 多因子综合评分：避免单一因子偏差
    - 归一化处理：极端值处理 + Z-score标准化
    - 动态轮动：定期根据因子得分调整持仓
    
    Params:
        rebalance_freq: 再平衡频率（交易日），默认20天
        top_n: 持仓ETF数量，默认3
        lookback: 因子计算窗口，默认60天
        factor_configs: 因子配置字典
        normalization_config: 归一化配置
        min_score: 最低综合得分阈值
        weighting_method: 权重分配方法，'equal'或'score_weighted'
        exec_type: 订单执行类型，'open'或'close'
    """
    
    name = "etf_sharp"
    description = "ETF夏普比率轮动策略"
    
    params = (
        ('rebalance_freq', 5),
        ('top_n', 3),
        ('lookback', 60),
        ('factor_configs', None),
        ('normalization_config', None),
        ('min_score', -np.inf),
        ('weighting_method', 'equal'),
        ('exec_type', 'open'),
        ('stop_loss_pct', 0.10),
        ('trailing_stop_pct', 0.05),
        ('trailing_stop_enabled', True),
        ('stop_loss_cooldown', 5),
    )
    
    def __init__(self):
        super().__init__()
        
        factor_configs = self.p.factor_configs or ETF_SHARP_FACTOR_CONFIGS
        normalization_config = self.p.normalization_config or DEFAULT_NORMALIZATION_CONFIG
        
        self.scorer = FactorScorer(
            factor_configs=factor_configs,
            normalization_config=normalization_config,
        )
        
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
        
        self.entry_prices: Dict[str, float] = {}
        self.highest_prices: Dict[str, float] = {}
        self.stop_loss_dates: Dict[str, int] = {}
        self.position_sizes: Dict[str, int] = {}
        
        self.log(f"策略初始化: 资产数量={len(self.datas)}, 持仓数量={self.p.top_n}")
        self.log(f"因子配置: {list(self.scorer.factor_configs.keys())}")
        self.log(f"归一化方法: {normalization_config.get('standardize', {}).get('method', 'zscore')}")
        self.log(f"权重分配方法: {self.p.weighting_method}")
        self.log(f"订单执行类型: {self.p.exec_type} ({'次日开盘价' if self.p.exec_type == 'open' else '次日收盘价'})")
        self.log(f"止损比例: {self.p.stop_loss_pct:.1%}, 移动止盈: {self.p.trailing_stop_pct:.1%}, 冷却期: {self.p.stop_loss_cooldown}天")
    
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
        
        self._check_stop_loss()
        
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
        for symbol, score in sorted_assets:
            if len(selected) >= self.p.top_n:
                break
            
            if self._is_in_cooldown(symbol):
                self.log(f"资产 {symbol} 在止损冷却期内，跳过")
                continue
            
            if score >= self.p.min_score:
                selected.append(symbol)
            else:
                self.log(f"资产 {symbol} 得分 {score:.4f} 低于阈值 {self.p.min_score}, 跳过")
        
        return selected
    
    def _calculate_weights(self, selected: List[str], scores: Dict[str, float]) -> Dict[str, float]:
        """
        计算持仓权重
        
        Args:
            selected: 选中的资产列表
            scores: 综合得分字典
        
        Returns:
            {symbol: weight}
        """
        if not selected:
            return {}
        
        if self.p.weighting_method == 'equal':
            weight_per_asset = 0.95 / len(selected)
            return {symbol: weight_per_asset for symbol in selected}
        
        elif self.p.weighting_method == 'score_weighted':
            positive_scores = {s: max(scores.get(s, 0), 0) for s in selected}
            total_score = sum(positive_scores.values())
            
            if total_score <= 0:
                weight_per_asset = 0.95 / len(selected)
                return {symbol: weight_per_asset for symbol in selected}
            
            weights = {}
            for symbol in selected:
                weights[symbol] = 0.95 * positive_scores[symbol] / total_score
            
            return weights
        
        else:
            weight_per_asset = 0.95 / len(selected)
            return {symbol: weight_per_asset for symbol in selected}
    
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
        
        weights = self._calculate_weights(selected, scores)
        
        for symbol in selected:
            score = scores[symbol]
            weight = weights[symbol]
            asset_info = ASSET_CONFIG.get(symbol, {})
            asset_name = asset_info.get('name', symbol)
            
            self.log_signal(
                signal_type='buy',
                data=self._get_data_by_symbol(symbol),
                trigger_condition=f'初始建仓: {asset_name} 得分 {score:.4f}, 权重 {weight:.2%}',
                indicator_values={
                    'score': score,
                    'target_weight': weight,
                },
                confidence=min(1.0, (score + 2) / 4),
            )
        
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            
            if symbol in weights:
                self._order_target_percent(data=data, target=weights[symbol])
            else:
                position = self.getposition(data)
                if position.size > 0:
                    self._order_target_percent(data=data, target=0)
        
        self.log(f"初始建仓完成，选中 {len(selected)} 个资产")
        for symbol, weight in weights.items():
            self.log(f"  {symbol}: 权重 {weight:.2%}")
    
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
        
        weights = self._calculate_weights(selected, scores)
        
        rebalance_info = []
        
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            position = self.getposition(data)
            
            current_weight = 0.0
            if position.size > 0:
                total_value = self.broker.getvalue()
                market_value = position.size * data.close[0]
                current_weight = market_value / total_value
            
            target_weight = weights.get(symbol, 0.0)
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
    
    def _check_stop_loss(self):
        """
        检查并执行止损
        
        遍历所有持仓，检查是否触发止损或移动止盈条件
        """
        current_day = len(self.datas[0])
        
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            position = self.getposition(data)
            
            if position.size <= 0:
                continue
            
            current_price = data.close[0]
            
            if symbol not in self.entry_prices:
                self.entry_prices[symbol] = current_price
                self.highest_prices[symbol] = current_price
                self.position_sizes[symbol] = int(position.size)
                continue
            
            entry_price = self.entry_prices[symbol]
            
            if symbol not in self.highest_prices:
                self.highest_prices[symbol] = entry_price
            
            self.highest_prices[symbol] = max(self.highest_prices[symbol], current_price)
            highest_price = self.highest_prices[symbol]
            
            loss_pct = (current_price - entry_price) / entry_price
            
            asset_info = ASSET_CONFIG.get(symbol, {})
            asset_name = asset_info.get('name', symbol)
            
            stop_triggered = False
            stop_type = None
            
            if loss_pct <= -self.p.stop_loss_pct:
                stop_triggered = True
                stop_type = 'stop_loss'
                trigger_msg = f'止损卖出: {asset_name} 亏损 {loss_pct:.2%} (阈值 {self.p.stop_loss_pct:.1%})'
            
            elif self.p.trailing_stop_enabled and current_price < highest_price:
                drawdown_from_high = (highest_price - current_price) / highest_price
                
                if drawdown_from_high >= self.p.trailing_stop_pct and loss_pct > 0:
                    stop_triggered = True
                    stop_type = 'trailing_stop'
                    trigger_msg = (
                        f'移动止盈: {asset_name} 从最高点 {highest_price:.3f} '
                        f'回撤 {drawdown_from_high:.2%} (阈值 {self.p.trailing_stop_pct:.1%})'
                    )
            
            if stop_triggered:
                self.log_signal(
                    signal_type=stop_type,
                    data=data,
                    trigger_condition=trigger_msg,
                    indicator_values={
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'highest_price': highest_price,
                        'loss_pct': loss_pct,
                        'position_size': int(position.size),
                    },
                    confidence=1.0,
                )
                
                self._order_target_percent(data=data, target=0)
                
                self.stop_loss_dates[symbol] = current_day
                
                self.log(trigger_msg)
                
                if symbol in self.entry_prices:
                    del self.entry_prices[symbol]
                if symbol in self.highest_prices:
                    del self.highest_prices[symbol]
                if symbol in self.position_sizes:
                    del self.position_sizes[symbol]
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """
        检查资产是否在止损冷却期内
        
        Args:
            symbol: 资产代码
        
        Returns:
            bool: 是否在冷却期内
        """
        if symbol not in self.stop_loss_dates:
            return False
        
        current_day = len(self.datas[0])
        stop_day = self.stop_loss_dates[symbol]
        days_since_stop = current_day - stop_day
        
        return days_since_stop < self.p.stop_loss_cooldown
    
    def _update_entry_price(self, symbol: str, price: float, size: int):
        """
        更新买入均价（加权平均）
        
        Args:
            symbol: 资产代码
            price: 买入价格
            size: 买入数量
        """
        if symbol in self.entry_prices and symbol in self.position_sizes:
            old_size = self.position_sizes[symbol]
            old_price = self.entry_prices[symbol]
            
            new_size = old_size + size
            new_price = (old_price * old_size + price * size) / new_size
            
            self.entry_prices[symbol] = new_price
            self.position_sizes[symbol] = new_size
        else:
            self.entry_prices[symbol] = price
            self.position_sizes[symbol] = size
            self.highest_prices[symbol] = price
    
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
        
        self.log(f"归一化配置: {self.scorer.get_normalization_info()}")

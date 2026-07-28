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

ASSET_CONFIG = {
    # 宽基指数
    '510300.SH': {'name': '沪深300ETF', 'category': 'equity_cn'},
    '159915.SZ': {'name': '创业板ETF', 'category': 'equity_cn'},

    # 海外
    '513100.SH': {'name': '纳指ETF', 'category': 'equity_us'},

    # 策略
    # '512890.SH': {'name': '红利低波ETF', 'category': 'equity_cn'},

    # 行业指数


    # 债券
    '511010.SH': {'name': '国债ETF', 'category': 'bond'},  # 5年期国债
    # '511260.SH': {'name': '十年国债ETF', 'category': 'bond', 'theme': '长债'},          # 10年期国债

    # 商品
    '518880.SH': {'name': '黄金ETF', 'category': 'commodity'},
    '159981.SZ': {'name': '能源化工ETF', 'category': 'commodity'},
    # '159985.SZ': {'name': '豆粕ETF', 'category': 'commodity'},
    # '159980.SZ': {'name': '有色ETF', 'category': 'commodity'},
}


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
        # 再平衡频率参数（动态化）
        ('rebalance_freq', 5),             # 兼容旧接口：基础再平衡频率
        ('min_rebalance_freq', 5),         # 最短再平衡间隔（交易日）
        ('max_rebalance_freq', 20),        # 最长再平衡间隔（交易日）
        ('rebalance_threshold', 0.08),     # 权重偏离触发阈值
        ('score_change_threshold', 0.8),   # 得分跳跃触发阈值（Z-score单位）

        # 持仓数量参数（动态化）
        ('top_n', 3),                      # 兼容旧接口：默认持仓数量
        ('top_n_max', 3),                  # 最大持仓数量
        ('top_n_min', 0),                  # 最小持仓数量
        ('use_dynamic_top_n', True),       # 是否开启动态 top_n
        ('score_gap_threshold', 0.5),      # 与前一名最大允许得分差距

        ('lookback', 60),
        ('factor_configs', None),
        ('normalization_config', None),
        ('weighting_method', 'equal'),
        ('exec_type', 'close'),
        ('stop_loss_pct', 0.10),
        ('trailing_stop_pct', 0.05),
        ('trailing_stop_enabled', True),
        ('stop_loss_cooldown', 5),
        ('score_smooth_periods', 1),       # 得分平滑周期数（1=不平滑）
        ('entry_confirmation', 1),         # 新资产入场确认次数（1=无延迟）
        ('max_position_pct', 0.95),        # 最大仓位比例（5%现金缓冲）
        ('max_single_position_pct', 0.40), # 单资产最大权重，防止动态top_n下过度集中
        ('min_rebalance_pct', 0.02),       # 最小调仓阈值
        ('max_turnover_pct', 0.2),         # 单次再平衡最大换手率（0=不限制）
        ('min_score', 0.0),                # 最低得分阈值（动态top_n下建议>=0）
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
        self.score_history: Dict[str, List[float]] = {s: [] for s in self.data_names}
        self.selection_history: Dict[str, int] = {s: 0 for s in self.data_names}
        self.last_selected: List[str] = []
        self.last_scores: Dict[str, float] = {}
        self._orders_today: set = set()

        self.log(f"策略初始化: 资产数量={len(self.datas)}, 最大持仓数量={self.p.top_n_max}")
        self.log(f"动态调仓: 间隔 {self.p.min_rebalance_freq}-{self.p.max_rebalance_freq} 天, 权重偏离阈值 {self.p.rebalance_threshold:.1%}, 得分跳跃阈值 {self.p.score_change_threshold:.2f}")
        self.log(f"动态持仓: 开启={self.p.use_dynamic_top_n}, 范围 {self.p.top_n_min}-{self.p.top_n_max}, 得分 gap 阈值 {self.p.score_gap_threshold:.2f}")
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
        symbol = data._name if hasattr(data, '_name') else 'unknown'
        self._orders_today.add(symbol)

        if self.p.exec_type == 'close':
            return self.order_target_percent(data=data, target=target, exectype=bt.Order.Close)
        else:
            return self.order_target_percent(data=data, target=target)

    def notify_order(self, order: bt.Order):
        """
        订单状态通知回调

        维护持仓成本价和最高价，用于止损/移动止盈计算。
        """
        super().notify_order(order)

        if order.status != order.Completed:
            return

        symbol = order.data._name if hasattr(order.data, '_name') else 'unknown'
        exec_price = order.executed.price
        exec_size = int(abs(order.executed.size))

        if order.isbuy():
            # 买入时更新加权平均成本与最高价
            self._update_entry_price(symbol, exec_price, exec_size)
        else:
            # 卖出时减少持仓数量；若全部卖出则清空跟踪状态
            old_size = self.position_sizes.get(symbol, 0)
            new_size = max(0, old_size - exec_size)
            self.position_sizes[symbol] = new_size

            if new_size == 0:
                if symbol in self.entry_prices:
                    del self.entry_prices[symbol]
                if symbol in self.highest_prices:
                    del self.highest_prices[symbol]
                if symbol in self.position_sizes:
                    del self.position_sizes[symbol]

    def prenext(self):
        """预热期 - 缓存数据"""
        self._update_data_cache()
    
    def nextstart(self):
        """第一个有效交易日 - 开始缓存数据"""
        self._update_data_cache()
        self.log(f"数据预热完成，开始等待足够数据计算因子")
    
    def next(self):
        """每日执行"""
        self._orders_today.clear()
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
        判断是否需要再平衡（复合触发器）

        触发条件（满足任一即调仓）:
        1. 达到最长再平衡间隔
        2. 当前选中组合与上次不同
        3. 任意资产当前权重与目标权重偏离超过阈值
        4. 资产得分相对上次发生显著跳跃

        同时受最短再平衡间隔约束，避免过度交易。
        """
        current_day = len(self.datas[0])

        if self.last_rebalance_day is None:
            return True

        days_since_rebalance = current_day - self.last_rebalance_day

        # 最短间隔保护：避免一天内多次触发
        if days_since_rebalance < self.p.min_rebalance_freq:
            return False

        # 1. 最长间隔强制再平衡
        if days_since_rebalance >= self.p.max_rebalance_freq:
            self.log(f"触发最长间隔再平衡: 距上次 {days_since_rebalance} 天")
            return True

        # 后续检查需要计算得分，若数据不足直接跳过
        if not self._has_enough_data():
            return False

        scores = self._compute_scores()
        if not scores:
            return False

        # 2. 选中组合变化（预览模式，不更新 selection_history）
        selected = self._select_assets(scores, preview=True)
        current_selected_set = set(selected)
        last_selected_set = set(self.last_selected)
        if current_selected_set != last_selected_set:
            new_in = current_selected_set - last_selected_set
            out = last_selected_set - current_selected_set
            self.log(f"触发组合变化再平衡: 新入={new_in}, 调出={out}")
            return True

        # 3. 权重偏离检查
        target_weights = self._calculate_weights(selected, scores)
        total_value = self.broker.getvalue()
        max_deviation = 0.0
        deviation_symbol = None
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            position = self.getposition(data)
            current_weight = 0.0
            if position.size > 0:
                market_value = position.size * data.close[0]
                current_weight = market_value / total_value
            target_weight = target_weights.get(symbol, 0.0)
            deviation = abs(current_weight - target_weight)
            if deviation > max_deviation:
                max_deviation = deviation
                deviation_symbol = symbol
            if deviation > self.p.rebalance_threshold:
                self.log(f"触发权重偏离再平衡: {symbol} 偏离 {deviation:.2%} (阈值 {self.p.rebalance_threshold:.1%})")
                return True

        # 4. 得分跳跃检查
        if self.last_scores:
            max_score_change = 0.0
            change_symbol = None
            for symbol, score in scores.items():
                last_score = self.last_scores.get(symbol)
                if last_score is None:
                    continue
                change = abs(score - last_score)
                if change > max_score_change:
                    max_score_change = change
                    change_symbol = symbol
            if max_score_change > self.p.score_change_threshold:
                self.log(f"触发得分跳跃再平衡: {change_symbol} 变化 {max_score_change:.3f} (阈值 {self.p.score_change_threshold:.2f})")
                return True

        return False
    
    def _compute_scores(self) -> Dict[str, float]:
        """
        计算所有资产的因子得分（使用平滑处理）

        Returns:
            {symbol: smoothed_score}
        """
        data_dfs = self._get_data_dfs()

        if not data_dfs:
            return {}

        raw_scores = self.scorer.compute_scores(data_dfs, lookback=self.p.lookback)

        smoothed_scores = {}
        for symbol in self.data_names:
            score = raw_scores.get(symbol, 0.0)
            self.score_history[symbol].append(score)
            if len(self.score_history[symbol]) > self.p.score_smooth_periods:
                self.score_history[symbol] = self.score_history[symbol][-self.p.score_smooth_periods:]
            smoothed_scores[symbol] = sum(self.score_history[symbol]) / len(self.score_history[symbol])

        return smoothed_scores
    
    def _select_assets(self, scores: Dict[str, float], is_initial: bool = False, preview: bool = False) -> List[str]:
        """
        选择得分最高的资产，支持动态 top_n

        动态模式：
        - 只选取得分 >= min_score 的资产
        - 相邻资产得分差距 > score_gap_threshold 时停止入选
        - 最终数量在 [top_n_min, top_n_max] 之间

        非动态模式（兼容旧接口）：
        - 固定选 top_n 个

        Args:
            scores: {symbol: score}
            is_initial: 是否为初始建仓
            preview: 是否为预览模式（不更新 selection_history）

        Returns:
            选中的资产代码列表
        """
        sorted_assets = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_assets:
            return []

        best_score = sorted_assets[0][1]

        # 动态 top_n：先根据得分质量确定可选资产
        if self.p.use_dynamic_top_n:
            # 整体得分偏低时：倾向于空仓或轻仓
            positive_scores = [s for s in scores.values() if s > 0]
            avg_positive = sum(positive_scores) / len(positive_scores) if positive_scores else 0.0

            # 根据头部得分和离散度确定目标持仓数
            target_count = self._determine_target_count(scores, best_score, avg_positive)
        else:
            target_count = self.p.top_n

        selected = []
        for symbol, score in sorted_assets:
            # 数量上限
            if len(selected) >= target_count:
                break

            # 绝对得分门槛
            if score < self.p.min_score:
                if self.p.use_dynamic_top_n:
                    break  # 得分排序递减，后续都不会满足
                else:
                    continue

            # 动态模式下：与前一名差距过大停止入选
            if self.p.use_dynamic_top_n and selected:
                prev_score = scores[selected[-1]]
                if prev_score - score > self.p.score_gap_threshold:
                    break

            if self._is_in_cooldown(symbol):
                if not preview:
                    self.log(f"资产 {symbol} 在止损冷却期内，跳过")
                continue

            data = self._get_data_by_symbol(symbol)
            position = self.getposition(data) if data else None
            has_position = position is not None and position.size > 0

            # 入场确认：非初始建仓时，没有持仓的新入选资产需要连续确认
            if not is_initial and not has_position and self.p.entry_confirmation > 1:
                streak = self.selection_history.get(symbol, 0)
                if streak < self.p.entry_confirmation - 1:
                    if not preview:
                        self.log(f"资产 {symbol} 得分 {score:.4f} 但连续入选仅 {streak} 次，需 {self.p.entry_confirmation - 1} 次确认，暂缓买入")
                    continue

            selected.append(symbol)

        # 动态模式下，如果入选数量低于 top_n_min，清空（空仓）
        if self.p.use_dynamic_top_n and len(selected) < self.p.top_n_min:
            if not preview:
                self.log(f"入选资产 {len(selected)} 只低于最低要求 {self.p.top_n_min}，本轮空仓")
            selected = []

        # 更新连续入选历史（仅在实际调仓时）
        if not preview:
            for symbol in self.data_names:
                if symbol in selected:
                    self.selection_history[symbol] = self.selection_history.get(symbol, 0) + 1
                else:
                    self.selection_history[symbol] = 0

        return selected

    def _determine_target_count(self, scores: Dict[str, float], best_score: float, avg_positive: float) -> int:
        """
        根据得分分布动态确定目标持仓数量

        策略逻辑：
        - 强市且资产间分化明显：满仓（top_n_max）
        - 中等市场：保持 top_n_max - 1 只
        - 弱市但仍有正分资产：轻仓（1-2只）
        - 无明显机会：空仓
        """
        # 如果最高分都不及格，空仓
        if best_score < self.p.min_score:
            return 0

        score_values = list(scores.values())
        score_std = pd.Series(score_values).std()
        if pd.isna(score_std):
            score_std = 0.0

        # 强市且分化：满仓
        if best_score >= 1.0 and score_std >= 0.8:
            target = self.p.top_n_max
        # 中等偏强市场：接近满仓
        elif best_score >= 0.5:
            target = max(self.p.top_n_min, self.p.top_n_max - 1)
        # 中等偏弱市场：半仓左右
        elif best_score >= 0.2:
            target = max(self.p.top_n_min, min(2, self.p.top_n_max - 1))
        # 弱市但仍有正分资产：轻仓
        elif avg_positive > 0:
            target = max(self.p.top_n_min, 1)
        # 无正分资产：空仓
        else:
            target = 0

        return min(target, self.p.top_n_max)

    def _calculate_weights(self, selected: List[str], scores: Dict[str, float]) -> Dict[str, float]:
        """
        计算持仓权重

        支持等权和按得分加权，并应用单资产权重上限，避免动态 top_n 下过度集中。

        Args:
            selected: 选中的资产列表
            scores: 综合得分字典

        Returns:
            {symbol: weight}
        """
        if not selected:
            return {}

        if self.p.weighting_method == 'equal':
            weight_per_asset = self.p.max_position_pct / len(selected)

        elif self.p.weighting_method == 'score_weighted':
            positive_scores = {s: max(scores.get(s, 0), 0) for s in selected}
            total_score = sum(positive_scores.values())

            if total_score <= 0:
                weight_per_asset = self.p.max_position_pct / len(selected)
            else:
                weights = {}
                for symbol in selected:
                    weights[symbol] = self.p.max_position_pct * positive_scores[symbol] / total_score
                # 应用单资产上限后，多余资金平分给未达上限的资产
                return self._apply_position_cap(weights)

        else:
            weight_per_asset = self.p.max_position_pct / len(selected)

        weights = {symbol: weight_per_asset for symbol in selected}
        return self._apply_position_cap(weights)

    def _apply_position_cap(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        应用单资产权重上限，并将多余资金重新分配。

        Args:
            weights: 原始权重

        Returns:
            应用上限后的权重
        """
        cap = self.p.max_single_position_pct
        if cap <= 0 or not weights:
            return weights

        # 迭代处理，直到没有资产超过上限
        for _ in range(len(weights)):
            excess = 0.0
            uncapped_symbols = []
            result = {}

            for symbol, weight in weights.items():
                if weight > cap:
                    excess += weight - cap
                    result[symbol] = cap
                else:
                    result[symbol] = weight
                    uncapped_symbols.append(symbol)

            if excess <= 0 or not uncapped_symbols:
                break

            redistribution = excess / len(uncapped_symbols)
            for symbol in uncapped_symbols:
                result[symbol] += redistribution

            weights = result

        return weights
    
    def _initial_rebalance(self):
        """初始建仓"""
        self.log("开始初始建仓...")
        
        scores = self._compute_scores()
        
        if not scores:
            self.log("无法计算因子得分，跳过初始建仓")
            return
        
        selected = self._select_assets(scores, is_initial=True)

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

        # 记录上次再平衡状态
        self.last_selected = selected
        self.last_scores = scores

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

        # 计算当前权重和目标权重
        total_value = self.broker.getvalue()
        weight_changes = []
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            position = self.getposition(data)

            current_weight = 0.0
            if position.size > 0:
                market_value = position.size * data.close[0]
                current_weight = market_value / total_value

            target_weight = weights.get(symbol, 0.0)
            weight_changes.append({
                'data': data,
                'symbol': symbol,
                'current_weight': current_weight,
                'target_weight': target_weight,
                'score': scores.get(symbol, 0),
            })

        # 换手率限制：大调仓时分阶段执行，模拟 buggy 版本的动态现金缓冲效果
        if self.p.max_turnover_pct > 0:
            raw_turnover = sum(abs(wc['current_weight'] - wc['target_weight']) for wc in weight_changes) / 2.0
            if raw_turnover > self.p.max_turnover_pct:
                scale = self.p.max_turnover_pct / raw_turnover
                self.log(f"换手率限制生效: 原始换手率 {raw_turnover:.2%}, 限制 {self.p.max_turnover_pct:.2%}, 缩放系数 {scale:.2f}")
                for wc in weight_changes:
                    wc['target_weight'] = wc['current_weight'] + scale * (wc['target_weight'] - wc['current_weight'])

        rebalance_info = []
        sell_orders = []
        buy_orders = []

        for wc in weight_changes:
            data = wc['data']
            symbol = wc['symbol']
            current_weight = wc['current_weight']
            target_weight = wc['target_weight']
            score = wc['score']

            asset_info = ASSET_CONFIG.get(symbol, {})
            asset_name = asset_info.get('name', symbol)

            rebalance_info.append({
                'symbol': symbol,
                'name': asset_name,
                'current_weight': current_weight,
                'target_weight': target_weight,
                'score': score,
            })

            if symbol in self._orders_today:
                self.log(f"资产 {symbol} 今日已有订单，跳过再平衡")
                continue

            if abs(current_weight - target_weight) > self.p.min_rebalance_pct:
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

                if target_weight < current_weight:
                    sell_orders.append((data, target_weight))
                else:
                    buy_orders.append((data, target_weight))

        # 先卖出释放现金，再买入，避免 backtrader 同 bar 内保证金预审失败
        for data, target in sell_orders:
            self._order_target_percent(data=data, target=target)

        for data, target in buy_orders:
            self._order_target_percent(data=data, target=target)

        self.log("再平衡执行完成")

        for info in rebalance_info:
            if info['target_weight'] > 0 or info['current_weight'] > 0:
                self.log(
                    f"  {info['name']}: 得分={info['score']:.4f}, "
                    f"权重 {info['current_weight']:.2%} -> {info['target_weight']:.2%}"
                )

        # 记录上次再平衡状态
        self.last_selected = selected
        self.last_scores = scores

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

            if symbol in self._orders_today:
                continue
            
            current_price = data.close[0]

            if symbol not in self.entry_prices:
                # 作为兜底：若 notify_order 未能及时更新，使用 backtrader 的成本价
                entry_price = position.price if position.price > 0 else current_price
                self.entry_prices[symbol] = entry_price
                self.highest_prices[symbol] = max(entry_price, current_price)
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

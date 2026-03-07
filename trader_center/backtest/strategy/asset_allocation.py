"""
大类资产配置策略

提供资产配置相关的策略，包括等权持有策略等。
"""

import backtrader as bt
from datetime import date
from typing import Dict, List, Optional
from .base import BaseStrategy


ASSET_CONFIG = {
    '518880.SH': {'name': '黄金ETF', 'category': 'commodity'},
    '510300.SH': {'name': '沪深300ETF', 'category': 'equity_cn'},
    '513100.SH': {'name': '纳指ETF', 'category': 'equity_us'},
    '511010.SH': {'name': '国债ETF', 'category': 'bond'},
    '159981.SZ': {'name': '能源化工ETF', 'category': 'commodity'},
}


class EqualWeightAssetAllocation(BaseStrategy):
    """
    大类资产等权持有策略
    
    通过等权重配置多种大类资产，定期再平衡以维持目标权重。
    
    策略特点:
    - 分散化投资：配置股票、债券、商品等多种资产
    - 定期再平衡：按固定频率或偏离阈值触发再平衡
    - 风险控制：通过资产分散降低单一资产风险
    
    Params:
        rebalance_freq: 再平衡频率（交易日），默认30天
        target_weight: 目标权重（每个资产），默认0.19（保留5%现金）
        tolerance: 权重偏离容忍度，默认0.05（5%）
    """
    
    name = "equal_weight_asset_allocation"
    description = "大类资产等权持有策略"
    
    params = (
        ('rebalance_freq', 30),
        ('target_weight', 0.19),
        ('tolerance', 0.05),
    )
    
    def __init__(self):
        super().__init__()
        self.last_rebalance_day: Optional[int] = None
        self.initialized = False
        self.data_names: List[str] = []
        
        for data in self.datas:
            name = data._name if hasattr(data, '_name') else 'unknown'
            self.data_names.append(name)
        
        self.log(f"策略初始化: 资产数量={len(self.datas)}, 目标权重={self.p.target_weight:.2%}")
    
    def prenext(self):
        """预热期"""
        pass
    
    def nextstart(self):
        """第一个有效交易日 - 初始建仓"""
        self._log_daily_state()
        
        self.log(f"开始初始建仓，共 {len(self.datas)} 个资产")
        
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            asset_info = ASSET_CONFIG.get(symbol, {})
            asset_name = asset_info.get('name', symbol)
            
            self.log_signal(
                signal_type='buy',
                data=data,
                trigger_condition=f'初始建仓: {asset_name} 目标权重 {self.p.target_weight:.2%}',
                indicator_values={
                    'close': data.close[0],
                    'target_weight': self.p.target_weight,
                },
                confidence=1.0,
            )
            
            self.order_target_percent(data=data, target=self.p.target_weight)
        
        self.initialized = True
        self.last_rebalance_day = len(self.datas[0])
        
        self.log(f"初始建仓完成，目标权重: {self.p.target_weight:.2%}")
    
    def next(self):
        """每日执行"""
        self._log_daily_state()
        
        if not self.initialized:
            return
        
        current_day = len(self.datas[0])
        
        if self._should_rebalance():
            self._rebalance()
            self.last_rebalance_day = current_day
    
    def _should_rebalance(self) -> bool:
        """
        判断是否需要再平衡
        
        条件:
        1. 达到再平衡频率
        2. 或权重偏离超过容忍度
        
        Returns:
            bool: 是否需要再平衡
        """
        current_day = len(self.datas[0])
        
        if self.last_rebalance_day is None:
            return False
        
        days_since_rebalance = current_day - self.last_rebalance_day
        
        if days_since_rebalance >= self.p.rebalance_freq:
            self.log(f"触发定期再平衡: 距上次 {days_since_rebalance} 天")
            return True
        
        max_deviation = self._calculate_max_deviation()
        if max_deviation > self.p.tolerance:
            self.log(f"触发偏离再平衡: 最大偏离 {max_deviation:.2%}")
            return True
        
        return False
    
    def _calculate_max_deviation(self) -> float:
        """
        计算当前持仓权重的最大偏离度
        
        Returns:
            float: 最大偏离度（绝对值）
        """
        total_value = self.broker.getvalue()
        if total_value <= 0:
            return 0.0
        
        max_deviation = 0.0
        
        for data in self.datas:
            position = self.getposition(data)
            if position.size == 0:
                current_weight = 0.0
            else:
                market_value = position.size * data.close[0]
                current_weight = market_value / total_value
            
            deviation = abs(current_weight - self.p.target_weight)
            max_deviation = max(max_deviation, deviation)
        
        return max_deviation
    
    def _rebalance(self):
        """执行再平衡操作"""
        self.log("开始执行再平衡...")
        
        total_value = self.broker.getvalue()
        
        rebalance_info = []
        
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            position = self.getposition(data)
            
            if position.size == 0:
                current_weight = 0.0
            else:
                market_value = position.size * data.close[0]
                current_weight = market_value / total_value
            
            deviation = current_weight - self.p.target_weight
            
            asset_info = ASSET_CONFIG.get(symbol, {})
            asset_name = asset_info.get('name', symbol)
            
            rebalance_info.append({
                'symbol': symbol,
                'name': asset_name,
                'current_weight': current_weight,
                'target_weight': self.p.target_weight,
                'deviation': deviation,
            })
            
            self.log_signal(
                signal_type='rebalance',
                data=data,
                trigger_condition=f'再平衡: {asset_name} 当前权重 {current_weight:.2%} -> 目标 {self.p.target_weight:.2%}',
                indicator_values={
                    'close': data.close[0],
                    'current_weight': current_weight,
                    'target_weight': self.p.target_weight,
                    'deviation': deviation,
                },
                confidence=1.0,
            )
            
            self.order_target_percent(data=data, target=self.p.target_weight)
        
        self.log("再平衡执行完成")
        
        for info in rebalance_info:
            self.log(
                f"  {info['name']}: {info['current_weight']:.2%} -> {info['target_weight']:.2%} "
                f"(偏离: {info['deviation']:+.2%})"
            )
    
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

"""
独立账户封装

为每个策略提供独立的资金和持仓管理。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional
from decimal import Decimal


@dataclass
class Position:
    """持仓记录"""
    symbol: str
    size: int
    avg_cost: float
    buy_date: date

    def market_value(self, current_price: float) -> float:
        """计算持仓市值"""
        return self.size * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        """计算浮动盈亏"""
        return self.size * (current_price - self.avg_cost)


@dataclass
class StrategyAccount:
    """
    策略独立账户

    管理单个策略的资金、持仓和交易记录。

    Attributes:
        strategy_name: 策略名称
        initial_cash: 初始资金
        cash: 当前可用现金
        positions: 持仓字典 {symbol: Position}
        trades: 交易记录列表
    """

    strategy_name: str
    initial_cash: float
    cash: float = field(default=None)
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if self.cash is None:
            self.cash = self.initial_cash

    def update_position(self, symbol: str, size_change: int, price: float,
                        trade_date: date = None):
        """
        更新持仓

        Args:
            symbol: 股票代码
            size_change: 数量变化（正数买入，负数卖出）
            price: 成交价格
            trade_date: 交易日期
        """
        trade_date = trade_date or date.today()

        if symbol not in self.positions:
            if size_change > 0:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    size=size_change,
                    avg_cost=price,
                    buy_date=trade_date
                )
        else:
            pos = self.positions[symbol]
            if size_change > 0:
                # 加仓，更新成本
                total_cost = pos.size * pos.avg_cost + size_change * price
                pos.size += size_change
                pos.avg_cost = total_cost / pos.size
            else:
                # 减仓
                pos.size += size_change  # size_change 是负数
                if pos.size <= 0:
                    del self.positions[symbol]

        # 记录交易
        self.trades.append({
            'date': trade_date,
            'symbol': symbol,
            'action': 'buy' if size_change > 0 else 'sell',
            'size': abs(size_change),
            'price': price,
        })

    def update_cash(self, amount: float):
        """
        更新现金

        Args:
            amount: 变化金额（正数增加，负数减少）
        """
        self.cash += amount

    def calculate_equity(self, prices: Dict[str, float]) -> float:
        """
        计算总权益

        Args:
            prices: 当前价格字典 {symbol: price}

        Returns:
            总权益 = 现金 + 持仓市值
        """
        position_value = sum(
            pos.market_value(prices.get(symbol, 0))
            for symbol, pos in self.positions.items()
        )
        return self.cash + position_value

    def get_position_size(self, symbol: str) -> int:
        """获取某股票持仓数量"""
        pos = self.positions.get(symbol)
        return pos.size if pos else 0

    def get_total_pnl(self, prices: Dict[str, float]) -> float:
        """
        计算总盈亏

        Args:
            prices: 当前价格字典

        Returns:
            总盈亏 = 当前权益 - 初始资金
        """
        equity = self.calculate_equity(prices)
        return equity - self.initial_cash

    def to_dict(self) -> Dict:
        """导出为字典"""
        return {
            'strategy_name': self.strategy_name,
            'initial_cash': self.initial_cash,
            'cash': self.cash,
            'positions': {
                symbol: {
                    'size': pos.size,
                    'avg_cost': pos.avg_cost,
                    'buy_date': pos.buy_date.isoformat(),
                }
                for symbol, pos in self.positions.items()
            },
            'trade_count': len(self.trades),
        }

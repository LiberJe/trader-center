"""
完整交易日志记录器

提供信号日志、资金日志、持仓日志、订单日志的记录功能。
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from pathlib import Path
import pandas as pd
import json


@dataclass
class SignalLog:
    """
    信号日志
    
    记录策略产生的交易信号。
    """
    datetime: datetime
    symbol: str
    signal_type: str
    trigger_condition: str
    indicator_values: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['datetime'] = self.datetime.isoformat()
        return d


@dataclass
class CapitalLog:
    """
    资金日志
    
    记录每日资金状态。
    """
    date: date
    cash: float
    position_value: float
    total_value: float
    cash_ratio: float = 0.0
    position_ratio: float = 0.0
    daily_pnl: float = 0.0
    daily_return: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['date'] = self.date.isoformat()
        return d


@dataclass
class PositionLog:
    """
    持仓日志
    
    记录每日持仓详情。
    """
    date: date
    symbol: str
    size: int
    cost_price: float
    current_price: float
    market_value: float
    pnl: float = 0.0
    pnl_ratio: float = 0.0
    holding_days: int = 0
    weight: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['date'] = self.date.isoformat()
        return d


@dataclass
class OrderLog:
    """
    订单日志
    
    记录订单提交和状态变化。
    """
    order_id: str
    datetime: datetime
    symbol: str
    action: str
    order_type: str = 'market'
    expected_price: float = 0.0
    expected_size: int = 0
    status: str = 'submitted'
    executed_price: float = 0.0
    executed_size: int = 0
    slippage: float = 0.0
    commission: float = 0.0
    message: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['datetime'] = self.datetime.isoformat()
        return d


class TradeLogger:
    """
    完整交易日志记录器
    
    集中管理信号、资金、持仓、订单四类日志。
    
    Example:
        >>> logger = TradeLogger('my_strategy')
        >>> logger.log_signal('buy', '000001.SZ', 'SMA金叉', confidence=0.8)
        >>> logger.log_capital(date.today(), 80000, 20000, 100000)
        >>> logger.save_all(Path('logs/backtest'))
    """
    
    def __init__(self, strategy_name: str):
        """
        初始化日志记录器
        
        Args:
            strategy_name: 策略名称
        """
        self.strategy_name = strategy_name
        self.signals: List[SignalLog] = []
        self.capitals: List[CapitalLog] = []
        self.positions: List[PositionLog] = []
        self.orders: List[OrderLog] = []
        
        self._order_map: Dict[str, OrderLog] = {}
        self._order_counter = 0
        self._prev_total_value: Optional[float] = None
        self._position_entry_dates: Dict[str, date] = {}
    
    def log_signal(
        self,
        signal_type: str,
        symbol: str,
        trigger_condition: str,
        indicator_values: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        dt: Optional[datetime] = None,
    ) -> SignalLog:
        """
        记录交易信号
        
        Args:
            signal_type: 信号类型 ('buy' / 'sell')
            symbol: 标的代码
            trigger_condition: 触发条件描述
            indicator_values: 指标值快照
            confidence: 信号强度 (0-1)
            target_price: 目标价格
            stop_loss: 止损价
            take_profit: 止盈价
            dt: 信号时间，默认当前时间
            
        Returns:
            SignalLog 信号日志对象
        """
        signal = SignalLog(
            datetime=dt or datetime.now(),
            symbol=symbol,
            signal_type=signal_type,
            trigger_condition=trigger_condition,
            indicator_values=indicator_values or {},
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.signals.append(signal)
        return signal
    
    def log_capital(
        self,
        log_date: date,
        cash: float,
        position_value: float,
        total_value: float,
        daily_pnl: float = 0.0,
    ) -> CapitalLog:
        """
        记录资金状态
        
        Args:
            log_date: 日期
            cash: 可用现金
            position_value: 持仓市值
            total_value: 总资产
            daily_pnl: 当日盈亏
            
        Returns:
            CapitalLog 资金日志对象
        """
        cash_ratio = cash / total_value if total_value > 0 else 0.0
        position_ratio = position_value / total_value if total_value > 0 else 0.0
        
        if self._prev_total_value and self._prev_total_value > 0:
            daily_return = (total_value - self._prev_total_value) / self._prev_total_value
        else:
            daily_return = 0.0
        
        capital = CapitalLog(
            date=log_date,
            cash=cash,
            position_value=position_value,
            total_value=total_value,
            cash_ratio=cash_ratio,
            position_ratio=position_ratio,
            daily_pnl=daily_pnl,
            daily_return=daily_return,
        )
        self.capitals.append(capital)
        self._prev_total_value = total_value
        return capital
    
    def log_position(
        self,
        log_date: date,
        symbol: str,
        size: int,
        cost_price: float,
        current_price: float,
        holding_days: int = 0,
    ) -> PositionLog:
        """
        记录持仓状态
        
        Args:
            log_date: 日期
            symbol: 标的代码
            size: 持仓数量
            cost_price: 成本价
            current_price: 当前价
            holding_days: 持仓天数
            
        Returns:
            PositionLog 持仓日志对象
        """
        market_value = size * current_price
        pnl = (current_price - cost_price) * size
        pnl_ratio = (current_price - cost_price) / cost_price if cost_price > 0 else 0.0
        
        total_value = self._prev_total_value or market_value
        weight = market_value / total_value if total_value > 0 else 0.0
        
        position = PositionLog(
            date=log_date,
            symbol=symbol,
            size=size,
            cost_price=cost_price,
            current_price=current_price,
            market_value=market_value,
            pnl=pnl,
            pnl_ratio=pnl_ratio,
            holding_days=holding_days,
            weight=weight,
        )
        self.positions.append(position)
        return position
    
    def log_order_submit(
        self,
        symbol: str,
        action: str,
        expected_price: float,
        expected_size: int,
        order_type: str = 'market',
        dt: Optional[datetime] = None,
    ) -> OrderLog:
        """
        记录订单提交
        
        Args:
            symbol: 标的代码
            action: 买卖方向 ('buy' / 'sell')
            expected_price: 预期价格
            expected_size: 预期数量
            order_type: 订单类型 ('market' / 'limit')
            dt: 订单时间
            
        Returns:
            OrderLog 订单日志对象
        """
        self._order_counter += 1
        order_id = f"{self._order_counter:04d}"
        
        order = OrderLog(
            order_id=order_id,
            datetime=dt or datetime.now(),
            symbol=symbol,
            action=action,
            order_type=order_type,
            expected_price=expected_price,
            expected_size=expected_size,
            status='submitted',
        )
        self.orders.append(order)
        self._order_map[order_id] = order
        return order
    
    def log_order_status(
        self,
        order_id: str,
        status: str,
        executed_price: float = 0.0,
        executed_size: int = 0,
        commission: float = 0.0,
        message: str = '',
    ) -> Optional[OrderLog]:
        """
        更新订单状态
        
        Args:
            order_id: 订单ID
            status: 新状态 ('accepted' / 'completed' / 'canceled' / 'rejected')
            executed_price: 成交价格
            executed_size: 成交数量
            commission: 手续费
            message: 状态消息
            
        Returns:
            OrderLog 更新后的订单日志，如果订单不存在则返回 None
        """
        order = self._order_map.get(order_id)
        if order is None:
            return None
        
        order.status = status
        order.executed_price = executed_price
        order.executed_size = executed_size
        order.commission = commission
        order.message = message
        
        if executed_price > 0 and order.expected_price > 0:
            order.slippage = executed_price - order.expected_price
            if order.action == 'buy':
                order.slippage = executed_price - order.expected_price
            else:
                order.slippage = order.expected_price - executed_price
        
        return order
    
    def to_dataframe(self, log_type: str) -> pd.DataFrame:
        """
        将指定类型的日志转换为 DataFrame
        
        Args:
            log_type: 日志类型 ('signals' / 'capitals' / 'positions' / 'orders')
            
        Returns:
            pandas DataFrame
        """
        type_map = {
            'signals': self.signals,
            'capitals': self.capitals,
            'positions': self.positions,
            'orders': self.orders,
        }
        
        if log_type not in type_map:
            raise ValueError(f"Unknown log type: {log_type}")
        
        data = type_map[log_type]
        if not data:
            return pd.DataFrame()
        
        records = [item.to_dict() for item in data]
        return pd.DataFrame(records)
    
    def get_signals_df(self) -> pd.DataFrame:
        """获取信号日志 DataFrame"""
        return self.to_dataframe('signals')
    
    def get_capitals_df(self) -> pd.DataFrame:
        """获取资金日志 DataFrame"""
        return self.to_dataframe('capitals')
    
    def get_positions_df(self) -> pd.DataFrame:
        """获取持仓日志 DataFrame"""
        return self.to_dataframe('positions')
    
    def get_orders_df(self) -> pd.DataFrame:
        """获取订单日志 DataFrame"""
        return self.to_dataframe('orders')
    
    def save_signals(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存信号日志
        
        Args:
            output_dir: 输出目录
            format: 格式 ('csv' / 'json')
            
        Returns:
            保存的文件路径
        """
        if not self.signals:
            return None
        
        df = self.get_signals_df()
        if df.empty:
            return None
        
        if format == "json":
            filepath = output_dir / "signals.json"
            df.to_json(filepath, orient='records', force_ascii=False, indent=2)
        else:
            filepath = output_dir / "signals.csv"
            df.to_csv(filepath, index=False, encoding='utf-8')
        
        return filepath
    
    def save_capitals(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存资金日志
        
        Args:
            output_dir: 输出目录
            format: 格式 ('csv' / 'json')
            
        Returns:
            保存的文件路径
        """
        if not self.capitals:
            return None
        
        df = self.get_capitals_df()
        if df.empty:
            return None
        
        if format == "json":
            filepath = output_dir / "capitals.json"
            df.to_json(filepath, orient='records', force_ascii=False, indent=2)
        else:
            filepath = output_dir / "capitals.csv"
            df.to_csv(filepath, index=False, encoding='utf-8')
        
        return filepath
    
    def save_positions(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存持仓日志
        
        Args:
            output_dir: 输出目录
            format: 格式 ('csv' / 'json')
            
        Returns:
            保存的文件路径
        """
        if not self.positions:
            return None
        
        df = self.get_positions_df()
        if df.empty:
            return None
        
        if format == "json":
            filepath = output_dir / "positions.json"
            df.to_json(filepath, orient='records', force_ascii=False, indent=2)
        else:
            filepath = output_dir / "positions.csv"
            df.to_csv(filepath, index=False, encoding='utf-8')
        
        return filepath
    
    def save_orders(self, output_dir: Path, format: str = "csv") -> Optional[Path]:
        """
        保存订单日志
        
        Args:
            output_dir: 输出目录
            format: 格式 ('csv' / 'json')
            
        Returns:
            保存的文件路径
        """
        if not self.orders:
            return None
        
        df = self.get_orders_df()
        if df.empty:
            return None
        
        if format == "json":
            filepath = output_dir / "orders.json"
            df.to_json(filepath, orient='records', force_ascii=False, indent=2)
        else:
            filepath = output_dir / "orders.csv"
            df.to_csv(filepath, index=False, encoding='utf-8')
        
        return filepath
    
    def save_all(self, output_dir: Path, format: str = "csv") -> Dict[str, Path]:
        """
        保存所有日志文件
        
        Args:
            output_dir: 输出目录
            format: 格式 ('csv' / 'json')
            
        Returns:
            保存的文件路径字典
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = {}
        
        signals_path = self.save_signals(output_dir, format)
        if signals_path:
            saved_files['signals'] = signals_path
        
        capitals_path = self.save_capitals(output_dir, format)
        if capitals_path:
            saved_files['capitals'] = capitals_path
        
        positions_path = self.save_positions(output_dir, format)
        if positions_path:
            saved_files['positions'] = positions_path
        
        orders_path = self.save_orders(output_dir, format)
        if orders_path:
            saved_files['orders'] = orders_path
        
        return saved_files
    
    def clear(self):
        """清空所有日志"""
        self.signals.clear()
        self.capitals.clear()
        self.positions.clear()
        self.orders.clear()
        self._order_map.clear()
        self._order_counter = 0
        self._prev_total_value = None
        self._position_entry_dates.clear()
    
    @property
    def signal_count(self) -> int:
        """信号数量"""
        return len(self.signals)
    
    @property
    def capital_count(self) -> int:
        """资金记录数量"""
        return len(self.capitals)
    
    @property
    def position_count(self) -> int:
        """持仓记录数量"""
        return len(self.positions)
    
    @property
    def order_count(self) -> int:
        """订单数量"""
        return len(self.orders)

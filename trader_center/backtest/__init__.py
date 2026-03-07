"""
Backtest Module - 基于 backtrader 的量化回测系统

Example:
    >>> from trader_center.backtest import BacktestRunner, BaseStrategy
    >>> runner = BacktestRunner()
    >>> result = runner.run(MyStrategy, symbol="000001.SZ")
"""

__version__ = "0.1.0"

def __getattr__(name):
    if name == "BaseStrategy":
        from .strategy.base import BaseStrategy
        return BaseStrategy
    if name == "BacktestRunner":
        from .runner import BacktestRunner
        return BacktestRunner
    if name == "BacktestResult":
        from .results import BacktestResult
        return BacktestResult
    if name == "BacktestConfig":
        from .config import BacktestConfig
        return BacktestConfig
    if name == "TradeLogger":
        from .trade_logger import TradeLogger
        return TradeLogger
    if name == "PerformanceAnalytics":
        from .analytics import PerformanceAnalytics
        return PerformanceAnalytics
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseStrategy",
    "BacktestRunner",
    "BacktestResult",
    "BacktestConfig",
    "TradeLogger",
    "PerformanceAnalytics",
]

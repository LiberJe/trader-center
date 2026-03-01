"""Backtest module with backtrader-based event-driven engine."""

from .engine import BacktestEngine
from .result import BacktestResult

__all__ = ['BacktestEngine', 'BacktestResult']

"""
基本面因子数据适配器

扩展 PandasDataFeed 支持基本面数据字段。
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FundamentalDataFeed(bt.feeds.PandasData):
    """
    支持基本面数据的数据适配器
    
    在标准 OHLCV 数据基础上，增加基本面数据字段支持。
    
    Params:
        datetime: 时间索引
        open, high, low, close, volume: 标准行情数据
        pe_ratio: 市盈率
        pb_ratio: 市净率
        ps_ratio: 市销率
        market_cap: 总市值
        revenue: 营业收入
        net_income: 净利润
        total_assets: 总资产
        total_equity: 净资产
        total_liabilities: 总负债
        current_assets: 流动资产
        current_liabilities: 流动负债
        operating_cash_flow: 经营现金流
        free_cash_flow: 自由现金流
        eps: 每股收益
        dividend_per_share: 每股股息
    """
    
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
        ('pe_ratio', 'pe_ratio'),
        ('pb_ratio', 'pb_ratio'),
        ('ps_ratio', 'ps_ratio'),
        ('market_cap', 'market_cap'),
        ('revenue', 'revenue'),
        ('net_income', 'net_income'),
        ('total_assets', 'total_assets'),
        ('total_equity', 'total_equity'),
        ('total_liabilities', 'total_liabilities'),
        ('current_assets', 'current_assets'),
        ('current_liabilities', 'current_liabilities'),
        ('cash', 'cash'),
        ('inventory', 'inventory'),
        ('ebit', 'ebit'),
        ('ebitda', 'ebitda'),
        ('ev', 'ev'),
        ('interest_expense', 'interest_expense'),
        ('operating_cash_flow', 'operating_cash_flow'),
        ('capital_expenditure', 'capital_expenditure'),
        ('free_cash_flow', 'free_cash_flow'),
        ('eps', 'eps'),
        ('eps_growth', 'eps_growth'),
        ('dividend_per_share', 'dividend_per_share'),
        ('receivables', 'receivables'),
        ('accounts_payable', 'accounts_payable'),
        ('retained_earnings', 'retained_earnings'),
        ('shares_outstanding', 'shares_outstanding'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._symbol = kwargs.get('name', 'unknown')
    
    @classmethod
    def from_datahub(
        cls,
        symbol: str,
        price_df: pd.DataFrame,
        fundamental_df: Optional[pd.DataFrame] = None,
    ) -> 'FundamentalDataFeed':
        """
        从 DataHub 数据创建 feed
        
        Args:
            symbol: 股票代码
            price_df: 价格数据 DataFrame (OHLCV)
            fundamental_df: 基本面数据 DataFrame (可选)
        
        Returns:
            FundamentalDataFeed 实例
        """
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        missing = required_cols - set(price_df.columns)
        if missing:
            raise ValueError(f"价格数据缺少必要列: {missing}")
        
        if not isinstance(price_df.index, pd.DatetimeIndex):
            if 'timestamp' in price_df.columns:
                price_df = price_df.set_index('timestamp')
            else:
                raise ValueError("DataFrame 需要 datetime index 或 timestamp 列")
        
        if fundamental_df is not None:
            if not isinstance(fundamental_df.index, pd.DatetimeIndex):
                if 'report_date' in fundamental_df.columns:
                    fundamental_df = fundamental_df.set_index('report_date')
            
            combined = cls._merge_price_fundamental(price_df, fundamental_df)
        else:
            combined = price_df.copy()
        
        return cls(dataname=combined, name=symbol)
    
    @staticmethod
    def _merge_price_fundamental(
        price_df: pd.DataFrame,
        fundamental_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        合并价格数据和基本面数据
        
        基本面数据通常是季度报告，需要向前填充到每个交易日。
        
        Args:
            price_df: 日线价格数据
            fundamental_df: 季度基本面数据
        
        Returns:
            合并后的 DataFrame
        """
        combined = price_df.copy()
        
        fund_cols = [col for col in fundamental_df.columns if col not in ['symbol', 'report_date']]
        
        for col in fund_cols:
            if col in fundamental_df.columns:
                combined[col] = np.nan
        
        for report_date, row in fundamental_df.iterrows():
            mask = combined.index >= report_date
            for col in fund_cols:
                if col in row.index and pd.notna(row[col]):
                    combined.loc[mask, col] = row[col]
        
        combined[fund_cols] = combined[fund_cols].ffill()
        
        return combined


class PandasDataFeed(bt.feeds.PandasData):
    """
    基于 pandas DataFrame 的数据适配器

    适配 DataHub 返回的数据格式，支持 A股日线数据。

    Args:
        dataname: pandas DataFrame，包含 open/high/low/close/volume
        name: 股票代码，如 "000001.SZ"

    Example:
        >>> df = data_hub.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
        >>> feed = PandasDataFeed(dataname=df, name="000001.SZ")
        >>> cerebro.adddata(feed)
    """

    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._symbol = kwargs.get('name', 'unknown')

    @classmethod
    def from_datahub(cls, symbol: str, df: pd.DataFrame) -> 'PandasDataFeed':
        """
        从 DataHub 数据创建 feed

        Args:
            symbol: 股票代码
            df: DataHub 返回的 DataFrame

        Returns:
            PandasDataFeed 实例

        Raises:
            ValueError: 如果 DataFrame 缺少必要列
        """
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame 缺少必要列: {missing}")

        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')
            else:
                raise ValueError("DataFrame 需要 datetime index 或 timestamp 列")

        return cls(dataname=df, name=symbol)

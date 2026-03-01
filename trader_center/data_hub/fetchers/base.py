"""Base fetcher abstract class."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

import pandas as pd


class FetcherError(Exception):
    """Exception raised when data fetching fails."""

    def __init__(self, message: str, source: Optional[str] = None):
        self.source = source
        self.message = message
        super().__init__(f"[{source}] {message}" if source else message)


class BaseFetcher(ABC):
    """Abstract base class for data fetchers."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the data source."""
        pass

    @abstractmethod
    def fetch_daily_bars(
        self, symbol: str, start: date, end: date
    ) -> pd.DataFrame:
        """
        Fetch daily OHLCV bars for a symbol.

        Args:
            symbol: Symbol code (e.g., "000001.SZ")
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount
        """
        pass

    @abstractmethod
    def fetch_symbols(self) -> pd.DataFrame:
        """
        Fetch all available symbols.

        Returns:
            DataFrame with columns: code, name, market, exchange, category
        """
        pass

    def validate_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize OHLCV data."""
        required_cols = ["date", "open", "high", "low", "close", "volume"]

        for col in required_cols:
            if col not in df.columns:
                raise FetcherError(f"Missing required column: {col}", self.source_name)

        # Ensure date column is datetime
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # Sort by date
        df = df.sort_values("date").reset_index(drop=True)

        return df

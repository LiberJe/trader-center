from datetime import datetime
from typing import List, Optional, Tuple
import pandas as pd
import logging

from trader_center.data_hub.fetchers.base import DataFetcher
from trader_center.data_hub.models import BarData, SymbolInfo

logger = logging.getLogger(__name__)


class FetcherRouter:
    """Fetcher 路由与合并中心"""

    def __init__(self):
        self.fetchers: List[DataFetcher] = []

    def register(self, fetcher: DataFetcher):
        """注册数据源"""
        self.fetchers.append(fetcher)
        # 按优先级排序
        self.fetchers.sort(key=lambda f: f.priority)
        logger.info(f"Registered fetcher: {fetcher.name} (priority={fetcher.priority})")

    def get_available_fetchers(self) -> List[DataFetcher]:
        """获取可用的数据源列表"""
        return [f for f in self.fetchers if f.check_available()]

    def fetch_bars(
        self, symbol: str, start: datetime, end: datetime, frequency: str
    ) -> Optional[pd.DataFrame]:
        """
        从多个源获取数据并合并
        策略：按优先级获取，互补缺失数据
        """
        available = self.get_available_fetchers()
        if not available:
            logger.error("No fetchers available")
            return None

        results = []
        for fetcher in available:
            try:
                bars = fetcher.get_bars(symbol, start, end, frequency)
                if bars:
                    df = pd.DataFrame([b.model_dump() for b in bars])
                    results.append((fetcher.name, fetcher.priority, df))
                    logger.debug(f"{fetcher.name}: fetched {len(df)} bars")
            except Exception as e:
                logger.warning(f"{fetcher.name} fetch failed: {e}")
                continue

        if not results:
            return None

        # 按优先级排序后合并
        results.sort(key=lambda x: x[1])
        return self._merge_results(results)

    def _merge_results(
        self, results: List[Tuple[str, int, pd.DataFrame]]
    ) -> pd.DataFrame:
        """
        合并多源数据
        策略：高优先级源为主，低优先级源互补缺失数据
        """
        base_name, _, base_df = results[0]
        merged = base_df.copy()

        for src_name, _, src_df in results[1:]:
            # 找出 base 中缺失的日期
            existing_dates = set(merged["timestamp"])
            missing = src_df[~src_df["timestamp"].isin(existing_dates)]

            if not missing.empty:
                logger.debug(f"{src_name}: complementing {len(missing)} missing bars")
                merged = pd.concat([merged, missing], ignore_index=True)

        # 排序
        merged = merged.sort_values("timestamp").reset_index(drop=True)
        return merged

    def fetch_symbols(self) -> List[SymbolInfo]:
        """获取股票列表（使用最高优先级的源）"""
        available = self.get_available_fetchers()
        if not available:
            return []

        # 使用最高优先级的源
        return available[0].get_symbols()

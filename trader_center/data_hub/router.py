from datetime import datetime
from typing import List, Optional, Tuple
import pandas as pd
import logging

from trader_center.data_hub.fetchers.router import FetcherRouter
from trader_center.data_hub.storage.hybrid_store import HybridStorage
from trader_center.data_hub.config import DataHubConfig
from trader_center.data_hub.models import BarData, SymbolInfo

logger = logging.getLogger(__name__)


class DataRouter:
    """
    数据路由中心 - 整合 Fetcher 和 Storage
    职责：
    1. 管理本地缓存
    2. 处理增量更新
    3. 多源数据合并
    """

    def __init__(self, config: Optional[DataHubConfig] = None):
        self.config = config or DataHubConfig()
        self.storage = HybridStorage(self.config)
        self.fetcher_router = FetcherRouter()

    def register_fetcher(self, fetcher):
        """注册数据源"""
        self.fetcher_router.register(fetcher)

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> pd.DataFrame:
        """
        获取K线数据（带增量更新）
        """
        # 1. 从本地获取已有数据
        local_df = self.storage.get_bars(symbol, start, end, frequency)

        # 2. 计算缺失的时间段
        missing_ranges = self._calculate_missing_ranges(
            local_df, start, end, symbol, frequency
        )

        if not missing_ranges:
            logger.debug(f"All data available locally for {symbol}")
            return local_df

        # 3. 从远程获取缺失数据
        all_new_data = []
        for miss_start, miss_end in missing_ranges:
            logger.info(f"Fetching missing data: {symbol} [{miss_start} to {miss_end}]")
            fetched = self.fetcher_router.fetch_bars(symbol, miss_start, miss_end, frequency)
            if fetched is not None and not fetched.empty:
                all_new_data.append(fetched)

        if not all_new_data:
            return local_df

        # 4. 合并新数据并保存
        new_df = pd.concat(all_new_data, ignore_index=True)
        self._save_to_storage(new_df)

        # 5. 返回完整数据
        if local_df.empty:
            return new_df
        else:
            combined = pd.concat([local_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['timestamp'], keep='first')
            return combined.sort_values('timestamp').reset_index(drop=True)

    def _calculate_missing_ranges(
        self,
        local_df: pd.DataFrame,
        requested_start: datetime,
        requested_end: datetime,
        symbol: str,
        frequency: str
    ) -> List[Tuple[datetime, datetime]]:
        """计算需要获取的缺失时间段"""
        # 获取本地数据的实际范围
        local_start, local_end = self.storage.get_data_range(symbol, frequency)

        if local_start is None:
            # 本地无数据，全量获取
            return [(requested_start, requested_end)]

        missing = []

        # 检查开头
        if requested_start < local_start:
            missing.append((requested_start, min(requested_end, local_start)))

        # 检查结尾
        if requested_end > local_end:
            missing.append((max(requested_start, local_end), requested_end))

        return missing

    def _save_to_storage(self, df: pd.DataFrame):
        """保存 DataFrame 到存储"""
        if df.empty:
            return

        bars = []
        for _, row in df.iterrows():
            try:
                bar = BarData(**row.to_dict())
                bars.append(bar)
            except Exception as e:
                logger.warning(f"Failed to parse bar: {e}")

        if bars:
            self.storage.save_bars(bars)

    def get_symbols(self, exchange: Optional[str] = None) -> List[SymbolInfo]:
        """获取股票列表"""
        # 先尝试从本地获取
        local = self.storage.get_symbols(exchange)
        if local:
            return local

        # 从远程获取并保存
        remote = self.fetcher_router.fetch_symbols()
        if remote:
            self.storage.save_symbols(remote)
            if exchange:
                return [s for s in remote if s.exchange == exchange]
            return remote

        return []

from datetime import datetime
from typing import List, Optional

import pandas as pd

from trader_center.data_hub.fetchers.base import DataFetcher
from trader_center.data_hub.models import BarData, SymbolInfo, Frequency


class AkshareFetcher(DataFetcher):
    """Akshare 数据源获取器"""

    name = "akshare"
    priority = 10  # 高优先级

    def __init__(self):
        self._ak = None

    def _get_ak(self):
        """延迟导入 akshare"""
        if self._ak is None:
            import akshare as ak

            self._ak = ak
        return self._ak

    def check_available(self) -> bool:
        """检查 akshare 是否可用"""
        try:
            import akshare as ak

            # 简单测试调用
            _ = ak.stock_zh_a_spot_em()
            return True
        except Exception:
            return False

    def _parse_symbol(self, symbol: str) -> tuple[str, str]:
        """解析 symbol: '000001.SZ' -> ('000001', 'SZ')"""
        parts = symbol.split(".")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid symbol format: {symbol}, expected 'code.exchange'"
            )
        return parts[0], parts[1]

    def _map_frequency(self, frequency: str) -> str:
        """频率映射"""
        mapping = {
            "1d": "daily",
            "1w": "weekly",
            "1m": "monthly",
            "1min": "1",
            "5min": "5",
            "15min": "15",
            "30min": "30",
            "60min": "60",
        }
        return mapping.get(frequency, "daily")

    def get_bars(
        self, symbol: str, start: datetime, end: datetime, frequency: str
    ) -> List[BarData]:
        """获取K线数据"""
        ak = self._get_ak()
        code, exchange = self._parse_symbol(symbol)
        period = self._map_frequency(frequency)

        # 调用 akshare 接口
        df = ak.stock_zh_a_hist(
            symbol=code,
            period=period,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",  # 前复权
        )

        if df.empty:
            return []

        # 转换为 BarData 列表
        bars = []
        for _, row in df.iterrows():
            bar = BarData(
                symbol=symbol,
                timestamp=datetime.strptime(str(row["日期"]), "%Y-%m-%d"),
                frequency=(
                    Frequency(frequency)
                    if frequency in [f.value for f in Frequency]
                    else Frequency.DAILY
                ),
                open=float(row["开盘"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                close=float(row["收盘"]),
                volume=float(row["成交量"]),
                amount=(
                    float(row["成交额"])
                    if "成交额" in row and pd.notna(row["成交额"])
                    else None
                ),
            )
            bars.append(bar)

        return bars

    def get_symbols(self) -> List[SymbolInfo]:
        """获取A股股票列表"""
        ak = self._get_ak()
        df = ak.stock_zh_a_spot_em()

        symbols = []
        for _, row in df.iterrows():
            # 解析代码和交易所
            code = str(row["代码"])
            # 根据代码判断交易所
            if code.startswith(("60", "68", "88", "89")):
                exchange = "SH"
            elif code.startswith(("00", "30", "82", "83")):
                exchange = "SZ"
            elif code.startswith(("43", "83", "87", "88")):
                exchange = "BJ"
            else:
                exchange = "SH"  # 默认

            symbol = SymbolInfo(
                symbol=f"{code}.{exchange}",
                name=str(row["名称"]),
                exchange=exchange,
                industry=(
                    str(row.get("所属行业", ""))
                    if pd.notna(row.get("所属行业"))
                    else None
                ),
            )
            symbols.append(symbol)

        return symbols

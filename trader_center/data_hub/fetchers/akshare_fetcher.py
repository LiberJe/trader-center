import logging
from datetime import datetime, date
from typing import List, Optional

import pandas as pd

from trader_center.data_hub.fetchers.base import DataFetcher
from trader_center.data_hub.models import (
    BarData, SymbolInfo, Frequency,
    MarketFundFlow, StockFundFlow, SectorFundFlow
)


class AkshareFetcher(DataFetcher):
    """Akshare 数据源获取器"""

    name = "akshare"
    priority = 10  # 高优先级

    def __init__(self):
        self._ak = None
        self.logger = logging.getLogger(__name__)

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

    def _parse_numeric(self, value, default=0.0) -> float:
        """解析数值，处理百分比字符串如 '20.01%' 和带单位的数值如 '7343.82万'"""
        if value is None or pd.isna(value):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        value_str = str(value).strip()

        # 处理百分比
        if value_str.endswith('%'):
            try:
                return float(value_str[:-1])
            except ValueError:
                return default

        # 处理中文单位
        if value_str.endswith('万'):
            try:
                return float(value_str[:-1]) * 10000
            except ValueError:
                return default
        if value_str.endswith('亿'):
            try:
                return float(value_str[:-1]) * 100000000
            except ValueError:
                return default

        try:
            return float(value_str)
        except ValueError:
            return default

    def _get_column(self, row, candidates, default=None):
        """从多个候选列名中获取第一个存在的值"""
        for col in candidates:
            if col in row:
                return row[col]
        return default

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

    def get_market_fund_flow(self, target_date: date) -> Optional[MarketFundFlow]:
        """获取大盘资金流向

        Args:
            target_date: 目标日期

        Returns:
            MarketFundFlow 对象，如果数据不可用则返回 None
        """
        ak = self._get_ak()
        date_str = target_date.strftime("%Y%m%d")

        try:
            # 获取大盘资金流向数据
            df = ak.stock_market_fund_flow()
            if df.empty:
                return None

            # 找到目标日期的数据
            date_col = "日期" if "日期" in df.columns else df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col]).dt.date
            row = df[df[date_col] == target_date]

            if row.empty:
                # 目标日期无数据，直接返回 None
                self.logger.warning(f"No data for {target_date}")
                return None

            row = row.iloc[0]

            return MarketFundFlow(
                date=target_date,
                market="all",
                main_force_net=self._parse_numeric(
                    self._get_column(row, ["主力净流入", "主力净流入-净额"])
                ),
                super_large_net=self._parse_numeric(
                    self._get_column(row, ["超大单净流入", "超大单净流入-净额"])
                ),
                large_net=self._parse_numeric(
                    self._get_column(row, ["大单净流入", "大单净流入-净额"])
                ),
                medium_net=self._parse_numeric(
                    self._get_column(row, ["中单净流入", "中单净流入-净额"])
                ),
                small_net=self._parse_numeric(
                    self._get_column(row, ["小单净流入", "小单净流入-净额"])
                ),
                total_amount=self._parse_numeric(
                    self._get_column(row, ["总成交额", "上证指数-成交额"])
                ),
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get market fund flow: {e}")
            return None

    def get_stock_fund_flow_rank(
        self, target_date: date, top_n: int = 100
    ) -> List[StockFundFlow]:
        """获取个股资金流向排名

        Args:
            target_date: 目标日期
            top_n: 返回前N条记录

        Returns:
            StockFundFlow 列表
        """
        ak = self._get_ak()

        try:
            # 获取个股资金流向排名
            df = ak.stock_fund_flow_individual()
            if df.empty:
                return []

            # 检查返回数据是否有日期列，验证日期是否匹配目标日期
            date_col = None
            for col in ["日期", "date", "时间"]:
                if col in df.columns:
                    date_col = col
                    break

            # 验证日期：这些API只返回最新数据
            from datetime import date as dt_date

            if date_col:
                # 有日期列，验证日期匹配
                df[date_col] = pd.to_datetime(df[date_col]).dt.date
                actual_date = df[date_col].iloc[0]
                if actual_date != target_date:
                    self.logger.warning(
                        f"Stock fund flow data date {actual_date} does not match target {target_date}"
                    )
                    return []
                data_date = actual_date
            else:
                # 无日期列，需要通过大盘数据推断实际日期
                try:
                    market_df = ak.stock_market_fund_flow()
                    if not market_df.empty:
                        market_date_col = "日期" if "日期" in market_df.columns else market_df.columns[0]
                        market_df[market_date_col] = pd.to_datetime(market_df[market_date_col]).dt.date
                        actual_date = market_df[market_date_col].iloc[0]

                        if actual_date != target_date:
                            self.logger.warning(
                                f"Stock fund flow actual date {actual_date} does not match target {target_date}, "
                                f"API may not have updated for today yet"
                            )
                            return []
                        data_date = actual_date
                    else:
                        # 无法获取大盘数据，假设是今天
                        data_date = target_date
                except Exception:
                    # 无法验证日期，假设是今天
                    data_date = target_date

            # 设置数据日期
            df["日期"] = data_date

            # 限制返回数量
            df = df.head(top_n)

            results = []
            for _, row in df.iterrows():
                # 尝试获取股票代码列（可能是"代码"或"股票代码"）
                code = str(self._get_column(row, ["代码", "股票代码"], ""))
                # 根据代码判断交易所
                if code.startswith(("60", "68", "88", "89")):
                    exchange = "SH"
                elif code.startswith(("00", "30", "82", "83")):
                    exchange = "SZ"
                elif code.startswith(("43", "83", "87", "88")):
                    exchange = "BJ"
                else:
                    exchange = "SH"

                # Get fund flow from "净额" column
                fund_flow_val = self._parse_numeric(self._get_column(row, ["净额"]))

                flow = StockFundFlow(
                    date=target_date,
                    symbol=f"{code}.{exchange}",
                    name=str(self._get_column(row, ["名称", "股票名称", "股票简称"], "")),
                    close_price=self._parse_numeric(self._get_column(row, ["最新价", "收盘价"])),
                    change_pct=self._parse_numeric(self._get_column(row, ["涨跌幅"])),
                    fund_flow=fund_flow_val,
                    flow_ratio=0.0,  # Not available in this API
                    main_force_net=fund_flow_val,  # Use net amount as main force
                )
                results.append(flow)

            return results
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get stock fund flow: {e}")
            return []

    def get_sector_fund_flow(
        self, target_date: date, sector_type: str = "industry"
    ) -> List[SectorFundFlow]:
        """获取板块资金流向

        Args:
            target_date: 目标日期
            sector_type: 板块类型，"industry" 或 "concept"

        Returns:
            SectorFundFlow 列表
        """
        ak = self._get_ak()

        try:
            # 根据类型调用不同的接口
            if sector_type == "industry":
                df = ak.stock_fund_flow_industry()
            else:
                df = ak.stock_fund_flow_concept()

            if df.empty:
                return []

            # 检查返回数据是否有日期列，验证日期是否匹配目标日期
            date_col = None
            for col in ["日期", "date", "时间"]:
                if col in df.columns:
                    date_col = col
                    break

            # 验证日期：这些API只返回最新数据
            from datetime import date as dt_date

            if date_col:
                # 有日期列，验证日期匹配
                df[date_col] = pd.to_datetime(df[date_col]).dt.date
                actual_date = df[date_col].iloc[0]
                if actual_date != target_date:
                    self.logger.warning(
                        f"Sector fund flow data date {actual_date} does not match target {target_date}"
                    )
                    return []
                data_date = actual_date
            else:
                # 无日期列，需要通过大盘数据推断实际日期
                try:
                    market_df = ak.stock_market_fund_flow()
                    if not market_df.empty:
                        market_date_col = "日期" if "日期" in market_df.columns else market_df.columns[0]
                        market_df[market_date_col] = pd.to_datetime(market_df[market_date_col]).dt.date
                        actual_date = market_df[market_date_col].iloc[0]

                        if actual_date != target_date:
                            self.logger.warning(
                                f"Sector fund flow actual date {actual_date} does not match target {target_date}, "
                                f"API may not have updated for today yet"
                            )
                            return []
                        data_date = actual_date
                    else:
                        # 无法获取大盘数据，假设是今天
                        data_date = target_date
                except Exception:
                    # 无法验证日期，假设是今天
                    data_date = target_date

            # 设置数据日期
            df["日期"] = data_date

            results = []
            for _, row in df.iterrows():
                # 获取板块名称（可能是"行业"或"概念"）
                sector_name = str(
                    self._get_column(row, ["行业", "概念", "板块名称"], "")
                )

                flow = SectorFundFlow(
                    date=target_date,
                    sector_type=sector_type,
                    sector_name=sector_name,
                    fund_flow=self._parse_numeric(
                        self._get_column(row, ["净额", "净流入"])
                    ),
                    change_pct=self._parse_numeric(
                        self._get_column(row, ["行业-涨跌幅", "涨跌幅"])
                    ),
                    leading_stock=str(self._get_column(row, ["领涨股", "龙头股"], "")),
                    leading_stock_change=self._parse_numeric(
                        self._get_column(row, ["领涨股-涨跌幅", "领涨股涨跌幅"])
                    ),
                )
                results.append(flow)

            return results
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get sector fund flow: {e}")
            return []

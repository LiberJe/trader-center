from datetime import datetime, date
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class Frequency(str, Enum):
    """数据频率"""

    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1m"
    MIN_1 = "1min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    MIN_30 = "30min"
    MIN_60 = "60min"


class BarData(BaseModel):
    """K线数据模型"""

    model_config = {"frozen": True}

    symbol: str = Field(..., description="股票代码，如 000001.SZ")
    timestamp: datetime = Field(..., description="时间戳")
    frequency: Frequency = Field(..., description="数据周期")

    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")

    amount: Optional[float] = Field(None, description="成交额")
    adj_factor: Optional[float] = Field(None, description="复权因子")
    is_suspended: bool = Field(False, description="是否停牌")


class SymbolInfo(BaseModel):
    """股票基础信息"""

    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    exchange: str = Field(..., pattern=r"^(SZ|SH|BJ|HK|US)$")
    type: str = Field(default="stock", pattern=r"^(stock|index|etf|bond)$")
    list_date: Optional[date] = None
    delist_date: Optional[date] = None
    industry: Optional[str] = None


class FinancialReport(BaseModel):
    """财务报告数据"""

    symbol: str
    report_date: date
    report_type: str = Field(..., pattern=r"^(Q1|Q2|Q3|annual)$")

    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    eps: Optional[float] = None
    roe: Optional[float] = None
    debt_ratio: Optional[float] = None

    raw_data: Optional[dict] = None


class MacroData(BaseModel):
    """宏观数据"""

    indicator: str
    country: str = "CN"
    timestamp: date
    value: float
    period: Optional[str] = None


class MarketFundFlow(BaseModel):
    """大盘资金流向"""

    model_config = {"frozen": True}

    date: date
    market: str  # sh/sz/all
    main_force_net: float  # 主力净流入(亿元)
    super_large_net: float  # 超大单净流入
    large_net: float  # 大单净流入
    medium_net: float  # 中单净流入
    small_net: float  # 小单净流入
    total_amount: float  # 总成交额


class StockFundFlow(BaseModel):
    """个股资金流向"""

    model_config = {"frozen": True}

    date: date
    symbol: str
    name: str
    close_price: float
    change_pct: float
    fund_flow: float  # 净流入(万元)
    flow_ratio: float  # 净流占比
    main_force_net: float  # 主力净流入


class SectorFundFlow(BaseModel):
    """板块资金流向"""

    model_config = {"frozen": True}

    date: date
    sector_type: str  # industry/concept
    sector_name: str
    fund_flow: float
    change_pct: float
    leading_stock: str
    leading_stock_change: float

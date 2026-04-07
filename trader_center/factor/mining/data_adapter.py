"""
因子数据适配器

处理不同数据格式之间的转换，使 BaseFactor 能够与 FactorAnalysisPipeline 配合使用。
"""

from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np


def wide_to_dict(
    price_df: pd.DataFrame,
    include_ohlcv: bool = False,
    open_df: pd.DataFrame = None,
    high_df: pd.DataFrame = None,
    low_df: pd.DataFrame = None,
    volume_df: pd.DataFrame = None,
) -> Dict[str, pd.DataFrame]:
    """
    将宽表格式价格数据转换为字典格式
    
    宽表格式：index=日期，columns=股票代码
    字典格式：{symbol: DataFrame}，每个 DataFrame 包含 OHLCV 数据
    
    Args:
        price_df: 收盘价数据（index=日期，columns=股票代码）
        include_ohlcv: 是否包含完整 OHLCV 数据
        open_df: 开盘价数据（可选）
        high_df: 最高价数据（可选）
        low_df: 最低价数据（可选）
        volume_df: 成交量数据（可选）
    
    Returns:
        {symbol: DataFrame} 格式的字典，每个 DataFrame 包含 OHLCV 数据
    
    Example:
        >>> price_df = pd.DataFrame({
        ...     'AAPL': [100, 101, 102],
        ...     'MSFT': [200, 201, 202]
        ... }, index=pd.date_range('2023-01-01', periods=3))
        >>> data_dict = wide_to_dict(price_df)
        >>> list(data_dict.keys())
        ['AAPL', 'MSFT']
    """
    data_dict = {}
    
    for symbol in price_df.columns:
        data = pd.DataFrame({'close': price_df[symbol]})
        
        if include_ohlcv:
            if open_df is not None and symbol in open_df.columns:
                data['open'] = open_df[symbol]
            else:
                data['open'] = price_df[symbol]
            
            if high_df is not None and symbol in high_df.columns:
                data['high'] = high_df[symbol]
            else:
                data['high'] = price_df[symbol]
            
            if low_df is not None and symbol in low_df.columns:
                data['low'] = low_df[symbol]
            else:
                data['low'] = price_df[symbol]
            
            if volume_df is not None and symbol in volume_df.columns:
                data['volume'] = volume_df[symbol]
            else:
                data['volume'] = 0
        
        data_dict[symbol] = data
    
    return data_dict


def dict_to_wide(
    data_dict: Dict[str, Union[pd.Series, pd.DataFrame]],
    column: str = None,
) -> pd.DataFrame:
    """
    将字典格式数据转换为宽表格式
    
    Args:
        data_dict: {symbol: Series/DataFrame} 格式的字典
        column: 如果值是 DataFrame，指定要提取的列名
    
    Returns:
        宽表格式 DataFrame（index=日期，columns=股票代码）
    
    Example:
        >>> data_dict = {
        ...     'AAPL': pd.Series([100, 101, 102]),
        ...     'MSFT': pd.Series([200, 201, 202])
        ... }
        >>> wide_df = dict_to_wide(data_dict)
    """
    result = {}
    
    for symbol, data in data_dict.items():
        if isinstance(data, pd.DataFrame):
            if column and column in data.columns:
                result[symbol] = data[column]
            else:
                result[symbol] = data.iloc[:, 0]
        else:
            result[symbol] = data
    
    return pd.DataFrame(result)


def prepare_ohlcv_data(
    price_df: pd.DataFrame,
    open_df: pd.DataFrame = None,
    high_df: pd.DataFrame = None,
    low_df: pd.DataFrame = None,
    volume_df: pd.DataFrame = None,
) -> Dict[str, pd.DataFrame]:
    """
    准备 OHLCV 数据字典
    
    这是 wide_to_dict 的便捷封装，自动包含完整 OHLCV 数据。
    
    Args:
        price_df: 收盘价数据（宽表格式）
        open_df: 开盘价数据（可选，默认使用收盘价）
        high_df: 最高价数据（可选，默认使用收盘价）
        low_df: 最低价数据（可选，默认使用收盘价）
        volume_df: 成交量数据（可选，默认填充0）
    
    Returns:
        {symbol: DataFrame} 格式的字典
    """
    return wide_to_dict(
        price_df=price_df,
        include_ohlcv=True,
        open_df=open_df,
        high_df=high_df,
        low_df=low_df,
        volume_df=volume_df,
    )


def align_dataframes(*dfs: pd.DataFrame) -> List[pd.DataFrame]:
    """
    对齐多个 DataFrame 的索引和列
    
    Args:
        *dfs: 多个 DataFrame
    
    Returns:
        对齐后的 DataFrame 列表
    """
    if not dfs:
        return []
    
    valid_dfs = [df for df in dfs if df is not None and not df.empty]
    
    if not valid_dfs:
        return list(dfs)
    
    common_index = valid_dfs[0].index
    common_columns = valid_dfs[0].columns
    
    for df in valid_dfs[1:]:
        common_index = common_index.intersection(df.index)
        common_columns = common_columns.intersection(df.columns)
    
    result = []
    for df in dfs:
        if df is not None and not df.empty:
            result.append(df.loc[common_index, common_columns])
        else:
            result.append(df)
    
    return result


def validate_wide_format(
    df: pd.DataFrame,
    name: str = "data",
) -> bool:
    """
    验证 DataFrame 是否为宽表格式
    
    Args:
        df: 要验证的 DataFrame
        name: 数据名称（用于错误信息）
    
    Returns:
        True 如果格式正确
    
    Raises:
        ValueError: 如果格式不正确
    """
    if df is None:
        raise ValueError(f"{name} 不能为 None")
    
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"{name} 必须是 DataFrame，当前类型: {type(df)}")
    
    if df.empty:
        raise ValueError(f"{name} 不能为空")
    
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            raise ValueError(f"{name} 的索引必须是日期类型")
    
    return True

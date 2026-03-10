"""
因子存储

提供因子数据的持久化存储功能。
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import pandas as pd
import numpy as np
import logging
import json

from trader_center.data_hub.storage import HybridStore


logger = logging.getLogger(__name__)


class FactorStore:
    """
    因子存储
    
    管理因子数据的持久化存储，支持多种存储后端。
    
    Example:
        store = FactorStore()
        
        # 保存因子数据
        store.save('momentum', '000001.SZ', factor_data, date(2024, 1, 1))
        
        # 加载因子数据
        data = store.load('momentum', ['000001.SZ'], start_date, end_date)
    """
    
    def __init__(
        self,
        storage: Optional[HybridStore] = None,
        base_path: Optional[Path] = None,
    ):
        """
        初始化因子存储
        
        Args:
            storage: HybridStore实例
            base_path: 存储基础路径（如果storage为None）
        """
        self.storage = storage
        self._base_path = base_path or Path('./data/factors')
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
    
    def save(
        self,
        factor_name: str,
        symbol: str,
        factor_data: pd.Series,
        calc_date: Optional[date] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        保存因子数据
        
        Args:
            factor_name: 因子名称
            symbol: 股票代码
            factor_data: 因子值Series，index为日期
            calc_date: 计算日期（可选）
            metadata: 因子元数据（可选）
        """
        df = factor_data.to_frame(name='value')
        df['symbol'] = symbol
        df['factor_name'] = factor_name
        df['calc_date'] = calc_date or date.today()
        
        df = df.reset_index()
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'date'})
        elif 'timestamp' in df.columns:
            df = df.rename(columns={'timestamp': 'date'})
        
        df['date'] = pd.to_datetime(df['date'])
        
        table_name = f'factor_{factor_name}'
        
        if self.storage:
            self.storage.save(df, table_name=table_name)
        else:
            self._save_to_file(factor_name, symbol, df)
        
        if metadata:
            self._save_metadata(factor_name, metadata)
        
        logger.info(
            f"保存因子数据: {factor_name} ({symbol}), "
            f"记录数={len(df)}, 日期范围={df['date'].min()} ~ {df['date'].max()}"
        )
    
    def save_batch(
        self,
        factor_name: str,
        factor_df: pd.DataFrame,
        calc_date: Optional[date] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        批量保存因子数据
        
        Args:
            factor_name: 因子名称
            factor_df: 因子值DataFrame，index为日期，columns为股票代码
            calc_date: 计算日期（可选）
            metadata: 因子元数据（可选）
        """
        records = []
        
        for symbol in factor_df.columns:
            factor_series = factor_df[symbol].dropna()
            if len(factor_series) == 0:
                continue
            
            for date_idx, value in factor_series.items():
                records.append({
                    'date': pd.to_datetime(date_idx),
                    'symbol': symbol,
                    'factor_name': factor_name,
                    'value': value,
                    'calc_date': calc_date or date.today(),
                })
        
        if not records:
            logger.warning(f"没有有效数据需要保存: {factor_name}")
            return
        
        df = pd.DataFrame(records)
        
        table_name = f'factor_{factor_name}'
        
        if self.storage:
            self.storage.save(df, table_name=table_name)
        else:
            self._save_batch_to_file(factor_name, df)
        
        if metadata:
            self._save_metadata(factor_name, metadata)
        
        logger.info(
            f"批量保存因子数据: {factor_name}, "
            f"股票数={len(factor_df.columns)}, "
            f"记录数={len(df)}"
        )
    
    def load(
        self,
        factor_name: str,
        symbols: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        加载因子数据
        
        Args:
            factor_name: 因子名称
            symbols: 股票代码列表（可选，默认加载所有）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
        
        Returns:
            因子值DataFrame，index为日期，columns为股票代码
        """
        table_name = f'factor_{factor_name}'
        
        if self.storage:
            df = self.storage.load(
                table_name=table_name,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            df = self._load_from_file(factor_name, start_date, end_date)
        
        if df is None or len(df) == 0:
            logger.warning(f"未找到因子数据: {factor_name}")
            return pd.DataFrame()
        
        if symbols:
            df = df[df['symbol'].isin(symbols)]
        
        if len(df) == 0:
            return pd.DataFrame()
        
        result = df.pivot_table(
            index='date',
            columns='symbol',
            values='value',
            aggfunc='first'
        )
        
        return result
    
    def load_latest(
        self,
        factor_name: str,
        symbols: Optional[List[str]] = None,
    ) -> pd.Series:
        """
        加载最新的因子数据
        
        Args:
            factor_name: 因子名称
            symbols: 股票代码列表（可选）
        
        Returns:
            最新因子值Series，index为股票代码
        """
        df = self.load(factor_name, symbols)
        
        if df.empty:
            return pd.Series(dtype=float)
        
        latest_date = df.index.max()
        return df.loc[latest_date]
    
    def get_available_dates(
        self,
        factor_name: str,
        symbol: Optional[str] = None,
    ) -> List[date]:
        """
        获取可用的日期列表
        
        Args:
            factor_name: 因子名称
            symbol: 股票代码（可选）
        
        Returns:
            可用日期列表
        """
        df = self.load(factor_name, [symbol] if symbol else None)
        
        if df.empty:
            return []
        
        return [d.date() for d in df.index]
    
    def get_metadata(self, factor_name: str) -> Optional[Dict[str, Any]]:
        """
        获取因子元数据
        
        Args:
            factor_name: 因子名称
        
        Returns:
            因子元数据字典
        """
        if factor_name in self._metadata_cache:
            return self._metadata_cache[factor_name]
        
        metadata_path = self._base_path / factor_name / 'metadata.json'
        
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        self._metadata_cache[factor_name] = metadata
        return metadata
    
    def _save_metadata(self, factor_name: str, metadata: Dict[str, Any]) -> None:
        """保存因子元数据"""
        metadata_path = self._base_path / factor_name / 'metadata.json'
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        self._metadata_cache[factor_name] = metadata
    
    def _save_to_file(
        self,
        factor_name: str,
        symbol: str,
        df: pd.DataFrame,
    ) -> None:
        """保存到文件"""
        file_path = self._base_path / factor_name / f'{symbol}.parquet'
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_parquet(file_path, index=False)
    
    def _save_batch_to_file(self, factor_name: str, df: pd.DataFrame) -> None:
        """批量保存到文件"""
        for symbol, group in df.groupby('symbol'):
            file_path = self._base_path / factor_name / f'{symbol}.parquet'
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                group = pd.concat([existing, group], ignore_index=True)
                group = group.drop_duplicates(subset=['date'], keep='last')
            
            group.to_parquet(file_path, index=False)
    
    def _load_from_file(
        self,
        factor_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[pd.DataFrame]:
        """从文件加载"""
        factor_path = self._base_path / factor_name
        
        if not factor_path.exists():
            return None
        
        all_data = []
        for file_path in factor_path.glob('*.parquet'):
            df = pd.read_parquet(file_path)
            all_data.append(df)
        
        if not all_data:
            return None
        
        result = pd.concat(all_data, ignore_index=True)
        
        if start_date:
            result = result[result['date'] >= pd.to_datetime(start_date)]
        if end_date:
            result = result[result['date'] <= pd.to_datetime(end_date)]
        
        return result
    
    def delete(
        self,
        factor_name: str,
        symbol: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> None:
        """
        删除因子数据
        
        Args:
            factor_name: 因子名称
            symbol: 股票代码（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
        """
        if self.storage:
            logger.warning("HybridStore不支持删除操作")
            return
        
        factor_path = self._base_path / factor_name
        
        if not factor_path.exists():
            return
        
        if symbol is None and start_date is None and end_date is None:
            import shutil
            shutil.rmtree(factor_path)
            logger.info(f"删除因子目录: {factor_name}")
            return
        
        if symbol:
            file_path = factor_path / f'{symbol}.parquet'
            if file_path.exists():
                if start_date is None and end_date is None:
                    file_path.unlink()
                    logger.info(f"删除因子文件: {factor_name}/{symbol}")
                else:
                    df = pd.read_parquet(file_path)
                    if start_date:
                        df = df[df['date'] < pd.to_datetime(start_date)]
                    if end_date:
                        df = df[df['date'] > pd.to_datetime(end_date)]
                    df.to_parquet(file_path, index=False)
                    logger.info(f"删除因子数据: {factor_name}/{symbol}, 日期范围={start_date}~{end_date}")
    
    def list_factors(self) -> List[str]:
        """
        列出所有已存储的因子
        
        Returns:
            因子名称列表
        """
        if self.storage:
            logger.warning("HybridStore不支持列出因子")
            return []
        
        if not self._base_path.exists():
            return []
        
        return [d.name for d in self._base_path.iterdir() if d.is_dir()]
    
    def __repr__(self) -> str:
        return f"FactorStore(base_path={self._base_path})"

"""
多因子轮动策略配置

提供资产配置和策略参数配置支持。
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


# 默认资产配置
ASSET_CONFIG = {
    '518880.SH': {'name': '黄金ETF', 'category': 'commodity'},
    '510300.SH': {'name': '沪深300ETF', 'category': 'equity_cn'},
    '513100.SH': {'name': '纳指ETF', 'category': 'equity_us'},
    '511010.SH': {'name': '国债ETF', 'category': 'bond'},
    '159981.SZ': {'name': '能源化工ETF', 'category': 'commodity'},
}


@dataclass
class MultiFactorRotationConfig:
    """
    多因子轮动策略配置类

    支持从字典或JSON文件加载配置，并提供导出功能。

    Attributes:
        assets: 资产配置字典 {symbol: {name, category}}
        rebalance_freq: 再平衡频率（交易日），默认20天
        top_n: 持仓资产数量，默认3
        lookback: 因子计算的历史数据长度，默认60天
        exec_type: 订单执行类型，'open'为次日开盘价，'close'为次日收盘价
    """

    assets: Dict[str, Dict[str, str]]
    rebalance_freq: int = 20
    top_n: int = 3
    lookback: int = 60
    exec_type: str = "close"

    def __post_init__(self):
        """验证配置有效性"""
        if not self.assets:
            raise ValueError("资产配置不能为空")
        if self.rebalance_freq <= 0:
            raise ValueError("再平衡频率必须大于0")
        if self.top_n <= 0:
            raise ValueError("持仓数量必须大于0")
        if self.lookback <= 0:
            raise ValueError("回看周期必须大于0")
        if self.exec_type not in ("open", "close"):
            raise ValueError("执行类型必须是 'open' 或 'close'")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "MultiFactorRotationConfig":
        """
        从字典加载配置

        Args:
            config_dict: 配置字典，包含 assets 和 strategy_params

        Returns:
            MultiFactorRotationConfig 实例
        """
        assets = config_dict.get("assets", ASSET_CONFIG)
        params = config_dict.get("strategy_params", {})

        return cls(
            assets=assets,
            rebalance_freq=params.get("rebalance_freq", 20),
            top_n=params.get("top_n", 3),
            lookback=params.get("lookback", 60),
            exec_type=params.get("exec_type", "close"),
        )

    @classmethod
    def load_from_json(cls, filepath: str) -> "MultiFactorRotationConfig":
        """
        从JSON文件加载配置

        Args:
            filepath: JSON文件路径

        Returns:
            MultiFactorRotationConfig 实例
        """
        with open(filepath, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        导出为字典格式

        Returns:
            配置字典
        """
        return {
            "assets": self.assets,
            "strategy_params": {
                "rebalance_freq": self.rebalance_freq,
                "top_n": self.top_n,
                "lookback": self.lookback,
                "exec_type": self.exec_type,
            },
        }

    def to_json(self, filepath: str, indent: int = 2) -> None:
        """
        保存配置到JSON文件

        Args:
            filepath: 目标文件路径
            indent: JSON缩进空格数
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=indent, ensure_ascii=False)

    def get_asset_info(self, symbol: str) -> Dict[str, str]:
        """
        获取资产信息

        Args:
            symbol: 资产代码

        Returns:
            资产信息字典，如果不存在则返回空字典
        """
        return self.assets.get(symbol, {})

    def get_asset_name(self, symbol: str) -> str:
        """
        获取资产名称

        Args:
            symbol: 资产代码

        Returns:
            资产名称，如果不存在则返回代码本身
        """
        return self.assets.get(symbol, {}).get("name", symbol)

    @property
    def symbols(self) -> list:
        """获取所有资产代码列表"""
        return list(self.assets.keys())

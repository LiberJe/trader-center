"""Risk-parity universe defaults and the shared external configuration boundary."""

from collections.abc import Mapping
from copy import deepcopy


LEG_LABELS = {
    "equity": "股票",
    "bond": "利率债10Y",
    "gold": "黄金",
    "commodity": "商品三混合",
}

# Built-in universe. An explicit asset_config replaces this whole symbol pool;
# merging would accidentally retain 510300.SH when the caller selects 513100.SH.
DEFAULT_ASSET_CONFIG = {
    "510300.SH": {"name": "沪深300ETF", "leg": "equity"},
    "511260.SH": {"name": "十年国债ETF", "leg": "bond"},
    "518880.SH": {"name": "黄金ETF", "leg": "gold"},
    "159981.SZ": {"name": "能源化工ETF", "leg": "commodity"},
    "159985.SZ": {"name": "豆粕ETF", "leg": "commodity"},
    "159980.SZ": {"name": "有色ETF", "leg": "commodity"},
}


def resolve_risk_parity_config(asset_config=None):
    """Return independent (assets, legs) snapshots for one run.

    Input: {symbol: {name: optional ETF name, leg: leg key or display name,
                     leg_name: optional display name for a custom leg}}.
    The four built-in keys and Chinese names are interchangeable. Other nonempty
    leg keys are allowed; each configured leg receives 1/N risk budget and its
    members form an equal-weight basket. Explicit configurations are complete
    universes, not additions to the defaults. At least two legs are required.
    """
    source = DEFAULT_ASSET_CONFIG if asset_config is None else asset_config
    if not isinstance(source, Mapping) or not source:
        raise ValueError("风险平价 asset_config 必须是非空的标的配置字典")
    assets, legs = {}, {}
    aliases = {name: key for key, name in LEG_LABELS.items()}
    for symbol, raw_info in source.items():
        if not isinstance(symbol, str) or not symbol.strip() or symbol != symbol.strip():
            raise ValueError(f"风险平价标的代码必须是非空且无首尾空白的字符串: {symbol!r}")
        if not isinstance(raw_info, Mapping):
            raise ValueError(f"风险平价标的 {symbol} 的配置必须是字典")
        info = deepcopy(dict(raw_info))
        raw_leg = info.get("leg")
        if not isinstance(raw_leg, str) or not raw_leg.strip():
            raise ValueError(f"风险平价标的 {symbol} 必须指定非空资产腿 leg")
        leg = aliases.get(raw_leg.strip(), raw_leg.strip())
        name = info.get("name", symbol)
        leg_name = info.get("leg_name", LEG_LABELS.get(leg, leg))
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"风险平价标的 {symbol} 的 name 必须是非空字符串")
        if not isinstance(leg_name, str) or not leg_name.strip():
            raise ValueError(f"风险平价资产腿 {leg} 的 leg_name 必须是非空字符串")
        name, leg_name = name.strip(), leg_name.strip()
        if leg in legs and legs[leg]["name"] != leg_name:
            raise ValueError(f"风险平价资产腿 {leg} 的 leg_name 不一致")
        if leg not in legs:
            legs[leg] = {"name": leg_name, "members": []}
        legs[leg]["members"].append(symbol)
        info.update(name=name, leg=leg)
        assets[symbol] = info
    if len(legs) < 2:
        raise ValueError("风险平价至少需要两条非空资产腿，才能估计协方差并计算 ERC")
    if len({leg["name"] for leg in legs.values()}) != len(legs):
        raise ValueError("不同风险平价资产腿不能使用相同的显示名称")
    for leg in legs.values():
        leg["members"] = tuple(leg["members"])
    return assets, legs


# Compatibility export for default-universe research code. Strategy execution
# uses an instance snapshot, never these globals as a runtime symbol source.
_, DEFAULT_LEG_CONFIG = resolve_risk_parity_config()

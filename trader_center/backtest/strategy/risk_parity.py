"""
四资产风险平价策略（策略规格书 v3.2）

4 腿 6 只 ETF（全部 A 股场内）：
- 中国股票：510300.SH 沪深300ETF
- 利率债：  511260.SH 上证10年期国债ETF
- 黄金：    518880.SH 黄金ETF
- 商品：    159981.SZ 能源化工 + 159985.SZ 豆粕 + 159980.SZ 有色（三等权合成一条腿）

规则（沿用规格书 v3.2 参数，2026-10-13 起改为每日检查）：
- 权重方法：按资产腿分配等风险预算，每腿 1/N；w ≥ 0，Σw = 1
- 协方差：Ledoit-Wolf (2004, Honey) 收缩，滚动 250 个交易日，
  估计窗口截至 T-1 收盘（无前视偏差）
- 调仓机制：每个交易日收盘检查最新 ERC 目标；
  Σ|实际权重 − 目标权重| > 5% 才触发（每日检查 ≠ 每日交易）
- 执行时点：触发日收盘计算，T+1 收盘生效（broker cheat-on-close 实现）
- 持有方式：调仓间自然漂移，不每日再平衡
- 交易成本：5bp / 单位单边换手，ETF 无印花税、无最低佣金
- 商品腿内部固定三等权（执行时三只各买目标腿权重的 1/3）

实现说明：
- 佣金与成交方式由策略在 __init__ 中写入 broker（覆盖运行器默认的
  A股佣金方案），使策略自包含、可在任意 BacktestRunner 下复现。
- cheat-on-close 成交回报延后一根 bar；执行日的阈值检查计入当日
  已提交且资金可覆盖的收盘订单，避免用调仓前仓位重复触发。
"""

from typing import Dict, List, Optional

import backtrader as bt
import numpy as np

from .base import BaseStrategy
from .risk_parity_math import (
    erc_weights,
    ledoit_wolf_cov,
    risk_contributions,
    shrinkage_intensity,
)
from trader_center.backtest.broker import AStockCommissionScheme


# 腿定义：顺序即 ERC 求解中的资产顺序，每腿分配 1/N 风险预算
LEG_CONFIG = {
    "equity": {
        "name": "股票",
        "members": ("510300.SH",), # 510300.SH 沪深300ETF
        # "members": ("513100.SH",), # 510300.SH 纳指ETF
        # "members": ("510300.SH","513100.SH",), # 混合
    },
    "bond": {
        "name": "利率债10Y",
        "members": ("511260.SH",),
    },
    "gold": {
        "name": "黄金",
        "members": ("518880.SH",),
    },
    "commodity": {
        "name": "商品三混合",
        "members": ("159981.SZ", "159985.SZ", "159980.SZ"),
    },
}

LEG_NAMES = list(LEG_CONFIG.keys())


class RiskParityStrategy4A(BaseStrategy):
    """
    四资产风险平价策略（规格书 v3.2）

    以 4 条宏观腿（A股 / 10Y国债 / 黄金 / 商品三混合）构建等风险贡献组合，
    协方差使用 Ledoit-Wolf 收缩估计，每日检查、偏离超过阈值才调仓，
    T+1 收盘执行。

    Params:
        cov_window: 协方差滚动估计窗口（交易日），默认 250
        rebalance_threshold: 调仓触发阈值（Σ|实际−目标|，L1 偏离），默认 0.05
        commission: 单边佣金率，默认 0.0005（5bp）
        stamp_duty: 印花税率，默认 0.0（ETF 免印花税）
        min_commission: 最低佣金，默认 0.0
    """

    name = "risk_parity_4a"
    description = "四资产风险平价策略（ERC + LW收缩 + 每日阈值检查，规格书v3.2）"

    params = (
        ("cov_window", 250),
        ("rebalance_threshold", 0.05),
        ("commission", 0.0005),
        ("stamp_duty", 0.0),
        ("min_commission", 0.0),
    )

    def __init__(self):
        super().__init__()

        # 所有腿成员（6 只 ETF）
        self.symbols: List[str] = []
        for leg in LEG_NAMES:
            self.symbols.extend(LEG_CONFIG[leg]["members"])

        self._data_by_symbol: Dict[str, bt.DataBase] = {}
        for data in self.datas:
            symbol = data._name if hasattr(data, "_name") else "unknown"
            self._data_by_symbol[symbol] = data

        missing = [s for s in self.symbols if s not in self._data_by_symbol]
        if missing:
            raise ValueError(
                f"风险平价策略缺少数据: {missing}，需要加载: {self.symbols}"
            )

        # 收益历史：按日对齐追加（所有 feed 在同一交易日都有 bar）
        self._dates: List = []
        self._rets: Dict[str, list] = {s: [] for s in self.symbols}

        self._initialized = False
        self._pending_targets: Optional[Dict[str, float]] = None
        self._rebalance_orders_today: List[bt.Order] = []
        self.rebalance_count = 0
        self.last_leg_weights: Optional[np.ndarray] = None
        self.last_risk_contrib: Optional[np.ndarray] = None

        # --- 交易成本与成交方式（覆盖运行器默认配置）---
        # T+1 收盘生效：cheat-on-close，使 next() 中提交的市价单以当日收盘成交
        self.broker.set_coc(True)
        self.broker.addcommissioninfo(
            AStockCommissionScheme(
                commission=self.p.commission,
                stamp_duty=self.p.stamp_duty,
                min_commission=self.p.min_commission,
            )
        )

        # 初始化时未预加载的 feed 还没有日期，配置日志无需读取未来 bar。
        self.logger.info(
            f"策略初始化: 腿={LEG_NAMES}, 窗口={self.p.cov_window}, "
            f"每日检查, 阈值={self.p.rebalance_threshold:.2%}, 每腿风险预算={1 / len(LEG_NAMES):.2%}, "
            f"佣金={self.p.commission:.4%}"
        )

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def next(self):
        # 上一日订单已由 broker 处理；今日只投影本次 next() 提交的订单。
        self._rebalance_orders_today = []
        self._log_daily_state()

        # 1) 执行上一交易日收盘计算出的调仓目标（T+1 收盘生效）
        if self._pending_targets is not None:
            self._execute_rebalance(self._pending_targets)
            self._pending_targets = None

        # 2) 记录今日收盘收益（估计窗口截至 T-1，故计算时剔除当日）
        today = self.datas[0].datetime.date(0)
        self._dates.append(today)
        for symbol in self.symbols:
            data = self._data_by_symbol[symbol]
            self._rets[symbol].append(data.close[0] / data.close[-1] - 1.0)

        # 3) 决策（在 T 收盘）
        if not self._initialized:
            if len(self._dates) >= self.p.cov_window + 1:
                self._decide_rebalance(initial=True)
        else:
            self._decide_rebalance(initial=False)

    # ------------------------------------------------------------------
    # 决策
    # ------------------------------------------------------------------

    def _decide_rebalance(self, initial: bool):
        """在 T 收盘计算目标权重并决定是否调仓"""
        leg_targets, cov, rc = self._compute_leg_weights()
        etf_targets = self._leg_to_etf_weights(leg_targets)

        if initial:
            self._pending_targets = etf_targets
            self._initialized = True
            self._log_decision(etf_targets, leg_targets, cov, rc, deviation=None)
            self.log(
                f"初始建仓: 目标腿权重 {dict(zip(LEG_NAMES, np.round(leg_targets, 4)))}"
            )
            return

        current_legs = self._current_leg_weights()
        deviation = float(np.sum(np.abs(current_legs - leg_targets)))
        self.log(
            f"每日检查: 腿偏离(L1)={deviation:.2%} (阈值 {self.p.rebalance_threshold:.2%})"
        )

        if deviation > self.p.rebalance_threshold:
            self._pending_targets = etf_targets
            self._log_decision(etf_targets, leg_targets, cov, rc, deviation)
        else:
            self.log("偏离未超阈值，不调仓")

    def _compute_leg_weights(self):
        """用截至 T-1 的 250 日收益计算 ERC 目标权重"""
        window = self.p.cov_window
        cols = []
        for leg in LEG_NAMES:
            members = LEG_CONFIG[leg]["members"]
            if leg == "commodity":
                # 商品腿：三标的日内等权再平衡合成
                combo = np.mean([self._rets[m][:-1][-window:] for m in members], axis=0)
                cols.append(combo)
            else:
                cols.append(self._rets[members[0]][:-1][-window:])
        leg_ret = np.column_stack(cols)

        cov = ledoit_wolf_cov(leg_ret)
        # ERC 默认根据协方差维度 N 分配 1/N 风险预算，不区分股票或其他腿。
        leg_w = erc_weights(cov)
        rc = risk_contributions(leg_w, cov)

        self.last_leg_weights = leg_w
        self.last_risk_contrib = rc
        return leg_w, cov, rc

    def _leg_to_etf_weights(self, leg_w: np.ndarray) -> Dict[str, float]:
        """腿权重展开为 6 只 ETF 的目标权重（商品腿三等权）"""
        targets: Dict[str, float] = {}
        for i, leg in enumerate(LEG_NAMES):
            members = LEG_CONFIG[leg]["members"]
            for m in members:
                targets[m] = float(leg_w[i]) / len(members)
        return targets

    def _current_leg_weights(self) -> np.ndarray:
        """按 T 收盘估值，决策时计入当日资金可覆盖的 COC 收盘订单。

        broker 在下一根 bar 才交付当日收盘成交。按提交顺序投影仓位与
        佣金，保证执行日的检查使用成交后仓位；下一日清空投影并使用
        broker 已确认的实际仓位。资金检查与先卖后买的顺序保持一致。
        """
        total = self.broker.getvalue()
        sizes = {
            symbol: self.getposition(self._data_by_symbol[symbol]).size
            for symbol in self.symbols
        }
        available_cash = self.broker.getcash()
        for order in self._rebalance_orders_today:
            if not order.alive():
                continue
            symbol = order.data._name
            size = order.created.size - order.executed.size
            price = order.created.pclose
            commission = self.broker.getcommissioninfo(order.data).getcommission(size, price)
            available_cash -= size * price + commission
            if available_cash < 0:
                # Broker 的提交检查会拒绝资金不足的订单，不计其仓位与佣金。
                continue
            sizes[symbol] += size
            total -= commission
        if total <= 0:
            return np.zeros(len(LEG_NAMES))
        values = []
        for leg in LEG_NAMES:
            v = 0.0
            for m in LEG_CONFIG[leg]["members"]:
                v += sizes[m] * self._data_by_symbol[m].close[0]
            values.append(v)
        return np.array(values) / total

    def _log_decision(self, etf_targets, leg_targets, cov, rc, deviation):
        intensity = None
        try:
            window = self.p.cov_window
            cols = []
            for leg in LEG_NAMES:
                members = LEG_CONFIG[leg]["members"]
                if leg == "commodity":
                    cols.append(
                        np.mean([self._rets[m][:-1][-window:] for m in members], axis=0)
                    )
                else:
                    cols.append(self._rets[members[0]][:-1][-window:])
            intensity = shrinkage_intensity(np.column_stack(cols))
        except Exception:
            pass

        current = self._current_leg_weights()
        for i, leg in enumerate(LEG_NAMES):
            member = LEG_CONFIG[leg]["members"][0]
            data = self._data_by_symbol[member]
            leg_name = LEG_CONFIG[leg]["name"]
            dev_text = "" if deviation is None else f", 组合L1偏离={deviation:.2%}"
            self.log_signal(
                signal_type="rebalance",
                data=data,
                trigger_condition=(
                    f"{'初始建仓' if deviation is None else '风险平价调仓'}: "
                    f"{leg_name} 当前={current[i]:.2%} -> 目标={leg_targets[i]:.2%}{dev_text}, "
                    f"T+1收盘执行"
                ),
                indicator_values={
                    "leg": leg,
                    "current_weight": round(float(current[i]), 6),
                    "target_weight": round(float(leg_targets[i]), 6),
                    "risk_contrib": round(float(rc[i]), 6),
                    "lw_shrinkage": (
                        None if intensity is None else round(float(intensity), 6)
                    ),
                },
                confidence=1.0,
            )

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    def _execute_rebalance(self, targets: Dict[str, float]):
        """在 T+1 提交订单（cheat-on-close 以当日收盘成交）。

        先卖后买；买入按目标权重从大到小提交。
        数量通过佣金方案的 getsize() 向下取整到 100 股整手；
        同批买入共享一个本地资金预算（现金 + 预估卖出回款），
        逐单扣减，避免多个买单各自按全额现金封顶导致的资金挤兑拒单。
        """
        total = self.broker.getvalue()
        self.rebalance_count += 1
        comminfo = self.broker.getcommissioninfo(self._data_by_symbol[self.symbols[0]])

        def _current_w(symbol: str) -> float:
            data = self._data_by_symbol[symbol]
            pos = self.getposition(data)
            return pos.size * data.close[0] / total if total > 0 else 0.0

        sells = sorted(
            (s for s in self.symbols if targets[s] < _current_w(s)),
            key=lambda s: targets[s] - _current_w(s),
        )
        buys = sorted(
            (s for s in self.symbols if targets[s] >= _current_w(s)),
            key=lambda s: -targets[s],
        )

        # 本地资金预算：当前现金 + 预估卖出回款（按整手取整，偏保守）
        budget = self.broker.getcash()
        for symbol in sells:
            data = self._data_by_symbol[symbol]
            pos = self.getposition(data)
            diff_value = max(0.0, pos.size * data.close[0] - targets[symbol] * total)
            budget += comminfo.getsize(data.close[0], diff_value) * data.close[0]

        # 先卖出（降权重），按超配幅度从大到小
        for symbol in sells:
            order = self.order_target_percent(
                data=self._data_by_symbol[symbol], target=targets[symbol]
            )
            if order is not None:
                self._rebalance_orders_today.append(order)

        # 后买入：整手数量在本地预算内计算，逐单扣减（含佣金与 0.1% 缓冲）
        for symbol in buys:
            data = self._data_by_symbol[symbol]
            pos = self.getposition(data)
            price = data.close[0]
            current_value = pos.size * price
            target_value = targets[symbol] * total
            if target_value <= current_value:
                continue
            size = comminfo.getsize(price, min(target_value - current_value, budget * 0.999))
            if size <= 0:
                self.log(f"资金不足，跳过加仓 {symbol}")
                continue
            budget -= size * price * (1.0 + self.p.commission + 0.001)
            order = self.buy(data=data, size=size)
            if order is not None:
                self._rebalance_orders_today.append(order)

        self.log(
            f"执行调仓 #{self.rebalance_count}: "
            + ", ".join(f"{s}={w:.2%}" for s, w in targets.items())
        )

    # ------------------------------------------------------------------
    # 结束
    # ------------------------------------------------------------------

    def stop(self):
        super().stop()
        if self.last_leg_weights is not None:
            self.log(
                f"调仓次数: {self.rebalance_count}, "
                f"最终腿权重: {dict(zip(LEG_NAMES, np.round(self.last_leg_weights, 4)))}, "
                f"最终风险贡献: {dict(zip(LEG_NAMES, np.round(self.last_risk_contrib, 4)))}"
            )

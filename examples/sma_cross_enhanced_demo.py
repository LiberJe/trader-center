#!/usr/bin/env python3
"""增强型双均线策略回测示例."""

import os

import numpy as np
import pandas as pd
from trader_center.backtest import BacktestEngine
from trader_center.backtest.examples import SmaCrossEnhanced


def create_sample_data(days=120):
    """创建示例数据."""
    dates = pd.date_range("2024-01-01", periods=days, freq="B")
    prices = [100]
    for _ in range(1, days):
        change = (np.random.random() - 0.48) * 2  # 轻微上涨趋势
        prices.append(prices[-1] * (1 + change / 100))

    df = pd.DataFrame(
        {
            "open": [p * (1 - 0.005) for p in prices],
            "high": [p * (1 + 0.01) for p in prices],
            "low": [p * (1 - 0.01) for p in prices],
            "close": prices,
            "volume": [10000] * days,
        },
        index=dates,
    )

    return df


def main():
    """运行回测示例."""
    print("=" * 60)
    print("增强型双均线策略回测示例")
    print("=" * 60)

    # 创建数据
    df = create_sample_data(120)
    print(f"\n数据范围: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"数据条数: {len(df)}")

    # 配置回测引擎
    engine = BacktestEngine(initial_cash=100000, commission=0.0003, stake=100)  # 0.03% 手续费

    # 运行回测
    result = engine.run(
        data=df,
        strategy=SmaCrossEnhanced,
        params=dict(
            # 均线参数
            fast_period=5,
            slow_period=20,
            # ADX过滤
            use_adx_filter=True,
            adx_threshold=25,
            # 趋势确认
            use_trend_confirm=True,
            trend_ma_period=60,
            # 仓位管理
            use_volatility_sizing=True,
            risk_per_trade=0.02,
            max_position_pct=0.5,
            # 止损
            use_stop_loss=True,
            stop_loss_atr_mult=2.0,
        ),
    )

    # 打印报告
    print("\n" + result.report())

    # 保存结果
    os.makedirs("results", exist_ok=True)
    result.save("results/sma_cross_enhanced")
    print("\n结果已保存到 results/ 目录")


if __name__ == "__main__":
    main()

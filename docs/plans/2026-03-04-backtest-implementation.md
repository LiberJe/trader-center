# Backtrader 回测系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于 backtrader 构建支持多策略独立账户和并行回测的完整回测系统

**Architecture:** 封装 backtrader 原生 API，添加 A股特性支持（涨跌停、T+1、手续费），通过独立账户模式实现多策略隔离，使用 ProcessPoolExecutor 实现多进程并行

**Tech Stack:** backtrader, pandas, pydantic, pytest, concurrent.futures

---

## 任务清单

- [ ] Task 1: 项目基础结构搭建
- [ ] Task 2: DataHub 数据适配器 (PandasDataFeed)
- [ ] Task 3: A股 Broker 配置 (手续费、涨跌停、T+1)
- [ ] Task 4: 策略基类 (BaseStrategy)
- [ ] Task 5: 独立账户封装 (StrategyAccount)
- [ ] Task 6: 回测结果封装 (BacktestResult)
- [ ] Task 7: 多策略并行运行器 (MultiStrategyRunner)
- [ ] Task 8: 回测配置模块 (config.py)
- [ ] Task 9: CLI 命令行入口
- [ ] Task 10: 示例策略 (SMA交叉)
- [ ] Task 11: 集成测试

---

### Task 1: 项目基础结构搭建

**Files:**
- Create: `trader_center/backtest/__init__.py`
- Create: `trader_center/backtest/strategy/__init__.py`
- Create: `tests/backtest/__init__.py`
- Modify: `pyproject.toml` or `setup.py` - 添加 backtrader 依赖

**Step 1: 创建目录结构**

Run:
```bash
mkdir -p trader_center/backtest/strategy
mkdir -p tests/backtest
```

**Step 2: 检查 backtrader 依赖**

Check `pyproject.toml` or `setup.py` for dependencies section.

**Step 3: 添加 backtrader 依赖**

Edit `pyproject.toml`:
```toml
[project.dependencies]
backtrader = "^1.9.78"
```

Or edit `setup.py`:
```python
install_requires=[
    # ... existing deps
    "backtrader>=1.9.78",
]
```

**Step 4: 创建 backtest __init__.py**

Create `trader_center/backtest/__init__.py`:
```python
"""
Backtest Module - 基于 backtrader 的量化回测系统

Example:
    >>> from trader_center.backtest import BacktestRunner, BaseStrategy
    >>> runner = BacktestRunner()
    >>> result = runner.run(MyStrategy, symbol="000001.SZ")
"""

__version__ = "0.1.0"

# 延迟导入，避免循环依赖
def __getattr__(name):
    if name == "BaseStrategy":
        from .strategy.base import BaseStrategy
        return BaseStrategy
    if name == "BacktestRunner":
        from .runner import BacktestRunner
        return BacktestRunner
    if name == "BacktestResult":
        from .results import BacktestResult
        return BacktestResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseStrategy",
    "BacktestRunner",
    "BacktestResult",
]
```

**Step 5: 创建 strategy __init__.py**

Create `trader_center/backtest/strategy/__init__.py`:
```python
"""策略模块"""
from .base import BaseStrategy

__all__ = ["BaseStrategy"]
```

**Step 6: 创建 tests __init__.py**

Create `tests/backtest/__init__.py`:
```python
"""Backtest 模块测试"""
```

**Step 7: Commit**

```bash
git add trader_center/backtest/ tests/backtest/ pyproject.toml
git commit -m "feat(backtest): add module structure and backtrader dependency

- Create backtest package structure
- Add backtrader to dependencies
- Add lazy imports in __init__.py

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: DataHub 数据适配器 (PandasDataFeed)

**Files:**
- Create: `trader_center/backtest/data_feed.py`
- Create: `tests/backtest/test_data_feed.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_data_feed.py`:
```python
import pandas as pd
import pytest
from datetime import datetime


def test_pandas_data_feed_creation():
    """测试 PandasDataFeed 创建"""
    from trader_center.backtest.data_feed import PandasDataFeed

    # 创建模拟数据
    df = pd.DataFrame({
        'open': [10.0, 11.0, 12.0],
        'high': [11.0, 12.0, 13.0],
        'low': [9.0, 10.0, 11.0],
        'close': [10.5, 11.5, 12.5],
        'volume': [1000, 2000, 3000],
    }, index=pd.date_range('2024-01-01', periods=3))

    feed = PandasDataFeed(dataname=df, name="000001.SZ")
    assert feed is not None
    assert feed._name == "000001.SZ"


def test_pandas_data_feed_column_mapping():
    """测试列名映射"""
    from trader_center.backtest.data_feed import PandasDataFeed

    df = pd.DataFrame({
        'open': [10.0],
        'high': [11.0],
        'low': [9.0],
        'close': [10.5],
        'volume': [1000],
        'amount': [10000.0],
    }, index=pd.date_range('2024-01-01', periods=1))

    feed = PandasDataFeed(dataname=df, name="000001.SZ")
    # 验证列映射正确
    assert hasattr(feed, 'lines')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_data_feed.py -v`
Expected: FAIL with "No module named 'trader_center.backtest.data_feed'"

**Step 3: Write minimal implementation**

Create `trader_center/backtest/data_feed.py`:
```python
"""
DataHub → Backtrader 数据适配器

将 DataHub 获取的 pandas DataFrame 转换为 backtrader 可用的数据 feed。
"""

import backtrader as bt
import pandas as pd
from datetime import datetime
from typing import Optional


class PandasDataFeed(bt.feeds.PandasData):
    """
    基于 pandas DataFrame 的数据适配器

    适配 DataHub 返回的数据格式，支持 A股日线数据。

    Args:
        dataname: pandas DataFrame，包含 open/high/low/close/volume
        name: 股票代码，如 "000001.SZ"

    Example:
        >>> df = data_hub.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
        >>> feed = PandasDataFeed(dataname=df, name="000001.SZ")
        >>> cerebro.adddata(feed)
    """

    # 定义列映射（DataHub 列名 -> backtrader 字段）
    params = (
        ('datetime', None),  # 使用 DataFrame index 作为 datetime
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),  # A股无持仓量概念
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._symbol = kwargs.get('name', 'unknown')

    @classmethod
    def from_datahub(cls, symbol: str, df: pd.DataFrame) -> 'PandasDataFeed':
        """
        从 DataHub 数据创建 feed

        Args:
            symbol: 股票代码
            df: DataHub 返回的 DataFrame

        Returns:
            PandasDataFeed 实例

        Raises:
            ValueError: 如果 DataFrame 缺少必要列
        """
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame 缺少必要列: {missing}")

        # 确保 index 是 datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')
            else:
                raise ValueError("DataFrame 需要 datetime index 或 timestamp 列")

        return cls(dataname=df, name=symbol)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_data_feed.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/data_feed.py tests/backtest/test_data_feed.py
git commit -m "feat(backtest): add PandasDataFeed for DataHub integration

- Create PandasDataFeed extending bt.feeds.PandasData
- Add from_datahub() factory method
- Handle column mapping and datetime index
- Add unit tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: A股 Broker 配置

**Files:**
- Create: `trader_center/backtest/broker.py`
- Create: `tests/backtest/test_broker.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_broker.py`:
```python
import pytest


def test_astock_commission_scheme():
    """测试 A股手续费计算"""
    from trader_center.backtest.broker import AStockCommission

    comm = AStockCommission()

    # 买入 10万元，万2.5佣金
    buy_cost = comm.getcommission(size=1000, price=100.0, is_buy=True)
    # 1000 * 100 = 100000，万2.5 = 25元
    assert buy_cost == 25.0

    # 卖出 10万元，万2.5佣金 + 千1印花税 = 25 + 100 = 125
    sell_cost = comm.getcommission(size=1000, price=100.0, is_buy=False)
    assert sell_cost == 125.0


def test_minimum_commission():
    """测试最低5元佣金"""
    from trader_center.backtest.broker import AStockCommission

    comm = AStockCommission()

    # 买入 1万元，万2.5 = 2.5元，但最低5元
    buy_cost = comm.getcommission(size=100, price=100.0, is_buy=True)
    assert buy_cost == 5.0


def test_configure_broker():
    """测试配置 backtrader broker"""
    import backtrader as bt
    from trader_center.backtest.broker import configure_astock_broker

    cerebro = bt.Cerebro()
    configure_astock_broker(cerebro, cash=100000.0)

    assert cerebro.broker.getcash() == 100000.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_broker.py -v`
Expected: FAIL with module not found

**Step 3: Write minimal implementation**

Create `trader_center/backtest/broker.py`:
```python
"""
A股 Broker 配置

实现 A股交易规则：
- 买入：佣金万2.5，最低5元
- 卖出：佣金万2.5 + 印花税千1，最低5元
- 涨跌停限制（需在策略中检查）
- T+1 限制（需在策略中检查）
"""

import backtrader as bt
from dataclasses import dataclass
from typing import Optional


@dataclass
class AStockCommissionScheme(bt.CommInfoBase):
    """
    A股手续费计算方案

    规则：
    - 佣金：万2.5 (0.025%)
    - 印花税：千1 (0.1%)，仅卖出收取
    - 最低佣金：5元
    """

    params = (
        ('commission', 0.00025),   # 万2.5
        ('stamp_duty', 0.001),      # 千1印花税
        ('min_commission', 5.0),    # 最低5元
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_PERC),
    )

    def getcommission(self, size: float, price: float, is_buy: bool) -> float:
        """
        计算手续费

        Args:
            size: 成交数量
            price: 成交价格
            is_buy: 是否买入

        Returns:
            总费用（元）
        """
        amount = abs(size) * price

        # 佣金（买卖都收）
        commission = amount * self.p.commission
        commission = max(commission, self.p.min_commission)

        # 印花税（仅卖出）
        stamp_duty = 0
        if not is_buy:
            stamp_duty = amount * self.p.stamp_duty

        return commission + stamp_duty


# 别名，方便导入
AStockCommission = AStockCommissionScheme


def configure_astock_broker(
    cerebro: bt.Cerebro,
    cash: float = 100000.0,
    slip_perc: float = 0.0,
    slip_fixed: float = 0.0,
) -> bt.Broker:
    """
    配置 A股 Broker

    Args:
        cerebro: backtrader Cerebro 实例
        cash: 初始资金
        slip_perc: 滑点百分比
        slip_fixed: 固定滑点金额

    Returns:
        配置好的 Broker 实例
    """
    # 设置初始资金
    cerebro.broker.setcash(cash)

    # 添加手续费方案
    comminfo = AStockCommissionScheme()
    cerebro.broker.addcommissioninfo(comminfo)

    # 设置滑点
    if slip_perc > 0 or slip_fixed > 0:
        cerebro.broker.set_slippage_perc(slip_perc, slip_fixed)

    return cerebro.broker


@dataclass
class AStockConstraints:
    """
    A股交易限制检查器

    用于在策略中检查 A股特有规则：
    - 涨跌停限制
    - T+1 交易限制
    """

    # 涨跌停幅度（默认 10%，ST 股票 5%，创业板/科创板 20%）
    limit_up_pct: float = 0.10
    limit_down_pct: float = 0.10

    def can_buy(self, data: bt.DataBase, last_close: float) -> bool:
        """
        检查是否可以买入（非涨停）

        Args:
            data: backtrader Data 对象
            last_close: 昨日收盘价

        Returns:
            True 如果可以买入
        """
        limit_up = last_close * (1 + self.limit_up_pct)
        current_price = data.close[0]

        # 当前价格低于涨停价才能买入
        return current_price < limit_up * 0.999  # 留一点容差

    def can_sell(self, data: bt.DataBase, last_close: float) -> bool:
        """
        检查是否可以卖出（非跌停）

        Args:
            data: backtrader Data 对象
            last_close: 昨日收盘价

        Returns:
            True 如果可以卖出
        """
        limit_down = last_close * (1 - self.limit_down_pct)
        current_price = data.close[0]

        # 当前价格高于跌停价才能卖出
        return current_price > limit_down * 1.001  # 留一点容差
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_broker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/broker.py tests/backtest/test_broker.py
git commit -m "feat(backtest): add AStock broker configuration

- AStockCommissionScheme for commission and stamp duty
- configure_astock_broker() helper function
- AStockConstraints for limit up/down checks
- Add unit tests for commission calculation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: 策略基类 (BaseStrategy)

**Files:**
- Create: `trader_center/backtest/strategy/base.py`
- Create: `tests/backtest/test_base_strategy.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_base_strategy.py`:
```python
import pytest
import backtrader as bt


def test_base_strategy_exists():
    """测试 BaseStrategy 可以导入"""
    from trader_center.backtest.strategy.base import BaseStrategy
    assert BaseStrategy is not None


def test_base_strategy_has_required_attrs():
    """测试 BaseStrategy 有必要的属性"""
    from trader_center.backtest.strategy.base import BaseStrategy

    assert hasattr(BaseStrategy, 'name')
    assert hasattr(BaseStrategy, 'description')
    assert hasattr(BaseStrategy, 'log')


def test_strategy_log_method():
    """测试策略日志功能"""
    from trader_center.backtest.strategy.base import BaseStrategy
    import logging

    # 创建一个简单的测试
    class TestStrategy(BaseStrategy):
        name = "test"

        def __init__(self):
            super().__init__()
            self.logs = []

        def log(self, txt, dt=None):
            # 覆盖以捕获日志
            self.logs.append(txt)

    strategy = TestStrategy()
    strategy.log("测试消息")
    assert "测试消息" in strategy.logs
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_base_strategy.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `trader_center/backtest/strategy/base.py`:
```python
"""
策略基类

封装 backtrader 的 bt.Strategy，添加 A股特性和日志功能。
"""

import backtrader as bt
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging


class BaseStrategy(bt.Strategy):
    """
    A股策略基类

    封装 backtrader 原生 Strategy，添加：
    - 统一日志记录
    - A股交易限制检查
    - 订单跟踪
    - 独立账户支持

    Attributes:
        name: 策略名称（类属性，必须设置）
        description: 策略描述（类属性）

    Example:
        class MyStrategy(BaseStrategy):
            name = "my_strategy"
            description = "我的策略"

            params = (('period', 20),)

            def __init__(self):
                super().__init__()
                self.sma = bt.indicators.SMA(period=self.p.period)

            def next(self):
                if self.sma > self.data.close:
                    self.buy()
    """

    # 类属性，子类必须设置
    name: str = "base"
    description: str = ""

    # backtrader params
    params = ()

    def __init__(self):
        """初始化策略"""
        super().__init__()
        self.logger = logging.getLogger(f"backtest.strategy.{self.name}")

        # 订单跟踪
        self.orders: List[bt.Order] = []
        self.trades: List[Dict[str, Any]] = []

        # 持仓信息（用于T+1检查）
        self._buy_dates: Dict[str, datetime] = {}

    def log(self, txt: str, dt: Optional[datetime] = None):
        """
        记录日志

        Args:
            txt: 日志内容
            dt: 日期时间，默认使用当前数据日期
        """
        dt = dt or self.datas[0].datetime.date(0)
        msg = f"[{dt.isoformat()}] {txt}"
        self.logger.info(msg)

    def notify_order(self, order: bt.Order):
        """
        订单状态通知回调

        子类可重写此方法处理订单状态变化。

        Args:
            order: backtrader Order 对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            action = "买入" if order.isbuy() else "卖出"
            self.log(
                f"订单成交 {action}: 价格={order.executed.price:.2f}, "
                f"数量={order.executed.size}, "
                f"金额={order.executed.value:.2f}, "
                f"手续费={order.executed.comm:.2f}"
            )

            # 记录交易
            self.trades.append({
                'date': self.datas[0].datetime.date(0),
                'action': 'buy' if order.isbuy() else 'sell',
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm,
            })

            # 记录买入日期（用于T+1检查）
            if order.isbuy():
                symbol = order.data._name
                self._buy_dates[symbol] = self.datas[0].datetime.date(0)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单失败: {order.status}")

        # 从跟踪列表中移除已完成/失败的订单
        if order in self.orders:
            self.orders.remove(order)

    def notify_trade(self, trade: bt.Trade):
        """
        交易通知回调

        Args:
            trade: backtrader Trade 对象
        """
        if not trade.isclosed:
            return

        self.log(
            f"交易闭环: 毛盈亏={trade.pnl:.2f}, "
            f"净盈亏={trade.pnlcomm:.2f}"
        )

    def can_sell_today(self, data: bt.DataBase) -> bool:
        """
        检查今天是否可以卖出（T+1检查）

        Args:
            data: 数据对象

        Returns:
            True 如果可以卖出
        """
        symbol = data._name
        if symbol not in self._buy_dates:
            return True  # 不是今天买的

        buy_date = self._buy_dates[symbol]
        today = data.datetime.date(0)

        return today > buy_date  # 必须是次日及以后

    def prenext(self):
        """预热期，数据不足时调用"""
        pass

    def nextstart(self):
        """第一个有完整数据的 bar"""
        pass

    def next(self):
        """
        逐 K 线执行

        子类必须重写此方法实现策略逻辑。
        """
        raise NotImplementedError("子类必须实现 next() 方法")

    def stop(self):
        """回测结束时调用"""
        # 计算并记录最终收益
        portfolio_value = self.broker.getvalue()
        cash = self.broker.getcash()
        self.log(f"回测结束: 总资产={portfolio_value:.2f}, 现金={cash:.2f}")

    def get_trades_df(self):
        """
        获取交易记录 DataFrame

        Returns:
            pandas DataFrame
        """
        import pandas as pd
        return pd.DataFrame(self.trades)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_base_strategy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/strategy/base.py tests/backtest/test_base_strategy.py
git commit -m "feat(backtest): add BaseStrategy with A-stock features

- Extend bt.Strategy with logging and order tracking
- Add T+1 sell restriction check
- Add trade recording and export
- Add notify_order/notify_trade callbacks

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: 独立账户封装 (StrategyAccount)

**Files:**
- Create: `trader_center/backtest/account.py`
- Create: `tests/backtest/test_account.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_account.py`:
```python
import pytest
from datetime import date


def test_strategy_account_creation():
    """测试账户创建"""
    from trader_center.backtest.account import StrategyAccount

    account = StrategyAccount(
        strategy_name="test_strategy",
        initial_cash=100000.0
    )

    assert account.strategy_name == "test_strategy"
    assert account.initial_cash == 100000.0
    assert account.cash == 100000.0
    assert account.positions == {}


def test_strategy_account_position_update():
    """测试持仓更新"""
    from trader_center.backtest.account import StrategyAccount

    account = StrategyAccount(
        strategy_name="test",
        initial_cash=100000.0
    )

    # 买入
    account.update_position("000001.SZ", 100, 10.0)
    assert account.positions["000001.SZ"] == 100

    # 卖出
    account.update_position("000001.SZ", -100, 11.0)
    assert "000001.SZ" not in account.positions


def test_strategy_account_equity_calculation():
    """测试权益计算"""
    from trader_center.backtest.account import StrategyAccount

    account = StrategyAccount(
        strategy_name="test",
        initial_cash=100000.0
    )

    account.update_position("000001.SZ", 100, 10.0)
    account.cash -= 1000.0  # 扣除买入成本

    # 持仓市值 100 * 12 = 1200
    equity = account.calculate_equity({"000001.SZ": 12.0})
    assert equity == 100000.0 - 1000.0 + 1200.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_account.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `trader_center/backtest/account.py`:
```python
"""
独立账户封装

为每个策略提供独立的资金和持仓管理。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional
from decimal import Decimal


@dataclass
class Position:
    """持仓记录"""
    symbol: str
    size: int
    avg_cost: float
    buy_date: date

    def market_value(self, current_price: float) -> float:
        """计算持仓市值"""
        return self.size * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        """计算浮动盈亏"""
        return self.size * (current_price - self.avg_cost)


@dataclass
class StrategyAccount:
    """
    策略独立账户

    管理单个策略的资金、持仓和交易记录。

    Attributes:
        strategy_name: 策略名称
        initial_cash: 初始资金
        cash: 当前可用现金
        positions: 持仓字典 {symbol: Position}
        trades: 交易记录列表
    """

    strategy_name: str
    initial_cash: float
    cash: float = field(default=None)
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if self.cash is None:
            self.cash = self.initial_cash

    def update_position(self, symbol: str, size_change: int, price: float,
                        trade_date: date = None):
        """
        更新持仓

        Args:
            symbol: 股票代码
            size_change: 数量变化（正数买入，负数卖出）
            price: 成交价格
            trade_date: 交易日期
        """
        trade_date = trade_date or date.today()

        if symbol not in self.positions:
            if size_change > 0:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    size=size_change,
                    avg_cost=price,
                    buy_date=trade_date
                )
        else:
            pos = self.positions[symbol]
            if size_change > 0:
                # 加仓，更新成本
                total_cost = pos.size * pos.avg_cost + size_change * price
                pos.size += size_change
                pos.avg_cost = total_cost / pos.size
            else:
                # 减仓
                pos.size += size_change  # size_change 是负数
                if pos.size <= 0:
                    del self.positions[symbol]

        # 记录交易
        self.trades.append({
            'date': trade_date,
            'symbol': symbol,
            'action': 'buy' if size_change > 0 else 'sell',
            'size': abs(size_change),
            'price': price,
        })

    def update_cash(self, amount: float):
        """
        更新现金

        Args:
            amount: 变化金额（正数增加，负数减少）
        """
        self.cash += amount

    def calculate_equity(self, prices: Dict[str, float]) -> float:
        """
        计算总权益

        Args:
            prices: 当前价格字典 {symbol: price}

        Returns:
            总权益 = 现金 + 持仓市值
        """
        position_value = sum(
            pos.market_value(prices.get(symbol, 0))
            for symbol, pos in self.positions.items()
        )
        return self.cash + position_value

    def get_position_size(self, symbol: str) -> int:
        """获取某股票持仓数量"""
        pos = self.positions.get(symbol)
        return pos.size if pos else 0

    def get_total_pnl(self, prices: Dict[str, float]) -> float:
        """
        计算总盈亏

        Args:
            prices: 当前价格字典

        Returns:
            总盈亏 = 当前权益 - 初始资金
        """
        equity = self.calculate_equity(prices)
        return equity - self.initial_cash

    def to_dict(self) -> Dict:
        """导出为字典"""
        return {
            'strategy_name': self.strategy_name,
            'initial_cash': self.initial_cash,
            'cash': self.cash,
            'positions': {
                symbol: {
                    'size': pos.size,
                    'avg_cost': pos.avg_cost,
                    'buy_date': pos.buy_date.isoformat(),
                }
                for symbol, pos in self.positions.items()
            },
            'trade_count': len(self.trades),
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_account.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/account.py tests/backtest/test_account.py
git commit -m "feat(backtest): add StrategyAccount for isolated account management

- StrategyAccount dataclass for cash and positions
- Position tracking with avg cost calculation
- Trade recording per account
- Equity and PnL calculation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: 回测结果封装 (BacktestResult)

**Files:**
- Create: `trader_center/backtest/results.py`
- Create: `tests/backtest/test_results.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_results.py`:
```python
import pytest
from datetime import date


def test_backtest_result_creation():
    """测试结果对象创建"""
    from trader_center.backtest.results import BacktestResult

    result = BacktestResult(
        strategy_name="test",
        initial_cash=100000.0,
        final_value=110000.0,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result.strategy_name == "test"
    assert result.return_pct == 0.10  # 10%


def test_backtest_result_metrics():
    """测试绩效指标计算"""
    from trader_center.backtest.results import BacktestResult

    result = BacktestResult(
        strategy_name="test",
        initial_cash=100000.0,
        final_value=90000.0,
        trades=[
            {'date': date(2024, 1, 1), 'pnl': 1000},
            {'date': date(2024, 1, 2), 'pnl': -2000},
            {'date': date(2024, 1, 3), 'pnl': 500},
        ],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result.total_trades == 3
    assert result.win_rate == 2/3  # 2胜1负
    assert result.return_pct == -0.10  # -10%
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_results.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `trader_center/backtest/results.py`:
```python
"""
回测结果封装

定义回测结果的数据结构和绩效指标计算。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Optional, Any
import pandas as pd


@dataclass
class BacktestResult:
    """
    回测结果

    包含回测的所有输出数据和绩效指标。

    Attributes:
        strategy_name: 策略名称
        initial_cash: 初始资金
        final_value: 最终资产价值
        trades: 交易记录列表
        daily_values: 每日资产价值序列
        start_date: 回测开始日期
        end_date: 回测结束日期
        logs: 日志记录
        params: 策略参数
    """

    strategy_name: str
    initial_cash: float
    final_value: float
    start_date: date
    end_date: date

    trades: List[Dict[str, Any]] = field(default_factory=list)
    daily_values: List[Dict[str, Any]] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    params: Optional[Dict[str, Any]] = None

    # 运行时信息
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None

    @property
    def return_pct(self) -> float:
        """总收益率"""
        if self.initial_cash == 0:
            return 0.0
        return (self.final_value - self.initial_cash) / self.initial_cash

    @property
    def total_trades(self) -> int:
        """总交易次数"""
        return len(self.trades)

    @property
    def win_rate(self) -> float:
        """胜率"""
        if not self.trades:
            return 0.0
        winning_trades = sum(1 for t in self.trades if t.get('pnl', 0) > 0)
        return winning_trades / len(self.trades)

    @property
    def profit_factor(self) -> float:
        """盈亏比"""
        gross_profit = sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) < 0))
        if gross_loss == 0:
            return gross_profit if gross_profit > 0 else 1.0
        return gross_profit / gross_loss

    def calculate_max_drawdown(self) -> float:
        """
        计算最大回撤

        Returns:
            最大回撤百分比（负数）
        """
        if not self.daily_values:
            return 0.0

        df = pd.DataFrame(self.daily_values)
        if 'value' not in df.columns:
            return 0.0

        df['peak'] = df['value'].cummax()
        df['drawdown'] = (df['value'] - df['peak']) / df['peak']
        return df['drawdown'].min()

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率（简化版，假设252个交易日）

        Args:
            risk_free_rate: 无风险利率（年化）

        Returns:
            夏普比率
        """
        if not self.daily_values or len(self.daily_values) < 2:
            return 0.0

        df = pd.DataFrame(self.daily_values)
        if 'value' not in df.columns:
            return 0.0

        # 计算日收益率
        df['return'] = df['value'].pct_change()

        # 年化收益率
        excess_return = df['return'].mean() * 252 - risk_free_rate
        volatility = df['return'].std() * (252 ** 0.5)

        if volatility == 0:
            return 0.0

        return excess_return / volatility

    def to_summary(self) -> Dict[str, Any]:
        """生成摘要字典"""
        return {
            'strategy_name': self.strategy_name,
            'params': self.params,
            'period': f"{self.start_date} ~ {self.end_date}",
            'initial_cash': self.initial_cash,
            'final_value': self.final_value,
            'return_pct': f"{self.return_pct:.2%}",
            'total_trades': self.total_trades,
            'win_rate': f"{self.win_rate:.2%}",
            'profit_factor': f"{self.profit_factor:.2f}",
            'max_drawdown': f"{self.calculate_max_drawdown():.2%}",
            'sharpe_ratio': f"{self.calculate_sharpe_ratio():.2f}",
            'duration_seconds': self.duration_seconds,
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame（一行）"""
        return pd.DataFrame([self.to_summary()])

    def save(self, filepath: str):
        """
        保存结果到文件

        Args:
            filepath: 文件路径，支持 .json, .csv, .html
        """
        import json

        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                json.dump({
                    'summary': self.to_summary(),
                    'trades': self.trades,
                    'daily_values': self.daily_values,
                    'logs': self.logs,
                }, f, indent=2, default=str)

        elif filepath.endswith('.csv'):
            self.to_dataframe().to_csv(filepath, index=False)

        elif filepath.endswith('.html'):
            # 生成简单的 HTML 报告
            html = f"""
            <html>
            <head><title>{self.strategy_name} Backtest Result</title></head>
            <body>
                <h1>{self.strategy_name} 回测结果</h1>
                <pre>{pd.DataFrame([self.to_summary()]).to_html()}</pre>
            </body>
            </html>
            """
            with open(filepath, 'w') as f:
                f.write(html)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_results.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/results.py tests/backtest/test_results.py
git commit -m "feat(backtest): add BacktestResult for result encapsulation

- BacktestResult dataclass with all metrics
- Performance calculations: return, win_rate, max_drawdown, sharpe
- Export to JSON/CSV/HTML
- Trade and daily value tracking

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: 多策略并行运行器

**Files:**
- Create: `trader_center/backtest/runner.py`
- Create: `tests/backtest/test_runner.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_runner.py`:
```python
import pytest
from datetime import date


def test_backtest_runner_creation():
    """测试运行器创建"""
    from trader_center.backtest.runner import BacktestRunner

    runner = BacktestRunner()
    assert runner is not None


def test_backtest_runner_with_max_workers():
    """测试带进程数限制的创建"""
    from trader_center.backtest.runner import BacktestRunner

    runner = BacktestRunner(max_workers=2)
    assert runner.max_workers == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_runner.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `trader_center/backtest/runner.py`:
```python
"""
回测运行器

支持单策略回测和多策略并行回测。
"""

import backtrader as bt
from datetime import date, datetime
from typing import Type, List, Dict, Any, Optional, Union
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
import time

from trader_center.backtest.strategy.base import BaseStrategy
from trader_center.backtest.data_feed import PandasDataFeed
from trader_center.backtest.broker import configure_astock_broker
from trader_center.backtest.results import BacktestResult
from trader_center.backtest.account import StrategyAccount

# 导入 DataHub
try:
    import trader_center.data_hub as dh
except ImportError:
    dh = None


logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    回测运行器

    负责：
    - 从 DataHub 加载数据
    - 配置 backtrader Cerebro
    - 执行回测
    - 收集结果

    Example:
        >>> runner = BacktestRunner()
        >>> result = runner.run(
        ...     strategy=SmaStrategy,
        ...     symbols=["000001.SZ"],
        ...     start="2024-01-01",
        ...     end="2024-12-31",
        ...     initial_cash=100000
        ... )
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Args:
            max_workers: 多进程并行时的最大进程数，None 表示使用 CPU 核心数
        """
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)

    def run(
        self,
        strategy: Type[BaseStrategy],
        symbols: Union[str, List[str]],
        start: Union[str, date],
        end: Union[str, date],
        initial_cash: float = 100000.0,
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> BacktestResult:
        """
        运行单策略回测

        Args:
            strategy: 策略类（继承 BaseStrategy）
            symbols: 股票代码或列表
            start: 开始日期
            end: 结束日期
            initial_cash: 初始资金
            strategy_params: 策略参数

        Returns:
            BacktestResult 回测结果
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        start_time = time.time()
        strategy_name = getattr(strategy, 'name', strategy.__name__)

        try:
            # 创建 Cerebro
            cerebro = bt.Cerebro()

            # 添加策略
            if strategy_params:
                cerebro.addstrategy(strategy, **strategy_params)
            else:
                cerebro.addstrategy(strategy)

            # 加载数据
            for symbol in symbols:
                data = self._load_data(symbol, start, end)
                if data:
                    cerebro.adddata(data)

            if not cerebro.datas:
                return BacktestResult(
                    strategy_name=strategy_name,
                    initial_cash=initial_cash,
                    final_value=initial_cash,
                    start_date=self._parse_date(start),
                    end_date=self._parse_date(end),
                    error_message="No data loaded",
                )

            # 配置 Broker
            configure_astock_broker(cerebro, cash=initial_cash)

            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

            # 运行回测
            self.logger.info(f"Running backtest for {strategy_name}")
            results = cerebro.run()

            # 收集结果
            strat = results[0]
            final_value = cerebro.broker.getvalue()

            # 提取交易记录
            trades = strat.get_trades_df().to_dict('records') if hasattr(strat, 'get_trades_df') else []

            return BacktestResult(
                strategy_name=strategy_name,
                initial_cash=initial_cash,
                final_value=final_value,
                trades=trades,
                start_date=self._parse_date(start),
                end_date=self._parse_date(end),
                params=strategy_params,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return BacktestResult(
                strategy_name=strategy_name,
                initial_cash=initial_cash,
                final_value=initial_cash,
                start_date=self._parse_date(start),
                end_date=self._parse_date(end),
                params=strategy_params,
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            )

    def run_multiple(
        self,
        strategies: List[Dict[str, Any]],
        symbols: Union[str, List[str]],
        start: Union[str, date],
        end: Union[str, date],
        initial_cash: float = 100000.0,
    ) -> List[BacktestResult]:
        """
        并行运行多策略回测

        Args:
            strategies: 策略配置列表，每项包含 'class', 'params', 'name'
            symbols: 股票代码或列表
            start: 开始日期
            end: 结束日期
            initial_cash: 初始资金

        Returns:
            BacktestResult 列表
        """
        if self.max_workers == 1:
            # 单进程模式
            results = []
            for config in strategies:
                result = self.run(
                    strategy=config['class'],
                    symbols=symbols,
                    start=start,
                    end=end,
                    initial_cash=initial_cash,
                    strategy_params=config.get('params'),
                )
                results.append(result)
            return results

        # 多进程并行
        workers = self.max_workers or 4
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = []
            for config in strategies:
                future = executor.submit(
                    self._run_single_worker,
                    config,
                    symbols,
                    start,
                    end,
                    initial_cash,
                )
                futures.append(future)

            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
                    results.append(BacktestResult(
                        strategy_name="unknown",
                        initial_cash=initial_cash,
                        final_value=initial_cash,
                        start_date=self._parse_date(start),
                        end_date=self._parse_date(end),
                        error_message=str(e),
                    ))

            return results

    def _run_single_worker(
        self,
        config: Dict[str, Any],
        symbols: List[str],
        start: Union[str, date],
        end: Union[str, date],
        initial_cash: float,
    ) -> BacktestResult:
        """工作进程执行的函数（必须是静态方法或模块函数）"""
        runner = BacktestRunner(max_workers=1)
        return runner.run(
            strategy=config['class'],
            symbols=symbols,
            start=start,
            end=end,
            initial_cash=initial_cash,
            strategy_params=config.get('params'),
        )

    def _load_data(
        self,
        symbol: str,
        start: Union[str, date],
        end: Union[str, date],
    ) -> Optional[PandasDataFeed]:
        """
        从 DataHub 加载数据

        Args:
            symbol: 股票代码
            start: 开始日期
            end: 结束日期

        Returns:
            PandasDataFeed 或 None
        """
        if dh is None:
            self.logger.error("DataHub not available")
            return None

        try:
            df = dh.get_daily_bars(symbol, start, end)
            if df.empty:
                self.logger.warning(f"No data for {symbol}")
                return None

            return PandasDataFeed.from_datahub(symbol, df)

        except Exception as e:
            self.logger.error(f"Failed to load data for {symbol}: {e}")
            return None

    def _parse_date(self, d: Union[str, date]) -> date:
        """解析日期"""
        if isinstance(d, str):
            return datetime.strptime(d, '%Y-%m-%d').date()
        return d
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_runner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/runner.py tests/backtest/test_runner.py
git commit -m "feat(backtest): add BacktestRunner with multi-process support

- BacktestRunner for single and multi-strategy backtesting
- ProcessPoolExecutor for parallel strategy execution
- DataHub integration for data loading
- Auto-configure analyzers and broker

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: 回测配置模块

**Files:**
- Create: `trader_center/backtest/config.py`
- Create: `tests/backtest/test_config.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_config.py`:
```python
import pytest


def test_config_defaults():
    """测试默认配置"""
    from trader_center.backtest.config import BacktestConfig

    config = BacktestConfig()
    assert config.initial_cash == 100000.0
    assert config.commission_rate == 0.00025


def test_config_custom_values():
    """测试自定义配置"""
    from trader_center.backtest.config import BacktestConfig

    config = BacktestConfig(
        initial_cash=500000.0,
        commission_rate=0.0003,
    )
    assert config.initial_cash == 500000.0
    assert config.commission_rate == 0.0003
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_config.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `trader_center/backtest/config.py`:
```python
"""
回测配置

管理回测的默认参数和配置选项。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class BacktestConfig:
    """
    回测配置

    Attributes:
        initial_cash: 初始资金（默认10万）
        commission_rate: 佣金率（默认万2.5）
        stamp_duty_rate: 印花税率（默认千1）
        min_commission: 最低佣金（默认5元）
        limit_up_pct: 涨停幅度（默认10%）
        limit_down_pct: 跌停幅度（默认10%）
        max_workers: 并行进程数（默认None=CPU核心数）
        output_dir: 结果输出目录
    """

    # 资金配置
    initial_cash: float = 100000.0

    # 手续费配置
    commission_rate: float = 0.00025  # 万2.5
    stamp_duty_rate: float = 0.001     # 千1
    min_commission: float = 5.0        # 最低5元

    # 交易限制
    limit_up_pct: float = 0.10    # 涨停10%
    limit_down_pct: float = 0.10  # 跌停10%

    # 执行配置
    max_workers: Optional[int] = None

    # 输出配置
    output_dir: Path = field(default_factory=lambda: Path.home() / ".trader_center" / "backtest_results")

    def __post_init__(self):
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            'initial_cash': self.initial_cash,
            'commission_rate': self.commission_rate,
            'stamp_duty_rate': self.stamp_duty_rate,
            'min_commission': self.min_commission,
            'limit_up_pct': self.limit_up_pct,
            'limit_down_pct': self.limit_down_pct,
            'max_workers': self.max_workers,
            'output_dir': str(self.output_dir),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'BacktestConfig':
        """从字典创建配置"""
        config = cls(**d)
        if 'output_dir' in d:
            config.output_dir = Path(d['output_dir'])
        return config
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/config.py tests/backtest/test_config.py
git commit -m "feat(backtest): add BacktestConfig for configuration management

- Dataclass for all backtest parameters
- Default values for A-stock trading
- Auto-create output directory
- Dict serialization support

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: CLI 命令行入口

**Files:**
- Create: `trader_center/backtest/cli.py`
- Create: `trader_center/backtest/__main__.py`
- Create: `tests/backtest/test_cli.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_cli.py`:
```python
import pytest


def test_cli_import():
    """测试 CLI 模块可导入"""
    from trader_center.backtest.cli import main
    assert callable(main)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_cli.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `trader_center/backtest/cli.py`:
```python
"""
回测 CLI

命令行入口用于执行回测任务。
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
import logging

from trader_center.backtest.runner import BacktestRunner
from trader_center.backtest.config import BacktestConfig


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """创建参数解析器"""
    parser = argparse.ArgumentParser(
        prog='backtest',
        description='Trader Center 量化回测系统'
    )

    parser.add_argument(
        '--strategy', '-s',
        help='策略模块路径，如 examples.sma_cross'
    )

    parser.add_argument(
        '--symbol', '-sym',
        action='append',
        help='股票代码，可多次指定'
    )

    parser.add_argument(
        '--start', '-f',
        help='开始日期 (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end', '-t',
        help='结束日期 (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--cash', '-c',
        type=float,
        default=100000.0,
        help='初始资金（默认10万）'
    )

    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=1,
        help='并行进程数（默认1）'
    )

    parser.add_argument(
        '--output', '-o',
        help='输出文件路径 (.json, .csv, .html)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )

    return parser


def main(args: Optional[list] = None) -> int:
    """
    CLI 入口

    Returns:
        退出码，0 表示成功
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    if parsed.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 参数验证
    if not parsed.strategy:
        logger.error("请指定策略 --strategy")
        return 1

    if not parsed.symbol:
        logger.error("请指定至少一个股票代码 --symbol")
        return 1

    # 默认日期
    end_date = parsed.end or date.today().isoformat()
    if not parsed.start:
        # 默认回测1年
        end = date.fromisoformat(end_date)
        start = end - timedelta(days=365)
        start_date = start.isoformat()
    else:
        start_date = parsed.start

    try:
        # 动态导入策略
        strategy = load_strategy(parsed.strategy)
        if strategy is None:
            logger.error(f"无法加载策略: {parsed.strategy}")
            return 1

        # 执行回测
        runner = BacktestRunner(max_workers=parsed.workers)
        result = runner.run(
            strategy=strategy,
            symbols=parsed.symbol,
            start=start_date,
            end=end_date,
            initial_cash=parsed.cash,
        )

        # 打印结果
        print_result(result)

        # 保存结果
        if parsed.output:
            result.save(parsed.output)
            logger.info(f"结果已保存到: {parsed.output}")

        return 0 if result.error_message is None else 1

    except Exception as e:
        logger.error(f"回测执行失败: {e}")
        return 1


def load_strategy(strategy_path: str):
    """
    动态加载策略类

    Args:
        strategy_path: 模块路径，如 "examples.sma_cross"

    Returns:
        策略类或 None
    """
    try:
        parts = strategy_path.split('.')
        module_path = '.'.join(parts[:-1])
        class_name = parts[-1]

        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except Exception as e:
        logger.error(f"加载策略失败: {e}")
        return None


def print_result(result):
    """打印回测结果"""
    print("\n" + "=" * 50)
    print(f"策略: {result.strategy_name}")
    print(f"周期: {result.start_date} ~ {result.end_date}")
    print("-" * 50)
    print(f"初始资金: {result.initial_cash:,.2f}")
    print(f"最终资产: {result.final_value:,.2f}")
    print(f"收益率:   {result.return_pct:+.2%}")
    print(f"交易次数: {result.total_trades}")
    print(f"胜率:     {result.win_rate:.1%}")
    print(f"盈亏比:   {result.profit_factor:.2f}")
    print("=" * 50 + "\n")


if __name__ == '__main__':
    sys.exit(main())
```

Create `trader_center/backtest/__main__.py`:
```python
"""
python -m trader_center.backtest
"""

from .cli import main

if __name__ == '__main__':
    import sys
    sys.exit(main())
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/cli.py trader_center/backtest/__main__.py tests/backtest/test_cli.py
git commit -m "feat(backtest): add CLI for backtest execution

- CLI with argparse for strategy, symbol, date parameters
- Dynamic strategy loading from module path
- Result printing and file export
- __main__.py for python -m execution

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 10: 示例策略

**Files:**
- Create: `trader_center/backtest/strategy/examples.py`
- Create: `tests/backtest/test_examples.py`

**Step 1: Write the failing test**

Create `tests/backtest/test_examples.py`:
```python
import pytest


def test_sma_cross_strategy_exists():
    """测试 SMA 交叉策略可导入"""
    from trader_center.backtest.strategy.examples import SmaCrossStrategy
    assert SmaCrossStrategy.name == "sma_cross"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_examples.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `trader_center/backtest/strategy/examples.py`:
```python
"""
示例策略

提供几个常用的示例策略作为参考和测试。
"""

import backtrader as bt
from .base import BaseStrategy


class SmaCrossStrategy(BaseStrategy):
    """
    双均线交叉策略

    当短期均线上穿长期均线时买入，下穿时卖出。

    Params:
        fast: 短期均线周期（默认5日）
        slow: 长期均线周期（默认20日）
    """

    name = "sma_cross"
    description = "双均线交叉策略"

    params = (
        ('fast', 5),
        ('slow', 20),
    )

    def __init__(self):
        super().__init__()
        self.sma_fast = bt.indicators.SMA(period=self.p.fast)
        self.sma_slow = bt.indicators.SMA(period=self.p.slow)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        # 无持仓时，金叉买入
        if not self.position:
            if self.crossover > 0:
                self.log(f"金叉买入，价格: {self.data.close[0]:.2f}")
                self.buy()
        # 有持仓时，死叉卖出
        else:
            if self.crossover < 0:
                self.log(f"死叉卖出，价格: {self.data.close[0]:.2f}")
                self.sell()


class RsiStrategy(BaseStrategy):
    """
    RSI 策略

    RSI < 30 超卖买入，RSI > 70 超买卖出。

    Params:
        period: RSI周期（默认14日）
        oversold: 超卖阈值（默认30）
        overbought: 超买阈值（默认70）
    """

    name = "rsi"
    description = "RSI超买超卖策略"

    params = (
        ('period', 14),
        ('oversold', 30),
        ('overbought', 70),
    )

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(period=self.p.period)

    def next(self):
        if not self.position:
            if self.rsi < self.p.oversold:
                self.log(f"RSI超卖买入: {self.rsi[0]:.1f}")
                self.buy()
        else:
            if self.rsi > self.p.overbought:
                self.log(f"RSI超买卖出: {self.rsi[0]:.1f}")
                self.sell()


class BuyAndHoldStrategy(BaseStrategy):
    """
    买入持有策略（基准策略）

    第一天买入，持有到期末。
    """

    name = "buy_and_hold"
    description = "买入持有基准策略"

    def __init__(self):
        super().__init__()
        self.bought = False

    def next(self):
        if not self.bought:
            self.log(f"买入持有: {self.data.close[0]:.2f}")
            self.order_target_percent(target=0.99)  # 99%仓位
            self.bought = True
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_examples.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add trader_center/backtest/strategy/examples.py tests/backtest/test_examples.py
git commit -m "feat(backtest): add example strategies

- SmaCrossStrategy: dual moving average crossover
- RsiStrategy: RSI overbought/oversold
- BuyAndHoldStrategy: baseline strategy

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 11: 集成测试

**Files:**
- Create: `tests/backtest/test_integration.py`

**Step 1: Write the integration test**

Create `tests/backtest/test_integration.py`:
```python
"""
回测集成测试

测试完整回测流程：DataFeed -> Strategy -> Broker -> Result
"""

import pytest
from datetime import date
import pandas as pd


@pytest.fixture
def sample_data():
    """创建模拟K线数据"""
    dates = pd.date_range('2024-01-01', '2024-03-01', freq='B')
    n = len(dates)

    # 生成简单的趋势数据
    base_price = 10.0
    prices = [base_price + i * 0.05 for i in range(n)]

    df = pd.DataFrame({
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [10000 + i * 100 for i in range(n)],
    }, index=dates)

    return df


def test_backtest_full_flow(sample_data, monkeypatch):
    """测试完整回测流程"""
    from trader_center.backtest.runner import BacktestRunner
    from trader_center.backtest.strategy.examples import BuyAndHoldStrategy
    from trader_center.backtest.data_feed import PandasDataFeed

    # Mock DataHub
    def mock_get_daily_bars(symbol, start, end):
        return sample_data

    import trader_center.data_hub as dh
    monkeypatch.setattr(dh, 'get_daily_bars', mock_get_daily_bars)

    # 执行回测
    runner = BacktestRunner(max_workers=1)
    result = runner.run(
        strategy=BuyAndHoldStrategy,
        symbols=["TEST.SZ"],
        start="2024-01-01",
        end="2024-03-01",
        initial_cash=100000.0,
    )

    # 验证结果
    assert result.strategy_name == "buy_and_hold"
    assert result.initial_cash == 100000.0
    assert result.error_message is None
    # 买入持有应该有盈利（上升趋势）
    assert result.final_value > result.initial_cash
    assert result.total_trades >= 1


def test_backtest_with_error_handling():
    """测试错误处理"""
    from trader_center.backtest.runner import BacktestRunner
    from trader_center.backtest.strategy.base import BaseStrategy

    class BrokenStrategy(BaseStrategy):
        name = "broken"

        def next(self):
            raise ValueError("模拟错误")

    runner = BacktestRunner(max_workers=1)
    result = runner.run(
        strategy=BrokenStrategy,
        symbols=["000001.SZ"],
        start="2024-01-01",
        end="2024-01-10",
        initial_cash=100000.0,
    )

    # 应该返回错误结果而不是抛出异常
    assert result.error_message is not None
    assert "模拟错误" in result.error_message
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/backtest/test_integration.py -v`
Expected: PASS (可能需要根据实际数据情况调整)

**Step 3: Commit**

```bash
git add tests/backtest/test_integration.py
git commit -m "test(backtest): add integration tests

- Test full backtest flow with mocked data
- Test error handling in strategy execution
- Verify result calculation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 实现完成总结

实现完成后，代码库将包含：

```
trader_center/backtest/
├── __init__.py           # 公共API导出
├── __main__.py           # CLI入口
├── cli.py                # 命令行实现
├── config.py             # 配置管理
├── data_feed.py          # DataHub适配器
├── broker.py             # A股手续费/限制
├── account.py            # 独立账户
├── results.py            # 结果封装
├── runner.py             # 回测执行器
├── strategy/
│   ├── __init__.py
│   ├── base.py           # 策略基类
│   └── examples.py       # 示例策略
└── utils.py              # 工具函数（预留）

tests/backtest/
├── __init__.py
├── test_data_feed.py
├── test_broker.py
├── test_base_strategy.py
├── test_account.py
├── test_results.py
├── test_runner.py
├── test_config.py
├── test_cli.py
├── test_examples.py
└── test_integration.py
```

## 使用方式

```python
# Python API
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.examples import SmaCrossStrategy

runner = BacktestRunner(max_workers=4)
result = runner.run(
    strategy=SmaCrossStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params={'fast': 10, 'slow': 30}
)
print(f"收益率: {result.return_pct:.2%}")

# CLI
python -m trader_center.backtest --strategy trader_center.backtest.strategy.examples.SmaCrossStrategy --symbol 000001.SZ --start 2024-01-01 --end 2024-12-31 -o result.json
```

---

计划创建日期: 2026-03-04

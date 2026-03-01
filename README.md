# Trader Center

Personal financial market research framework.

## Features

- **Data Hub**: Unified data access for A-share (AkShare), US/HK stocks (Yahoo), Crypto (Binance)
- **Backtest**: Vectorized and event-driven backtest engines
- **Monitor**: Daily market overview, watchlist, alerts

## Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# Initialize database
tc init

# Fetch data
tc data sync

# Run backtest
examples/backtest_demo.py

# Market overview
tc monitor overview
```

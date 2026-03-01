# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trader Center is a quantitative trading framework with two main modules:

1. **DataHub** (`trader_center/data_hub/`): Data fetching and storage system for A-share market data
2. **Monitor** (`trader_center/monitor/`): CLI tool for executing market observation tasks

## Common Commands

### Setup
```bash
# Install package in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=trader_center

# Run specific test file
pytest tests/monitor/test_task_router.py

# Run specific test
pytest tests/monitor/test_task_router.py::test_auto_discover
```

### Code Quality
```bash
# Format code
black trader_center tests

# Lint code
ruff check trader_center tests
```

### Monitor CLI
```bash
# List available tasks
python -m trader_center.monitor --list

# Execute fund flow task
python -m trader_center.monitor fund_flow

# Execute with specific date
python -m trader_center.monitor fund_flow --date 2025-08-26

# Export to file
python -m trader_center.monitor fund_flow -o report.txt
```

## Architecture

### DataHub Module

**Data Flow**: `DataRouter` → `FetcherRouter` / `HybridStorage`

- **DataRouter** (`data_hub/router.py`): Entry point that coordinates fetching and storage. Implements incremental updates by calculating missing date ranges and only fetching what's needed.
- **FetcherRouter** (`data_hub/fetchers/router.py`): Routes data requests to multiple fetchers (primarily akshare), merges results with priority-based fallback.
- **HybridStorage** (`data_hub/storage/hybrid_store.py`): Dual-backend storage - SQLite for metadata/symbol lists, Parquet for time-series bar data.
- **Models** (`data_hub/models.py`): Pydantic models: `BarData`, `SymbolInfo`, `MarketFundFlow`, `StockFundFlow`, `SectorFundFlow`.

**Key Pattern**: All data passes through Pydantic models before storage. Bar data is stored as Parquet files partitioned by symbol and frequency.

### Monitor Module

**Execution Flow**: `CLI` → `TaskRouter` → `Task` → `Formatter`

- **BaseTask** (`monitor/base_task.py`): Abstract base class for all tasks. Requires `name`, `description` class attributes. Must implement `run(**kwargs) -> dict` with status: "success" | "skipped" | "error".
- **TaskRouter** (`monitor/task_router.py`): Auto-discovers tasks from `tasks/` directory using `pkgutil`. Maintains singleton via `get_task_router()`.
- **CLI** (`monitor/cli.py`): Argument parsing and execution entry point.

**Adding a New Task**:
1. Copy `tasks/_template_/` to `tasks/my_task/`
2. Implement `MyTask(BaseTask)` in `task.py` with required `name`, `description`, `run()` method
3. Optional: Implement `format_output()` for custom display
4. Task is auto-discovered on next CLI invocation

**Task Conventions**:
- Return dict must include `"status"` key
- Dates accepted as `datetime.date` objects
- Use `validate_params()` for input validation

### Configuration

**DataHubConfig** (`data_hub/config.py`):
- Default data dir: `~/.trader_center/data/`
- SQLite metadata: `metadata.db`
- Parquet bars: `bars/` directory

### External Dependencies

- **akshare**: A-share market data source
- **pandas/pyarrow**: Data manipulation and Parquet I/O
- **pydantic**: Data validation models

## Testing Patterns

Tests use pytest with class-based fixtures for task testing:

```python
class DummyTask(BaseTask):
    name = "dummy"
    description = "A dummy task"

    def run(self, **kwargs):
        return {"status": "success"}
```

Integration tests mock external APIs (akshare) to avoid network calls.

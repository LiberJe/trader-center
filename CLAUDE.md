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
pytest tests/data_hub/test_models.py

# Run specific test
pytest tests/monitor/test_task_router.py::test_auto_discover

# Run tests by module
pytest tests/monitor/          # Monitor module tests
pytest tests/data_hub/         # DataHub module tests
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

# Execute with specific date (YYYY-MM-DD or YYYYMMDD)
python -m trader_center.monitor fund_flow --date 2025-08-26
python -m trader_center.monitor fund_flow -d 20250826

# Show top N records (default: 10)
python -m trader_center.monitor fund_flow -t 20

# Export to file
python -m trader_center.monitor fund_flow -o report.txt

# Verbose output
python -m trader_center.monitor fund_flow -v

# Clean fund flow data for a specific date
python -m trader_center.monitor clean --fund-flow -d 2025-08-26

# Clean all fund flow data
python -m trader_center.monitor clean --fund-flow --all
```

## Architecture

### DataHub Module

**Data Flow**: `API` → `DataRouter` → `Cache` → `FetcherRouter` / `HybridStorage`

- **API Layer** (`data_hub/__init__.py`): Functional interface exposed to users - `get_daily_bars()`, `get_stock_list()`, `delete_fund_flow_data()`
- **DataRouter** (`data_hub/router.py`): Entry point that coordinates fetching and storage. Implements incremental updates by calculating missing date ranges and only fetching what's needed.
- **FetcherRouter** (`data_hub/fetchers/router.py`): Routes data requests to multiple fetchers (primarily akshare), merges results with priority-based fallback.
- **HybridStorage** (`data_hub/storage/hybrid_store.py`): Dual-backend storage - SQLite for metadata/symbol lists, Parquet for time-series bar data.
- **Cache Layer** (`data_hub/cache/`): LRU memory cache with TTL support. Cache keys built via `key_builder.py`, managed by `manager.py`.
- **Models** (`data_hub/models.py`): Pydantic models: `BarData`, `SymbolInfo`, `MarketFundFlow`, `StockFundFlow`, `SectorFundFlow`.

**Key Patterns**:
- All data passes through Pydantic models before storage
- Bar data stored as Parquet files partitioned by symbol and frequency
- Incremental updates: DataRouter calculates missing date ranges and only fetches what's needed

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
- Return dict must include `"status"` key with values: "success" | "skipped" | "error"
- Dates accepted as `datetime.date` objects
- Use `validate_params()` for input validation
- Include `"reason"` key when status is "skipped" or "error"

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

### Task Testing
Tests use pytest with class-based fixtures for task testing:

```python
class DummyTask(BaseTask):
    name = "dummy"
    description = "A dummy task"

    def run(self, **kwargs):
        return {"status": "success"}
```

### Integration Tests
- Mock external APIs (akshare) to avoid network calls
- Use temporary directories for storage tests
- Test data flow from fetcher → storage → retrieval

### Test Organization
- `tests/monitor/`: CLI, task router, base task tests
- `tests/data_hub/`: Models, storage, fetchers, integration tests

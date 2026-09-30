# Services

Services implement application workflows.

## Responsibilities

- `market_data_service.py`: refresh and read local OHLCV cache.
- `catalog_service.py`: seed and query strategy models/versions.
- `strategy_execution_service.py`: run single predictions and rolling backtests.
- `metrics_service.py`: compute strategy benchmarks from persisted predictions.
- `directions.py`: shared direction calculation.

Services should be testable with mocked external dependencies.

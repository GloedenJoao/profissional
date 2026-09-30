# Models

SQLAlchemy models define the local SQLite persistence contract.

## Tables

- `stocks`: ticker metadata.
- `market_bars`: persisted OHLCV bars used by local executions and backtests.
- `actual_prices`: realized close prices used as ground truth.
- `strategy_models`: catalog entries for model families.
- `strategy_versions`: versioned executable strategy code and hypotheses.
- `strategy_runs`: single-run or backtest executions.
- `strategy_predictions`: row-level predictions emitted by a run/version.
- `predictions` and `agent_predictions`: legacy compatibility tables; do not build new workflows on them.

Model changes should be paired with tests that create the schema in temporary SQLite.

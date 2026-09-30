# Stock Oracle

This repository is a local educational webapp for benchmarking local strategy agents on stock predictions. It is not a financial product and must not present predictions as investment advice.

## Architecture rules

- Keep runtime code under `app/`; do not place application logic in templates or scripts.
- Runtime strategy execution and backtests must be local. Do not call external LLMs or market APIs from a strategy run.
- Market data refresh may call public sources through fetchers in `app/data/fetchers`, but execution/backtest code must read persisted `market_bars`.
- Persist strategy models, versions, runs, and every generated prediction so accuracy can be measured over time.
- New strategy logic should be added through the strategy catalog/seed definitions and exercised through the sandbox executor.
- The Python sandbox is an in-process safety guard for trusted local experimentation, not a strong isolation boundary for untrusted code.
- Keep external calls out of tests by mocking price fetchers and using temporary SQLite databases.

## Local commands

- Install: `pip install -e ".[dev]"`
- Initialize database: `python scripts/init_db.py`
- Run app: `python scripts/run_dev.py`
- Test: `pytest`

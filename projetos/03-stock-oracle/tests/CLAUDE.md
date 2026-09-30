# Tests

Tests validate behavior without network calls.

## Rules

- Mock yfinance through fetcher seams.
- Use temporary SQLite databases.
- Cover strategy contracts, sandbox acceptance/rejection, persistence schema, cache, execution/backtest workflows, metrics, and routes.
- Remove tests that only validate obsolete Claude prompt behavior when replacing that workflow.

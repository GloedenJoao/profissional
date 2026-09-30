# Data

This layer fetches and prepares public market data.

Strategy execution and backtests must consume persisted market bars through services, not live fetcher calls.

## Rules

- Fetchers should expose small functions with clear failure modes.
- External fetchers should stay thin and easy to mock in tests.
- Processors should be deterministic and free of external calls.
- Tests must mock fetchers that touch public services.
- Keep ticker normalization in fetchers so services receive consistent symbols.

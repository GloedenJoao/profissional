# App Layer

`app/` contains the web application and all runtime business logic.

## Boundaries

- `routers/` owns HTTP concerns only: request parsing, redirects, templates, response codes.
- `services/` owns workflows, strategy execution, backtests, and calculations.
- `models/` owns SQLAlchemy persistence models.
- `agents/` owns local strategy contracts, sandbox execution, and seeded strategy definitions.
- `data/` owns external market data access and transformations.

Do not call yfinance or execute strategy code directly from routers or templates. Route code should delegate to services.

from sqlalchemy import inspect


def test_schema_creates_expected_tables(db_session):
    tables = set(inspect(db_session.get_bind()).get_table_names())

    assert {
        "stocks",
        "market_bars",
        "actual_prices",
        "predictions",
        "agent_predictions",
        "strategy_models",
        "strategy_versions",
        "strategy_runs",
        "strategy_predictions",
    }.issubset(tables)

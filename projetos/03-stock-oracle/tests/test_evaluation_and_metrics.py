from datetime import date, timedelta

from app.services.catalog_service import ensure_seed_catalog, get_active_versions
from app.services.market_data_service import upsert_market_bar
from app.services.metrics_service import compute_metrics
from app.services.strategy_execution_service import RunRequest, run_strategy_request


def _seed_bars(db_session, ticker="MSFT", count=45):
    start = date(2026, 1, 1)
    for index in range(count):
        close = 100.0 + index
        upsert_market_bar(
            db_session,
            ticker=ticker,
            price_date=start + timedelta(days=index),
            open_price=close - 0.5,
            high_price=close + 1.0,
            low_price=close - 1.0,
            close_price=close,
            volume=1000 + index,
        )
    db_session.commit()


def test_backtest_updates_strategy_metrics(db_session):
    ensure_seed_catalog(db_session)
    version = get_active_versions(db_session)[0]
    _seed_bars(db_session)

    run = run_strategy_request(
        db_session,
        RunRequest(
            ticker="MSFT",
            version_ids=[version.id],
            mode="backtest",
            horizon_days=1,
            refresh=False,
        ),
    )

    assert run.status == "completed"
    assert run.prediction_count > 0
    assert run.resolved_count == run.prediction_count

    metrics = compute_metrics(db_session)
    assert metrics[0].strategy_version_id == version.id
    assert metrics[0].resolved_count == run.prediction_count
    assert metrics[0].directional_accuracy is not None
    assert metrics[0].rolling_accuracy is not None


def test_backtest_supports_five_day_horizon(db_session):
    ensure_seed_catalog(db_session)
    version = get_active_versions(db_session)[0]
    _seed_bars(db_session, ticker="AAPL", count=60)

    run = run_strategy_request(
        db_session,
        RunRequest(
            ticker="AAPL",
            version_ids=[version.id],
            mode="backtest",
            horizon_days=5,
            refresh=False,
        ),
    )

    assert run.horizon_days == 5
    assert run.resolved_count == run.prediction_count

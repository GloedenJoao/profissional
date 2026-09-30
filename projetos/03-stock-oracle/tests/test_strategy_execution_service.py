from datetime import date, timedelta

from app.models.strategy import StrategyPrediction, StrategyRun
from app.services.catalog_service import ensure_seed_catalog, get_active_versions
from app.services.market_data_service import upsert_market_bar
from app.services.strategy_execution_service import RunRequest, run_strategy_request


def _seed_bars(db_session, ticker="AAPL", count=30):
    start = date(2026, 1, 1)
    for index in range(count):
        upsert_market_bar(
            db_session,
            ticker=ticker,
            price_date=start + timedelta(days=index),
            close_price=120.0 + (index * 0.5),
        )
    db_session.commit()


def test_single_run_persists_unresolved_predictions(db_session):
    ensure_seed_catalog(db_session)
    version = get_active_versions(db_session)[0]
    _seed_bars(db_session)

    run = run_strategy_request(
        db_session,
        RunRequest(
            ticker="aapl",
            version_ids=[version.id],
            mode="single",
            horizon_days=1,
            refresh=False,
        ),
    )

    saved = db_session.get(StrategyRun, run.id)
    predictions = db_session.query(StrategyPrediction).filter_by(run_id=run.id).all()
    assert saved.status == "completed"
    assert saved.ticker == "AAPL"
    assert saved.prediction_count == 1
    assert saved.resolved_count == 0
    assert predictions[0].actual_price is None


def test_backtest_persists_predictions_with_actuals(db_session):
    ensure_seed_catalog(db_session)
    version = get_active_versions(db_session)[0]
    _seed_bars(db_session, count=35)

    run = run_strategy_request(
        db_session,
        RunRequest(
            ticker="AAPL",
            version_ids=[version.id],
            mode="backtest",
            horizon_days=1,
            refresh=False,
        ),
    )

    predictions = db_session.query(StrategyPrediction).filter_by(run_id=run.id).all()
    assert run.prediction_count == len(predictions)
    assert all(prediction.actual_price is not None for prediction in predictions)

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import mean

from sqlalchemy.orm import Session, selectinload

from app.agents.sandbox import StrategyExecutor
from app.agents.strategy_types import PriceBar, StrategyContext
from app.data.fetchers.price import normalize_ticker
from app.models.market import MarketBar
from app.models.strategy import StrategyPrediction, StrategyRun, StrategyVersion
from app.services.catalog_service import get_versions
from app.services.directions import direction_from_prices
from app.services.market_data_service import bars_as_price_bars, ensure_stock, get_cached_bars, refresh_market_bars


class StrategyExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunRequest:
    ticker: str
    version_ids: list[int]
    mode: str
    horizon_days: int
    period: str = "1y"
    refresh: bool = False


def run_strategy_request(db: Session, request: RunRequest) -> StrategyRun:
    ticker = ensure_stock(db, request.ticker)
    if request.mode not in {"single", "backtest"}:
        raise ValueError("mode must be single or backtest")
    if request.horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    if request.refresh:
        refresh_market_bars(db, ticker, period=request.period)

    versions = get_versions(db, request.version_ids)
    if not versions:
        raise ValueError("at least one active strategy version is required")

    run = StrategyRun(
        ticker=ticker,
        mode=request.mode,
        horizon_days=request.horizon_days,
        selected_versions=json.dumps([version.id for version in versions]),
        run_config=json.dumps({"period": request.period, "refresh": request.refresh}, sort_keys=True),
        status="completed",
    )
    db.add(run)
    db.flush()

    try:
        bars = get_cached_bars(db, ticker)
        if request.mode == "single":
            _execute_single(db, run, versions, bars)
        else:
            _execute_backtest(db, run, versions, bars)
        _update_run_metrics(run)
        run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.now(UTC)
        db.commit()
        raise StrategyExecutionError(f"Strategy run {run.id} failed: {exc}") from exc


def _execute_single(db: Session, run: StrategyRun, versions: list[StrategyVersion], bars: list[MarketBar]) -> None:
    if not bars:
        raise ValueError("no cached market bars found for ticker")
    as_of_index = len(bars) - 1
    for version in versions:
        _execute_one(db, run, version, bars, as_of_index, actual_bar=None)


def _execute_backtest(db: Session, run: StrategyRun, versions: list[StrategyVersion], bars: list[MarketBar]) -> None:
    min_history = max(5, run.horizon_days)
    if len(bars) <= min_history + run.horizon_days:
        raise ValueError("not enough cached market bars for backtest")
    last_index = len(bars) - run.horizon_days - 1
    for as_of_index in range(min_history, last_index + 1):
        actual_bar = bars[as_of_index + run.horizon_days]
        for version in versions:
            _execute_one(db, run, version, bars, as_of_index, actual_bar=actual_bar)


def _execute_one(
    db: Session,
    run: StrategyRun,
    version: StrategyVersion,
    bars: list[MarketBar],
    as_of_index: int,
    actual_bar: MarketBar | None,
) -> None:
    visible_bars = bars[: as_of_index + 1]
    as_of_bar = bars[as_of_index]
    target_date = actual_bar.price_date if actual_bar is not None else _future_trading_date(as_of_bar.price_date, run.horizon_days)
    context = StrategyContext(
        ticker=run.ticker,
        as_of_date=as_of_bar.price_date,
        target_date=target_date,
        horizon_days=run.horizon_days,
        history=bars_as_price_bars(visible_bars),
        parameters=json.loads(version.parameters or "{}"),
    )
    signal = StrategyExecutor().execute(version.code, context)
    predicted_direction = direction_from_prices(as_of_bar.close_price, signal.predicted_price)
    actual_price = actual_bar.close_price if actual_bar is not None else None
    actual_direction = (
        direction_from_prices(as_of_bar.close_price, actual_bar.close_price)
        if actual_bar is not None
        else None
    )
    db.add(
        StrategyPrediction(
            run_id=run.id,
            strategy_version_id=version.id,
            ticker=run.ticker,
            as_of_date=as_of_bar.price_date,
            target_date=target_date,
            base_price=as_of_bar.close_price,
            predicted_price=signal.predicted_price,
            predicted_direction=predicted_direction,
            confidence=signal.confidence,
            reasoning=signal.reasoning,
            actual_price=actual_price,
            actual_direction=actual_direction,
        )
    )
    db.flush()


def _update_run_metrics(run: StrategyRun) -> None:
    predictions = list(run.predictions)
    resolved = [prediction for prediction in predictions if prediction.actual_price is not None]
    run.prediction_count = len(predictions)
    run.resolved_count = len(resolved)
    if not resolved:
        run.directional_accuracy = None
        run.mae = None
        run.mape = None
        return

    correct = [prediction.predicted_direction == prediction.actual_direction for prediction in resolved]
    run.directional_accuracy = round(sum(correct) / len(correct), 4)
    run.mae = round(mean(abs(prediction.predicted_price - prediction.actual_price) for prediction in resolved), 4)
    mape_values = [
        abs(prediction.predicted_price - prediction.actual_price) / prediction.actual_price
        for prediction in resolved
        if prediction.actual_price
    ]
    run.mape = round(mean(mape_values), 4) if mape_values else None


def _future_trading_date(start: date, horizon_days: int) -> date:
    candidate = start
    remaining = horizon_days
    while remaining > 0:
        candidate += timedelta(days=1)
        if candidate.weekday() < 5:
            remaining -= 1
    return candidate


def get_run(db: Session, run_id: int) -> StrategyRun | None:
    return db.get(
        StrategyRun,
        run_id,
        options=[
            selectinload(StrategyRun.predictions).selectinload(StrategyPrediction.strategy_version),
        ],
    )

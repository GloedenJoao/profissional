from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload
from starlette import status

from app.database import get_db
from app.models.strategy import StrategyPrediction, StrategyRun, StrategyVersion
from app.services.catalog_service import list_models
from app.services.market_data_service import get_cached_bars
from app.services.metrics_service import compute_metrics


router = APIRouter()


@router.get("/api/metrics")
def metrics_json(db: Session = Depends(get_db)):
    return [asdict(metric) for metric in compute_metrics(db)]


@router.get("/api/history/{ticker}")
def history_json(ticker: str, db: Session = Depends(get_db)):
    bars = get_cached_bars(db, ticker, limit=250)
    return [
        {
            "date": bar.price_date.isoformat(),
            "open": bar.open_price,
            "high": bar.high_price,
            "low": bar.low_price,
            "close": bar.close_price,
            "volume": bar.volume,
        }
        for bar in bars
    ]


@router.get("/api/models")
def models_json(db: Session = Depends(get_db)):
    return [
        {
            "id": model.id,
            "slug": model.slug,
            "name": model.name,
            "description": model.description,
            "versions": [
                {
                    "id": version.id,
                    "version": version.version,
                    "name": version.name,
                    "hypothesis": version.hypothesis,
                    "parameters": version.parameters,
                    "is_active": version.is_active,
                }
                for version in sorted(model.versions, key=lambda item: item.version)
            ],
        }
        for model in list_models(db)
    ]


@router.get("/api/runs")
def runs_json(db: Session = Depends(get_db)):
    runs = list(
        db.scalars(select(StrategyRun).order_by(desc(StrategyRun.started_at)).limit(100)).all()
    )
    return [
        {
            "id": run.id,
            "ticker": run.ticker,
            "mode": run.mode,
            "horizon_days": run.horizon_days,
            "status": run.status,
            "prediction_count": run.prediction_count,
            "resolved_count": run.resolved_count,
            "directional_accuracy": run.directional_accuracy,
            "mae": run.mae,
            "mape": run.mape,
            "started_at": run.started_at.isoformat(),
        }
        for run in runs
    ]


@router.get("/api/runs/{run_id}/predictions")
def run_predictions_json(run_id: int, db: Session = Depends(get_db)):
    predictions = list(
        db.scalars(
            select(StrategyPrediction)
            .options(selectinload(StrategyPrediction.strategy_version).selectinload(StrategyVersion.model))
            .where(StrategyPrediction.run_id == run_id)
            .order_by(StrategyPrediction.as_of_date.asc(), StrategyPrediction.strategy_version_id.asc())
        ).all()
    )
    return [
        {
            "id": prediction.id,
            "model": prediction.strategy_version.model.name,
            "version": prediction.strategy_version.version,
            "ticker": prediction.ticker,
            "as_of_date": prediction.as_of_date.isoformat(),
            "target_date": prediction.target_date.isoformat(),
            "base_price": prediction.base_price,
            "predicted_price": prediction.predicted_price,
            "predicted_direction": prediction.predicted_direction,
            "actual_price": prediction.actual_price,
            "actual_direction": prediction.actual_direction,
            "confidence": prediction.confidence,
        }
        for prediction in predictions
    ]


@router.post("/evaluate")
def legacy_evaluate_all():
    return RedirectResponse(url="/metrics", status_code=status.HTTP_303_SEE_OTHER)

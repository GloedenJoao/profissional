from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload
from starlette import status

from app.database import get_db
from app.models.market import MarketBar
from app.models.strategy import StrategyModel, StrategyPrediction, StrategyRun, StrategyVersion
from app.services.catalog_service import get_model, list_models
from app.services.market_data_service import get_cached_bars
from app.services.metrics_service import compute_metrics
from app.services.strategy_execution_service import get_run


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    runs = _latest_runs(db, limit=8)
    ticker = (request.query_params.get("ticker") or (runs[0].ticker if runs else "AAPL")).strip().upper()
    bars = get_cached_bars(db, ticker, limit=90)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "ticker": ticker,
            "runs": runs,
            "metrics": compute_metrics(db),
            "chart": _chart_data(bars),
        },
    )


@router.get("/runs/new")
def new_run(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="new_run.html",
        context={
            "request": request,
            "models": list_models(db),
            "error": None,
            "selected": {},
        },
    )


@router.get("/predictions/new")
def legacy_new_prediction():
    return RedirectResponse(url="/runs/new", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/runs/{run_id}")
def run_detail(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return templates.TemplateResponse(
        request=request,
        name="run_detail.html",
        context={
            "request": request,
            "run": run,
            "predictions": sorted(run.predictions, key=lambda item: (item.as_of_date, item.strategy_version_id)),
        },
    )


@router.get("/models")
def models_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="models.html",
        context={
            "request": request,
            "models": list_models(db),
        },
    )


@router.get("/models/{model_id}")
def model_detail(model_id: int, request: Request, db: Session = Depends(get_db)):
    model = get_model(db, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return templates.TemplateResponse(
        request=request,
        name="model_detail.html",
        context={
            "request": request,
            "model": model,
        },
    )


@router.get("/predictions")
def predictions_page(request: Request, db: Session = Depends(get_db)):
    predictions = list(
        db.scalars(
            select(StrategyPrediction)
            .options(
                selectinload(StrategyPrediction.strategy_version).selectinload(StrategyVersion.model),
                selectinload(StrategyPrediction.run),
            )
            .order_by(desc(StrategyPrediction.created_at))
            .limit(200)
        ).all()
    )
    return templates.TemplateResponse(
        request=request,
        name="predictions.html",
        context={
            "request": request,
            "predictions": predictions,
        },
    )


@router.get("/metrics")
def metrics_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="metrics.html",
        context={
            "request": request,
            "metrics": compute_metrics(db),
        },
    )


def _latest_runs(db: Session, limit: int) -> list[StrategyRun]:
    return list(
        db.scalars(
            select(StrategyRun)
            .options(selectinload(StrategyRun.predictions))
            .order_by(desc(StrategyRun.started_at))
            .limit(limit)
        ).all()
    )


def _chart_data(bars: list[MarketBar]) -> dict[str, object]:
    if not bars:
        return {"points": "", "min_price": None, "max_price": None, "latest_price": None, "bars": []}
    closes = [bar.close_price for bar in bars]
    min_price = min(closes)
    max_price = max(closes)
    span = max(max_price - min_price, 0.0001)
    max_index = max(len(bars) - 1, 1)
    points = []
    for index, bar in enumerate(bars):
        x = round((index / max_index) * 100, 2)
        y = round(100 - (((bar.close_price - min_price) / span) * 100), 2)
        points.append(f"{x},{y}")
    return {
        "points": " ".join(points),
        "min_price": min_price,
        "max_price": max_price,
        "latest_price": closes[-1],
        "bars": bars,
    }

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

from app.database import get_db
from app.routers.pages import templates
from app.services.catalog_service import list_models, mutate_version
from app.services.strategy_execution_service import RunRequest, StrategyExecutionError, run_strategy_request


router = APIRouter()


@router.post("/runs")
def create_run(
    request: Request,
    ticker: str = Form(...),
    mode: str = Form("backtest"),
    horizon_days: int = Form(1),
    period: str = Form("1y"),
    version_ids: list[int] = Form(default=[]),
    refresh: bool = Form(False),
    db: Session = Depends(get_db),
):
    selected = {
        "ticker": ticker,
        "mode": mode,
        "horizon_days": horizon_days,
        "period": period,
        "version_ids": version_ids,
        "refresh": refresh,
    }
    try:
        run = run_strategy_request(
            db,
            RunRequest(
                ticker=ticker,
                version_ids=version_ids,
                mode=mode,
                horizon_days=horizon_days,
                period=period,
                refresh=refresh,
            ),
        )
    except (ValueError, StrategyExecutionError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="new_run.html",
            context={
                "request": request,
                "models": list_models(db),
                "error": str(exc),
                "selected": selected,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url=f"/runs/{run.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/predictions")
def legacy_create_prediction():
    return RedirectResponse(url="/runs/new", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/models/{version_id}/mutate")
def mutate_model_version(version_id: int, db: Session = Depends(get_db)):
    clone = mutate_version(db, version_id)
    return RedirectResponse(url=f"/models/{clone.model_id}", status_code=status.HTTP_303_SEE_OTHER)

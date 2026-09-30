from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.fetchers.price import get_actual_close
from app.models.prediction import Prediction
from app.models.stock import ActualPrice
from app.services.directions import direction_from_prices


@dataclass(frozen=True)
class EvaluationSummary:
    resolved: int
    skipped: int


def resolve_prediction(db: Session, prediction_id: int) -> bool:
    prediction = db.get(Prediction, prediction_id)
    if prediction is None or prediction.status != "open":
        return False
    resolved = _resolve_one(db, prediction)
    db.commit()
    return resolved


def resolve_open_predictions(db: Session) -> EvaluationSummary:
    predictions = db.scalars(
        select(Prediction)
        .where(Prediction.status == "open")
        .where(Prediction.target_date <= datetime.now(UTC).date())
        .order_by(Prediction.target_date.asc())
    ).all()

    resolved = 0
    skipped = 0
    for prediction in predictions:
        if _resolve_one(db, prediction):
            resolved += 1
        else:
            skipped += 1
    db.commit()
    return EvaluationSummary(resolved=resolved, skipped=skipped)


def _resolve_one(db: Session, prediction: Prediction) -> bool:
    if prediction.base_price is None:
        prediction.status = "failed"
        prediction.error_message = "Cannot evaluate prediction without base_price."
        return False

    actual_close = get_actual_close(prediction.ticker, prediction.target_date)
    if actual_close is None:
        return False

    prediction.actual_price = actual_close
    prediction.actual_direction = direction_from_prices(prediction.base_price, actual_close)
    prediction.status = "resolved"
    prediction.resolved_at = datetime.now(UTC)
    _upsert_actual_price(db, prediction)
    return True


def _upsert_actual_price(db: Session, prediction: Prediction) -> None:
    existing = db.scalar(
        select(ActualPrice).where(
            ActualPrice.ticker == prediction.ticker,
            ActualPrice.price_date == prediction.target_date,
        )
    )
    if existing is None:
        db.add(
            ActualPrice(
                ticker=prediction.ticker,
                price_date=prediction.target_date,
                close_price=prediction.actual_price,
            )
        )
    else:
        existing.close_price = prediction.actual_price
        existing.fetched_at = datetime.now(UTC)


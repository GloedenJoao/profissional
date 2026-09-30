from dataclasses import dataclass
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.strategy import StrategyPrediction, StrategyVersion


@dataclass(frozen=True)
class StrategyMetrics:
    strategy_version_id: int
    model_name: str
    version_name: str
    prediction_count: int
    resolved_count: int
    directional_accuracy: float | None
    rolling_accuracy: float | None
    mae: float | None
    mape: float | None


def compute_metrics(db: Session) -> list[StrategyMetrics]:
    versions = list(
        db.scalars(
            select(StrategyVersion)
            .options(
                selectinload(StrategyVersion.model),
                selectinload(StrategyVersion.predictions),
            )
            .where(StrategyVersion.is_active.is_(True))
            .order_by(StrategyVersion.id.asc())
        ).all()
    )
    return [_compute_version_metrics(version) for version in versions if version.predictions]


def _compute_version_metrics(version: StrategyVersion) -> StrategyMetrics:
    predictions = sorted(version.predictions, key=lambda item: (item.target_date, item.id))
    resolved = [prediction for prediction in predictions if prediction.actual_price is not None]
    if not resolved:
        return StrategyMetrics(
            strategy_version_id=version.id,
            model_name=version.model.name,
            version_name=version.name,
            prediction_count=len(predictions),
            resolved_count=0,
            directional_accuracy=None,
            rolling_accuracy=None,
            mae=None,
            mape=None,
        )

    return StrategyMetrics(
        strategy_version_id=version.id,
        model_name=version.model.name,
        version_name=version.name,
        prediction_count=len(predictions),
        resolved_count=len(resolved),
        directional_accuracy=_directional_accuracy(resolved),
        rolling_accuracy=_directional_accuracy(resolved[-20:]),
        mae=round(mean(abs(prediction.predicted_price - prediction.actual_price) for prediction in resolved), 4),
        mape=_mape(resolved),
    )


def _directional_accuracy(predictions: list[StrategyPrediction]) -> float | None:
    comparable = [prediction for prediction in predictions if prediction.actual_direction is not None]
    if not comparable:
        return None
    correct = [prediction.predicted_direction == prediction.actual_direction for prediction in comparable]
    return round(sum(correct) / len(correct), 4)


def _mape(predictions: list[StrategyPrediction]) -> float | None:
    values = [
        abs(prediction.predicted_price - prediction.actual_price) / prediction.actual_price
        for prediction in predictions
        if prediction.actual_price
    ]
    return round(mean(values), 4) if values else None

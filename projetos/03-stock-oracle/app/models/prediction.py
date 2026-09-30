from datetime import UTC, date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


DIRECTIONS = ("up", "down", "flat")
PREDICTION_STATUSES = ("open", "resolved", "failed")


def utc_now() -> datetime:
    return datetime.now(UTC)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("status in ('open', 'resolved', 'failed')", name="ck_prediction_status"),
        CheckConstraint(
            "orchestrator_predicted_direction is null or orchestrator_predicted_direction in ('up', 'down', 'flat')",
            name="ck_prediction_orchestrator_direction",
        ),
        CheckConstraint(
            "actual_direction is null or actual_direction in ('up', 'down', 'flat')",
            name="ck_prediction_actual_direction",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("stocks.ticker"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    agents_used: Mapped[str] = mapped_column(Text, default="[]")
    base_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    orchestrator_predicted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    orchestrator_predicted_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    orchestrator_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    orchestrator_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="predictions")
    agent_predictions: Mapped[list["AgentPrediction"]] = relationship(
        back_populates="prediction",
        cascade="all, delete-orphan",
    )


class AgentPrediction(Base):
    __tablename__ = "agent_predictions"
    __table_args__ = (
        UniqueConstraint("prediction_id", "agent_name", name="uq_agent_prediction_prediction_agent"),
        CheckConstraint("predicted_direction in ('up', 'down', 'flat')", name="ck_agent_prediction_direction"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(80), index=True)
    predicted_price: Mapped[float] = mapped_column(Float)
    predicted_direction: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    prompt_tokens_used: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    prediction: Mapped[Prediction] = relationship(back_populates="agent_predictions")


from app.models.stock import Stock  # noqa: E402


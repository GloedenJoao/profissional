from datetime import UTC, date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


RUN_MODES = ("single", "backtest")
RUN_STATUSES = ("completed", "failed")


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrategyModel(Base):
    __tablename__ = "strategy_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    versions: Mapped[list["StrategyVersion"]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
    )


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_strategy_version_model_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("strategy_models.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(160))
    hypothesis: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    parameters: Mapped[str] = mapped_column(Text, default="{}")
    code_hash: Mapped[str] = mapped_column(String(64), index=True)
    parent_version_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_versions.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    model: Mapped[StrategyModel] = relationship(back_populates="versions")
    parent_version: Mapped["StrategyVersion | None"] = relationship(remote_side=[id])
    predictions: Mapped[list["StrategyPrediction"]] = relationship(back_populates="strategy_version")


class StrategyRun(Base):
    __tablename__ = "strategy_runs"
    __table_args__ = (
        CheckConstraint("mode in ('single', 'backtest')", name="ck_strategy_run_mode"),
        CheckConstraint("status in ('completed', 'failed')", name="ck_strategy_run_status"),
        CheckConstraint("horizon_days > 0", name="ck_strategy_run_horizon_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("stocks.ticker"), index=True)
    mode: Mapped[str] = mapped_column(String(20), index=True)
    horizon_days: Mapped[int] = mapped_column(Integer)
    selected_versions: Mapped[str] = mapped_column(Text, default="[]")
    run_config: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="completed", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prediction_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved_count: Mapped[int] = mapped_column(Integer, default=0)
    directional_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    predictions: Mapped[list["StrategyPrediction"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class StrategyPrediction(Base):
    __tablename__ = "strategy_predictions"
    __table_args__ = (
        UniqueConstraint("run_id", "strategy_version_id", "as_of_date", name="uq_strategy_prediction_run_version_date"),
        CheckConstraint("predicted_direction in ('up', 'down', 'flat')", name="ck_strategy_prediction_direction"),
        CheckConstraint(
            "actual_direction is null or actual_direction in ('up', 'down', 'flat')",
            name="ck_strategy_prediction_actual_direction",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("strategy_runs.id"), index=True)
    strategy_version_id: Mapped[int] = mapped_column(ForeignKey("strategy_versions.id"), index=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("stocks.ticker"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date, index=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    base_price: Mapped[float] = mapped_column(Float)
    predicted_price: Mapped[float] = mapped_column(Float)
    predicted_direction: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    run: Mapped[StrategyRun] = relationship(back_populates="predictions")
    strategy_version: Mapped[StrategyVersion] = relationship(back_populates="predictions")

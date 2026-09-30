from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Stock(Base):
    __tablename__ = "stocks"

    ticker: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="stock")
    actual_prices: Mapped[list["ActualPrice"]] = relationship(back_populates="stock")
    market_bars: Mapped[list["MarketBar"]] = relationship(back_populates="stock")


class ActualPrice(Base):
    __tablename__ = "actual_prices"
    __table_args__ = (UniqueConstraint("ticker", "price_date", name="uq_actual_price_ticker_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("stocks.ticker"), index=True)
    price_date: Mapped[date] = mapped_column(Date, index=True)
    close_price: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    stock: Mapped[Stock] = relationship(back_populates="actual_prices")


from app.models.market import MarketBar  # noqa: E402
from app.models.prediction import Prediction  # noqa: E402

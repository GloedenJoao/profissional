from datetime import UTC, date, datetime
from math import isnan
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.strategy_types import PriceBar
from app.data.fetchers.price import get_price_history, normalize_ticker
from app.models.market import MarketBar
from app.models.stock import Stock


def ensure_stock(db: Session, ticker: str) -> str:
    ticker = normalize_ticker(ticker)
    if db.get(Stock, ticker) is None:
        db.add(Stock(ticker=ticker))
        db.flush()
    return ticker


def refresh_market_bars(db: Session, ticker: str, period: str = "1y") -> int:
    ticker = ensure_stock(db, ticker)
    history = get_price_history(ticker, period=period)
    count = 0
    for index, row in history.iterrows():
        price_date = _date_from_index(index)
        close_price = _number(row, "Close")
        if price_date is None or close_price is None:
            continue
        upsert_market_bar(
            db=db,
            ticker=ticker,
            price_date=price_date,
            open_price=_number(row, "Open"),
            high_price=_number(row, "High"),
            low_price=_number(row, "Low"),
            close_price=close_price,
            volume=_number(row, "Volume"),
        )
        count += 1
    db.commit()
    return count


def upsert_market_bar(
    db: Session,
    ticker: str,
    price_date: date,
    close_price: float,
    open_price: float | None = None,
    high_price: float | None = None,
    low_price: float | None = None,
    volume: float | None = None,
) -> MarketBar:
    ticker = ensure_stock(db, ticker)
    existing = db.scalar(
        select(MarketBar).where(
            MarketBar.ticker == ticker,
            MarketBar.price_date == price_date,
        )
    )
    if existing is None:
        existing = MarketBar(
            ticker=ticker,
            price_date=price_date,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
        )
        db.add(existing)
        db.flush()
        return existing

    existing.open_price = open_price
    existing.high_price = high_price
    existing.low_price = low_price
    existing.close_price = close_price
    existing.volume = volume
    existing.fetched_at = datetime.now(UTC)
    db.flush()
    return existing


def get_cached_bars(
    db: Session,
    ticker: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = None,
) -> list[MarketBar]:
    ticker = normalize_ticker(ticker)
    stmt = select(MarketBar).where(MarketBar.ticker == ticker)
    if start_date is not None:
        stmt = stmt.where(MarketBar.price_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(MarketBar.price_date <= end_date)
    stmt = stmt.order_by(MarketBar.price_date.asc())
    bars = list(db.scalars(stmt).all())
    if limit is not None and limit > 0:
        return bars[-limit:]
    return bars


def bars_as_price_bars(bars: list[MarketBar]) -> list[PriceBar]:
    return [
        PriceBar(
            price_date=bar.price_date,
            open_price=bar.open_price,
            high_price=bar.high_price,
            low_price=bar.low_price,
            close_price=bar.close_price,
            volume=bar.volume,
        )
        for bar in bars
    ]


def _date_from_index(index: Any) -> date | None:
    if hasattr(index, "date"):
        return index.date()
    if isinstance(index, date):
        return index
    return None


def _number(row: Any, key: str) -> float | None:
    try:
        value = row[key]
    except Exception:
        return None
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if isnan(number):
        return None
    return number

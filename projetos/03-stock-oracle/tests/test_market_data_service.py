from datetime import date

import pytest

from app.models.market import MarketBar
from app.services import market_data_service


def test_upsert_market_bar_updates_existing_row(db_session):
    market_data_service.upsert_market_bar(db_session, " aapl ", date(2026, 1, 5), close_price=100.0)
    market_data_service.upsert_market_bar(db_session, "AAPL", date(2026, 1, 5), close_price=101.5)
    db_session.commit()

    rows = db_session.query(MarketBar).all()

    assert len(rows) == 1
    assert rows[0].ticker == "AAPL"
    assert rows[0].close_price == pytest.approx(101.5)


def test_refresh_market_bars_persists_fetcher_history(monkeypatch, db_session, sample_history):
    monkeypatch.setattr(market_data_service, "get_price_history", lambda ticker, period: sample_history)

    count = market_data_service.refresh_market_bars(db_session, "MSFT", period="90d")

    assert count == len(sample_history)
    assert len(market_data_service.get_cached_bars(db_session, "MSFT")) == len(sample_history)

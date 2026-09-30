from datetime import date

import pytest

from app.data.fetchers import price


class FakeTicker:
    def __init__(self, history):
        self._history = history

    def history(self, **kwargs):
        return self._history


def test_get_current_price_uses_latest_close(monkeypatch, sample_history):
    monkeypatch.setattr(price, "_ticker", lambda ticker: FakeTicker(sample_history))

    assert price.get_current_price(" aapl ") == pytest.approx(129.5)


def test_get_actual_close_returns_first_available_close(monkeypatch, sample_history):
    monkeypatch.setattr(price, "_ticker", lambda ticker: FakeTicker(sample_history))

    assert price.get_actual_close("AAPL", date(2026, 1, 5)) == pytest.approx(100.0)


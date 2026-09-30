from datetime import date, timedelta
from typing import Any


class PriceDataUnavailable(RuntimeError):
    pass


def normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("ticker is required")
    return normalized


def _ticker(ticker: str) -> Any:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("Install yfinance before fetching market data.") from exc
    return yf.Ticker(ticker)


def get_current_price(ticker: str) -> float:
    ticker = normalize_ticker(ticker)
    history = _ticker(ticker).history(period="5d", interval="1d", auto_adjust=False)
    if history is None or history.empty or "Close" not in history:
        raise PriceDataUnavailable(f"No recent close price found for {ticker}")
    close = history["Close"].dropna()
    if close.empty:
        raise PriceDataUnavailable(f"No recent close price found for {ticker}")
    return float(close.iloc[-1])


def get_price_history(ticker: str, period: str = "90d") -> Any:
    ticker = normalize_ticker(ticker)
    history = _ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
    if history is None or history.empty or "Close" not in history:
        raise PriceDataUnavailable(f"No price history found for {ticker}")
    return history


def get_actual_close(ticker: str, price_date: date) -> float | None:
    ticker = normalize_ticker(ticker)
    end_date = price_date + timedelta(days=5)
    history = _ticker(ticker).history(
        start=price_date.isoformat(),
        end=end_date.isoformat(),
        interval="1d",
        auto_adjust=False,
    )
    if history is None or history.empty or "Close" not in history:
        return None
    close = history["Close"].dropna()
    if close.empty:
        return None
    return float(close.iloc[0])


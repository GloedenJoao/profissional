from math import sqrt
from typing import Any


def compute_rsi(close: Any, window: int = 14) -> float | None:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.dropna()
    if rsi.empty:
        return None
    return round(float(rsi.iloc[-1]), 4)


def summarize_history(history: Any) -> dict[str, float | int | None]:
    if history is None or history.empty or "Close" not in history:
        raise ValueError("history must include a Close series")

    close = history["Close"].dropna()
    if close.empty:
        raise ValueError("history must include at least one close price")

    returns = close.pct_change().dropna()
    latest_close = float(close.iloc[-1])
    first_close = float(close.iloc[0])
    summary: dict[str, float | int | None] = {
        "observations": int(len(close)),
        "latest_close": round(latest_close, 4),
        "period_return_pct": _pct_change(first_close, latest_close),
        "change_5d_pct": _window_pct_change(close, 5),
        "change_20d_pct": _window_pct_change(close, 20),
        "sma_20": _rolling_mean(close, 20),
        "sma_50": _rolling_mean(close, 50),
        "rsi_14": compute_rsi(close, 14),
        "volatility_20d_annualized_pct": None,
    }
    if len(returns) >= 2:
        summary["volatility_20d_annualized_pct"] = round(
            float(returns.tail(20).std() * sqrt(252) * 100),
            4,
        )
    return summary


def _rolling_mean(series: Any, window: int) -> float | None:
    if len(series) < window:
        return None
    return round(float(series.tail(window).mean()), 4)


def _window_pct_change(series: Any, window: int) -> float | None:
    if len(series) <= window:
        return None
    return _pct_change(float(series.iloc[-window - 1]), float(series.iloc[-1]))


def _pct_change(start: float, end: float) -> float | None:
    if start == 0:
        return None
    return round(((end - start) / start) * 100, 4)


from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class PriceBar:
    price_date: date
    open_price: float | None
    high_price: float | None
    low_price: float | None
    close_price: float
    volume: float | None = None

    def to_context(self) -> dict[str, Any]:
        return {
            "date": self.price_date.isoformat(),
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "close": self.close_price,
            "volume": self.volume,
        }


@dataclass(frozen=True)
class StrategyContext:
    ticker: str
    as_of_date: date
    target_date: date
    horizon_days: int
    history: list[PriceBar]
    parameters: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.ticker.strip():
            raise ValueError("ticker is required")
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        if not self.history:
            raise ValueError("history is required")

    @property
    def current_price(self) -> float:
        return self.history[-1].close_price

    def to_sandbox_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "as_of_date": self.as_of_date.isoformat(),
            "target_date": self.target_date.isoformat(),
            "horizon_days": self.horizon_days,
            "current_price": self.current_price,
            "history": [bar.to_context() for bar in self.history],
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class StrategySignal:
    predicted_price: float
    confidence: float
    reasoning: str

    def __post_init__(self) -> None:
        if self.predicted_price <= 0:
            raise ValueError("predicted_price must be positive")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.reasoning.strip():
            raise ValueError("reasoning is required")

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StrategySignal":
        return cls(
            predicted_price=float(data["predicted_price"]),
            confidence=float(data["confidence"]),
            reasoning=str(data["reasoning"]),
        )

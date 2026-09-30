from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.models.prediction import DIRECTIONS


@dataclass(frozen=True)
class AgentInput:
    ticker: str
    current_price: float
    target_date: date
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.ticker.strip():
            raise ValueError("ticker is required")
        if self.current_price <= 0:
            raise ValueError("current_price must be positive")


@dataclass(frozen=True)
class AgentOutput:
    agent_name: str
    predicted_price: float
    predicted_direction: str
    confidence: float
    reasoning: str
    prompt_tokens_used: int = 0

    def __post_init__(self) -> None:
        if not self.agent_name.strip():
            raise ValueError("agent_name is required")
        if self.predicted_price <= 0:
            raise ValueError("predicted_price must be positive")
        if self.predicted_direction not in DIRECTIONS:
            raise ValueError(f"predicted_direction must be one of {DIRECTIONS}")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.reasoning.strip():
            raise ValueError("reasoning is required")

    @classmethod
    def from_mapping(cls, data: dict[str, Any], default_agent_name: str) -> "AgentOutput":
        return cls(
            agent_name=str(data.get("agent_name") or default_agent_name),
            predicted_price=float(data["predicted_price"]),
            predicted_direction=str(data["predicted_direction"]).lower(),
            confidence=float(data["confidence"]),
            reasoning=str(data["reasoning"]),
            prompt_tokens_used=int(data.get("prompt_tokens_used") or 0),
        )


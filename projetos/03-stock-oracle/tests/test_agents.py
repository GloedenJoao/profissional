from datetime import date

import pytest

from app.agents.sandbox import StrategyExecutor, StrategySandboxError
from app.agents.strategy_types import PriceBar, StrategyContext, StrategySignal


def _context() -> StrategyContext:
    return StrategyContext(
        ticker="AAPL",
        as_of_date=date(2026, 1, 10),
        target_date=date(2026, 1, 13),
        horizon_days=1,
        parameters={"scale": 1.01},
        history=[
            PriceBar(date(2026, 1, 8), None, None, None, 100.0),
            PriceBar(date(2026, 1, 9), None, None, None, 102.0),
            PriceBar(date(2026, 1, 10), None, None, None, 103.0),
        ],
    )


def test_strategy_executor_returns_valid_signal():
    code = """def predict(context):
    current = context["history"][-1]["close"]
    predicted = current * float(context["parameters"]["scale"])
    return {
        "predicted_price": round(predicted, 4),
        "confidence": 0.7,
        "reasoning": "Teste local.",
    }
"""

    signal = StrategyExecutor().execute(code, _context())

    assert signal.predicted_price == pytest.approx(104.03)
    assert signal.confidence == 0.7


@pytest.mark.parametrize(
    "code",
    [
        "import os\ndef predict(context):\n    return {}",
        "def predict(context):\n    open('x')\n    return {}",
        "def predict(context):\n    eval('1 + 1')\n    return {}",
        "def predict(context):\n    value = context.__class__\n    return {}",
        "def predict(context):\n    return {'reasoning': '__class__'}",
        "def predict(context):\n    while True:\n        return {}\n",
    ],
)
def test_strategy_executor_rejects_unsafe_code(code):
    with pytest.raises(StrategySandboxError):
        StrategyExecutor().execute(code, _context())


def test_strategy_signal_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        StrategySignal(predicted_price=10.0, confidence=1.5, reasoning="invalid")

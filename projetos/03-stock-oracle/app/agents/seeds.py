from dataclasses import dataclass


@dataclass(frozen=True)
class StrategySeed:
    slug: str
    name: str
    description: str
    hypothesis: str
    code: str
    parameters: dict[str, float | int | str]


SEED_STRATEGIES: tuple[StrategySeed, ...] = (
    StrategySeed(
        slug="naive-drift",
        name="Naive Drift",
        description="Projeta o proximo movimento usando a variacao recente amortecida.",
        hypothesis="Movimentos recentes contem um sinal fraco que pode ser extrapolado com amortecimento.",
        parameters={"lookback": 5, "damping": 0.5},
        code="""def predict(context):
    history = context["history"]
    params = context["parameters"]
    lookback = int(params["lookback"])
    damping = float(params["damping"])
    current = history[-1]["close"]
    start = history[0]["close"]
    if len(history) > lookback:
        start = history[-lookback - 1]["close"]
    change = (current - start) / start
    predicted = current * (1 + change * damping)
    confidence = min(0.85, max(0.35, abs(change) * 8))
    return {
        "predicted_price": round(predicted, 4),
        "confidence": round(confidence, 4),
        "reasoning": "Drift recente extrapolado com amortecimento.",
    }
""",
    ),
    StrategySeed(
        slug="moving-average-reversion",
        name="Moving Average Reversion",
        description="Compara o preco atual com uma media movel curta e espera reversao parcial.",
        hypothesis="Desvios de curto prazo em relacao a media tendem a reverter parcialmente.",
        parameters={"window": 20, "reversion": 0.35},
        code="""def predict(context):
    history = context["history"]
    params = context["parameters"]
    window = int(params["window"])
    reversion = float(params["reversion"])
    if len(history) < window:
        window = len(history)
    total = 0
    for idx in range(window):
        total = total + history[-idx - 1]["close"]
    average = total / window
    current = history[-1]["close"]
    predicted = current + ((average - current) * reversion)
    deviation = abs(current - average) / average
    confidence = min(0.8, max(0.3, deviation * 6))
    return {
        "predicted_price": round(predicted, 4),
        "confidence": round(confidence, 4),
        "reasoning": "Reversao parcial para media movel curta.",
    }
""",
    ),
    StrategySeed(
        slug="rsi-mean-reversion",
        name="RSI Mean Reversion",
        description="Usa ganhos e perdas recentes como proxy de RSI para projetar reversao.",
        hypothesis="Condicoes de sobrecompra/sobrevenda de curto prazo tendem a reverter.",
        parameters={"window": 14, "effect": 0.025},
        code="""def predict(context):
    history = context["history"]
    params = context["parameters"]
    window = int(params["window"])
    effect = float(params["effect"])
    if len(history) <= window:
        window = len(history) - 1
    gains = 0
    losses = 0
    for idx in range(window):
        current_close = history[-idx - 1]["close"]
        previous_close = history[-idx - 2]["close"]
        change = current_close - previous_close
        if change >= 0:
            gains = gains + change
        else:
            losses = losses + abs(change)
    current = history[-1]["close"]
    total = gains + losses
    if total == 0:
        predicted = current
        confidence = 0.3
    else:
        rsi_proxy = gains / total
        bias = 0.5 - rsi_proxy
        predicted = current * (1 + bias * effect)
        confidence = min(0.78, max(0.3, abs(bias) * 1.4))
    return {
        "predicted_price": round(predicted, 4),
        "confidence": round(confidence, 4),
        "reasoning": "Proxy de RSI aplicado como reversao a media.",
    }
""",
    ),
)

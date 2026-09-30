import asyncio
import json
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.agents.claude_client import ClaudeClient
from app.agents.orchestrator import OrchestratorAgent
from app.agents.registry import available_agents, create_agent
from app.agents.types import AgentInput, AgentOutput
from app.data.fetchers.price import get_current_price, get_price_history, normalize_ticker
from app.data.processors.technical import summarize_history
from app.models.prediction import AgentPrediction, Prediction
from app.models.stock import Stock


class PredictionPipelineError(RuntimeError):
    pass


def next_weekday(start: date | None = None) -> date:
    candidate = (start or datetime.now(UTC).date()) + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


async def run_prediction(
    db: Session,
    ticker: str,
    agent_names: list[str] | None = None,
    client: ClaudeClient | None = None,
) -> Prediction:
    ticker = normalize_ticker(ticker)
    selected_agents = agent_names or available_agents()
    _ensure_stock(db, ticker)

    target_date = next_weekday()
    try:
        current_price = get_current_price(ticker)
        history = get_price_history(ticker)
        technical_summary = summarize_history(history)
        agent_input = AgentInput(
            ticker=ticker,
            current_price=current_price,
            target_date=target_date,
            payload={"technical_summary": technical_summary},
        )
        agent_outputs = await _run_agents(selected_agents, agent_input, client)
        orchestrator_output = OrchestratorAgent().synthesize(agent_outputs, current_price)
        prediction = _persist_success(
            db=db,
            ticker=ticker,
            target_date=target_date,
            current_price=current_price,
            selected_agents=selected_agents,
            agent_outputs=agent_outputs,
            orchestrator_output=orchestrator_output,
        )
    except Exception as exc:
        prediction = _persist_failure(db, ticker, target_date, selected_agents, exc)
        raise PredictionPipelineError(f"Prediction {prediction.id} failed: {exc}") from exc

    return prediction


async def _run_agents(
    selected_agents: list[str],
    agent_input: AgentInput,
    client: ClaudeClient | None,
) -> list[AgentOutput]:
    tasks = [create_agent(name, client=client).predict(agent_input) for name in selected_agents]
    return list(await asyncio.gather(*tasks))


def _ensure_stock(db: Session, ticker: str) -> None:
    if db.get(Stock, ticker) is None:
        db.add(Stock(ticker=ticker))
        db.flush()


def _persist_success(
    db: Session,
    ticker: str,
    target_date: date,
    current_price: float,
    selected_agents: list[str],
    agent_outputs: list[AgentOutput],
    orchestrator_output: AgentOutput,
) -> Prediction:
    prediction = Prediction(
        ticker=ticker,
        target_date=target_date,
        status="open",
        agents_used=json.dumps(selected_agents),
        base_price=current_price,
        orchestrator_predicted_price=orchestrator_output.predicted_price,
        orchestrator_predicted_direction=orchestrator_output.predicted_direction,
        orchestrator_confidence=orchestrator_output.confidence,
        orchestrator_reasoning=orchestrator_output.reasoning,
    )
    db.add(prediction)
    db.flush()
    for output in agent_outputs:
        db.add(
            AgentPrediction(
                prediction_id=prediction.id,
                agent_name=output.agent_name,
                predicted_price=output.predicted_price,
                predicted_direction=output.predicted_direction,
                confidence=output.confidence,
                reasoning=output.reasoning,
                prompt_tokens_used=output.prompt_tokens_used,
            )
        )
    db.commit()
    db.refresh(prediction)
    return prediction


def _persist_failure(
    db: Session,
    ticker: str,
    target_date: date,
    selected_agents: list[str],
    exc: Exception,
) -> Prediction:
    prediction = Prediction(
        ticker=ticker,
        target_date=target_date,
        status="failed",
        agents_used=json.dumps(selected_agents),
        error_message=str(exc),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


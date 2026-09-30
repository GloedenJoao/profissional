from app.agents.base import BaseAgent
from app.agents.claude_client import ClaudeClient
from app.agents.historical import HistoricalAgent


AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    HistoricalAgent.name: HistoricalAgent,
}


def available_agents() -> list[str]:
    return sorted(AGENT_REGISTRY)


def create_agent(name: str, client: ClaudeClient | None = None) -> BaseAgent:
    try:
        agent_cls = AGENT_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown agent: {name}") from exc
    return agent_cls(client=client)


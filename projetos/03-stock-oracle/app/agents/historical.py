from typing import Any

from app.agents.base import BaseAgent
from app.agents.types import AgentInput


class HistoricalAgent(BaseAgent):
    name = "historical"

    async def _fetch_data(self, agent_input: AgentInput) -> dict[str, Any]:
        return {
            "technical_summary": agent_input.payload.get("technical_summary", {}),
        }

    def _build_prompt(self, agent_input: AgentInput, data: dict[str, Any]) -> str:
        return (
            "Voce e um agente educacional de analise tecnica. "
            "Analise somente os dados historicos e indicadores fornecidos. "
            "Nao de recomendacao de investimento; produza apenas uma previsao mensuravel.\n\n"
            f"Ticker: {agent_input.ticker}\n"
            f"Preco atual: {agent_input.current_price:.4f}\n"
            f"Data alvo: {agent_input.target_date.isoformat()}\n"
            f"Resumo tecnico: {data['technical_summary']}\n\n"
            "Preveja o preco de fechamento para a data alvo e a direcao versus o preco atual."
        )


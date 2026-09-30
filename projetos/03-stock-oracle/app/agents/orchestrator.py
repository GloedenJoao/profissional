from statistics import mean

from app.agents.types import AgentOutput
from app.services.directions import direction_from_prices


class OrchestratorAgent:
    name = "orchestrator"

    def synthesize(self, agent_outputs: list[AgentOutput], current_price: float) -> AgentOutput:
        if not agent_outputs:
            raise ValueError("at least one agent output is required")

        predicted_price = mean(output.predicted_price for output in agent_outputs)
        confidence = mean(output.confidence for output in agent_outputs)
        direction = direction_from_prices(current_price, predicted_price)
        names = ", ".join(output.agent_name for output in agent_outputs)
        reasoning = (
            f"Consolidacao inicial baseada em media simples dos agentes: {names}. "
            "Este orquestrador e deterministico na v1 para facilitar medicao."
        )
        return AgentOutput(
            agent_name=self.name,
            predicted_price=round(predicted_price, 4),
            predicted_direction=direction,
            confidence=round(confidence, 4),
            reasoning=reasoning,
            prompt_tokens_used=0,
        )


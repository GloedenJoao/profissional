from abc import ABC, abstractmethod
from typing import Any

from app.agents.claude_client import ClaudeClient, ClaudeJSONResult
from app.agents.types import AgentInput, AgentOutput


class BaseAgent(ABC):
    name: str

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self.client = client or ClaudeClient()

    async def predict(self, agent_input: AgentInput) -> AgentOutput:
        data = await self._fetch_data(agent_input)
        prompt = self._build_prompt(agent_input, data)
        result = await self._call_claude(prompt)
        payload = dict(result.data)
        payload["prompt_tokens_used"] = result.prompt_tokens_used
        return AgentOutput.from_mapping(payload, default_agent_name=self.name)

    async def _call_claude(self, prompt: str) -> ClaudeJSONResult:
        return await self.client.create_json(prompt, self.output_schema())

    @abstractmethod
    async def _fetch_data(self, agent_input: AgentInput) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def _build_prompt(self, agent_input: AgentInput, data: dict[str, Any]) -> str:
        raise NotImplementedError

    @staticmethod
    def output_schema() -> dict[str, str]:
        return {
            "predicted_price": "number greater than zero",
            "predicted_direction": "one of: up, down, flat",
            "confidence": "number from 0.0 to 1.0",
            "reasoning": "short explanation in Portuguese",
        }


import json
from dataclasses import dataclass
from typing import Any

from app.config import Settings, get_settings


@dataclass(frozen=True)
class ClaudeJSONResult:
    data: dict[str, Any]
    prompt_tokens_used: int


class ClaudeClient:
    """Thin Anthropic adapter that returns validated JSON dictionaries."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise RuntimeError("Install project dependencies before calling Claude.") from exc

        self._client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)

    async def create_json(self, prompt: str, schema_hint: dict[str, Any]) -> ClaudeJSONResult:
        response = await self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=self.settings.anthropic_max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": self._with_json_contract(prompt, schema_hint),
                }
            ],
        )
        text = self._extract_text(response)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Claude response was not valid JSON: {text[:240]}") from exc
        if not isinstance(data, dict):
            raise ValueError("Claude response JSON must be an object")
        return ClaudeJSONResult(data=data, prompt_tokens_used=self._usage_tokens(response))

    @staticmethod
    def _with_json_contract(prompt: str, schema_hint: dict[str, Any]) -> str:
        return (
            f"{prompt}\n\n"
            "Return only a JSON object. Do not wrap it in markdown.\n"
            f"Expected JSON shape: {json.dumps(schema_hint, sort_keys=True)}"
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        for block in getattr(response, "content", []) or []:
            block_type = getattr(block, "type", None)
            if block_type is None and isinstance(block, dict):
                block_type = block.get("type")
            if block_type == "text":
                text = getattr(block, "text", None)
                if text is None and isinstance(block, dict):
                    text = block.get("text")
                if text:
                    return str(text)
        raise ValueError("Claude response did not include a text block")

    @staticmethod
    def _usage_tokens(response: Any) -> int:
        usage = getattr(response, "usage", None)
        if usage is None:
            return 0
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        return int(input_tokens) + int(output_tokens)


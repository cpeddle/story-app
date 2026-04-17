from __future__ import annotations

import time
from typing import Literal

from llm_eval.providers.base import LLMProvider, ProviderResponse


# Approximate per-token pricing (USD): (input_per_1k, output_per_1k)
_ANTHROPIC_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-20250514": (0.003, 0.015),
    "claude-3-5-sonnet-20241022": (0.003, 0.015),
}


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def query(
        self,
        prompt: str,
        image_path: str | None = None,
        response_format: Literal["json", "text"] = "json",
        temperature: float = 0.0,
    ) -> ProviderResponse:
        try:
            content = self._build_content(prompt, image_path)
            system_prompt = (
                "Output ONLY valid JSON." if response_format == "json" else ""
            )

            kwargs: dict = {
                "model": self._model,
                "max_tokens": 4096,
                "temperature": temperature,
                "messages": [{"role": "user", "content": content}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            t0 = time.perf_counter()
            response = self._client.messages.create(**kwargs)
            latency_ms = (time.perf_counter() - t0) * 1000

            raw_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    raw_text += block.text

            usage = response.usage
            input_tokens = usage.input_tokens if usage else 0
            output_tokens = usage.output_tokens if usage else 0

            return ProviderResponse(
                raw_text=raw_text,
                model=response.model or self._model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_estimate=self._estimate_cost(input_tokens, output_tokens),
            )
        except Exception as exc:
            return ProviderResponse(
                raw_text="",
                model=self._model,
                provider=self.provider_name,
                latency_ms=0.0,
                error=str(exc),
            )

    def _build_content(self, prompt: str, image_path: str | None) -> list[dict] | str:
        if image_path is None:
            return prompt

        media_type = self._get_image_media_type(image_path)
        b64 = self._encode_image_base64(image_path)
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64,
                },
            },
            {"type": "text", "text": prompt},
        ]

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = _ANTHROPIC_PRICING.get(self._model, (0.003, 0.015))
        return (input_tokens / 1000) * rates[0] + (output_tokens / 1000) * rates[1]

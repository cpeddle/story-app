from __future__ import annotations

import time
from typing import Literal

from llm_eval.providers.base import LLMProvider, ProviderResponse


# Approximate per-token pricing (USD): (input_per_1k, output_per_1k)
_MISTRAL_PRICING: dict[str, tuple[float, float]] = {
    "pixtral-large-latest": (0.002, 0.006),
}


class MistralProvider(LLMProvider):
    """Mistral AI provider (Pixtral Large)."""

    provider_name = "mistral"

    def __init__(self, api_key: str, model: str = "pixtral-large-latest") -> None:
        from mistralai.client import Mistral
        self._client = Mistral(api_key=api_key)
        self._model = model

    def query(
        self,
        prompt: str,
        image_path: str | None = None,
        response_format: Literal["json", "text"] = "json",
        temperature: float = 0.0,
    ) -> ProviderResponse:
        try:
            messages = self._build_messages(prompt, image_path)
            kwargs: dict = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format == "json":
                kwargs["response_format"] = {"type": "json_object"}

            t0 = time.perf_counter()
            response = self._client.chat.complete(**kwargs)
            latency_ms = (time.perf_counter() - t0) * 1000

            choice = response.choices[0]
            raw_text = choice.message.content or ""
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

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

    def _build_messages(self, prompt: str, image_path: str | None) -> list[dict]:
        if image_path is None:
            return [{"role": "user", "content": prompt}]

        media_type = self._get_image_media_type(image_path)
        b64 = self._encode_image_base64(image_path)
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{b64}",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = _MISTRAL_PRICING.get(self._model, (0.002, 0.006))
        return (input_tokens / 1000) * rates[0] + (output_tokens / 1000) * rates[1]

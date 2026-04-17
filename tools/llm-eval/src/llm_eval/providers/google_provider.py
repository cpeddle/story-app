from __future__ import annotations

import time
from typing import Literal

from llm_eval.providers.base import LLMProvider, ProviderResponse


# Approximate per-token pricing (USD): (input_per_1k, output_per_1k)
_GOOGLE_PRICING: dict[str, tuple[float, float]] = {
    "gemini-2.5-pro": (0.00125, 0.005),
    "gemini-2.5-flash": (0.000075, 0.0003),
    "gemini-2.0-flash": (0.0001, 0.0004),
    "gemini-flash-latest": (0.0001, 0.0004),
}


class GoogleProvider(LLMProvider):
    """Google Gemini provider via google-genai SDK."""

    provider_name = "google"

    def __init__(self, api_key: str, model: str = "gemini-2.5-pro") -> None:
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def query(
        self,
        prompt: str,
        image_path: str | None = None,
        response_format: Literal["json", "text"] = "json",
        temperature: float = 0.0,
    ) -> ProviderResponse:
        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type=(
                    "application/json" if response_format == "json" else None
                ),
            )

            contents: list = []
            if image_path is not None:
                from PIL import Image
                img = Image.open(image_path)
                contents.append(img)
            contents.append(prompt)

            t0 = time.perf_counter()
            response = self._client.models.generate_content(
                model=self._model, contents=contents, config=config,
            )
            latency_ms = (time.perf_counter() - t0) * 1000

            raw_text = response.text or ""
            meta = getattr(response, "usage_metadata", None)
            input_tokens = getattr(meta, "prompt_token_count", 0) or 0
            output_tokens = getattr(meta, "candidates_token_count", 0) or 0

            return ProviderResponse(
                raw_text=raw_text,
                model=self._model,
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

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = _GOOGLE_PRICING.get(self._model, (0.00125, 0.005))
        return (input_tokens / 1000) * rates[0] + (output_tokens / 1000) * rates[1]

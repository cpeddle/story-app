from __future__ import annotations

import time
from typing import Literal

from llm_eval.providers.base import LLMProvider, ProviderResponse


class LMStudioProvider(LLMProvider):
    """LM Studio local model provider via OpenAI-compatible API."""

    provider_name = "lmstudio"

    def __init__(
        self,
        model: str = "local-model",
        base_url: str = "http://localhost:1234/v1",
    ) -> None:
        import openai
        self._client = openai.OpenAI(api_key="lm-studio", base_url=base_url)
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
            # JSON mode may not be supported by all local models — try, fall back
            use_json = response_format == "json"
            if use_json:
                kwargs["response_format"] = {"type": "json_object"}

            t0 = time.perf_counter()
            try:
                response = self._client.chat.completions.create(**kwargs)
            except Exception:
                if use_json:
                    # Retry without JSON mode
                    kwargs.pop("response_format", None)
                    response = self._client.chat.completions.create(**kwargs)
                else:
                    raise
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
                cost_estimate=0.0,
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

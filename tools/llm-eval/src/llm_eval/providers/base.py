from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ProviderResponse:
    """Response from an LLM provider."""
    raw_text: str
    model: str
    provider: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_estimate: float = 0.0
    error: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM provider adapters."""

    provider_name: str = "unknown"

    @abstractmethod
    def query(
        self,
        prompt: str,
        image_path: str | None = None,
        response_format: Literal["json", "text"] = "json",
        temperature: float = 0.0,
    ) -> ProviderResponse:
        """Send prompt (with optional image) and return structured response."""

    def _encode_image_base64(self, image_path: str) -> str:
        """Encode an image file as base64."""
        import base64
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_image_media_type(self, image_path: str) -> str:
        """Determine media type from file extension."""
        ext = image_path.rsplit(".", 1)[-1].lower()
        media_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        return media_types.get(ext, "image/jpeg")

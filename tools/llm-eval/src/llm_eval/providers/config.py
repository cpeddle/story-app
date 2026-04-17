from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_api_keys(env_path: str | None = None) -> dict[str, str]:
    """Load API keys from .env file and/or environment variables.

    Returns dict mapping provider name to API key.
    Keys with empty/missing values are excluded.
    """
    if env_path:
        load_dotenv(env_path)
    else:
        # Search in common locations
        for candidate in [Path.cwd() / ".env", Path.cwd().parent / ".env"]:
            if candidate.exists():
                load_dotenv(candidate)
                break

    keys: dict[str, str] = {}
    mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "mistral": "MISTRAL_API_KEY",
    }
    for provider, env_var in mapping.items():
        val = os.environ.get(env_var, "").strip()
        if val:
            keys[provider] = val
    return keys


def get_provider(name: str, model: str, api_keys: dict[str, str]) -> "LLMProvider":
    """Factory to create a provider instance by name."""
    if name == "openai":
        from llm_eval.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_keys["openai"], model=model)
    elif name == "anthropic":
        from llm_eval.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_keys["anthropic"], model=model)
    elif name == "google":
        from llm_eval.providers.google_provider import GoogleProvider
        return GoogleProvider(api_key=api_keys["google"], model=model)
    elif name == "mistral":
        from llm_eval.providers.mistral_provider import MistralProvider
        return MistralProvider(api_key=api_keys["mistral"], model=model)
    elif name == "lmstudio":
        from llm_eval.providers.lmstudio_provider import LMStudioProvider
        base_url = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        return LMStudioProvider(model=model, base_url=base_url)
    else:
        raise ValueError(f"Unknown provider: {name}")

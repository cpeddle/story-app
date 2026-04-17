"""Tests for LLM provider adapters."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

from llm_eval.providers.base import LLMProvider, ProviderResponse


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    def _make_fake_response(self):
        usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        message = MagicMock(content='{"result": "ok"}')
        choice = MagicMock(message=message)
        resp = MagicMock(choices=[choice], usage=usage, model="gpt-4o")
        return resp

    @patch("openai.OpenAI")
    def test_text_query(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._make_fake_response()

        from llm_eval.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
        resp = provider.query("Hello", response_format="json")

        assert isinstance(resp, ProviderResponse)
        assert resp.raw_text == '{"result": "ok"}'
        assert resp.model == "gpt-4o"
        assert resp.provider == "openai"
        assert resp.latency_ms > 0
        assert resp.input_tokens == 10
        assert resp.output_tokens == 20
        assert resp.error is None

    @patch("openai.OpenAI")
    def test_error_handling(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")

        from llm_eval.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="test-key")
        resp = provider.query("Hello")

        assert resp.error is not None
        assert "API down" in resp.error
        assert resp.raw_text == ""
        assert resp.provider == "openai"


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    def _make_fake_response(self):
        text_block = MagicMock(text='{"result": "ok"}')
        usage = MagicMock(input_tokens=15, output_tokens=25)
        resp = MagicMock(content=[text_block], usage=usage, model="claude-sonnet-4-20250514")
        return resp

    @patch("anthropic.Anthropic")
    def test_text_query(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._make_fake_response()

        from llm_eval.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(api_key="test-key")
        resp = provider.query("Hello", response_format="json")

        assert resp.raw_text == '{"result": "ok"}'
        assert resp.provider == "anthropic"
        assert resp.latency_ms > 0
        assert resp.input_tokens == 15
        assert resp.output_tokens == 25
        assert resp.error is None

        # Verify system prompt is set for JSON mode
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs.get("system") == "Output ONLY valid JSON."

    @patch("anthropic.Anthropic")
    def test_text_mode_no_system_prompt(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._make_fake_response()

        from llm_eval.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(api_key="test-key")
        provider.query("Hello", response_format="text")

        call_kwargs = mock_client.messages.create.call_args
        assert "system" not in call_kwargs.kwargs

    @patch("anthropic.Anthropic")
    def test_error_handling(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("Rate limited")

        from llm_eval.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(api_key="test-key")
        resp = provider.query("Hello")

        assert resp.error is not None
        assert "Rate limited" in resp.error
        assert resp.raw_text == ""


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

class TestGoogleProvider:
    def _make_fake_response(self):
        meta = MagicMock(prompt_token_count=12, candidates_token_count=18)
        resp = MagicMock(text='{"result": "ok"}', usage_metadata=meta)
        return resp

    @patch("google.genai.Client")
    def test_text_query(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.return_value = self._make_fake_response()

        from llm_eval.providers.google_provider import GoogleProvider
        provider = GoogleProvider(api_key="test-key", model="gemini-2.5-pro")
        resp = provider.query("Hello", response_format="json")

        assert resp.raw_text == '{"result": "ok"}'
        assert resp.provider == "google"
        assert resp.latency_ms > 0
        assert resp.input_tokens == 12
        assert resp.output_tokens == 18
        assert resp.error is None

    @patch("google.genai.Client")
    def test_error_handling(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = RuntimeError("Quota exceeded")

        from llm_eval.providers.google_provider import GoogleProvider
        provider = GoogleProvider(api_key="test-key")
        resp = provider.query("Hello")

        assert resp.error is not None
        assert "Quota exceeded" in resp.error


# ---------------------------------------------------------------------------
# Mistral
# ---------------------------------------------------------------------------

class TestMistralProvider:
    def _make_fake_response(self):
        usage = MagicMock(prompt_tokens=8, completion_tokens=16)
        message = MagicMock(content='{"result": "ok"}')
        choice = MagicMock(message=message)
        resp = MagicMock(choices=[choice], usage=usage, model="pixtral-large-latest")
        return resp

    @patch("mistralai.client.Mistral")
    def test_text_query(self, mock_mistral_cls):
        mock_client = MagicMock()
        mock_mistral_cls.return_value = mock_client
        mock_client.chat.complete.return_value = self._make_fake_response()

        from llm_eval.providers.mistral_provider import MistralProvider
        provider = MistralProvider(api_key="test-key")
        resp = provider.query("Hello", response_format="json")

        assert resp.raw_text == '{"result": "ok"}'
        assert resp.provider == "mistral"
        assert resp.latency_ms > 0
        assert resp.input_tokens == 8
        assert resp.output_tokens == 16
        assert resp.error is None

    @patch("mistralai.client.Mistral")
    def test_error_handling(self, mock_mistral_cls):
        mock_client = MagicMock()
        mock_mistral_cls.return_value = mock_client
        mock_client.chat.complete.side_effect = RuntimeError("Forbidden")

        from llm_eval.providers.mistral_provider import MistralProvider
        provider = MistralProvider(api_key="test-key")
        resp = provider.query("Hello")

        assert resp.error is not None
        assert "Forbidden" in resp.error


# ---------------------------------------------------------------------------
# LM Studio
# ---------------------------------------------------------------------------

class TestLMStudioProvider:
    def _make_fake_response(self):
        usage = MagicMock(prompt_tokens=0, completion_tokens=0)
        message = MagicMock(content='{"result": "local"}')
        choice = MagicMock(message=message)
        resp = MagicMock(choices=[choice], usage=usage, model="local-model")
        return resp

    @patch("openai.OpenAI")
    def test_text_query(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._make_fake_response()

        from llm_eval.providers.lmstudio_provider import LMStudioProvider
        provider = LMStudioProvider(model="local-model")
        resp = provider.query("Hello", response_format="json")

        assert resp.raw_text == '{"result": "local"}'
        assert resp.provider == "lmstudio"
        assert resp.latency_ms > 0
        assert resp.cost_estimate == 0.0
        assert resp.error is None

        # Verify dummy API key and custom base_url
        mock_openai_cls.assert_called_once_with(
            api_key="lm-studio", base_url="http://localhost:1234/v1"
        )

    @patch("openai.OpenAI")
    def test_json_fallback(self, mock_openai_cls):
        """If JSON mode fails, LM Studio should retry without it."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # First call raises (JSON mode unsupported), second succeeds
        mock_client.chat.completions.create.side_effect = [
            RuntimeError("Unsupported response_format"),
            self._make_fake_response(),
        ]

        from llm_eval.providers.lmstudio_provider import LMStudioProvider
        provider = LMStudioProvider()
        resp = provider.query("Hello", response_format="json")

        assert resp.error is None
        assert resp.raw_text == '{"result": "local"}'
        assert mock_client.chat.completions.create.call_count == 2

    @patch("openai.OpenAI")
    def test_error_handling(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("Connection refused")

        from llm_eval.providers.lmstudio_provider import LMStudioProvider
        provider = LMStudioProvider()
        resp = provider.query("Hello", response_format="text")

        assert resp.error is not None
        assert "Connection refused" in resp.error


# ---------------------------------------------------------------------------
# Config / Factory
# ---------------------------------------------------------------------------

class TestConfig:
    def test_load_api_keys(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "")
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

        from llm_eval.providers.config import load_api_keys
        keys = load_api_keys()

        assert keys["openai"] == "sk-test"
        assert keys["anthropic"] == "ant-test"
        assert "google" not in keys
        assert "mistral" not in keys

    @patch("openai.OpenAI")
    def test_get_provider_openai(self, mock_openai_cls):
        from llm_eval.providers.config import get_provider
        p = get_provider("openai", "gpt-4o", {"openai": "sk-test"})
        assert p.provider_name == "openai"

    @patch("anthropic.Anthropic")
    def test_get_provider_anthropic(self, mock_cls):
        from llm_eval.providers.config import get_provider
        p = get_provider("anthropic", "claude-sonnet-4-20250514", {"anthropic": "ant-test"})
        assert p.provider_name == "anthropic"

    @patch("google.genai.Client")
    def test_get_provider_google(self, mock_cls):
        from llm_eval.providers.config import get_provider
        p = get_provider("google", "gemini-2.5-pro", {"google": "goog-test"})
        assert p.provider_name == "google"

    @patch("mistralai.client.Mistral")
    def test_get_provider_mistral(self, mock_cls):
        from llm_eval.providers.config import get_provider
        p = get_provider("mistral", "pixtral-large-latest", {"mistral": "mis-test"})
        assert p.provider_name == "mistral"

    @patch("openai.OpenAI")
    def test_get_provider_lmstudio(self, mock_cls):
        from llm_eval.providers.config import get_provider
        p = get_provider("lmstudio", "local-model", {})
        assert p.provider_name == "lmstudio"

    def test_get_provider_unknown(self):
        from llm_eval.providers.config import get_provider
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent", "model", {})


# ---------------------------------------------------------------------------
# Base class contract
# ---------------------------------------------------------------------------

class TestBaseContract:
    def test_provider_response_defaults(self):
        r = ProviderResponse(
            raw_text="hi", model="m", provider="p", latency_ms=1.0
        )
        assert r.input_tokens == 0
        assert r.output_tokens == 0
        assert r.cost_estimate == 0.0
        assert r.error is None

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_image_media_type(self):
        class Dummy(LLMProvider):
            def query(self, prompt, image_path=None, response_format="json", temperature=0.0):
                return ProviderResponse(raw_text="", model="", provider="", latency_ms=0)

        d = Dummy()
        assert d._get_image_media_type("photo.png") == "image/png"
        assert d._get_image_media_type("photo.jpg") == "image/jpeg"
        assert d._get_image_media_type("photo.webp") == "image/webp"
        assert d._get_image_media_type("photo.bmp") == "image/jpeg"  # fallback

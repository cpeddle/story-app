"""Tests for the experiment runner and results module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from llm_eval.results import TrialResult
from llm_eval.runner import ExperimentRunner, TrialConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trial_result(**overrides) -> TrialResult:
    defaults = dict(
        trial_id="test-scene__test-model__zero-shot__json__run1",
        input_id="test-scene",
        input_type="image",
        model="test-model",
        provider="openai",
        prompt_variation="zero-shot",
        output_format="json",
        run_number=1,
        raw_output='{"layers": []}',
        latency_ms=123.4,
        input_tokens=50,
        output_tokens=100,
        cost_estimate=0.01,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    defaults.update(overrides)
    return TrialResult(**defaults)


def _make_trial_config(**overrides) -> TrialConfig:
    defaults = dict(
        input_id="test-scene",
        input_type="image",
        input_path="/fake/input.jpg",
        model="test-model",
        provider="openai",
        prompt_template="/fake/prompt.txt",
        prompt_variation="zero-shot",
        output_format="json",
        run_number=1,
    )
    defaults.update(overrides)
    return TrialConfig(**defaults)


# ---------------------------------------------------------------------------
# TrialConfig
# ---------------------------------------------------------------------------

class TestTrialConfig:
    def test_trial_id_format(self):
        cfg = _make_trial_config(
            input_id="outdoor-carriage",
            model="gpt-4o",
            prompt_variation="few-shot",
            output_format="svg",
            run_number=2,
        )
        tid = cfg.trial_id
        assert tid == "outdoor-carriage__gpt-4o__few-shot__svg__run2"

    def test_trial_id_sanitises_slashes_and_dots(self):
        cfg = _make_trial_config(model="meta/llama-3.1-70b")
        tid = cfg.trial_id
        assert "/" not in tid
        assert "." not in tid
        assert "meta_llama-3_1-70b" in tid


# ---------------------------------------------------------------------------
# TrialResult — save / load
# ---------------------------------------------------------------------------

class TestTrialResultPersistence:
    def test_save_and_load_round_trip(self, tmp_path):
        original = _make_trial_result()
        saved_path = original.save(tmp_path)

        assert saved_path.exists()
        assert saved_path.name == f"{original.trial_id}.json"

        loaded = TrialResult.load(saved_path)
        assert loaded.trial_id == original.trial_id
        assert loaded.input_id == original.input_id
        assert loaded.model == original.model
        assert loaded.raw_output == original.raw_output
        assert loaded.latency_ms == original.latency_ms
        assert loaded.input_tokens == original.input_tokens
        assert loaded.output_tokens == original.output_tokens
        assert loaded.cost_estimate == original.cost_estimate
        assert loaded.error is None
        assert loaded.scores == {}
        assert loaded.timestamp == original.timestamp

    def test_save_creates_directory(self, tmp_path):
        result = _make_trial_result()
        nested = tmp_path / "deep" / "nested"
        result.save(nested)
        assert (nested / f"{result.trial_id}.json").exists()

    def test_load_all(self, tmp_path):
        for i in range(1, 4):
            _make_trial_result(
                trial_id=f"scene__model__zero-shot__json__run{i}",
                run_number=i,
            ).save(tmp_path)

        results = TrialResult.load_all(tmp_path)
        assert len(results) == 3
        assert [r.run_number for r in results] == [1, 2, 3]

    def test_load_all_ignores_gitkeep(self, tmp_path):
        _make_trial_result().save(tmp_path)
        (tmp_path / ".gitkeep").write_text("")

        results = TrialResult.load_all(tmp_path)
        assert len(results) == 1

    def test_auto_timestamp(self):
        result = _make_trial_result(timestamp="")
        assert result.timestamp != ""
        assert "T" in result.timestamp  # ISO 8601


# ---------------------------------------------------------------------------
# ExperimentRunner — build_matrix
# ---------------------------------------------------------------------------

class TestBuildMatrix:
    def _write_yaml_config(self, tmp_path):
        """Create a minimal experiment config and referenced files."""
        config = {
            "inputs": [
                {"id": "test-scene", "type": "image", "path": "dummy.jpg"},
            ],
            "models": [
                {"name": "test-model", "provider": "openai"},
            ],
            "prompts": [
                {"template": "prompts/image_input.txt", "variation": "zero-shot"},
            ],
            "output_formats": ["json"],
            "runs_per_trial": 2,
        }
        import yaml
        config_path = tmp_path / "experiment.yaml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")

        # Create referenced files
        (tmp_path / "dummy.jpg").write_bytes(b"\xff\xd8dummy")
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "image_input.txt").write_text("Describe {schema}", encoding="utf-8")

        return config_path

    @patch("llm_eval.runner.load_api_keys", return_value={"openai": "fake-key"})
    def test_build_matrix_count(self, _mock_keys, tmp_path):
        config_path = self._write_yaml_config(tmp_path)
        runner = ExperimentRunner(output_dir=tmp_path / "out")
        matrix = runner.build_matrix(config_path)

        # 1 input × 1 model × 1 prompt × 1 format × 2 runs = 2
        assert len(matrix) == 2
        assert all(isinstance(c, TrialConfig) for c in matrix)
        assert matrix[0].run_number == 1
        assert matrix[1].run_number == 2

    @patch("llm_eval.runner.load_api_keys", return_value={"openai": "fake-key"})
    def test_build_matrix_filters_text_prompt_for_image_input(self, _mock_keys, tmp_path):
        """Image inputs should skip prompts with 'text_input' in the template path."""
        import yaml
        config = {
            "inputs": [{"id": "img", "type": "image", "path": "dummy.jpg"}],
            "models": [{"name": "m", "provider": "openai"}],
            "prompts": [
                {"template": "prompts/image_input.txt", "variation": "zero-shot"},
                {"template": "prompts/text_input.txt", "variation": "zero-shot"},
            ],
            "output_formats": ["json"],
            "runs_per_trial": 1,
        }
        config_path = tmp_path / "experiment.yaml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")
        (tmp_path / "dummy.jpg").write_bytes(b"\xff\xd8")
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "image_input.txt").write_text("img prompt", encoding="utf-8")
        (prompts_dir / "text_input.txt").write_text("txt prompt", encoding="utf-8")

        runner = ExperimentRunner(output_dir=tmp_path / "out")
        matrix = runner.build_matrix(config_path)

        assert len(matrix) == 1
        assert "image_input" in matrix[0].prompt_template


# ---------------------------------------------------------------------------
# ExperimentRunner — run_matrix
# ---------------------------------------------------------------------------

class TestRunMatrix:
    @patch("llm_eval.runner.load_api_keys", return_value={"openai": "fake-key"})
    def test_resume_skips_existing(self, _mock_keys, tmp_path):
        """If a result file already exists, the trial should be skipped."""
        out_dir = tmp_path / "results"
        out_dir.mkdir()

        cfg = _make_trial_config()
        # Pre-save a result matching this config's trial_id
        _make_trial_result(trial_id=cfg.trial_id).save(out_dir)

        runner = ExperimentRunner(output_dir=out_dir, inter_trial_delay_s=0)
        results = runner.run_matrix([cfg])

        assert results == []

    @patch("llm_eval.runner.load_api_keys", return_value={"openai": "fake-key"})
    def test_dry_run_returns_empty(self, _mock_keys, tmp_path):
        runner = ExperimentRunner(output_dir=tmp_path / "out", inter_trial_delay_s=0)
        configs = [_make_trial_config(run_number=i) for i in range(1, 4)]
        results = runner.run_matrix(configs, dry_run=True)
        assert results == []

    @patch("llm_eval.runner.load_api_keys", return_value={})
    def test_skips_missing_api_key(self, _mock_keys, tmp_path):
        """Trial is skipped when provider API key is unavailable."""
        runner = ExperimentRunner(output_dir=tmp_path / "out", inter_trial_delay_s=0)
        cfg = _make_trial_config(provider="openai")
        results = runner.run_matrix([cfg])
        assert results == []

    @patch("llm_eval.runner.load_api_keys", return_value={"openai": "fake-key"})
    @patch("llm_eval.runner.get_provider")
    def test_successful_trial(self, mock_get_provider, _mock_keys, tmp_path):
        """A successful trial saves output and returns a result."""
        from llm_eval.providers.base import ProviderResponse

        mock_provider = MagicMock()
        mock_provider.query.return_value = ProviderResponse(
            raw_text='{"layers": []}',
            model="test-model",
            provider="openai",
            latency_ms=200.0,
            input_tokens=50,
            output_tokens=80,
        )
        mock_get_provider.return_value = mock_provider

        out_dir = tmp_path / "results"
        # Create dummy prompt template
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "image_input.txt").write_text("Generate {schema}", encoding="utf-8")

        cfg = _make_trial_config(
            prompt_template=str(prompt_dir / "image_input.txt"),
            input_path=str(tmp_path / "dummy.jpg"),
        )
        (tmp_path / "dummy.jpg").write_bytes(b"\xff\xd8")

        runner = ExperimentRunner(output_dir=out_dir, inter_trial_delay_s=0)
        results = runner.run_matrix([cfg])

        assert len(results) == 1
        assert results[0].raw_output == '{"layers": []}'
        assert results[0].error is None
        assert (out_dir / f"{cfg.trial_id}.json").exists()

    @patch("llm_eval.runner.load_api_keys", return_value={"openai": "fake-key"})
    @patch("llm_eval.runner.get_provider")
    def test_trial_with_error(self, mock_get_provider, _mock_keys, tmp_path):
        """Provider errors are captured without crashing the matrix."""
        mock_get_provider.side_effect = RuntimeError("Connection refused")

        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "image_input.txt").write_text("Generate {schema}", encoding="utf-8")

        cfg = _make_trial_config(
            prompt_template=str(prompt_dir / "image_input.txt"),
            input_path=str(tmp_path / "dummy.jpg"),
        )
        (tmp_path / "dummy.jpg").write_bytes(b"\xff\xd8")

        runner = ExperimentRunner(output_dir=tmp_path / "out", inter_trial_delay_s=0)
        results = runner.run_matrix([cfg])

        assert len(results) == 1
        assert results[0].error is not None
        assert "Connection refused" in results[0].error

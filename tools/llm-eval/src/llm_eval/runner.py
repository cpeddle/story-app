from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from llm_eval.providers import get_provider, load_api_keys, ProviderResponse
from llm_eval.results import TrialResult

logger = logging.getLogger(__name__)


@dataclass
class TrialConfig:
    """Configuration for a single trial."""
    input_id: str
    input_type: Literal["image", "text"]
    input_path: str
    model: str
    provider: str
    prompt_template: str
    prompt_variation: str          # "zero-shot", "few-shot", "cot", "two-pass"
    output_format: Literal["json", "svg"]
    run_number: int
    # Optional: path to example JSON for few-shot
    example_path: str | None = None

    @property
    def trial_id(self) -> str:
        """Generate a unique trial identifier."""
        safe_model = self.model.replace("/", "_").replace(".", "_")
        return f"{self.input_id}__{safe_model}__{self.prompt_variation}__{self.output_format}__run{self.run_number}"


class ExperimentRunner:
    """Orchestrates running trials across the evaluation matrix."""

    def __init__(
        self,
        output_dir: str | Path,
        schema_path: str | None = None,
        inter_trial_delay_s: float = 2.0,
        env_path: str | None = None,
    ):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._schema_path = schema_path
        self._delay = inter_trial_delay_s
        self._api_keys = load_api_keys(env_path)
        self._schema_text = ""
        if schema_path:
            self._schema_text = Path(schema_path).read_text(encoding="utf-8")

    def build_matrix(self, config_path: str | Path) -> list[TrialConfig]:
        """Parse a YAML experiment config and produce the full trial matrix."""
        config_path = Path(config_path)
        base_dir = config_path.parent

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        runs = config.get("runs_per_trial", 3)
        output_formats = config.get("output_formats", ["json"])
        configs = []

        for inp in config.get("inputs", []):
            input_path = str(base_dir / inp["path"])
            for model_cfg in config.get("models", []):
                # Check if this model's provider key is available (or lmstudio)
                provider = model_cfg["provider"]
                for prompt_cfg in config.get("prompts", []):
                    template_path = str(base_dir / prompt_cfg["template"])
                    # Filter: image prompts only for image inputs, text prompts only for text inputs
                    if inp["type"] == "text" and "image_input" in prompt_cfg["template"]:
                        continue
                    if inp["type"] == "image" and "text_input" in prompt_cfg["template"]:
                        continue
                    for fmt in output_formats:
                        for run in range(1, runs + 1):
                            example_path = None
                            if prompt_cfg.get("example"):
                                example_path = str(base_dir / prompt_cfg["example"])
                            configs.append(TrialConfig(
                                input_id=inp["id"],
                                input_type=inp["type"],
                                input_path=input_path,
                                model=model_cfg["name"],
                                provider=provider,
                                prompt_template=template_path,
                                prompt_variation=prompt_cfg["variation"],
                                output_format=fmt,
                                run_number=run,
                                example_path=example_path,
                            ))

        return configs

    def _is_completed(self, trial_id: str) -> bool:
        """Check if a trial result file already exists (resume support)."""
        return (self._output_dir / f"{trial_id}.json").exists()

    def _build_prompt(self, config: TrialConfig) -> str:
        """Build the full prompt from template + schema + variations."""
        template = Path(config.prompt_template).read_text(encoding="utf-8")

        # Substitute schema
        prompt = template.replace("{schema}", self._schema_text)

        # Substitute text description for text inputs
        if config.input_type == "text":
            description = Path(config.input_path).read_text(encoding="utf-8").strip()
            prompt = description if "{description}" not in prompt else prompt.replace("{description}", description)

        # Add few-shot example if present
        if config.example_path and config.prompt_variation == "few-shot":
            example_text = Path(config.example_path).read_text(encoding="utf-8")
            # Look for few_shot_suffix.txt alongside the template
            suffix_path = Path(config.prompt_template).parent / "few_shot_suffix.txt"
            if suffix_path.exists():
                suffix = suffix_path.read_text(encoding="utf-8")
                prompt += "\n\n" + suffix.replace("{example}", example_text)
            else:
                prompt += f"\n\nExample:\n{example_text}\n\nNow produce the template for the provided input."

        # Add CoT prefix
        if config.prompt_variation == "cot":
            cot_path = Path(config.prompt_template).parent / "cot_prefix.txt"
            if cot_path.exists():
                cot = cot_path.read_text(encoding="utf-8")
                prompt += "\n\n" + cot

        # SVG output format modifier
        if config.output_format == "svg":
            svg_path = Path(config.prompt_template).parent / "svg_output.txt"
            if svg_path.exists():
                svg_prompt = svg_path.read_text(encoding="utf-8")
                prompt += "\n\n" + svg_prompt

        return prompt

    def run_trial(self, config: TrialConfig) -> TrialResult:
        """Execute a single trial and return the result."""
        image_path = config.input_path if config.input_type == "image" else None
        response_format = "text" if config.output_format == "svg" else "json"

        try:
            provider = get_provider(config.provider, config.model, self._api_keys)

            if config.prompt_variation == "two-pass":
                # Step 1: get spatial layout description (free-text, with image if available)
                step1_path = Path(config.prompt_template).parent / "two_pass_step1.txt"
                step1_prompt = step1_path.read_text(encoding="utf-8") if step1_path.exists() else "Describe the spatial layout of this scene."
                if config.input_type == "text":
                    description = Path(config.input_path).read_text(encoding="utf-8").strip()
                    step1_prompt = step1_prompt.replace("{description}", description)
                r1 = provider.query(prompt=step1_prompt, image_path=image_path, response_format="text", temperature=0.0)

                # Step 2: convert description to JSON using schema
                step2_path = Path(config.prompt_template).parent / "two_pass_step2.txt"
                step2_template = step2_path.read_text(encoding="utf-8") if step2_path.exists() else "Convert this to JSON matching {schema}:\n{step1_output}"
                step2_prompt = step2_template.replace("{schema}", self._schema_text).replace("{step1_output}", r1.raw_text)
                r2 = provider.query(prompt=step2_prompt, image_path=None, response_format=response_format, temperature=0.0)

                # Merge: final output is step 2, but accumulate tokens/cost/latency from both steps
                response = ProviderResponse(
                    raw_text=r2.raw_text,
                    model=r2.model,
                    provider=r2.provider,
                    latency_ms=r1.latency_ms + r2.latency_ms,
                    input_tokens=(r1.input_tokens or 0) + (r2.input_tokens or 0),
                    output_tokens=(r1.output_tokens or 0) + (r2.output_tokens or 0),
                    cost_estimate=(r1.cost_estimate or 0.0) + (r2.cost_estimate or 0.0),
                    error=r1.error or r2.error,
                )
            else:
                prompt = self._build_prompt(config)
                response = provider.query(
                    prompt=prompt,
                    image_path=image_path,
                    response_format=response_format,
                    temperature=0.0,
                )
        except Exception as e:
            response = ProviderResponse(
                raw_text="",
                model=config.model,
                provider=config.provider,
                latency_ms=0.0,
                error=str(e),
            )

        return TrialResult(
            trial_id=config.trial_id,
            input_id=config.input_id,
            input_type=config.input_type,
            model=config.model,
            provider=config.provider,
            prompt_variation=config.prompt_variation,
            output_format=config.output_format,
            run_number=config.run_number,
            raw_output=response.raw_text,
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_estimate=response.cost_estimate,
            error=response.error,
        )

    def run_matrix(self, configs: list[TrialConfig], dry_run: bool = False) -> list[TrialResult]:
        """Run all trials in the matrix sequentially."""
        if dry_run:
            logger.info("DRY RUN — printing trial matrix:")
            for i, c in enumerate(configs, 1):
                logger.info(f"  [{i}/{len(configs)}] {c.trial_id}")
            return []

        results = []
        total = len(configs)
        skipped = 0

        for i, config in enumerate(configs, 1):
            if self._is_completed(config.trial_id):
                logger.info(f"  [{i}/{total}] SKIP (exists): {config.trial_id}")
                skipped += 1
                continue

            # Check if provider key is available
            if config.provider not in self._api_keys and config.provider != "lmstudio":
                logger.warning(f"  [{i}/{total}] SKIP (no API key for {config.provider}): {config.trial_id}")
                skipped += 1
                continue

            logger.info(f"  [{i}/{total}] Running: {config.trial_id}")
            result = self.run_trial(config)
            result.save(self._output_dir)
            results.append(result)

            if result.error:
                logger.warning(f"    ERROR: {result.error}")
            else:
                logger.info(f"    OK — {result.latency_ms:.0f}ms, {result.output_tokens} tokens")

            # Inter-trial delay (skip on last trial)
            if i < total and self._delay > 0:
                time.sleep(self._delay)

        logger.info(f"Done: {len(results)} completed, {skipped} skipped, {total} total")
        return results

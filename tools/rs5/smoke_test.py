#!/usr/bin/env python3
"""Self-contained smoke test for RS-5 evaluation pipeline.

Usage:
    1. Create tools/.env with:  ANTHROPIC_API_KEY=your-key-here
    2. Run: python rs5/smoke_test.py

This makes ONE API call (text-only, ~$0.002) and verifies the full pipeline:
API call → JSON response → schema validation → scoring → result file written.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add rs5 directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm_eval.providers.config import load_api_keys, get_provider
from llm_eval.validator import SchemaValidator
from scorer import RS5Scorer


def main():
    base_dir = Path(__file__).parent
    env_path = base_dir.parent / ".env"

    # Check for API key
    keys = load_api_keys(str(env_path) if env_path.exists() else None)
    if "anthropic" not in keys:
        print("FAIL: No ANTHROPIC_API_KEY found.")
        print(f"Create {env_path} with: ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    print("1. API key found ✓")

    # Load schema and build prompt
    schema_path = str(base_dir / "schema" / "scene-template.schema.json")
    schema_text = Path(schema_path).read_text(encoding="utf-8")
    description = (base_dir / "text-descriptions" / "outdoor-carriage.txt").read_text(encoding="utf-8").strip()
    prompt_template = (base_dir / "prompts" / "text_input.txt").read_text(encoding="utf-8")
    prompt = prompt_template.replace("{schema}", schema_text).replace("{description}", description)

    # Make real API call
    print("2. Calling Anthropic Claude (text-only, zero-shot)...")
    provider = get_provider("anthropic", "claude-sonnet-4-20250514", keys)
    response = provider.query(prompt=prompt, response_format="json", temperature=0.0)

    if response.error:
        print(f"FAIL: API error — {response.error}")
        sys.exit(1)

    print(f"   Response received: {response.latency_ms:.0f}ms, {response.output_tokens} tokens ✓")

    # Validate against schema
    print("3. Validating JSON schema...")
    validator = SchemaValidator(schema_path)
    result = validator.validate(response.raw_text)

    if not result.valid:
        print(f"   Schema validation failed: {result.errors[:3]}")
        print(f"   Raw output (first 500 chars): {response.raw_text[:500]}")
        # Not a hard failure — the pipeline works, model just gave bad output
        print("   (Pipeline works, but model output didn't validate)")
    else:
        print(f"   Schema valid ✓")

    # Score against ground truth
    print("4. Scoring against ground truth...")
    scorer = RS5Scorer(str(base_dir / "ground-truth"), schema_path)
    score = scorer.score_trial(response.raw_text, "outdoor-carriage")
    print(f"   Weighted score: {score.weighted_score:.3f}")
    print(f"   Door detection: {score.door_detection_rate:.3f}")
    print(f"   Door position:  {score.door_position_error:.3f}")
    print(f"   Schema:         {score.schema_compliance:.3f}")

    # Write result file using proper TrialResult format
    from llm_eval.results import TrialResult
    trial_result = TrialResult(
        trial_id="smoke-test",
        input_id="text-outdoor-carriage",
        input_type="text",
        model=response.model,
        provider=response.provider,
        prompt_variation="zero-shot",
        output_format="json",
        run_number=1,
        raw_output=response.raw_text,
        latency_ms=response.latency_ms,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_estimate=response.cost_estimate,
        error=response.error,
        scores={
            "weighted_score": score.weighted_score,
            "door_detection_rate": score.door_detection_rate,
            "door_position_error": score.door_position_error,
            "spawn_plausibility": score.spawn_plausibility,
            "zone_coverage": score.zone_coverage,
            "schema_compliance": score.schema_compliance,
        },
    )
    result_path = trial_result.save(str(base_dir / "results"))
    print(f"5. Result written to {result_path} ✓")

    print("\n✓ SMOKE TEST PASSED — full pipeline verified end-to-end")


if __name__ == "__main__":
    main()

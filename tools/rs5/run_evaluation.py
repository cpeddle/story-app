#!/usr/bin/env python3
"""RS-5 Evaluation Orchestrator — runs the full LLM evaluation pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

# Add rs5 directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from llm_eval.runner import ExperimentRunner
from llm_eval.results import TrialResult
from scorer import RS5Scorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="RS-5 Scene Template Pipeline — LLM Evaluation")
    parser.add_argument(
        "--config", "-c",
        default=str(Path(__file__).parent / "experiment.yaml"),
        help="Path to experiment YAML config (default: experiment.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the trial matrix without executing",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="Skip running trials, only re-score existing results",
    )
    parser.add_argument(
        "--env",
        default=None,
        help="Path to .env file with API keys",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    # Resolve paths relative to config file
    base_dir = config_path.parent
    
    # Read config to get schema and ground-truth paths
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)

    schema_path = str(base_dir / config.get("schema", "schema/scene-template.schema.json"))
    ground_truth_dir = str(base_dir / config.get("ground_truth_dir", "ground-truth/"))
    results_dir = base_dir / "results"

    # Create runner
    runner = ExperimentRunner(
        output_dir=results_dir,
        schema_path=schema_path,
        inter_trial_delay_s=config.get("inter_trial_delay_s", 2.0),
        env_path=args.env or str(base_dir / ".env") if (base_dir / ".env").exists() else args.env,
    )

    # Build matrix
    matrix = runner.build_matrix(config_path)
    logger.info(f"Trial matrix: {len(matrix)} trials")

    if args.dry_run:
        logger.info("DRY RUN — trial matrix:")
        for i, trial in enumerate(matrix, 1):
            logger.info(f"  [{i:3d}] {trial.trial_id}")
        logger.info(f"Total: {len(matrix)} trials")
        return

    # Run trials (or skip if score-only)
    if not args.score_only:
        logger.info("Running trials...")
        runner.run_matrix(matrix)
    
    # Score all results
    logger.info("Scoring results...")
    scorer = RS5Scorer(ground_truth_dir, schema_path)
    results = TrialResult.load_all(results_dir)
    
    if not results:
        logger.warning("No result files found to score.")
        return

    # Group results by (input_id, model, prompt_variation, output_format) for consistency scoring
    from collections import defaultdict
    groups = defaultdict(list)
    for r in results:
        key = (r.input_id, r.model, r.prompt_variation, r.output_format)
        groups[key].append(r)

    for result in results:
        if result.error:
            result.scores = {
                "door_detection_rate": 0.0,
                "door_position_error": 0.0,
                "spawn_plausibility": 0.0,
                "zone_coverage": 0.0,
                "schema_compliance": 0.0,
                "consistency": 0.0,
                "weighted_score": 0.0,
            }
            continue
        
        # Determine ground truth ID: strip "text-" prefix for text inputs
        gt_id = result.input_id
        if gt_id.startswith("text-"):
            gt_id = gt_id[5:]
        
        score = scorer.score_trial(result.raw_output, gt_id)
        
        # Compute consistency within the group
        key = (result.input_id, result.model, result.prompt_variation, result.output_format)
        group_jsons = [r.raw_output for r in groups[key] if not r.error]
        score.consistency = scorer.score_consistency(group_jsons)
        score.weighted_score = scorer._compute_weighted(score)
        
        result.scores = {
            "door_detection_rate": score.door_detection_rate,
            "door_position_error": score.door_position_error,
            "spawn_plausibility": score.spawn_plausibility,
            "zone_coverage": score.zone_coverage,
            "schema_compliance": score.schema_compliance,
            "consistency": score.consistency,
            "weighted_score": score.weighted_score,
        }

    # Save scored results back
    for result in results:
        result.save(results_dir)
    logger.info(f"Scored {len(results)} results")

    # Write summary CSV
    summary_path = results_dir / "summary.csv"
    fieldnames = [
        "trial_id", "input_id", "input_type", "model", "provider",
        "prompt_variation", "output_format", "run_number",
        "latency_ms", "input_tokens", "output_tokens", "cost_estimate",
        "door_detection_rate", "door_position_error", "spawn_plausibility",
        "zone_coverage", "schema_compliance", "consistency", "weighted_score",
        "error",
    ]
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = {
                "trial_id": r.trial_id,
                "input_id": r.input_id,
                "input_type": r.input_type,
                "model": r.model,
                "provider": r.provider,
                "prompt_variation": r.prompt_variation,
                "output_format": r.output_format,
                "run_number": r.run_number,
                "latency_ms": f"{r.latency_ms:.0f}",
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_estimate": f"{r.cost_estimate:.4f}",
                "error": r.error or "",
            }
            row.update({k: f"{v:.3f}" for k, v in r.scores.items()})
            writer.writerow(row)
    
    logger.info(f"Summary CSV written to {summary_path}")
    
    # Print quick summary to stdout
    print(f"\n{'='*80}")
    print(f"RS-5 Evaluation Summary — {len(results)} trials scored")
    print(f"{'='*80}")
    
    # Group by model for leaderboard
    model_scores = defaultdict(list)
    for r in results:
        if r.scores.get("weighted_score", 0) > 0:
            model_scores[r.model].append(r.scores["weighted_score"])
    
    if model_scores:
        print(f"\n{'Model':<35} {'Avg Score':>10} {'Trials':>8}")
        print(f"{'-'*35} {'-'*10} {'-'*8}")
        for model, scores in sorted(model_scores.items(), key=lambda x: -sum(x[1])/len(x[1])):
            avg = sum(scores) / len(scores)
            print(f"{model:<35} {avg:>10.3f} {len(scores):>8}")
    
    print()


if __name__ == "__main__":
    main()

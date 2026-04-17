#!/usr/bin/env python3
"""RS-5 Results Analysis — generates summary tables from evaluation results."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm-eval" / "src"))
from llm_eval.results import TrialResult

COMMERCIAL_PROVIDERS = {"openai", "anthropic", "google", "mistral"}
OPEN_SOURCE_PROVIDERS = {"lmstudio"}
QUALITY_THRESHOLDS = [0.60, 0.70, 0.80, 0.90]


def load_results(results_dir: Path) -> pd.DataFrame:
    """Load all trial JSON files into a DataFrame, flattening scores."""
    trials = TrialResult.load_all(results_dir)
    if not trials:
        return pd.DataFrame()

    rows = []
    for t in trials:
        row = {
            "trial_id": t.trial_id,
            "input_id": t.input_id,
            "input_type": t.input_type,
            "model": t.model,
            "provider": t.provider,
            "prompt_variation": t.prompt_variation,
            "output_format": t.output_format,
            "run_number": t.run_number,
            "latency_ms": t.latency_ms,
            "input_tokens": t.input_tokens,
            "output_tokens": t.output_tokens,
            "cost_estimate": t.cost_estimate,
            "error": t.error,
        }
        scores = t.scores or {}
        row["weighted_score"] = scores.get("weighted_score", None)
        row["schema_compliance"] = scores.get("schema_compliance", None)
        row["door_detection_rate"] = scores.get("door_detection_rate", None)
        row["door_position_error"] = scores.get("door_position_error", None)
        row["spawn_plausibility"] = scores.get("spawn_plausibility", None)
        row["zone_coverage"] = scores.get("zone_coverage", None)
        row["consistency"] = scores.get("consistency", None)
        rows.append(row)

    return pd.DataFrame(rows)


def _scored(df: pd.DataFrame) -> pd.DataFrame:
    """Return only rows that have a weighted_score."""
    return df.dropna(subset=["weighted_score"])


def _fmt(v: float | None, decimals: int = 3) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:.{decimals}f}"


def _fmt_signed(v: float | None, decimals: int = 3) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:+.{decimals}f}"


def _pct(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v * 100:.1f}%"


def _provider_type(provider: str) -> str:
    p = provider.lower()
    if p in COMMERCIAL_PROVIDERS:
        return "Commercial"
    if p in OPEN_SOURCE_PROVIDERS:
        return "Open-Source"
    return "Other"


# ---------------------------------------------------------------------------
# Table generators
# ---------------------------------------------------------------------------

def table_leaderboard(df: pd.DataFrame) -> str:
    """1. Per-Model Leaderboard."""
    scored = _scored(df)
    if scored.empty:
        return "_No scored trials available._"

    g = scored.groupby("model").agg(
        avg_score=("weighted_score", "mean"),
        std_dev=("weighted_score", "std"),
        schema_pct=("schema_compliance", "mean"),
        trials=("weighted_score", "count"),
    ).sort_values("avg_score", ascending=False)

    lines = ["| Model | Avg Score | Std Dev | Schema % | Trials |",
             "|-------|-----------|---------|----------|--------|"]
    for model, r in g.iterrows():
        lines.append(
            f"| {model} | {_fmt(r.avg_score)} | {_fmt(r.std_dev)} "
            f"| {_pct(r.schema_pct)} | {int(r.trials)} |"
        )
    return "\n".join(lines)


def table_image_vs_text(df: pd.DataFrame) -> str:
    """2. Image vs Text Comparison."""
    scored = _scored(df)
    if scored.empty:
        return "_No scored trials available._"

    # Derive scene from input_id by stripping "text-" prefix
    scored = scored.copy()
    scored["scene"] = scored["input_id"].str.replace(r"^text-", "", regex=True)

    pivot = scored.groupby(["scene", "input_type"])["weighted_score"].mean().unstack(fill_value=None)
    if "image" not in pivot.columns or "text" not in pivot.columns:
        return "_Need both image and text inputs to compare._"

    both = pivot.dropna(subset=["image", "text"])
    if both.empty:
        return "_No scenes with both image and text inputs._"

    both = both.copy()
    both["delta"] = both["image"] - both["text"]

    lines = ["| Scene | Image Score | Text Score | Delta |",
             "|-------|-------------|------------|-------|"]
    for scene, r in both.iterrows():
        lines.append(
            f"| {scene} | {_fmt(r['image'])} | {_fmt(r['text'])} "
            f"| {_fmt_signed(r['delta'], 4):>9s} |"
        )
    return "\n".join(lines)


def table_prompt_variation(df: pd.DataFrame) -> str:
    """3. Prompt Variation Comparison."""
    scored = _scored(df)
    if scored.empty:
        return "_No scored trials available._"

    g = scored.groupby("prompt_variation")["weighted_score"].mean()
    baseline = g.get("zero-shot", None)

    lines = ["| Variation | Avg Score | Δ vs Zero-Shot |",
             "|-----------|-----------|----------------|"]
    for var in sorted(g.index):
        avg = g[var]
        delta = (avg - baseline) if baseline is not None else None
        delta_str = _fmt(delta, 4) if delta is not None else "—"
        if var == "zero-shot":
            delta_str = "baseline"
        lines.append(f"| {var} | {_fmt(avg)} | {delta_str} |")
    return "\n".join(lines)


def table_format_comparison(df: pd.DataFrame) -> str:
    """4. JSON vs SVG Format Comparison."""
    scored = _scored(df)
    if scored.empty:
        return "_No scored trials available._"

    g = scored.groupby("output_format").agg(
        avg_score=("weighted_score", "mean"),
        schema_pct=("schema_compliance", "mean"),
        position_acc=("door_position_error", "mean"),
    )

    lines = ["| Format | Avg Score | Schema % | Position Accuracy |",
             "|--------|-----------|----------|-------------------|"]
    for fmt, r in g.iterrows():
        # Position accuracy is inverse of error: lower error = higher accuracy
        pos = _fmt(r.position_acc)
        lines.append(
            f"| {fmt.upper()} | {_fmt(r.avg_score)} | {_pct(r.schema_pct)} | {pos} |"
        )
    return "\n".join(lines)


def table_commercial_vs_open(df: pd.DataFrame) -> str:
    """5. Commercial vs Open-Source Summary."""
    scored = _scored(df)
    if scored.empty:
        return "_No scored trials available._"

    scored = scored.copy()
    scored["provider_type"] = scored["provider"].apply(_provider_type)

    g = scored.groupby("provider_type").agg(
        avg_score=("weighted_score", "mean"),
        avg_cost=("cost_estimate", "mean"),
        avg_latency=("latency_ms", "mean"),
    )

    lines = ["| Type | Avg Score | Avg Cost | Avg Latency (ms) |",
             "|------|-----------|----------|-------------------|"]
    for ptype, r in g.iterrows():
        lines.append(
            f"| {ptype} | {_fmt(r.avg_score)} "
            f"| ${r.avg_cost:.4f} | {r.avg_latency:.0f} |"
        )
    return "\n".join(lines)


def table_consistency(df: pd.DataFrame) -> str:
    """6. Consistency Analysis."""
    scored = _scored(df)
    if scored.empty:
        return "_No scored trials available._"

    g = scored.groupby("model").agg(
        avg_consistency=("consistency", "mean"),
        min_score=("weighted_score", "min"),
        max_score=("weighted_score", "max"),
        std_dev=("weighted_score", "std"),
    ).sort_values("avg_consistency", ascending=False)

    lines = ["| Model | Avg Consistency | Min Score | Max Score | Std Dev |",
             "|-------|-----------------|-----------|-----------|---------|"]
    for model, r in g.iterrows():
        lines.append(
            f"| {model} | {_fmt(r.avg_consistency)} "
            f"| {_fmt(r.min_score)} | {_fmt(r.max_score)} | {_fmt(r.std_dev)} |"
        )
    return "\n".join(lines)


def table_cost_quality_frontier(df: pd.DataFrame) -> str:
    """7. Cost-Quality Frontier."""
    scored = _scored(df)
    if scored.empty:
        return "_No scored trials available._"

    g = scored.groupby("model").agg(
        avg_score=("weighted_score", "mean"),
        avg_cost=("cost_estimate", "mean"),
    )

    lines = ["| Threshold | Model | Avg Score | Avg Cost/Trial |",
             "|-----------|-------|-----------|----------------|"]
    for threshold in QUALITY_THRESHOLDS:
        eligible = g[g["avg_score"] >= threshold]
        if eligible.empty:
            lines.append(f"| {threshold:.0%} | — | — | — |")
        else:
            cheapest = eligible.sort_values("avg_cost").iloc[0]
            model = cheapest.name
            lines.append(
                f"| {threshold:.0%} | {model} "
                f"| {_fmt(cheapest.avg_score)} | ${cheapest.avg_cost:.4f} |"
            )
    return "\n".join(lines)


def table_prompt_portability(df: pd.DataFrame) -> str:
    """8. Prompt Portability — Few-Shot improvement per model."""
    scored = _scored(df)
    if scored.empty:
        return "_No scored trials available._"

    # Keep only models that have both zero-shot and few-shot results
    pivot = scored.groupby(["model", "prompt_variation"])["weighted_score"].mean().unstack()
    if "zero-shot" not in pivot.columns or "few-shot" not in pivot.columns:
        return "_Need both zero-shot and few-shot results for portability analysis._"

    both = pivot.dropna(subset=["zero-shot", "few-shot"]).copy()
    if both.empty:
        return "_No models with both zero-shot and few-shot results._"

    both["improvement"] = both["few-shot"] - both["zero-shot"]

    lines = ["| Model | Zero-Shot Avg | Few-Shot Avg | Improvement |",
             "|-------|---------------|--------------|-------------|"]
    for model, r in both.iterrows():
        lines.append(
            f"| {model} | {_fmt(r['zero-shot'])} "
            f"| {_fmt(r['few-shot'])} | {_fmt(r['improvement'], 4)} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def write_csv_summary(df: pd.DataFrame, output_path: Path) -> None:
    """Write a flat CSV with per-model aggregated statistics."""
    scored = _scored(df)
    if scored.empty:
        return

    scored = scored.copy()
    scored["provider_type"] = scored["provider"].apply(_provider_type)

    g = scored.groupby("model").agg(
        provider=("provider", "first"),
        provider_type=("provider_type", "first"),
        avg_weighted_score=("weighted_score", "mean"),
        std_weighted_score=("weighted_score", "std"),
        avg_schema_compliance=("schema_compliance", "mean"),
        avg_consistency=("consistency", "mean"),
        avg_cost=("cost_estimate", "mean"),
        avg_latency_ms=("latency_ms", "mean"),
        total_trials=("weighted_score", "count"),
    ).sort_values("avg_weighted_score", ascending=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    g.to_csv(output_path, float_format="%.4f")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="RS-5 evaluation results analysis")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "results",
        help="Directory containing scored TrialResult JSON files",
    )
    args = parser.parse_args()

    results_dir: Path = args.results_dir
    if not results_dir.exists():
        print("No results found.")
        return

    df = load_results(results_dir)
    if df.empty:
        print("No results found.")
        return

    sections = [
        ("1. Per-Model Leaderboard", table_leaderboard),
        ("2. Image vs Text Comparison", table_image_vs_text),
        ("3. Prompt Variation Comparison", table_prompt_variation),
        ("4. JSON vs SVG Format Comparison", table_format_comparison),
        ("5. Commercial vs Open-Source Summary", table_commercial_vs_open),
        ("6. Consistency Analysis", table_consistency),
        ("7. Cost-Quality Frontier", table_cost_quality_frontier),
        ("8. Prompt Portability Analysis", table_prompt_portability),
    ]

    for title, fn in sections:
        print(f"\n## {title}\n")
        print(fn(df))

    csv_path = results_dir / "analysis-summary.csv"
    write_csv_summary(df, csv_path)
    print(f"\n---\nCSV summary written to `{csv_path}`")


if __name__ == "__main__":
    main()

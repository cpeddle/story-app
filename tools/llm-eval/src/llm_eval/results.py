from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class TrialResult:
    """Result of a single evaluation trial."""
    trial_id: str               # Unique identifier: "{input_id}__{model}__{prompt_variation}__{run}"
    input_id: str               # e.g., "outdoor-carriage" or "text-outdoor-carriage"
    input_type: str             # "image" or "text"
    model: str                  # Model identifier
    provider: str               # Provider name
    prompt_variation: str       # "zero-shot", "few-shot", "cot", "two-pass"
    output_format: str          # "json" or "svg"
    run_number: int             # 1, 2, or 3
    raw_output: str = ""        # Raw LLM response text
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_estimate: float = 0.0
    error: str | None = None
    timestamp: str = ""         # ISO 8601
    scores: dict = field(default_factory=dict)  # Filled by scorer

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def save(self, output_dir: str | Path) -> Path:
        """Save this result as a JSON file. Returns the file path."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{self.trial_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        return filepath

    @classmethod
    def load(cls, filepath: str | Path) -> TrialResult:
        """Load a TrialResult from a JSON file."""
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def load_all(cls, results_dir: str | Path) -> list[TrialResult]:
        """Load all TrialResult files from a directory. Skips files that don't match the schema."""
        results_dir = Path(results_dir)
        results = []
        for filepath in sorted(results_dir.glob("*.json")):
            if filepath.name == ".gitkeep":
                continue
            try:
                results.append(cls.load(filepath))
            except (TypeError, KeyError):
                continue
        return results

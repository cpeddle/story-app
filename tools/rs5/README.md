# RS-5: LLM Scene Template Pipeline — Evaluation Tooling

RS-5 evaluates whether LLMs with vision capabilities can generate scene templates for Story App. A scene template defines interactive elements (doors, spawn points, object zones) for a scene background image, enabling the game engine to place characters and objects.

This directory contains the RS-5-specific scoring, prompts, ground truth, and orchestration. It depends on the shared `llm-eval` harness for provider adapters, experiment running, and result persistence.

## Quick Start

```bash
# Activate venv (from tools/ directory)
.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate  # macOS/Linux

# 1. Configure API keys
#    Copy tools/.env.example → tools/.env and fill in at least ANTHROPIC_API_KEY

# 2. Run smoke test (1 API call, ~$0.002)
python rs5/smoke_test.py

# 3. Run full evaluation
python rs5/run_evaluation.py

# 4. Dry-run (preview trial matrix without making API calls)
python rs5/run_evaluation.py --dry-run

# 5. Re-score existing results only (no API calls)
python rs5/run_evaluation.py --score-only

# 6. Analyse results
uv run --with pandas python rs5/analyse_results.py
```

## Directory Structure

```
rs5/
├── experiment.yaml          # Full experiment configuration (7 models × 6 inputs × 4 prompts)
├── experiment-smoke.yaml    # Minimal smoke-test config (1 model × 1 input × 1 prompt × 1 run)
├── run_evaluation.py        # Main orchestrator — builds matrix, runs trials, scores
├── analyse_results.py       # Results analysis & reporting (requires pandas)
├── smoke_test.py            # Quick end-to-end verification (~$0.002)
├── scorer.py                # RS-5-specific scoring (Hungarian matching, IoU, etc.)
├── svg_validator.py         # SVG template validator (structure & attribute checks)
├── prompts/                 # Prompt templates
│   ├── image_input.txt      #   Image-based scene analysis prompt
│   ├── text_input.txt       #   Text description prompt
│   ├── svg_output.txt       #   SVG output format instructions
│   ├── cot_prefix.txt       #   Chain-of-thought reasoning prefix
│   ├── few_shot_suffix.txt  #   Few-shot example injection
│   ├── two_pass_step1.txt   #   Two-pass: analysis step
│   └── two_pass_step2.txt   #   Two-pass: generation step
├── ground-truth/            # Hand-authored ground-truth templates
│   ├── outdoor-carriage.json
│   ├── castle-corridor.json
│   └── castle-throne-room.json
├── text-descriptions/       # Text inputs for text-only trials
│   ├── outdoor-carriage.txt
│   ├── castle-corridor.txt
│   └── childs-bedroom.txt
├── schema/                  # JSON Schema for scene templates
│   └── scene-template.schema.json
├── results/                 # Output directory (gitignored)
└── tests/                   # Unit tests
    ├── test_scorer.py
    └── test_svg_validator.py
```

## Experiment Configuration

Experiments are defined in YAML. The runner builds a trial matrix as the Cartesian product of inputs × models × prompts × output formats × runs.

```yaml
spike: rs5
schema: schema/scene-template.schema.json
ground_truth_dir: ground-truth/

inputs:
  - id: outdoor-carriage
    type: image                              # "image" or "text"
    path: ../assets/archive/scenes/outdoor-carriage/carriage-scene-v1.jpg

models:
  - { name: claude-sonnet-4-20250514, provider: anthropic }
  - { name: gpt-4o, provider: openai }

prompts:
  - { template: prompts/image_input.txt, variation: zero-shot }
  - { template: prompts/image_input.txt, variation: few-shot, example: ground-truth/outdoor-carriage.json }

output_formats: [json, svg]
runs_per_trial: 3              # Repeated runs to measure consistency
inter_trial_delay_s: 2         # Delay between API calls (rate-limit courtesy)
```

The runner automatically filters incompatible combinations (e.g., image prompts are skipped for text inputs and vice versa).

### Key Fields

| Field | Description |
|-------|-------------|
| `inputs` | Scene images or text descriptions to evaluate. `type` controls which prompt templates apply. |
| `models` | Model name + provider key. Provider must be configured in `tools/.env`. |
| `prompts` | Prompt template file + variation label. `example` supplies a few-shot ground-truth file. |
| `output_formats` | `json`, `svg`, or both. |
| `runs_per_trial` | How many times each unique trial is repeated (for consistency scoring). |

## Scoring Framework

`RS5Scorer` evaluates generated scene templates against hand-authored ground truth using six weighted metrics:

| Metric | Weight | Description |
|--------|--------|-------------|
| **Door detection rate** | 25% | Fraction of ground-truth doors matched to predicted doors (Hungarian assignment). |
| **Door position error** | 25% | Mean normalised distance between matched door positions (`1 − error/tolerance`). Tolerance = 10% of canvas. |
| **Spawn plausibility** | 15% | Whether spawn points fall within or near walkable/expected regions. |
| **Zone coverage IoU** | 15% | Intersection-over-Union between predicted and ground-truth object zones. |
| **Schema compliance** | 10% | Whether the generated JSON passes validation against `scene-template.schema.json`. Binary: 1.0 or 0.0. |
| **Consistency** | 10% | Cross-run agreement — how similar are repeated runs for the same trial config. |

### Thresholds

| Weighted Score | Verdict |
|----------------|---------|
| ≥ 80% | **PASS** |
| 60–79% | **MARGINAL** |
| < 60% | **FAIL** |

## Adding a Model

1. Add the model to `experiment.yaml` (or `experiment-smoke.yaml` for testing) under `models:`:
   ```yaml
   models:
     - { name: your-model-name, provider: openai }  # or anthropic, google, mistral, lmstudio
   ```
2. Ensure the provider's API key is configured in `tools/.env`.
3. If the model requires a new provider, see the [llm-eval README](../llm-eval/README.md#adding-a-new-provider).

## Ground Truth

The three ground-truth templates were hand-authored from reference scene images:

- `outdoor-carriage.json` — Outdoor scene with carriage, path, and woodland zones
- `castle-corridor.json` — Interior corridor with multiple doorways
- `castle-throne-room.json` — Throne room with entrance and side passages

### Adding a New Scene

1. View the reference image to identify interactive elements.
2. Identify all doors (with position, size, destination), spawn points, and object zones (with bounding boxes and allowed object types).
3. Author a JSON file matching the schema in `schema/scene-template.schema.json`.
4. Validate the file:
   ```bash
   python -c "
   import jsonschema, json
   schema = json.load(open('rs5/schema/scene-template.schema.json'))
   data = json.load(open('rs5/ground-truth/your-scene.json'))
   jsonschema.validate(data, schema)
   print('Valid')
   "
   ```
5. Add a corresponding input entry in `experiment.yaml`.

## Running Tests

```bash
# From the tools/ directory
cd rs5
uv run --with lxml --with pytest pytest tests/ -v
```

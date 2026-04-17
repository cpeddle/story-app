# LLM Evaluation Harness

Reusable evaluation framework for Story App research spikes. Provides LLM provider adapters, an experiment runner, JSON Schema validation, and result persistence — all designed to be shared across multiple spike evaluations (RS-5, future spikes).

## Prerequisites

- Python ≥ 3.10
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`

## Setup

```bash
cd tools
uv venv .venv
.venv\Scripts\activate    # Windows
# or: source .venv/bin/activate  # macOS/Linux
uv pip install -e llm-eval[dev]
```

## API Key Configuration

Copy `.env.example` to `tools/.env` and fill in keys:

```ini
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
MISTRAL_API_KEY=...
```

Only configure the providers you intend to use. LM Studio runs locally and doesn't require an API key — just set `LMSTUDIO_BASE_URL` if the default (`http://localhost:1234/v1`) differs.

## Architecture

```
llm-eval/
├── pyproject.toml                    # Package metadata & dependencies
├── src/llm_eval/
│   ├── __init__.py
│   ├── providers/                    # LLM provider adapters
│   │   ├── base.py                   #   LLMProvider ABC, ProviderResponse dataclass
│   │   ├── config.py                 #   load_api_keys(), get_provider() factory
│   │   ├── openai_provider.py        #   OpenAI (GPT-4o, GPT-4o-mini, …)
│   │   ├── anthropic_provider.py     #   Anthropic (Claude Sonnet, …)
│   │   ├── google_provider.py        #   Google (Gemini 2.5 Pro, Flash, …)
│   │   ├── mistral_provider.py       #   Mistral (Pixtral Large, …)
│   │   └── lmstudio_provider.py      #   LM Studio (local models)
│   ├── runner.py                     # ExperimentRunner — trial matrix & orchestration
│   ├── validator.py                  # SchemaValidator — JSON Schema validation
│   └── results.py                    # TrialResult dataclass, persistence & loading
└── tests/                            # Unit tests
```

### Key Components

| Module | Responsibility |
|--------|---------------|
| `providers/base.py` | Defines `LLMProvider` ABC and `ProviderResponse` dataclass. All provider adapters implement this interface. |
| `providers/config.py` | `load_api_keys()` reads from `.env` files or environment variables. `get_provider()` is the factory that instantiates provider adapters by name. |
| `runner.py` | `ExperimentRunner` parses a YAML experiment config, builds the full trial matrix (inputs × models × prompts × output formats × runs), and orchestrates execution with inter-trial delay. |
| `validator.py` | `SchemaValidator` validates LLM-generated JSON against a JSON Schema and returns structured error reports. |
| `results.py` | `TrialResult` dataclass captures all trial metadata, raw output, parsed output, scores, latency, and token usage. Handles serialisation to/from JSON. |

## Provider Interface

Each provider adapter implements the `LLMProvider` abstract base class. You can use providers directly:

```python
from llm_eval.providers import get_provider, load_api_keys

keys = load_api_keys("path/to/.env")
provider = get_provider("anthropic", "claude-sonnet-4-20250514", keys)
response = provider.query(prompt="Describe this scene", image_path="scene.jpg")

print(response.raw_text)
print(f"Latency: {response.latency_ms:.0f}ms, tokens: {response.input_tokens}+{response.output_tokens}")
```

`ProviderResponse` includes: `raw_text`, `model`, `provider`, `latency_ms`, `input_tokens`, `output_tokens`, `cost_estimate`, and `error`.

## Running Tests

```bash
cd tools
python -m pytest llm-eval/tests/ -v
```

Or with `uv`:

```bash
cd tools/llm-eval
uv run pytest tests/ -v
```

## Adding a New Provider

1. Create `src/llm_eval/providers/yourprovider.py` implementing the `LLMProvider` ABC.  
   At minimum, implement the `query()` method and set `provider_name`.
2. Register the provider in `providers/config.py` — add a branch to `get_provider()` and map the env var in `load_api_keys()`.
3. Add the env var to `tools/.env.example`.

## Adding a New Spike

To create a new evaluation spike that reuses this harness:

1. Create `tools/your-spike/` with this structure:
   ```
   your-spike/
   ├── experiment.yaml       # YAML experiment configuration
   ├── run_evaluation.py     # Main orchestrator
   ├── scorer.py             # Spike-specific scorer with score_trial() method
   ├── prompts/              # Prompt templates
   ├── ground-truth/         # Hand-authored reference data
   ├── schema/               # JSON Schema for output validation
   └── tests/                # Unit tests
   ```
2. Implement a scorer class with a `score_trial()` method that returns per-trial scores.
3. Create a YAML experiment config following the same structure as `rs5/experiment.yaml` (inputs, models, prompts, output_formats, runs_per_trial).
4. Reuse `ExperimentRunner`, `SchemaValidator`, and `TrialResult` from `llm_eval`:
   ```python
   from llm_eval.runner import ExperimentRunner
   from llm_eval.validator import SchemaValidator
   from llm_eval.results import TrialResult
   ```

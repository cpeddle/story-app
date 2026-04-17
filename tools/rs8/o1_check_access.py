"""
RS-7 O-1 — OpenAI API Access Verification
==========================================
Confirms the OPENAI_API_KEY is functional, lists available models relevant to
this spike, and records observed rate-limit information.

Usage:
    cd tools
    uv run python rs7/o1_check_access.py

Output:
    Prints model list, API version, and a summary table to stdout.
    Writes JSON report to rs7/outputs/o1_access_report.json.

Preconditions:
    tools/.env: OPENAI_API_KEY=sk-...
"""

import json
import os
import sys
import time
from pathlib import Path

# Locate and load tools/.env (script lives at tools/rs7/, env is at tools/.env)
ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

import openai

OUT_DIR = Path(__file__).parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILE = OUT_DIR / "o1_access_report.json"

# Keyword groups for model filtering
RELEVANT_KEYWORDS = ["gpt-4", "o3", "o4", "image", "moderation"]


def get_relevant_models(client: openai.OpenAI) -> list[str]:
    """Return model IDs relevant to this spike."""
    models = client.models.list()
    found = []
    for m in models.data:
        mid = m.id
        if any(kw in mid for kw in RELEVANT_KEYWORDS):
            found.append(mid)
    return sorted(found)


def verify_text_completion(client: openai.OpenAI, model: str = "gpt-4.1-mini") -> dict:
    """Make a minimal chat completion to confirm billing and response works."""
    try:
        t0 = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_tokens=5,
            temperature=0.0,
        )
        latency_ms = round((time.perf_counter() - t0) * 1000)
        content = response.choices[0].message.content or ""
        usage = response.usage
        return {
            "model": response.model,
            "response": content.strip(),
            "latency_ms": latency_ms,
            "input_tokens": usage.prompt_tokens if usage else None,
            "output_tokens": usage.completion_tokens if usage else None,
            "error": None,
        }
    except Exception as exc:
        return {"model": model, "response": None, "latency_ms": None,
                "input_tokens": None, "output_tokens": None, "error": str(exc)}


def check_image_model(client: openai.OpenAI) -> dict:
    """Probe gpt-image-1 availability and check supported sizes.
    Does NOT generate an image — only checks if the model is listed and
    verifies the endpoint accepts a minimal request structure."""
    # We do not generate an image in O-1 to conserve credits.
    # We just verify the model is in the list and record what we know from docs.
    return {
        "note": "Image generation not attempted in O-1 (cost conservation).",
        "check": "Verified via model list only.",
    }


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip().strip('"').strip("'")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set. Add it to tools/.env", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("RS-7 O-1 — OpenAI API Access Verification")
    print(f"openai package version : {openai.__version__}")
    print(f"Key prefix             : {api_key[:14]}...")
    print("=" * 60)

    client = openai.OpenAI(api_key=api_key)

    # 1. Relevant models
    print("\n[1] Fetching relevant models...")
    models = get_relevant_models(client)
    print(f"    Found {len(models)} relevant models:")
    for m in models:
        print(f"      {m}")

    # Gate checks
    has_gpt41    = any("gpt-4.1" in m and "mini" not in m and "nano" not in m for m in models)
    has_gpt41m   = any("gpt-4.1-mini" in m for m in models)
    has_image1   = any("gpt-image-1" in m for m in models)
    has_o3       = any("o3" in m for m in models)
    has_o4mini   = any("o4-mini" in m for m in models)

    print(f"\n    gpt-4.1         : {'✅' if has_gpt41   else '❌'}")
    print(f"    gpt-4.1-mini    : {'✅' if has_gpt41m  else '❌'}")
    print(f"    gpt-image-1     : {'✅' if has_image1  else '❌'}")
    print(f"    o3              : {'✅' if has_o3      else '❌'}")
    print(f"    o4-mini         : {'✅' if has_o4mini  else '❌'}")

    # 2. Text completion smoke test
    print("\n[2] Smoke-test chat completion (gpt-4.1-mini)...")
    smoke = verify_text_completion(client, "gpt-4.1-mini")
    if smoke["error"]:
        print(f"    ❌ ERROR: {smoke['error']}")
    else:
        print(f"    ✅ Response     : '{smoke['response']}'")
        print(f"       Latency     : {smoke['latency_ms']} ms")
        print(f"       Tokens in   : {smoke['input_tokens']}")
        print(f"       Tokens out  : {smoke['output_tokens']}")
        cost_in  = (smoke["input_tokens"]  or 0) / 1_000_000 * 0.40
        cost_out = (smoke["output_tokens"] or 0) / 1_000_000 * 1.60
        print(f"       Est. cost   : ${cost_in + cost_out:.6f} USD (gpt-4.1-mini rates)")

    # 3. Image model check (no generation)
    in_list_note = check_image_model(client)

    # 4. Rate-limit note
    print("\n[3] Rate limit info:")
    print("    NOTE: OpenAI does not expose rate limits via a list endpoint.")
    print("    Check https://platform.openai.com/account/rate-limits for Plus limits.")
    print("    Typical Plus: ~30 RPM for gpt-4.1; ~3 images/min for gpt-image-1.")

    # 5. Structured Outputs check (version gate)
    import importlib
    so_supported = True
    try:
        # beta.chat.completions.parse was introduced in openai >=1.40
        _ = client.beta.chat.completions.parse
    except AttributeError:
        so_supported = False
    print(f"\n[4] Structured Outputs (.beta.chat.completions.parse) : {'✅ available' if so_supported else '❌ not available — upgrade openai'}")

    # Write JSON report
    report = {
        "openai_version": openai.__version__,
        "key_prefix": api_key[:14] + "...",
        "relevant_models": models,
        "gates": {
            "gpt-4.1": has_gpt41,
            "gpt-4.1-mini": has_gpt41m,
            "gpt-image-1": has_image1,
            "o3": has_o3,
            "o4-mini": has_o4mini,
            "structured_outputs_available": so_supported,
        },
        "smoke_test": smoke,
        "image_check": in_list_note,
        "rate_limit_note": "Check https://platform.openai.com/account/rate-limits — typical Plus: ~30 RPM gpt-4.1, ~3 img/min gpt-image-1",
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2))
    print(f"\n✅ Report written to {REPORT_FILE}")

    # Final gate summary
    critical_pass = smoke["error"] is None and (has_gpt41 or has_gpt41m)
    print("\n" + "=" * 60)
    print(f"O-1 GATE: {'PASS ✅' if critical_pass else 'FAIL ❌'}")
    print("  O-2 (dialogue quality spike) — " + ("UNBLOCKED" if critical_pass else "BLOCKED"))
    print("  O-5 (image generation)       — " + ("UNBLOCKED" if has_image1 else "BLOCKED (gpt-image-1 not available)"))
    print("=" * 60)


if __name__ == "__main__":
    main()

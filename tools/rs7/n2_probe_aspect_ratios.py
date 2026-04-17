"""
RS-6 N-2 — Aspect Ratio Probe
Empirically discovers which aspectRatio values the Nano Banana API accepts.
Uses the default model (nano-banana) with a minimal prompt.
Does NOT download images — only checks HTTP response to determine validity.

Usage:
    python tools/rs6/n2_probe_aspect_ratios.py

Outputs:
    Prints a table of valid vs invalid aspect ratio values.
    These findings should be recorded in RS-6 §6 (N-2 findings).

Preconditions:
    tools/.env must contain: NB_API_KEY=nb_...
"""

import requests
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ENV_FILE = REPO_ROOT / "tools" / ".env"
BASE_URL = "https://www.nananobanana.com/api/v1"

# Probe prompt — minimal, low cost, consistent across all probes
PROBE_PROMPT = "A simple blue square on a white background"

# Candidate aspect ratio values to probe
# Includes common ratio strings, resolution hints, and descriptive keywords
CANDIDATE_RATIOS = [
    "default",
    "1:1",
    "4:3",
    "3:4",
    "16:9",
    "9:16",
    "3:2",
    "2:3",
    "21:9",
    "9:21",
    "landscape",
    "portrait",
    "square",
    "2000x1340",
    "1920x1080",
    "1280x720",
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def probe_ratio(api_key: str, ratio: str) -> tuple[bool, str]:
    """
    Returns (is_valid, detail).
    Uses async mode to avoid waiting for generation — we only check if the request
    is accepted (2xx) or rejected (4xx). Async returns immediately with a job ID.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "prompt": PROBE_PROMPT,
        "selectedModel": "nano-banana",
        "mode": "async",
        "aspectRatio": ratio,
    }
    try:
        resp = requests.post(f"{BASE_URL}/generate", headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            job_id = data.get("data", {}).get("id", data.get("id", "?"))
            return True, f"accepted (job: {job_id[:12]}...)"
        elif resp.status_code == 400:
            msg = resp.json().get("message", resp.text[:100])
            return False, f"400 Bad Request — {msg}"
        elif resp.status_code == 402:
            return False, "402 Insufficient credits"
        elif resp.status_code == 403:
            return False, "403 API not enabled"
        else:
            return False, f"{resp.status_code} — {resp.text[:80]}"
    except requests.RequestException as exc:
        return False, f"Request error: {exc}"


def main() -> None:
    env = load_env(ENV_FILE)
    api_key = env.get("NB_API_KEY", "")
    if not api_key:
        print("ERROR: NB_API_KEY not found in tools/.env")
        return

    print("=== RS-6 N-2 — Aspect Ratio Probe ===")
    print(f"Model: nano-banana (gemini-2.5-flash-image)")
    print(f"Mode: async (immediate accept/reject, no generation wait)")
    print(f"Probing {len(CANDIDATE_RATIOS)} candidate values...\n")

    results: list[tuple[str, bool, str]] = []
    for ratio in CANDIDATE_RATIOS:
        valid, detail = probe_ratio(api_key, ratio)
        status = "✅ VALID" if valid else "❌ INVALID"
        print(f"  {ratio:<20} {status:<12} {detail}")
        results.append((ratio, valid, detail))

    print("\n--- Summary ---")
    valid_ratios = [r for r, v, _ in results if v]
    invalid_ratios = [r for r, v, _ in results if not v]
    print(f"Valid   ({len(valid_ratios)}): {', '.join(valid_ratios)}")
    print(f"Invalid ({len(invalid_ratios)}): {', '.join(invalid_ratios)}")

    landscape_support = any(r in valid_ratios for r in ["16:9", "3:2", "21:9", "1920x1080", "2000x1340"])
    print(f"\nLandscape support: {'✅ YES' if landscape_support else '❌ NO — tablet display (2000×1340) may not be achievable'}")

    print("\nRecord these findings in RS-6 §6 (N-2 findings) and exec-plan-rs6.md N-2 acceptance criteria.")


if __name__ == "__main__":
    main()

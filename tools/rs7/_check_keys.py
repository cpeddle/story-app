"""
RS-6 — API Key Verification & Model Catalogue
Confirms NB_API_KEY is functional, prints credit balance, and lists all available models.

Usage:
    python tools/rs6/_check_keys.py

Preconditions:
    tools/.env must contain:
        NB_API_KEY=nb_...
        NB_STYLE_ANCHOR_URL=https://...   (optional — public URL for canonical-style.jpg)
"""

import requests
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ENV_FILE = REPO_ROOT / "tools" / ".env"
BASE_URL = "https://www.nananobanana.com/api/v1"


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main() -> None:
    env = load_env(ENV_FILE)

    api_key = env.get("NB_API_KEY", "")
    style_url = env.get("NB_STYLE_ANCHOR_URL", "")

    print("=== Nano Banana API Key Check ===")
    print(f"NB_API_KEY        : {'SET (' + str(len(api_key)) + ' chars)' if api_key else 'NOT SET'}")
    print(f"NB_STYLE_ANCHOR_URL: {'SET -> ' + style_url[:60] if style_url else 'not set (image-to-image tests will be skipped)'}")

    if not api_key:
        print("\nERROR: NB_API_KEY not found in tools/.env")
        print("  Add: NB_API_KEY=nb_your_key_here")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Check credit balance
    print("\n--- Credit Balance ---")
    resp = requests.get(f"{BASE_URL}/credits", headers=headers, timeout=15)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        print(f"  Credits available: {data.get('credits', 'unknown')}")
    elif resp.status_code == 401:
        print("  ERROR: Invalid API key (401 Unauthorized)")
        return
    elif resp.status_code == 403:
        print("  ERROR: API access not enabled (403 Forbidden)")
        print("  Visit www.nananobanana.com to enable API access (requires ¥1000 cumulative recharge or admin activation)")
        return
    else:
        print(f"  ERROR: {resp.status_code} — {resp.text[:200]}")
        return

    # List models (no auth required per docs, but include auth headers anyway)
    print("\n--- Available Models ---")
    resp = requests.get(f"{BASE_URL}/models", timeout=15)
    if resp.status_code == 200:
        models = resp.json().get("data", [])
        print(f"  {'Model name':<35} {'Display name':<30} {'Credits':>7} {'ImgIn':>6} {'AR':>4} {'Pro':>4}")
        print(f"  {'-'*35} {'-'*30} {'-'*7} {'-'*6} {'-'*4} {'-'*4}")
        for m in models:
            print(
                f"  {m.get('name',''):<35} "
                f"{m.get('displayName',''):<30} "
                f"{m.get('creditsCost', '?'):>7} "
                f"{'✅' if m.get('supportsImageInput') else '❌':>6} "
                f"{'✅' if m.get('supportsAspectRatio') else '❌':>4} "
                f"{'✅' if m.get('requiresPro') else '❌':>4}"
            )
        print(f"\n  Total models: {len(models)}")
    else:
        print(f"  Could not fetch models: {resp.status_code}")

    print("\n=== Check complete ===")


if __name__ == "__main__":
    main()

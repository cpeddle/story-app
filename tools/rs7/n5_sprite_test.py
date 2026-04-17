"""
RS-6 N-5 — Sprite Generation Test
Generates a full-body princess character sprite and compares against the RS-3
Recraft v3 baseline (assets/archive/characters/princess/recraft/recraft-princess-vector-v*.png).

Tests both text-only and style-anchored (referenceImageUrls) modes.

Usage:
    python tools/rs6/n5_sprite_test.py

Outputs (all in assets/rs6/sprites/):
    princess-text-v{n}.png
    princess-anchor-v{n}.png
    prompt-log.md entries appended to assets/rs6/prompt-log.md

Preconditions:
    tools/.env: NB_API_KEY=nb_...
    tools/.env: NB_STYLE_ANCHOR_URL=https://...   (required for anchor variants)
"""

import requests
from datetime import datetime
from pathlib import Path
from _image_utils import download_image


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ENV_FILE = REPO_ROOT / "tools" / ".env"
OUT_DIR = REPO_ROOT / "assets" / "rs6" / "sprites"
PROMPT_LOG = REPO_ROOT / "assets" / "rs6" / "prompt-log.md"
BASE_URL = "https://www.nananobanana.com/api/v1"
MODEL = "nano-banana"

# Square format — sprites must be 1:1 for paper-doll compositing
ASPECT_RATIO = "1:1"
VARIANTS = 2

# Sprite prompt — closely matches the RS-3 N-5 evaluation prompt for Recraft
# so comparisons are fair. See tools/rs3/n5_recraft_eval.py PROMPT_BASE.
PRINCESS_PROMPT = (
    "Full-body chibi kawaii princess character. Large head, small body, expressive eyes. "
    "Flat geometric shapes, bold black outline, flat colour fills only. "
    "Pink ballgown dress, golden crown, brown hair in flowing style. "
    "Large round eyes with white sclera dot, simple smile. "
    "Plain white background. "
    "No gradients, no shadows, no textures. "
    "Complete figure from head to toe, centred, square canvas."
)


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def append_prompt_log(entry: str) -> None:
    PROMPT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMPT_LOG, "a", encoding="utf-8") as f:
        f.write("\n" + entry + "\n")


def generate_sync(api_key: str, prompt: str, aspect_ratio: str, reference_urls: list[str] | None = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload: dict = {
        "prompt": prompt,
        "selectedModel": MODEL,
        "mode": "sync",
        "aspectRatio": aspect_ratio,
    }
    if reference_urls:
        payload["referenceImageUrls"] = reference_urls
    resp = requests.post(f"{BASE_URL}/generate", headers=headers, json=payload, timeout=120)
    if resp.status_code == 402:
        raise RuntimeError("Insufficient credits (402).")
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    env = load_env(ENV_FILE)
    api_key = env.get("NB_API_KEY", "")
    style_url = env.get("NB_STYLE_ANCHOR_URL", "")

    if not api_key:
        print("ERROR: NB_API_KEY not found in tools/.env")
        return

    if not style_url:
        print("WARNING: NB_STYLE_ANCHOR_URL not set — anchor variants will be skipped.")

    print("=== RS-6 N-5 — Sprite Generation Test (princess) ===")
    print(f"Model: {MODEL}  |  Aspect ratio: {ASPECT_RATIO}  |  Variants: {VARIANTS}")
    print()

    # Recraft baseline check
    recraft_dir = REPO_ROOT / "assets" / "archive" / "characters" / "princess" / "recraft"
    recraft_files = sorted(recraft_dir.glob("*.png")) if recraft_dir.exists() else []
    print(f"RS-3 Recraft baseline: {len(recraft_files)} files in {recraft_dir.relative_to(REPO_ROOT)}")
    print("  (Use these for visual comparison after generation)\n")

    # --- Mode A: Text-only ---
    print("Generating text-only variants …")
    for i in range(1, VARIANTS + 1):
        dest = OUT_DIR / f"princess-text-v{i}.png"
        if dest.exists():
            print(f"  v{i}: already exists, skipping")
            continue
        try:
            result = generate_sync(api_key, PRINCESS_PROMPT, ASPECT_RATIO)
            warning = result.get("success") is False and result.get("warning")
            if warning:
                print(f"  v{i}: ⚠️  Content safety warning")
            image_urls = result.get("imageUrls", [])
            if image_urls:
                download_image(image_urls[0], dest)
                print(f"  v{i}: ✅ Saved → {dest.relative_to(REPO_ROOT)}")
                append_prompt_log(
                    f"## princess-text-v{i} — {datetime.now().strftime('%Y-%m-%d')}\n"
                    f"**Tool:** Nano Banana API (`{MODEL}`)\n"
                    f"**Mode:** text-to-image\n"
                    f"**Aspect ratio:** {ASPECT_RATIO}\n"
                    f"**Prompt:** {PRINCESS_PROMPT}\n"
                    f"**Style reference:** none\n"
                    f"**Generation ID:** {result.get('generationId', '?')}\n"
                    f"**Credits used:** {result.get('creditsUsed', '?')}\n"
                    f"**Quality vs Recraft baseline:** [fill in: style match / outline quality / background cleanliness]\n"
                )
            else:
                print(f"  v{i}: ERROR — no imageUrls: {result}")
        except Exception as exc:
            print(f"  v{i}: ERROR — {exc}")

    # --- Mode B: Style-anchored ---
    if not style_url:
        print("\nSkipping anchor variants (NB_STYLE_ANCHOR_URL not set)")
    else:
        print("\nGenerating style-anchored variants …")
        for i in range(1, VARIANTS + 1):
            dest = OUT_DIR / f"princess-anchor-v{i}.png"
            if dest.exists():
                print(f"  v{i}: already exists, skipping")
                continue
            try:
                result = generate_sync(api_key, PRINCESS_PROMPT, ASPECT_RATIO, reference_urls=[style_url])
                warning = result.get("success") is False and result.get("warning")
                if warning:
                    print(f"  v{i}: ⚠️  Content safety warning")
                image_urls = result.get("imageUrls", [])
                if image_urls:
                    download_image(image_urls[0], dest)
                    print(f"  v{i}: ✅ Saved → {dest.relative_to(REPO_ROOT)}")
                    append_prompt_log(
                        f"## princess-anchor-v{i} — {datetime.now().strftime('%Y-%m-%d')}\n"
                        f"**Tool:** Nano Banana API (`{MODEL}`)\n"
                        f"**Mode:** image-to-image (style anchor)\n"
                        f"**Aspect ratio:** {ASPECT_RATIO}\n"
                        f"**Prompt:** {PRINCESS_PROMPT}\n"
                        f"**Style reference:** {style_url}\n"
                        f"**Generation ID:** {result.get('generationId', '?')}\n"
                        f"**Credits used:** {result.get('creditsUsed', '?')}\n"
                        f"**Quality vs text-only:** [fill in: same / better / worse — why]\n"
                        f"**Quality vs Recraft baseline:** [fill in]\n"
                    )
                else:
                    print(f"  v{i}: ERROR — no imageUrls: {result}")
            except Exception as exc:
                print(f"  v{i}: ERROR — {exc}")

    print("\n=== N-5 complete ===")
    print("Compare against Recraft baselines in assets/archive/characters/princess/recraft/")
    print("Quality gate checklist is in exec-plan-rs6.md Appendix A")
    print("Update RS-6 §6 (N-5 findings) with your assessment")


if __name__ == "__main__":
    main()

"""
RS-6 N-6 — Paper-Doll Parts Alignment Test
Generates princess parts (crown, hair, outfit) with explicit anchor-frame prompting
intended to produce parts that sit correctly on the full-body character.

This follows up on RS-3 N-9 which confirmed MISALIGN for DALL-E 3 generated parts.
The key difference here: the prompt strategy includes explicit anchor framing
instructions to try to get parts positioned correctly within the 1:1 canvas.

After generation, this script composites the parts onto the accepted full-body
character using the same numpy layering approach as RS-3 n9_part_anchor.py, and
saves the composite for visual assessment.

Usage:
    python tools/rs6/n6_parts_test.py

Outputs (all in assets/rs6/parts/):
    princess-crown-v{n}.png
    princess-hair-long-v{n}.png
    princess-outfit-ballgown-v{n}.png
    composite-v{n}.png          ← Naive 1:1 overlay (diagnoses alignment)

Preconditions:
    tools/.env: NB_API_KEY=nb_...
    assets/archive/characters/princess/princess-full-v5.jpg (or similar full-body baseline)
"""

import requests
from datetime import datetime
from pathlib import Path
from _image_utils import download_image


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ENV_FILE = REPO_ROOT / "tools" / ".env"
OUT_DIR = REPO_ROOT / "assets" / "rs6" / "parts"
PROMPT_LOG = REPO_ROOT / "assets" / "rs6" / "prompt-log.md"
BASE_URL = "https://www.nananobanana.com/api/v1"
MODEL = "nano-banana"
ASPECT_RATIO = "1:1"
VARIANTS = 2

# The baseline character used for alignment comparison (from RS-3)
FULL_BODY_BASELINE = REPO_ROOT / "assets" / "archive" / "characters" / "princess" / "princess-full-v5.jpg"

# Anchor-frame prompts — the key design choice here is to include explicit framing
# so the generated part sits in the correct region of the canvas relative to a
# full-body character that fills ~80% of the canvas height.
#
# RS-3 N-9 finding: DALL-E 3 generated parts as full-canvas hero images with no
# positional relationship to the character. The anchor-frame prompt strategy attempts
# to specify "what region of the canvas this part should occupy".
PARTS = [
    {
        "id": "crown",
        "prompt": (
            "A golden princess crown, isolated on a white background. "
            "Flat geometric kawaii illustration style, bold black outline, flat colour fills. "
            "The crown occupies the TOP of the canvas — it should be positioned at the top 15% "
            "of a 1:1 square image as if sitting on the head of a chibi princess character. "
            "Plain white background everywhere else. No gradients, no shadows."
        ),
    },
    {
        "id": "hair-long",
        "prompt": (
            "Long brown princess hair cascading down, isolated on a white background. "
            "Flat geometric kawaii illustration style, bold black outline, flat colour fills. "
            "Hair starts from the top 20% of a 1:1 square canvas (head region) and flows to "
            "the middle of the canvas. The hair is centred horizontally. "
            "Plain white background. No gradients, no shadows."
        ),
    },
    {
        "id": "outfit-ballgown",
        "prompt": (
            "A pink ballgown princess dress, isolated on a white background. "
            "Flat geometric kawaii illustration style, bold black outline, flat colour fills. "
            "The ballgown occupies the BOTTOM 60% of a 1:1 square canvas — dress starts at "
            "roughly 40% from top and fills to the bottom, centred horizontally. "
            "Plain white background above and around the dress. No gradients, no shadows."
        ),
    },
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


def append_prompt_log(entry: str) -> None:
    PROMPT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMPT_LOG, "a", encoding="utf-8") as f:
        f.write("\n" + entry + "\n")


def generate_sync(api_key: str, prompt: str, aspect_ratio: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "prompt": prompt,
        "selectedModel": MODEL,
        "mode": "sync",
        "aspectRatio": aspect_ratio,
    }
    resp = requests.post(f"{BASE_URL}/generate", headers=headers, json=payload, timeout=120)
    if resp.status_code == 402:
        raise RuntimeError("Insufficient credits (402).")
    resp.raise_for_status()
    return resp.json()


def composite_parts(part_paths: list[Path], baseline_path: Path, dest: Path) -> None:
    """
    Naive 1:1 pixel overlay — composites parts onto baseline using multiply-by-white
    (same approach as RS-3 n9_part_anchor.py). White pixels in parts become transparent.
    """
    try:
        import numpy as np
        from PIL import Image

        base = Image.open(baseline_path).convert("RGBA").resize((1024, 1024))
        composite = np.array(base, dtype=np.float32) / 255.0

        for part_path in part_paths:
            if not part_path.exists():
                print(f"  [composite] Skipping missing part: {part_path.name}")
                continue
            part = Image.open(part_path).convert("RGBA").resize((1024, 1024))
            part_arr = np.array(part, dtype=np.float32) / 255.0
            # Treat near-white pixels as transparent (threshold 0.90)
            mask = np.all(part_arr[:, :, :3] > 0.90, axis=2)
            composite[~mask] = part_arr[~mask]

        result = Image.fromarray((composite * 255).astype(np.uint8), mode="RGBA")
        dest.parent.mkdir(parents=True, exist_ok=True)
        result.save(dest)
        print(f"  [composite] Saved → {dest.relative_to(REPO_ROOT)}")
    except ImportError:
        print("  [composite] Skipped — Pillow and/or numpy not installed (pip install Pillow numpy)")


def main() -> None:
    env = load_env(ENV_FILE)
    api_key = env.get("NB_API_KEY", "")
    if not api_key:
        print("ERROR: NB_API_KEY not found in tools/.env")
        return

    print("=== RS-6 N-6 — Paper-Doll Parts Alignment Test ===")
    print(f"Model: {MODEL}  |  Aspect ratio: {ASPECT_RATIO}")
    print(f"Baseline: {FULL_BODY_BASELINE.relative_to(REPO_ROOT)} — {'✅ found' if FULL_BODY_BASELINE.exists() else '❌ NOT FOUND'}")
    print()

    for i in range(1, VARIANTS + 1):
        print(f"--- Variant set v{i} ---")
        generated_parts: list[Path] = []

        for part in PARTS:
            part_id = part["id"]
            dest = OUT_DIR / f"princess-{part_id}-v{i}.png"
            if dest.exists():
                print(f"  {part_id}: already exists, skipping")
                generated_parts.append(dest)
                continue
            try:
                result = generate_sync(api_key, part["prompt"], ASPECT_RATIO)
                warning = result.get("success") is False and result.get("warning")
                if warning:
                    print(f"  {part_id}: ⚠️  Content safety warning")
                image_urls = result.get("imageUrls", [])
                if image_urls:
                    download_image(image_urls[0], dest)
                    generated_parts.append(dest)
                    print(f"  {part_id}: ✅ Saved → {dest.relative_to(REPO_ROOT)}")
                    append_prompt_log(
                        f"## princess-{part_id}-v{i} — {datetime.now().strftime('%Y-%m-%d')}\n"
                        f"**Tool:** Nano Banana API (`{MODEL}`)\n"
                        f"**Mode:** text-to-image (anchor-frame strategy)\n"
                        f"**Aspect ratio:** {ASPECT_RATIO}\n"
                        f"**Prompt:** {part['prompt']}\n"
                        f"**Generation ID:** {result.get('generationId', '?')}\n"
                        f"**Credits used:** {result.get('creditsUsed', '?')}\n"
                        f"**Anchor alignment:** [fill in after compositing: PASS / PARTIAL / MISALIGN]\n"
                    )
                else:
                    print(f"  {part_id}: ERROR — no imageUrls: {result}")
            except Exception as exc:
                print(f"  {part_id}: ERROR — {exc}")

        # Composite all generated parts for this variant
        if FULL_BODY_BASELINE.exists() and generated_parts:
            composite_dest = OUT_DIR / f"composite-v{i}.png"
            print(f"  Compositing {len(generated_parts)} parts …")
            composite_parts(generated_parts, FULL_BODY_BASELINE, composite_dest)
        elif not FULL_BODY_BASELINE.exists():
            print("  Compositing skipped — baseline file not found")
        print()

    print("=== N-6 complete ===")
    print("Inspect composite-v*.png to assess anchor alignment:")
    print("  PASS     = parts sit correctly overlaid onto the full-body character")
    print("  PARTIAL  = mostly aligned but some offset")
    print("  MISALIGN = parts do not correspond positionally to the character (same as RS-3 N-9)")
    print("Record verdict in RS-6 §6 (N-6 findings) and update OQ-5")


if __name__ == "__main__":
    main()

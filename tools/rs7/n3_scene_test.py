"""
RS-6 N-3 — Scene Generation Test
Generates castle scene backgrounds using:
  (A) Text-only prompting (no style anchor)
  (B) Image-to-image with canonical-style.jpg as referenceImageUrls anchor

Compares output against RS-3 accepted scenes in assets/RS-3 Gemini Test/.
Run AFTER n2_probe_aspect_ratios.py — update LANDSCAPE_RATIO to the best supported value.

Usage:
    python tools/rs6/n3_scene_test.py

Outputs (all in assets/rs6/scenes/):
    outdoor-carriage-text-v{n}.png
    outdoor-carriage-anchor-v{n}.png
    throne-room-text-v{n}.png
    throne-room-anchor-v{n}.png
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
OUT_DIR = REPO_ROOT / "assets" / "rs6" / "scenes"
PROMPT_LOG = REPO_ROOT / "assets" / "rs6" / "prompt-log.md"
BASE_URL = "https://www.nananobanana.com/api/v1"
MODEL = "nano-banana"   # gemini-2.5-flash-image under the hood

# Update this after running n2_probe_aspect_ratios.py.
# Preferred values in order: "16:9" > "3:2" > "4:3" > "default"
LANDSCAPE_RATIO = "16:9"

VARIANTS_PER_SCENE = 2  # Number of variants per scene per mode

# Scene prompts — derived from RS-3 established style spec.
# These are intentionally similar to the prompts used in the manual Gemini workflow
# (tools/rs3/gemini-scene-prompts.md) to enable the direct A/B comparison in N-4.
SCENES = [
    {
        "id": "outdoor-carriage",
        "prompt": (
            "A fairy-tale outdoor scene with a horse-drawn carriage on a winding path. "
            "Flat geometric illustration style, kawaii / chibi proportions, bold black outlines, "
            "bright warm colours (green grass, peach sky, teal accents). No characters. "
            "Wide landscape composition, clear left exit and right exit on the path. "
            "No gradients, no shading, no photorealistic elements."
        ),
    },
    {
        "id": "throne-room",
        "prompt": (
            "A fairy-tale castle throne room interior. Flat geometric illustration style, "
            "kawaii proportions, bold black outlines, bright warm colours. Stone floor, "
            "ornate throne at the back wall, two arched doorways on the left and right sides. "
            "Colourful banners hanging on walls. No characters. Wide landscape composition. "
            "No gradients, no shading, no photorealistic elements."
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
        raise RuntimeError("Insufficient credits (402). Top up the Nano Banana account.")
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
        print("  Upload assets/style-reference/canonical-style.jpg to a public host and add:")
        print("  NB_STYLE_ANCHOR_URL=https://... to tools/.env")

    print(f"=== RS-6 N-3 — Scene Generation Test ===")
    print(f"Model: {MODEL}  |  Aspect ratio: {LANDSCAPE_RATIO}  |  Variants: {VARIANTS_PER_SCENE} each")
    print(f"Anchor: {'SET -> ' + style_url[:60] if style_url else 'NOT SET (text-only only)'}\n")

    for scene in SCENES:
        scene_id = scene["id"]
        prompt = scene["prompt"]

        # --- Mode A: Text-only ---
        print(f"[{scene_id}] Generating text-only variants …")
        for i in range(1, VARIANTS_PER_SCENE + 1):
            dest = OUT_DIR / f"{scene_id}-text-v{i}.png"
            if dest.exists():
                print(f"  v{i}: already exists, skipping — delete to regenerate")
                continue
            try:
                result = generate_sync(api_key, prompt, LANDSCAPE_RATIO)
                warning = result.get("success") is False and result.get("warning")
                if warning:
                    print(f"  v{i}: ⚠️  Content safety warning — image may not be usable")
                image_urls = result.get("imageUrls", [])
                if image_urls:
                    download_image(image_urls[0], dest)
                    print(f"  v{i}: ✅ Saved → {dest.relative_to(REPO_ROOT)}")
                    append_prompt_log(
                        f"## {scene_id}-text-v{i} — {datetime.now().strftime('%Y-%m-%d')}\n"
                        f"**Tool:** Nano Banana API (`{MODEL}`)\n"
                        f"**Mode:** text-to-image\n"
                        f"**Aspect ratio:** {LANDSCAPE_RATIO}\n"
                        f"**Prompt:** {prompt}\n"
                        f"**Style reference:** none\n"
                        f"**Generation ID:** {result.get('generationId', '?')}\n"
                        f"**Credits used:** {result.get('creditsUsed', '?')}\n"
                        f"**Notes:** [fill in quality assessment]\n"
                    )
                else:
                    print(f"  v{i}: ERROR — no imageUrls in response: {result}")
            except Exception as exc:
                print(f"  v{i}: ERROR — {exc}")

        # --- Mode B: Style-anchored ---
        if not style_url:
            print(f"[{scene_id}] Skipping anchor variants (NB_STYLE_ANCHOR_URL not set)\n")
            continue

        print(f"[{scene_id}] Generating style-anchored variants …")
        for i in range(1, VARIANTS_PER_SCENE + 1):
            dest = OUT_DIR / f"{scene_id}-anchor-v{i}.png"
            if dest.exists():
                print(f"  v{i}: already exists, skipping — delete to regenerate")
                continue
            try:
                result = generate_sync(api_key, prompt, LANDSCAPE_RATIO, reference_urls=[style_url])
                warning = result.get("success") is False and result.get("warning")
                if warning:
                    print(f"  v{i}: ⚠️  Content safety warning")
                image_urls = result.get("imageUrls", [])
                if image_urls:
                    download_image(image_urls[0], dest)
                    print(f"  v{i}: ✅ Saved → {dest.relative_to(REPO_ROOT)}")
                    append_prompt_log(
                        f"## {scene_id}-anchor-v{i} — {datetime.now().strftime('%Y-%m-%d')}\n"
                        f"**Tool:** Nano Banana API (`{MODEL}`)\n"
                        f"**Mode:** image-to-image (style anchor)\n"
                        f"**Aspect ratio:** {LANDSCAPE_RATIO}\n"
                        f"**Prompt:** {prompt}\n"
                        f"**Style reference:** {style_url}\n"
                        f"**Generation ID:** {result.get('generationId', '?')}\n"
                        f"**Credits used:** {result.get('creditsUsed', '?')}\n"
                        f"**Notes:** [fill in quality assessment vs text-only]\n"
                    )
                else:
                    print(f"  v{i}: ERROR — no imageUrls: {result}")
            except Exception as exc:
                print(f"  v{i}: ERROR — {exc}")
        print()

    print("=== N-3 complete ===")
    print(f"Review output in assets/rs6/scenes/ and update RS-6 §6 (N-3 findings)")
    print("Quality gate checklist is in exec-plan-rs6.md Appendix A")


if __name__ == "__main__":
    main()

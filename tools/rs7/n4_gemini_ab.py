"""
RS-6 N-4 — Gemini Manual vs Nano Banana API A/B Comparison
Re-generates scenes using the EXACT prompts from RS-3 gemini-scene-prompts.md to test
whether the Nano Banana API (default model = gemini-2.5-flash-image) matches the quality
of the hand-crafted manual Gemini workflow.

Run AFTER n2_probe_aspect_ratios.py — update LANDSCAPE_RATIO to the best supported value.

Usage:
    python tools/rs6/n4_gemini_ab.py

Outputs (all in assets/rs6/scenes/gemini-ab/):
    outdoor-carriage-api-v{n}.png
    throne-room-api-v{n}.png
    corridor-api-v{n}.png

These are the API-generated counterparts to the accepted RS-3 scenes in:
    assets/RS-3 Gemini Test/outdoor-carriage.png
    assets/RS-3 Gemini Test/castle-throne-room.png
    assets/RS-3 Gemini Test/castle-corridor.png

After generation, visually compare the pairs and record findings in RS-6 §6 (N-4).

Preconditions:
    tools/.env: NB_API_KEY=nb_...
"""

import requests
from datetime import datetime
from pathlib import Path
from _image_utils import download_image


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ENV_FILE = REPO_ROOT / "tools" / ".env"
OUT_DIR = REPO_ROOT / "assets" / "rs6" / "scenes" / "gemini-ab"
RS3_SCENES_DIR = REPO_ROOT / "assets" / "RS-3 Gemini Test" / "pass1"
PROMPT_LOG = REPO_ROOT / "assets" / "rs6" / "prompt-log.md"
BASE_URL = "https://www.nananobanana.com/api/v1"
MODEL = "nano-banana"

# Update after running n2_probe_aspect_ratios.py
LANDSCAPE_RATIO = "16:9"
VARIANTS = 2

# These prompts must match those in tools/rs3/gemini-scene-prompts.md where possible.
# If that file has been updated with exact prompts used to produce the RS-3 accepted scenes,
# copy them here verbatim for the most accurate comparison.
GEMINI_PROMPTS = [
    {
        "id": "outdoor-carriage",
        "rs3_file": "outdoor-carriage.png",
        "prompt": (
            "Flat 2D game background for a children's fairy-tale tablet game. Style: flat vector kawaii. "
            "Low-poly geometric shapes. Bold black outlines on all forms. Flat solid colour fills throughout "
            "— absolutely no gradients, no shadows, no ambient occlusion, no directional lighting, no surface "
            "texture, no masonry or brickwork detail. No depth-of-field blur. No photorealism. Clean simple "
            "geometric shapes only. Warm fairy-tale colour palette: soft golds, peach, warm blues, bright "
            "greens, cream. 16:9 landscape orientation.\n\n"
            "A countryside road scene viewed from the side. A wide cobblestone path made of flat geometric "
            "stone shapes runs along the bottom of the image from the left edge to the right edge. In the "
            "right-centre area of the path, a royal carriage with large circular wooden wheels sits parked "
            "— the carriage body is a geometric boxy shape in gold and red with a flat roof. Rolling green "
            "hills built from triangular low-poly planes fill the background, with a winding path leading "
            "toward a small castle with pointed towers on a hilltop in the upper-right background. Tall "
            "stylised geometric trees flank both sides of the scene.\n\n"
            "ON THE LEFT SIDE: there is a clear wide gap between the left-side trees at ground level, wide "
            "enough for a character to walk through — this is the exit to the castle gate. The gap must be "
            "visible and unobstructed.\n"
            "ON THE RIGHT SIDE: there is a matching clear wide gap between the right-side trees at ground "
            "level — this is the exit to the garden path. The gap must be visible and unobstructed.\n\n"
            "Warm peach-orange sky with simple geometric clouds. Bright greens, teal-blue sky accents, gold carriage.\n\n"
            "This is NOT a photo, NOT 3D rendered, NOT a painted illustration, NOT a mobile RPG background. "
            "NO realistic stone textures. NO atmospheric fog or bloom lighting. NO specular highlights. NO cast "
            "shadows. Flat coloured geometry only."
        ),
    },
    {
        "id": "throne-room",
        "rs3_file": "castle-throne-room.png",
        "prompt": (
            "Flat 2D game background for a children's fairy-tale tablet game. Style: flat vector kawaii. "
            "Low-poly geometric shapes. Bold black outlines on all forms. Flat solid colour fills throughout "
            "— absolutely no gradients, no shadows, no ambient occlusion, no directional lighting, no surface "
            "texture, no masonry or brickwork detail. No depth-of-field blur. No photorealism. Clean simple "
            "geometric shapes only. Warm fairy-tale colour palette: soft golds, peach, warm blues, bright "
            "greens, cream. 16:9 landscape orientation.\n\n"
            "The interior of a castle throne room viewed from the front, showing the full width of the room. "
            "A large ornate throne sits centred on a low raised dais at the back of the room — the throne "
            "has geometric carved shapes and a tall back, in gold and deep red. A long red carpet with a "
            "simple geometric border pattern runs from the centre foreground directly to the throne steps. "
            "Geometric stone columns flank the throne on both sides. Wall-mounted torches with bold flat "
            "flame shapes hang on the walls. Decorative gold and blue banners hang from the upper walls. "
            "The ceiling has simple geometric arched vaulting. The floor is made of large flat-coloured "
            "square stone tiles with a simple two-tone geometric pattern.\n\n"
            "ON THE LEFT WALL, at mid-height: a wide rounded archway is cut into the wall, open and dark "
            "beyond — this is the exit leading to the castle corridor.\n"
            "ON THE RIGHT WALL, at the same mid-height position: a matching wide rounded archway cut into "
            "the right wall, open and dark beyond — this is the exit to the second wing.\n\n"
            "Warm gold and navy blue colour palette. Cream and gold floor. Stone surfaces are flat solid "
            "colour geometric blocks only — NOT textured, NOT shaded, NOT realistic stone.\n\n"
            "This is NOT a photo, NOT 3D rendered, NOT a painted illustration, NOT a mobile RPG background. "
            "NO realistic stone textures. NO atmospheric fog or bloom lighting. NO specular highlights. NO cast "
            "shadows. Flat coloured geometry only."
        ),
    },
    {
        "id": "corridor",
        "rs3_file": "castle-corridor.png",
        "prompt": (
            "Flat 2D game background for a children's fairy-tale tablet game. Style: flat vector kawaii. "
            "Low-poly geometric shapes. Bold black outlines on all forms. Flat solid colour fills throughout "
            "— absolutely no gradients, no shadows, no ambient occlusion, no directional lighting, no surface "
            "texture, no masonry or brickwork detail. No depth-of-field blur. No photorealism. Clean simple "
            "geometric shapes only. Warm fairy-tale colour palette: soft golds, peach, warm blues, bright "
            "greens, cream. 16:9 landscape orientation.\n\n"
            "The interior of a long straight castle corridor viewed from one end, looking toward the opposite "
            "far end. The corridor extends in a long perspective toward a bright opening at the far end. "
            "The ceiling has simple geometric vaulted arches repeated along the corridor length. A red carpet "
            "runner with a simple geometric border pattern runs down the centre of the flat-colour stone floor. "
            "Wall-mounted torches with bold flat flame shapes hang at regular intervals on both walls. Gold "
            "and blue decorative banners hang between the torches.\n\n"
            "ON THE LEFT WALL in the foreground: a large wooden door with bold geometric rectangular panels.\n"
            "ON THE RIGHT WALL in the foreground: a matching wooden door.\n"
            "AT THE FAR END of the corridor: a bright open archway, noticeably brighter than the corridor "
            "interior, showing a warm outdoor sky beyond.\n\n"
            "The stone walls and floor must be flat solid colour blocks only — do NOT add texture. "
            "Warm cream and grey floor. Navy blue walls with gold accent bands.\n\n"
            "This is NOT a photo, NOT 3D rendered, NOT a painted illustration, NOT a mobile RPG background. "
            "NO realistic stone textures. NO atmospheric fog or bloom lighting. NO specular highlights. NO cast "
            "shadows. NO floor edge darkening. NO perspective-fade gradients. Flat coloured geometry only."
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
        raise RuntimeError("Insufficient credits (402). Top up the Nano Banana account.")
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    env = load_env(ENV_FILE)
    api_key = env.get("NB_API_KEY", "")
    if not api_key:
        print("ERROR: NB_API_KEY not found in tools/.env")
        return

    print("=== RS-6 N-4 — Gemini Manual vs Nano Banana API A/B ===")
    print(f"Model: {MODEL}  |  Aspect ratio: {LANDSCAPE_RATIO}")
    print()
    print("NOTE: For accurate A/B, replace the placeholder prompts in this script")
    print("with the EXACT prompts from tools/rs3/gemini-scene-prompts.md\n")

    for scene in GEMINI_PROMPTS:
        scene_id = scene["id"]
        rs3_path = RS3_SCENES_DIR / scene["rs3_file"]
        rs3_present = rs3_path.exists()

        print(f"[{scene_id}] RS-3 baseline: {'✅ found' if rs3_present else '❌ NOT FOUND'} at {rs3_path.name}")
        if not rs3_present:
            print(f"  Skipping — baseline file missing. Cannot perform A/B comparison.")
            continue

        for i in range(1, VARIANTS + 1):
            dest = OUT_DIR / f"{scene_id}-api-v{i}.png"
            if dest.exists():
                print(f"  v{i}: already exists, skipping")
                continue
            try:
                result = generate_sync(api_key, scene["prompt"], LANDSCAPE_RATIO)
                warning = result.get("success") is False and result.get("warning")
                if warning:
                    print(f"  v{i}: ⚠️  Content safety warning")
                image_urls = result.get("imageUrls", [])
                if image_urls:
                    download_image(image_urls[0], dest)
                    print(f"  v{i}: ✅ Saved → {dest.relative_to(REPO_ROOT)}")
                    append_prompt_log(
                        f"## {scene_id}-api-v{i} — {datetime.now().strftime('%Y-%m-%d')}\n"
                        f"**Tool:** Nano Banana API (`{MODEL}`)\n"
                        f"**Mode:** text-to-image (A/B replica)\n"
                        f"**Aspect ratio:** {LANDSCAPE_RATIO}\n"
                        f"**Prompt:** {scene['prompt']}\n"
                        f"**Baseline:** {scene['rs3_file']}\n"
                        f"**Generation ID:** {result.get('generationId', '?')}\n"
                        f"**Credits used:** {result.get('creditsUsed', '?')}\n"
                        f"**Quality vs baseline:** [fill in: same / better / worse — and why]\n"
                    )
                else:
                    print(f"  v{i}: ERROR — no imageUrls: {result}")
            except Exception as exc:
                print(f"  v{i}: ERROR — {exc}")
        print()

    print("=== N-4 complete ===")
    print("Compare API output vs RS-3 Gemini Test/ baselines, then update RS-6 §6 (N-4)")


if __name__ == "__main__":
    main()

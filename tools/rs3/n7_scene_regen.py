"""
N-7 — Scene Regeneration: Throne Room + Corridor
Generates flat vector kawaii interior scenes via Recraft v3 vector_illustration style.

Design notes:
- Recraft V4 Vector supports 1024x1024 only (landscape sizes rejected).
  SVG scenes are vector and scale losslessly in-app (Compose Canvas) to fill 2000x1340 display.
  This constraint is documented as AD-8.
- Style anchor from canonical-style.jpg encoded in text prompt (Recraft API is text-only;
  no image-reference parameter available in this endpoint).
- Format validation: magic bytes checked before saving; SVG rendered to PNG via cairosvg
  before any further use. Never assume extension == format (learned from N-5 stall).
- All outputs validated via PIL.Image.verify() before reporting success.

Usage:
    python tools/rs3/n7_scene_regen.py

Outputs:
    assets/archive/scenes/castle-throne-room/recraft/  -- SVG + PNG renders
    assets/archive/scenes/castle-corridor/recraft/     -- SVG + PNG renders
Logs:
    assets/prompt-log.md  (AD-3)
"""

import io
import sys
from datetime import datetime
from pathlib import Path

import cairosvg
import httpx
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = REPO_ROOT / "tools" / ".env"
PROMPT_LOG = REPO_ROOT / "assets" / "prompt-log.md"
API_URL = "https://external.api.recraft.ai/v1/images/generations"

THRONE_OUT = REPO_ROOT / "assets" / "archive" / "scenes" / "castle-throne-room" / "recraft"
CORRIDOR_OUT = REPO_ROOT / "assets" / "archive" / "scenes" / "castle-corridor" / "recraft"

# Recraft V4 Vector only supports 1024x1024 (AD-8). SVGs scale to device at runtime.
SIZE = "1024x1024"
STYLE = "vector_illustration"
VARIANTS = 2  # 2 variants per scene

# ── Prompts ───────────────────────────────────────────────────────────────────
# Style anchor characteristics from carriage-scene-v4 (canonical-style.jpg) encoded in text:
# flat geometric / low-poly shapes, bold black outlines, flat colour fills, warm palette,
# 2D side-view, vibrant saturated colours, no gradients, no shadows, no photorealism.

THRONE_ROOM_PROMPT = (
    "castle throne room interior scene, flat vector kawaii illustration, "
    "low-poly geometric shapes, bold black outlines, flat solid colour fills, "
    "golden throne on raised stone dais centered in composition, "
    "simplified flat arched stone walls, tall arched window in back wall with flat sky visible, "
    "flat geometric stone tile floor, warm gold amber and stone grey colour palette, "
    "open archway on left wall and open archway on right wall as natural exit zones, "
    "wall-mounted torch brackets as simple flat shapes, "
    "no gradients, no shadows, no ambient occlusion, no directional lighting effects, "
    "no stone texture detail, no stone masonry grout, no glow, no bloom, "
    "fairy tale game background art, flat 2D game scene"
)

CORRIDOR_PROMPT = (
    "castle stone corridor interior scene, flat vector kawaii illustration, "
    "low-poly geometric shapes, bold black outlines, flat solid colour fills, "
    "straight corridor with flat arched vaulted ceiling, "
    "stone block walls as flat rectangular colour panels, "
    "simple torch bracket shapes on walls with flat orange flame, "
    "flat geometric stone tile floor path leading to arched exit, "
    "warm grey amber and gold colour palette, "
    "open archway exit visible at straight-ahead far end of corridor, "
    "no gradients, no shadows, no directional lighting, "
    "no atmospheric bloom or glow, no stone texture or masonry grout detail, "
    "no ambient occlusion, no fog or haze, "
    "fairy tale game background art, flat 2D game scene"
)

SCENES = [
    {
        "name": "throne-room",
        "slug": "recraft-throne-room",
        "out_dir": THRONE_OUT,
        "prompt": THRONE_ROOM_PROMPT,
    },
    {
        "name": "corridor",
        "slug": "recraft-corridor",
        "out_dir": CORRIDOR_OUT,
        "prompt": CORRIDOR_PROMPT,
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def detect_format(data: bytes) -> str:
    """Return 'svg', 'png', 'jpeg', 'webp', or 'unknown' based on magic bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"\xff\xd8":
        return "jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    # SVG: starts with '<svg' or '<?xml' (after optional BOM)
    head = data[:100].lstrip(b"\xef\xbb\xbf")  # strip UTF-8 BOM
    if head.lstrip()[:4] in (b"<svg", b"<?xm"):
        return "svg"
    return "unknown"


def svg_to_png(svg_bytes: bytes, width: int = 1024, height: int = 1024) -> bytes:
    """Render SVG bytes to PNG bytes via cairosvg."""
    return cairosvg.svg2png(bytestring=svg_bytes, output_width=width, output_height=height)


def validate_png(path: Path) -> bool:
    """Return True if the file is a valid PIL-readable image."""
    try:
        img = Image.open(path)
        img.verify()
        return True
    except Exception:
        return False


def save_asset(raw: bytes, base_path: Path) -> tuple[Path, str]:
    """
    Detect actual format, save with correct extension, render SVG to PNG.
    Returns (canonical_path, format_name).
    canonical_path is the PNG (either downloaded directly or rendered from SVG).
    """
    fmt = detect_format(raw)

    if fmt == "svg":
        svg_path = base_path.with_suffix(".svg")
        svg_path.write_bytes(raw)
        png_data = svg_to_png(raw)
        png_path = base_path.with_suffix(".png")
        png_path.write_bytes(png_data)
        return png_path, "svg"

    elif fmt in ("png", "jpeg", "webp"):
        ext = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}[fmt]
        raw_path = base_path.with_suffix(ext)
        raw_path.write_bytes(raw)
        if fmt in ("jpeg", "webp"):
            # Convert to PNG for consistency
            png_path = base_path.with_suffix(".png")
            img = Image.open(raw_path).convert("RGBA")
            img.save(png_path, "PNG")
            return png_path, fmt
        return raw_path, fmt

    else:
        # Unknown format — save raw with .bin and bail
        bin_path = base_path.with_suffix(".bin")
        bin_path.write_bytes(raw)
        return bin_path, "unknown"


def append_prompt_log(text: str):
    with open(PROMPT_LOG, "a", encoding="utf-8") as f:
        f.write("\n" + text + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    env = load_env(ENV_FILE)
    api_key = env.get("RECRAFT_API_KEY", "")
    if not api_key:
        print("ERROR: RECRAFT_API_KEY not set in tools/.env", file=sys.stderr)
        sys.exit(1)

    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"N-7 Scene Regeneration — {date_str}")
    print(f"Style: {STYLE}  Size: {SIZE}  Variants per scene: {VARIANTS}")
    print()

    all_results = []

    with httpx.Client() as client:
        for scene in SCENES:
            scene["out_dir"].mkdir(parents=True, exist_ok=True)
            print(f"[{scene['name']}]")

            for v in range(1, VARIANTS + 1):
                filename_base = f"{scene['slug']}-v{v}"
                base_path = scene["out_dir"] / filename_base
                print(f"  Generating variant {v}...", end=" ", flush=True)

                try:
                    resp = client.post(
                        API_URL,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"prompt": scene["prompt"], "style": STYLE, "n": 1, "size": SIZE},
                        timeout=120,
                    )
                    resp.raise_for_status()
                    image_url = resp.json()["data"][0]["url"]

                    # Download
                    dl = client.get(image_url, timeout=60)
                    dl.raise_for_status()
                    raw = dl.content

                    # Detect, save, render
                    fmt = detect_format(raw)
                    png_path, saved_fmt = save_asset(raw, base_path)

                    # Validate
                    if not validate_png(png_path):
                        print(f"✗ PNG validation FAILED: {png_path.name}")
                        all_results.append({"scene": scene["name"], "variant": v, "status": "png_invalid"})
                        continue

                    size_kb = png_path.stat().st_size // 1024
                    print(f"✓ {png_path.name} ({size_kb} KB, actual_fmt={fmt})")
                    all_results.append({
                        "scene": scene["name"],
                        "variant": v,
                        "filename": png_path.name,
                        "actual_fmt": fmt,
                        "size_kb": size_kb,
                        "url": image_url,
                        "status": "ok",
                    })

                except httpx.HTTPStatusError as e:
                    print(f"✗ HTTP {e.response.status_code}: {e.response.text[:200]}")
                    all_results.append({"scene": scene["name"], "variant": v, "status": f"http_error_{e.response.status_code}"})
                except Exception as e:
                    print(f"✗ {e}")
                    all_results.append({"scene": scene["name"], "variant": v, "status": f"error: {e}"})
            print()

    # ── Summary ───────────────────────────────────────────────────────────────
    ok = [r for r in all_results if r.get("status") == "ok"]
    print(f"Results: {len(ok)}/{len(all_results)} successful")
    for r in all_results:
        print(f"  {r.get('scene','?'):15s} v{r.get('variant','?')}: {r.get('status','?')} "
              f"[{r.get('actual_fmt','?')}] {r.get('filename','')}")

    # ── Prompt log (AD-3) ─────────────────────────────────────────────────────
    log = [
        f"\n## Phase 2 — N-7 Scene Regeneration — {date_str}\n",
        "**Task:** N-7 — Regenerate throne room + corridor in flat vector kawaii style (Recraft v3)",
        f"**Tool:** Recraft v3 REST API, style=`{STYLE}`, size=`{SIZE}`",
        "**Style anchor:** Carriage-scene-v4 style characteristics encoded in text prompt (Recraft is text-only, no image-ref parameter)",
        "**Size constraint (AD-8):** Recraft V4 Vector supports 1024×1024 only. SVG scales losslessly to 2000×1340 at runtime.",
        "",
        "### Throne Room Prompt",
        f"```\n{THRONE_ROOM_PROMPT}\n```",
        "",
        "### Corridor Prompt",
        f"```\n{CORRIDOR_PROMPT}\n```",
        "",
        "### Results",
    ]
    for r in all_results:
        log.append(f"- `{r.get('filename', r.get('scene') + '-v' + str(r.get('variant')))}`"
                   f": {r.get('status')} [{r.get('actual_fmt', '?')}] {r.get('size_kb', '')}KB")
    append_prompt_log("\n".join(log))
    print("\nPrompt log updated.")


if __name__ == "__main__":
    main()

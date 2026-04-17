"""
N-5 — Recraft v3 Evaluation Script
Generates princess-full in Recraft's flat_illustration and vector_illustration styles,
downloads results, and produces a side-by-side style comparison report.

Usage:
    python tools/rs3/n5_recraft_eval.py

Outputs (all in assets/archive/characters/princess/recraft/):
    recraft-princess-vector-v{n}.png      — vector_illustration style variants
    recraft-princess-flat-v{n}.png        — flat_illustration style variants
    recraft-princess-icon-v{n}.png        — realvector/icon style if supported

Logs every generation in assets/prompt-log.md (AD-3).
"""

import httpx
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add tools/ to path for shared utilities
_TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from shared.retrieve_image import download_image as safe_download  # noqa: E402

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ENV_FILE = REPO_ROOT / "tools" / ".env"
OUT_DIR = REPO_ROOT / "assets" / "archive" / "characters" / "princess" / "recraft"
PROMPT_LOG = REPO_ROOT / "assets" / "prompt-log.md"
API_URL = "https://external.api.recraft.ai/v1/images/generations"

# N-5 Evaluation prompts — match the archive princess-full-v5 as closely as possible
# so the comparison is valid (same subject, different tool)
PROMPT_BASE = (
    "chibi kawaii princess character, full body, flat geometric shapes, "
    "bold black outline, pink ballgown dress, golden crown, brown hair, "
    "large round eyes, simple flat colour fills, white background, "
    "no gradients, no shadows, no textures, vector illustration style"
)

# Recraft style IDs to evaluate (validated against API 2026-04-16)
# Valid styles: vector_illustration, digital_illustration, icon, realistic_image
# Invalid (tested): flat_illustration, flat_vector, flat_design, line_art, sketch, pixel_art
STYLES = [
    ("vector_illustration", "vector-illustration"),
    ("digital_illustration", "digital-illustration"),
    ("icon", "icon"),
]

VARIANTS_PER_STYLE = 2   # Generate 2 variants per style (n=1 each, called twice)
SIZE = "1024x1024"


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def append_prompt_log(entry: str):
    with open(PROMPT_LOG, "a", encoding="utf-8") as f:
        f.write("\n" + entry + "\n")


def generate_image(client: httpx.Client, api_key: str, style_id: str, prompt: str) -> dict:
    resp = client.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"prompt": prompt, "style": style_id, "n": 1, "size": SIZE},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def download_image(client: httpx.Client, url: str, dest: Path) -> Path:
    """Download image with format detection and PIL.verify() validation."""
    result = safe_download(url, dest)
    return result.path


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    env = load_env(ENV_FILE)
    api_key = env.get("RECRAFT_API_KEY", "")
    if not api_key:
        print("ERROR: RECRAFT_API_KEY not set in tools/.env", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"N-5 Recraft Evaluation — {date_str}")
    print(f"Output directory: {OUT_DIR}")
    print(f"Styles: {[s[0] for s in STYLES]}, {VARIANTS_PER_STYLE} variants each")
    print()

    results = []

    with httpx.Client() as client:
        for style_id, style_slug in STYLES:
            print(f"[{style_id}]")
            for variant_idx in range(1, VARIANTS_PER_STYLE + 1):
                filename = f"recraft-princess-{style_slug}-v{variant_idx}.png"
                out_path = OUT_DIR / filename
                print(f"  Generating variant {variant_idx}...", end=" ", flush=True)

                try:
                    response = generate_image(client, api_key, style_id, PROMPT_BASE)
                    image_url = response["data"][0]["url"]
                    actual_path = download_image(client, image_url, out_path)
                    size_kb = actual_path.stat().st_size // 1024
                    filename = actual_path.name
                    print(f"✓ Saved {filename} ({size_kb} KB)")

                    results.append({
                        "style_id": style_id,
                        "variant": variant_idx,
                        "filename": filename,
                        "url": image_url,
                        "size_kb": size_kb,
                        "status": "ok",
                    })

                except httpx.HTTPStatusError as e:
                    print(f"✗ HTTP {e.response.status_code}: {e.response.text[:200]}")
                    results.append({
                        "style_id": style_id,
                        "variant": variant_idx,
                        "filename": filename,
                        "status": f"error: HTTP {e.response.status_code}",
                        "detail": e.response.text[:400],
                    })
                except Exception as e:
                    print(f"✗ {e}")
                    results.append({
                        "style_id": style_id,
                        "variant": variant_idx,
                        "filename": filename,
                        "status": f"error: {e}",
                    })

    # ── Write results summary ─────────────────────────────────────────────────
    print()
    print("Results summary:")
    for r in results:
        status = r["status"]
        print(f"  {r['filename']}: {status}")

    # ── Append to prompt-log.md (AD-3) ───────────────────────────────────────
    log_lines = [
        f"\n## Phase 2 — N-5 Recraft v3 Evaluation — {date_str}\n",
        "**Task:** N-5 — Evaluate Recraft v3 as alternative to DALL-E 3 for flat vector princess sprite",
        "**Comparison target:** `assets/archive/characters/princess/princess-full-v5.jpg` (DALL-E 3 archive)",
        "**Reference:** REC-6 (investigate Recraft v3 for SVG-native characters)",
        "",
        f"**Prompt:**",
        f"```",
        PROMPT_BASE,
        f"```",
        "",
        f"**Tool:** Recraft v3 API (`{API_URL}`)",
        f"**Size:** {SIZE}",
        "",
        "**Variants generated:**",
        "",
        "| File | Style | Status |",
        "|------|-------|--------|",
    ]
    for r in results:
        log_lines.append(f"| `recraft/{r['filename']}` | `{r['style_id']}` | {r['status']} |")

    log_lines += [
        "",
        "**Evaluation:** See RS-3 §12.3 for style comparison findings.",
        "**Output directory:** `assets/archive/characters/princess/recraft/`",
    ]

    append_prompt_log("\n".join(log_lines))
    print(f"\nPrompt log updated: {PROMPT_LOG}")
    print("\nNext step: visually evaluate outputs vs princess-full-v5.jpg and record in RS-3 §12.3")


if __name__ == "__main__":
    main()

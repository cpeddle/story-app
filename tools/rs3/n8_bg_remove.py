"""
N-8 — Background removal batch for selected character sprites.

Technique: edge-connected flood fill from image border through pixels "near"
the sampled background colour (Euclidean distance in RGB space), then
2px dilation to erase anti-aliasing fringe around the character silhouette.

This is more robust than per-channel thresholds (N-4 technique) because it
handles both light and dark backgrounds by calibrating against sampled corners.

Sprites processed:
  knight/knight-full-v4.jpg   — near-white bg, palette strip cropped
  dragon/dragon-full-v4.jpg   — warm peach bg with integrated artwork (NOTE: partial)
  dragon/dragon-full-v2.jpg   — dark grey bg (non-standard for archive)

Output: <original_name>.png (RGBA, transparent background) alongside source file.
Appends results to assets/prompt-log.md (AD-3).
"""

from pathlib import Path
import numpy as np
import scipy.ndimage
from PIL import Image
import datetime

ROOT = Path(__file__).resolve().parent.parent.parent  # story-app root
ARCHIVE = ROOT / "assets" / "archive" / "characters"
PROMPT_LOG = ROOT / "assets" / "prompt-log.md"

# Per-sprite config:
#   char        — subdirectory under archive/characters/
#   file        — source JPEG filename
#   bottom_crop — pixels to trim from bottom before processing (removes palette strips)
#   dist_thresh — Euclidean RGB distance threshold for "near background"
#                 35–45 is typical; increase if background fringe remains
SPRITES = [
    {
        "char": "knight",
        "file": "knight-full-v4.jpg",
        "bottom_crop": 185,   # palette strip occupies rows 845–990; crop from row 839 upward
        "dist_thresh": 38,
    },
    {
        "char": "dragon",
        "file": "dragon-full-v4.jpg",
        "bottom_crop": 0,
        "dist_thresh": 42,    # warm peach bg — wider tolerance needed
    },
    {
        "char": "dragon",
        "file": "dragon-full-v2.jpg",
        "bottom_crop": 0,
        "dist_thresh": 35,    # dark grey bg — well-separated from warm character
    },
]

DILATION_PX = 2  # pixels to dilate background mask (erases anti-aliasing fringe)


def sample_bg_colour(arr: np.ndarray) -> np.ndarray:
    """Median colour from 10×10 pixel samples at all 4 corners."""
    h, w = arr.shape[:2]
    c = 10
    corners = np.concatenate([
        arr[:c,    :c,    :3].reshape(-1, 3),
        arr[:c,    w-c:,  :3].reshape(-1, 3),
        arr[h-c:,  :c,    :3].reshape(-1, 3),
        arr[h-c:,  w-c:,  :3].reshape(-1, 3),
    ])
    return np.median(corners, axis=0)


def build_bg_mask(arr: np.ndarray, bg_colour: np.ndarray, dist_thresh: float) -> np.ndarray:
    """
    Boolean mask (True = background) via edge-connected flood fill.

    1. Classify every pixel as 'candidate background' if its Euclidean RGB
       distance from bg_colour is within dist_thresh.
    2. Flood fill from the image border through connected candidate-bg pixels.
       This excludes interior pockets (e.g. isolated dark areas inside the character).
    3. Return the flood-filled mask.
    """
    rgb = arr[:, :, :3].astype(np.float32)
    dist = np.linalg.norm(rgb - bg_colour.astype(np.float32), axis=2)
    candidate = dist <= dist_thresh

    # Pad with a True border so flood fill seeds from all 4 edges uniformly.
    padded = np.pad(candidate, pad_width=1, mode="constant", constant_values=True)
    labelled, _ = scipy.ndimage.label(padded)
    bg_label = labelled[0, 0]  # top-left padded pixel is guaranteed background
    bg_mask = (labelled == bg_label)[1:-1, 1:-1]  # strip padding

    return bg_mask


def dilate_bg_mask(mask: np.ndarray, px: int) -> np.ndarray:
    """Expand background mask outward by px pixels (erodes character outline)."""
    struct = scipy.ndimage.generate_binary_structure(2, 1)
    result = mask.copy()
    for _ in range(px):
        result = scipy.ndimage.binary_dilation(result, structure=struct)
    return result


def process_sprite(cfg: dict) -> dict:
    src = ARCHIVE / cfg["char"] / cfg["file"]
    dst = src.with_suffix(".png")

    print(f"\n{'─'*55}")
    print(f"  Source : {src.relative_to(ROOT)}")

    img = Image.open(src).convert("RGB")
    arr = np.array(img)
    h_orig, w_orig = arr.shape[:2]

    # Optional bottom crop (remove palette strips)
    bottom_crop = cfg.get("bottom_crop", 0)
    if bottom_crop > 0:
        arr = arr[:h_orig - bottom_crop, :, :]
        print(f"  Cropped: {bottom_crop}px from bottom (palette strip removed)")

    bg_colour = sample_bg_colour(arr)
    print(f"  BG colour (sampled median): R={bg_colour[0]:.0f}  G={bg_colour[1]:.0f}  B={bg_colour[2]:.0f}")

    bg_mask = build_bg_mask(arr, bg_colour, cfg["dist_thresh"])
    bg_mask = dilate_bg_mask(bg_mask, DILATION_PX)

    alpha = (~bg_mask).astype(np.uint8) * 255

    # If we cropped, restore to original canvas height with fully transparent bottom band
    if bottom_crop > 0:
        alpha_full = np.zeros((h_orig,), dtype=np.uint8)
        alpha_full_2d = np.zeros((h_orig, w_orig), dtype=np.uint8)
        alpha_full_2d[:h_orig - bottom_crop, :] = alpha
        alpha = alpha_full_2d
        # Also expand arr back for the RGBA compose
        arr_full = np.array(Image.open(src).convert("RGB"))
        arr = arr_full

    rgba = np.dstack([arr, alpha])
    out_img = Image.fromarray(rgba, "RGBA")
    out_img.save(dst)

    fg_pixels = int(alpha.sum() // 255)
    total = h_orig * w_orig
    fg_pct = 100 * fg_pixels / total

    print(f"  Foreground retained: {fg_pixels:,} / {total:,} ({fg_pct:.1f}%)")
    print(f"  Output : {dst.relative_to(ROOT)}")

    # Quality heuristic: flag if foreground fraction looks suspicious
    verdict = "✅ OK"
    note = ""
    if fg_pct < 5:
        verdict = "❌ ERROR — almost nothing retained (threshold too aggressive?)"
    elif fg_pct > 75:
        verdict = "⚠️  HIGH — background may not be fully removed (threshold too lenient?)"
        note = "Review output manually."
    print(f"  Quality: {verdict}  {note}")

    return {
        "file": cfg["file"],
        "output": str(dst.relative_to(ROOT)),
        "fg_pct": fg_pct,
        "verdict": verdict,
        "bg_colour": bg_colour,
    }


def append_prompt_log(results: list[dict]):
    date = datetime.date.today().isoformat()
    lines = [
        "",
        f"## Phase 2 — N-8 Background Removal Batch — {date}",
        "",
        "**Task:** N-8 — Background removal pass on selected character sprites",
        "**Tool:** Python (numpy + scipy.ndimage flood fill, 2px dilation) — `tools/rs3/n8_bg_remove.py`",
        "**Technique:** Edge-connected flood fill from image border through pixels within Euclidean RGB",
        "distance of sampled background colour; 2px dilation to erase anti-aliasing fringe.",
        "",
        "| Sprite | Output | BG Colour | FG % | Verdict |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        bg = r["bg_colour"]
        lines.append(
            f"| `{r['file']}` | `{r['output']}` | R={bg[0]:.0f} G={bg[1]:.0f} B={bg[2]:.0f} "
            f"| {r['fg_pct']:.1f}% | {r['verdict']} |"
        )
    lines.append("")

    with open(PROMPT_LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nAppended results to {PROMPT_LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    print("N-8 Background Removal Batch")
    print("=" * 55)
    print(f"Sprites to process: {len(SPRITES)}")
    print("Note: princess-full-v5.png already exists (N-4) — skipped.")

    results = []
    for cfg in SPRITES:
        try:
            result = process_sprite(cfg)
            results.append(result)
        except Exception as e:
            print(f"  ERROR processing {cfg['file']}: {e}")
            import traceback
            traceback.print_exc()

    append_prompt_log(results)
    print("\n" + "=" * 55)
    print("N-8 complete. Review output PNGs before using in app.")

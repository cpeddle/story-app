"""
N-9 — Character part anchor system test for princess sprite.

Tests whether princess parts (crown, hair, outfit) were generated with a
consistent anchor convention — i.e. whether naive 1:1 overlay at canvas
origin produces correct alignment, or whether a manual offset/scale is needed.

Parts selected for test:
  princess-crown-v4.jpg     — flat geometric style (v5 is 3D realistic; rejected)
  princess-hair-long-v4.jpg — flat geometric brown hair
  princess-outfit-ballgown-blue-v4.jpg — flat geometric blue ballgown

Base sprite:
  princess-full-v5.png     — transparent RGBA (already BG-removed in N-4)

Output:
  n9-part-composite-test.png      — naive 1:1 overlay (crown on top)
  n9-part-crown-only.png          — crown-removed test
  n9-parts-bgremoved/             — BG-removed part PNGs saved for inspection

Technique:
  BG removal: edge-connected flood fill (same as n8_bg_remove.py) with
  global-threshold fallback to also clear enclosed white areas (needed for
  hair where the face cutout is enclosed -- it must be transparent so the
  base body face shows through on composite).
"""

from pathlib import Path
import numpy as np
import scipy.ndimage
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent  # story-app root
ARCHIVE = ROOT / "assets" / "archive" / "characters" / "princess"
OUT_DIR = ARCHIVE / "n9-parts-bgremoved"
OUT_DIR.mkdir(exist_ok=True)

# Parts to test — (source_jpg, output_stem, dist_thresh, also_global_thresh)
# also_global_thresh: when True, also apply a global white-ish threshold pass
# to clear enclosed interior white holes (e.g. face cutout in hair image).
PARTS = [
    {
        "file": "princess-crown-v4.jpg",
        "stem": "crown-v4",
        "dist_thresh": 30,
        "global_thresh": True,   # simple shape, safe to use global
    },
    {
        "file": "princess-hair-long-v4.jpg",
        "stem": "hair-long-v4",
        "dist_thresh": 30,
        "global_thresh": True,   # face cutout must become transparent
    },
    {
        "file": "princess-outfit-ballgown-blue-v4.jpg",
        "stem": "outfit-ballgown-blue-v4",
        "dist_thresh": 35,
        "global_thresh": True,   # cream bg + enclosed light areas
    },
]

# Compositing order (bottom to top)
LAYER_ORDER = ["outfit-ballgown-blue-v4", "hair-long-v4", "crown-v4"]


# ── BG removal helpers (identical to n8_bg_remove.py) ───────────────────────

def sample_bg_colour(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    c = 10
    corners = np.concatenate([
        arr[:c,   :c,   :3].reshape(-1, 3),
        arr[:c,   w-c:, :3].reshape(-1, 3),
        arr[h-c:, :c,   :3].reshape(-1, 3),
        arr[h-c:, w-c:, :3].reshape(-1, 3),
    ])
    return np.median(corners, axis=0)


def build_bg_mask_flood(arr: np.ndarray, bg_colour: np.ndarray, dist_thresh: float) -> np.ndarray:
    """Edge-connected flood fill through pixels near bg_colour."""
    rgb = arr[:, :, :3].astype(np.float32)
    dist = np.linalg.norm(rgb - bg_colour.astype(np.float32), axis=2)
    candidate = dist <= dist_thresh
    padded = np.pad(candidate, 1, mode="constant", constant_values=True)
    labelled, _ = scipy.ndimage.label(padded)
    bg_label = labelled[0, 0]
    return (labelled == bg_label)[1:-1, 1:-1]


def build_bg_mask_global(arr: np.ndarray, bg_colour: np.ndarray, dist_thresh: float) -> np.ndarray:
    """Global threshold — marks ALL pixels near bg_colour as background.
    Used to clear enclosed white holes (e.g. face cutout inside hair outline)."""
    rgb = arr[:, :, :3].astype(np.float32)
    dist = np.linalg.norm(rgb - bg_colour.astype(np.float32), axis=2)
    return dist <= dist_thresh


def dilate_bg(mask: np.ndarray, px: int = 2) -> np.ndarray:
    s = scipy.ndimage.generate_binary_structure(2, 1)
    for _ in range(px):
        mask = scipy.ndimage.binary_dilation(mask, structure=s)
    return mask


def remove_bg(src: Path, dist_thresh: float, global_thresh: bool) -> np.ndarray:
    """Returns RGBA uint8 array with background removed."""
    img = Image.open(src).convert("RGB")
    arr = np.array(img)
    bg = sample_bg_colour(arr)
    print(f"  {src.name}: BG sampled as R={bg[0]:.0f} G={bg[1]:.0f} B={bg[2]:.0f}")

    # Flood-fill mask (border-connected background)
    mask = build_bg_mask_flood(arr, bg, dist_thresh)

    if global_thresh:
        # Also clear enclosed white areas (face holes, interior cutouts)
        # Use a slightly tighter threshold to avoid eroding character art
        global_mask = build_bg_mask_global(arr, bg, dist_thresh - 5)
        mask = mask | global_mask

    mask = dilate_bg(mask, 2)

    alpha = (~mask).astype(np.uint8) * 255
    rgba = np.dstack([arr, alpha])
    fg_px = int(alpha.sum() // 255)
    total = arr.shape[0] * arr.shape[1]
    print(f"  {src.name}: Foreground {fg_px:,}/{total:,} ({100*fg_px/total:.1f}%)")
    return rgba


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== N-9 Part BG Removal ===")
    part_pngs: dict[str, np.ndarray] = {}

    for cfg in PARTS:
        src = ARCHIVE / cfg["file"]
        print(f"\nProcessing: {src.name}")
        rgba = remove_bg(src, cfg["dist_thresh"], cfg["global_thresh"])
        out = OUT_DIR / f"{cfg['stem']}.png"
        Image.fromarray(rgba, "RGBA").save(out)
        print(f"  → Saved: {out}")
        part_pngs[cfg["stem"]] = rgba

    # ── Composite test ────────────────────────────────────────────────────────
    print("\n=== N-9 Composite Test ===")
    base_path = ARCHIVE / "princess-full-v5.png"
    base = np.array(Image.open(base_path).convert("RGBA"))
    canvas = base.copy()

    for stem in LAYER_ORDER:
        part = part_pngs[stem]
        h_p, w_p = part.shape[:2]
        h_c, w_c = canvas.shape[:2]

        # Ensure same canvas size (crop or pad if sizes differ)
        h = min(h_p, h_c)
        w = min(w_p, w_c)
        region_base = canvas[:h, :w].astype(np.float32)
        region_part = part[:h, :w].astype(np.float32)

        # Alpha compositing: result = part_rgb * part_alpha + base_rgb * (1 - part_alpha)
        part_alpha = region_part[:, :, 3:4] / 255.0
        blended = region_part[:, :, :3] * part_alpha + region_base[:, :, :3] * (1 - part_alpha)
        blended_alpha = region_part[:, :, 3:4] + region_base[:, :, 3:4] * (1 - part_alpha)
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        blended_alpha = np.clip(blended_alpha, 0, 255).astype(np.uint8)
        canvas[:h, :w, :3] = blended
        canvas[:h, :w, 3:4] = blended_alpha
        print(f"  Composited: {stem}")

    composite_out = ARCHIVE / "n9-part-composite-test.png"
    Image.fromarray(canvas, "RGBA").save(composite_out)
    print(f"\n→ Composite saved: {composite_out}")

    # ── Print alignment analysis hint ───────────────────────────────────────
    # Measure bounding box of non-transparent pixels in each part
    print("\n=== Bounding Boxes (non-transparent pixels) ===")
    base_rgba = np.array(Image.open(base_path).convert("RGBA"))
    _print_bbox("body (full)", base_rgba)
    for stem, rgba in part_pngs.items():
        _print_bbox(stem, rgba)


def _print_bbox(label: str, rgba: np.ndarray):
    alpha = rgba[:, :, 3]
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    if not rows.any():
        print(f"  {label}: empty")
        return
    r_min, r_max = np.where(rows)[0][[0, -1]]
    c_min, c_max = np.where(cols)[0][[0, -1]]
    h = rgba.shape[0]
    w = rgba.shape[1]
    print(f"  {label}: rows {r_min}–{r_max} ({r_min/h:.2f}–{r_max/h:.2f}h), "
          f"cols {c_min}–{c_max} ({c_min/w:.2f}–{c_max/w:.2f}w), "
          f"height={r_max-r_min}, width={c_max-c_min}")


if __name__ == "__main__":
    main()

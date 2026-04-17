"""
Safe image retrieval for Story App development tools.

External image-generation APIs (Nano Banana, Recraft, Gemini, OpenAI) may return
images in any format (JPEG, PNG, WebP, SVG, GIF) regardless of what was requested
or what the URL extension suggests. Saving blindly as .png causes downstream
failures when agents submit files to vision analysis — the format mismatch causes
a silent failure that agents retry indefinitely.

This module provides a single safe entry point:

    from shared.retrieve_image import download_image

The function:
1. Downloads raw bytes from a URL
2. Detects actual format via magic bytes (not extension, not Content-Type)
3. Saves with correct extension (renaming if needed)
4. Optionally converts to PNG (SVG rendered via cairosvg, JPEG/WebP via PIL)
5. Validates the final file with PIL.Image.verify()
6. Returns the actual path written + detected format name

History:
- 2026-04-16: Pattern emerged in RS-3 N-5/N-7 (Recraft SVG/WebP saved as .png)
- 2026-04-17: Recurred in RS-6 N-3 (Nano Banana JPEG saved as .png)
- 2026-04-17: _image_utils.py created in tools/rs6/ (magic bytes, no PIL.verify)
- 2026-04-17: Promoted to tools/shared/retrieve_image.py (compound-engineering)
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import requests
from PIL import Image

# ── Format detection ──────────────────────────────────────────────────────────

# Magic byte signatures → (format name, canonical extension)
_SIGNATURES: list[tuple[bytes, str, str]] = [
    (b"\x89PNG\r\n\x1a\n", "png", ".png"),
    (b"\xff\xd8\xff", "jpeg", ".jpg"),
    (b"GIF87a", "gif", ".gif"),
    (b"GIF89a", "gif", ".gif"),
]


def detect_format(data: bytes) -> tuple[str, str]:
    """Return (format_name, extension) from the first bytes of image data.

    Checks magic bytes — never trusts the URL extension or Content-Type.
    """
    # WebP: RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", ".webp"
    for sig, fmt, ext in _SIGNATURES:
        if data[: len(sig)] == sig:
            return fmt, ext
    # SVG heuristic (may start with BOM or whitespace)
    head = data[:256].lstrip(b"\xef\xbb\xbf").lstrip()
    if head[:4] in (b"<svg", b"<?xm"):
        return "svg", ".svg"
    return "unknown", ".bin"


# ── SVG rendering ─────────────────────────────────────────────────────────────


def svg_to_png(svg_bytes: bytes, width: int = 1024, height: int = 1024) -> bytes:
    """Render SVG bytes to PNG bytes via cairosvg.

    Requires: pip install cairosvg
    Raises ImportError if cairosvg is not installed.
    """
    import cairosvg

    return cairosvg.svg2png(
        bytestring=svg_bytes, output_width=width, output_height=height
    )


# ── Validation ────────────────────────────────────────────────────────────────


def verify_image(path: Path) -> bool:
    """Return True if the file is a valid PIL-readable image.

    This catches format mismatches, truncated files, and corrupted data
    BEFORE the file is submitted to vision analysis or other downstream tools.
    """
    try:
        img = Image.open(path)
        img.verify()
        return True
    except Exception:
        return False


# ── Download result ───────────────────────────────────────────────────────────


class DownloadResult(NamedTuple):
    """Result of a download_image call."""

    path: Path  # actual path written (may differ from requested dest)
    format: str  # detected format name ("png", "jpeg", "webp", "svg", "gif", "unknown")
    original_path: Path  # original dest requested (before extension correction)
    converted_to_png: bool  # True if a PNG conversion was performed


# ── Main entry point ──────────────────────────────────────────────────────────


def download_image(
    url: str,
    dest: Path,
    *,
    convert_to_png: bool = False,
    svg_width: int = 1024,
    svg_height: int = 1024,
    timeout: int = 60,
) -> DownloadResult:
    """Download an image from *url*, detect its real format, and save safely.

    Parameters
    ----------
    url : str
        The URL to download from.
    dest : Path
        Intended save path. The extension may be corrected based on actual format.
    convert_to_png : bool
        If True, convert non-PNG raster formats (JPEG, WebP) to PNG, and render
        SVG to PNG. The original file is also kept. Useful when downstream tools
        require PNG specifically.
    svg_width, svg_height : int
        Dimensions for SVG→PNG rendering (only used if format is SVG).
    timeout : int
        HTTP request timeout in seconds.

    Returns
    -------
    DownloadResult
        Named tuple with (path, format, original_path, converted_to_png).

    Raises
    ------
    requests.HTTPError
        If the download fails.
    ValueError
        If the downloaded file fails PIL.Image.verify() (not a valid image).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.content

    fmt, correct_ext = detect_format(data)
    requested_ext = dest.suffix.lower()

    # Save with correct extension
    if correct_ext != requested_ext:
        actual_dest = dest.with_suffix(correct_ext)
        print(
            f"  ⚠️  Format mismatch: content is {fmt} but filename had "
            f"'{requested_ext}' → saving as {actual_dest.name}"
        )
    else:
        actual_dest = dest

    actual_dest.write_bytes(data)
    converted = False

    # Handle SVG specially
    if fmt == "svg":
        # SVG can't be verified by PIL — keep the SVG, render to PNG if requested
        if convert_to_png:
            png_data = svg_to_png(data, width=svg_width, height=svg_height)
            png_path = dest.with_suffix(".png")
            png_path.write_bytes(png_data)
            if not verify_image(png_path):
                raise ValueError(
                    f"SVG→PNG render produced invalid image: {png_path}"
                )
            print(f"  ✅  SVG rendered to PNG: {png_path.name}")
            return DownloadResult(
                path=png_path,
                format=fmt,
                original_path=dest,
                converted_to_png=True,
            )
        return DownloadResult(
            path=actual_dest, format=fmt, original_path=dest, converted_to_png=False
        )

    # Validate raster image
    if fmt != "unknown" and not verify_image(actual_dest):
        raise ValueError(
            f"Downloaded file failed PIL.verify(): {actual_dest} (detected: {fmt})"
        )

    # Convert to PNG if requested and format is not already PNG
    if convert_to_png and fmt in ("jpeg", "webp", "gif"):
        png_path = dest.with_suffix(".png")
        img = Image.open(actual_dest).convert("RGBA")
        img.save(png_path, "PNG")
        if not verify_image(png_path):
            raise ValueError(f"PNG conversion produced invalid image: {png_path}")
        print(f"  ✅  Converted {fmt} → PNG: {png_path.name}")
        converted = True
        return DownloadResult(
            path=png_path, format=fmt, original_path=dest, converted_to_png=True
        )

    return DownloadResult(
        path=actual_dest,
        format=fmt,
        original_path=dest,
        converted_to_png=converted,
    )

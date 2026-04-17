---
description: 'Safe image retrieval rules for Python scripts that download images from external APIs. Prevents format mismatch loops where agents retry indefinitely.'
applyTo: '**/tools/**/*.py'
---

# Safe Image Retrieval — Story App Tools

## The Problem

External image-generation APIs (Nano Banana, Recraft, Gemini, OpenAI) return images in
unpredictable formats. A request for PNG may return JPEG, WebP, or SVG. When scripts save
these files with a hardcoded `.png` extension, downstream consumers (vision analysis, PIL,
Canvas rendering) fail silently, causing agents to retry the same broken submission in an
infinite loop.

**This has occurred three times:**

| Date | Spike | API | What happened |
|------|-------|-----|------|
| 2026-04-16 | RS-3 N-5 | Recraft | SVG/WebP saved as .png; vision analysis loop |
| 2026-04-17 | RS-7 N-3 | Nano Banana | JPEG saved as .png; vision analysis loop |
| 2026-04-17 | RS-7 follow-up | Nano Banana | Stale .png files from prior session re-encountered |

## Mandatory Rules

1. **MUST use `tools/shared/retrieve_image.py`** — import `download_image` from
   `shared.retrieve_image` for ALL image downloads in `tools/` scripts.

2. **MUST NOT hardcode file extensions** for downloaded images. Let `download_image()`
   detect the actual format and set the correct extension.

3. **MUST call `PIL.Image.open(f).verify()`** before submitting any image to vision
   analysis or other downstream tools. The shared utility does this automatically.

4. **MUST handle SVG** — if the API returns SVG, render to PNG via `cairosvg.svg2png()`
   before submitting to vision. Use `convert_to_png=True` in `download_image()`.

5. **MUST NOT assume Content-Type or URL extension reflects actual format.**
   Only magic-byte detection is trustworthy.

## Usage

```python
import sys
from pathlib import Path

# Add tools/ to path
_TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from shared.retrieve_image import download_image

# Basic: auto-detects format, saves with correct extension
result = download_image(url, Path("output/scene-v1.png"))
print(result.path)     # May be scene-v1.jpg if API returned JPEG
print(result.format)   # "jpeg"

# With PNG conversion (e.g., for Compose Canvas assets)
result = download_image(url, Path("output/scene-v1.png"), convert_to_png=True)
# Always returns a valid PNG at result.path
```

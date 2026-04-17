"""
Image download + format validation for RS-6 scripts.

Thin wrapper around the shared retrieve_image module. All RS-6 scripts import
from here; this file delegates to the project-wide safe retrieval utility.

Usage:
    from _image_utils import download_image

History:
- 2026-04-17: Created as standalone RS-6 utility
- 2026-04-17: Refactored to delegate to tools/shared/retrieve_image.py
"""

import sys
from pathlib import Path

# Add tools/ to path so `from shared.retrieve_image import ...` works
_tools_dir = Path(__file__).resolve().parent.parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from shared.retrieve_image import download_image as _safe_download  # noqa: E402


def download_image(url: str, dest: Path) -> Path:
    """Download an image, detect real format, save with correct extension.

    Returns the actual Path written (may differ from *dest* if the extension
    was corrected). Validates with PIL.verify() after saving.
    """
    result = _safe_download(url, dest)
    return result.path

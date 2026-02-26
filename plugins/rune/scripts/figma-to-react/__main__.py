"""Allow running as `python3 -m figma-to-react` (or via the directory)."""

from __future__ import annotations

import sys
from pathlib import Path

# Import bootstrap — same pattern as cli.py and tests/conftest.py.
# The directory is named "figma-to-react" (hyphenated — invalid Python package).
_PKG_DIR = Path(__file__).resolve().parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

from cli import main  # noqa: E402

main()

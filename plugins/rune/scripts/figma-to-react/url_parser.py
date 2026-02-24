"""
Figma URL Parser

Parses Figma URLs into structured components (file_key, node_id, type, branch_key).
Supports 7 URL types: file, design, proto, board, slides, dev, make.
Handles branch URLs and encoded node-id formats.

Security:
  SEC-001: Hostname validation prevents SSRF via crafted URLs.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import unquote, urlparse


class FigmaURLError(ValueError):
    """Raised when a Figma URL cannot be parsed."""


# Allowed hostnames — prevents SSRF by restricting to Figma domains only.
_ALLOWED_HOSTS = frozenset({"figma.com", "www.figma.com"})

# URL path types that correspond to Figma document URLs.
# Each maps to the path segment that appears after the hostname.
_URL_TYPES = frozenset({"file", "design", "proto", "board", "slides", "dev", "make"})

# Pattern: /{type}/{file_key}[/branch/{branch_key}][/title][?node-id=...]
# file_key is always the segment after the type.
_PATH_RE = re.compile(
    r"^/(?P<type>" + "|".join(_URL_TYPES) + r")"
    r"/(?P<file_key>[A-Za-z0-9]+)"
    r"(?:/branch/(?P<branch_key>[A-Za-z0-9]+))?"
    r"(?:/[^?]*)?"  # optional title segment (ignored)
    r"$"
)


def _normalize_node_id(raw: str) -> str:
    """Convert a raw node-id value to canonical colon-separated format.

    Figma encodes node IDs as ``1-3`` in URLs (hyphen) and ``1%3A3``
    (percent-encoded colon). The canonical API format uses colons: ``1:3``.

    Args:
        raw: The raw node-id query parameter value.

    Returns:
        Node ID with colons as separators.
    """
    # First decode any percent-encoding (%3A → :)
    decoded = unquote(raw)
    # Then convert hyphens to colons (1-3 → 1:3)
    return decoded.replace("-", ":")


def parse_figma_url(url: str) -> dict[str, Optional[str]]:
    """Parse a Figma URL into its structural components.

    Supports 7 URL types:
      - ``/file/``   — classic file URL
      - ``/design/`` — new design URL
      - ``/proto/``  — prototype URL
      - ``/board/``  — FigJam board URL
      - ``/slides/`` — slides URL
      - ``/dev/``    — dev mode URL
      - ``/make/``   — make URL

    Branch URLs (``/design/{key}/branch/{branch_key}/...``) are also handled.

    Args:
        url: A full Figma URL string (must start with https://figma.com/...).

    Returns:
        A dict with keys:
          - ``file_key``: The Figma file key (always present).
          - ``node_id``: The node ID in colon format, or None.
          - ``type``: The URL type (e.g., "design", "file").
          - ``branch_key``: The branch key, or None.

    Raises:
        FigmaURLError: If the URL is not a valid Figma document URL.
    """
    if not url or not isinstance(url, str):
        raise FigmaURLError("URL must be a non-empty string")

    parsed = urlparse(url)

    # SEC-001: SSRF prevention — only allow figma.com hostnames.
    hostname = (parsed.hostname or "").lower()
    if hostname not in _ALLOWED_HOSTS:
        raise FigmaURLError(
            f"Invalid hostname '{hostname}'. Only figma.com URLs are accepted (SSRF prevention)."
        )

    if parsed.scheme not in ("https", "http"):
        raise FigmaURLError(
            f"Invalid scheme '{parsed.scheme}'. Only https URLs are accepted."
        )

    # Match the path against known URL patterns.
    match = _PATH_RE.match(parsed.path)
    if not match:
        raise FigmaURLError(
            f"Cannot parse Figma URL path: {parsed.path}. "
            f"Expected /<type>/<file_key>[/branch/<branch_key>][/title] "
            f"where type is one of: {', '.join(sorted(_URL_TYPES))}"
        )

    # Extract node-id from query parameters.
    # Figma uses ?node-id=... in the URL.
    node_id: Optional[str] = None
    if parsed.query:
        # Parse query manually to handle node-id specifically.
        for param in parsed.query.split("&"):
            if param.startswith("node-id="):
                raw_value = param[len("node-id="):]
                if raw_value:
                    node_id = _normalize_node_id(raw_value)
                break

    return {
        "file_key": match.group("file_key"),
        "node_id": node_id,
        "type": match.group("type"),
        "branch_key": match.group("branch_key"),
    }

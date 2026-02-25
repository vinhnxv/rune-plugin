"""Image fill detection and handling for Figma-to-React conversion.

Detects image fills in Figma nodes and generates appropriate React
elements (``<img>`` tags or inline SVG placeholders). Works with the
Figma Images API to resolve image export URLs.

Usage::

    from .image_handler import ImageHandler

    handler = ImageHandler(image_urls={"hash123": "https://..."})
    element = handler.generate_image_element(ir_node)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from node_parser import FigmaIRNode


# ---------------------------------------------------------------------------
# Image handler
# ---------------------------------------------------------------------------


class ImageHandler:
    """Handles image fill detection and element generation.

    Maintains a mapping of Figma image reference hashes to resolved
    URLs (from the Figma Images API). Generates appropriate React
    elements for image-containing nodes.

    Args:
        image_urls: Dict mapping image ref hashes to resolved URLs.
    """

    def __init__(self, image_urls: Optional[Dict[str, str]] = None) -> None:
        self._image_urls: Dict[str, str] = image_urls or {}

    def set_image_urls(self, urls: Dict[str, str]) -> None:
        """Update the image URL mapping.

        Args:
            urls: Dict mapping image ref hashes to resolved URLs.
        """
        self._image_urls.update(urls)

    def resolve_url(self, image_ref: str) -> str:
        """Resolve an image reference hash to a URL.

        Args:
            image_ref: Figma image reference hash.

        Returns:
            Resolved URL, or empty string if not found.
        """
        return self._image_urls.get(image_ref, "")

    def has_image(self, node: FigmaIRNode) -> bool:
        """Check if a node contains an image fill.

        Args:
            node: IR node to check.

        Returns:
            True if the node has an image fill or is an SVG candidate.
        """
        return node.has_image_fill or node.is_svg_candidate

    def generate_image_jsx(
        self,
        node: FigmaIRNode,
        classes: str = "",
    ) -> str:
        """Generate JSX for an image-containing node.

        For image fills, generates an ``<img>`` tag with resolved URL.
        For SVG candidates (boolean ops, icons), generates an inline
        SVG placeholder.

        Args:
            node: IR node with image content.
            classes: Tailwind class string for the element.

        Returns:
            JSX string for the image element.
        """
        class_attr = f' className="{classes}"' if classes else ""

        if node.is_svg_candidate:
            return self._generate_svg_placeholder(node, class_attr)

        if node.has_image_fill and node.image_ref:
            url = _sanitize_image_url(self.resolve_url(node.image_ref))
            if not url:
                return f'<div{class_attr} />'
            alt = _sanitize_alt_text(node.name)
            width = round(node.width) if node.width > 0 else ""
            height = round(node.height) if node.height > 0 else ""
            size_attrs = ""
            if width:
                size_attrs += f' width={{{width}}}'
            if height:
                size_attrs += f' height={{{height}}}'
            return (
                f'<img src="{url}" alt="{alt}"{class_attr}{size_attrs} />'
            )

        # Fallback: div with background image
        return f'<div{class_attr} />'

    @staticmethod
    def _generate_svg_placeholder(
        node: FigmaIRNode,
        class_attr: str,
    ) -> str:
        """Generate an inline SVG placeholder for vector nodes.

        Args:
            node: SVG candidate IR node.
            class_attr: Pre-formatted className attribute string.

        Returns:
            JSX string with SVG placeholder.
        """
        width = round(node.width) if node.width > 0 else 24
        height = round(node.height) if node.height > 0 else 24

        return (
            f"<svg{class_attr} "
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" '
            f'fill="none" xmlns="http://www.w3.org/2000/svg">\n'
            f"  {{/* TODO: SVG paths for {node.name} */}}\n"
            f"</svg>"
        )


def collect_image_refs(node: FigmaIRNode) -> List[str]:
    """Collect all image reference hashes from a node tree.

    Traverses the IR tree and extracts unique image reference hashes
    that need to be resolved via the Figma Images API.

    Args:
        node: Root IR node.

    Returns:
        List of unique image reference hash strings.
    """
    return list(dict.fromkeys(_collect_refs_recursive(node)))  # Deduplicate while preserving order


def _collect_refs_recursive(node: FigmaIRNode):
    """Recursively yield image refs from the tree.

    Args:
        node: Current IR node.

    Yields:
        Image reference hash strings found in the subtree.
    """
    if node.image_ref:
        yield node.image_ref
    for child in node.children:
        yield from _collect_refs_recursive(child)


def _sanitize_image_url(url: str) -> str:
    """Sanitize an image URL for safe use in JSX src attributes.

    Args:
        url: Raw URL string to sanitize.

    Returns:
        Sanitized URL, or "about:blank" if the URL is unsafe.
    """
    if not url:
        return ""
    # SEC-AUDIT-004: Restrict to HTTPS only — Figma API always returns HTTPS URLs.
    # Allowing http:// would create mixed content risk in deployed React apps.
    if not url.startswith("https://"):
        return "about:blank"
    return url.replace('"', "%22")


def _sanitize_alt_text(name: str) -> str:
    """Sanitize a Figma node name for use as alt text.

    Removes quotes and special characters that could break JSX attributes.

    Args:
        name: Raw Figma node name.

    Returns:
        Sanitized alt text string.
    """
    return name.replace('"', "").replace("'", "").replace("<", "").replace(">", "").strip()

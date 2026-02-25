"""React JSX code generation from Figma IR nodes.

Transforms a ``FigmaIRNode`` tree into React function components with
Tailwind CSS classes. Handles all node types, styled text segments,
image fills, and SVG candidates.

Usage::

    from .react_generator import generate_component

    jsx_code = generate_component(ir_node, image_urls={"hash": "url"})
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from figma_types import NodeType, TypeStyle
from image_handler import ImageHandler, collect_image_refs
from layout_resolver import resolve_child_layout, resolve_container_layout
from node_parser import FigmaIRNode
from style_builder import StyleBuilder
from tailwind_mapper import (
    TailwindMapper,
    map_font_size,
    map_font_weight,
    map_letter_spacing,
    map_line_height,
    map_text_align,
)


# ---------------------------------------------------------------------------
# Name sanitization
# ---------------------------------------------------------------------------

_COMPONENT_NAME_RE = re.compile(r"[^a-zA-Z0-9]")


def _to_component_name(name: str) -> str:
    """Convert a Figma node name to a valid React component name.

    Sanitizes the name to PascalCase and ensures it starts with an
    uppercase letter.

    Args:
        name: Raw Figma node name.

    Returns:
        Valid React component name (PascalCase).
    """
    # Split on non-alphanumeric chars, capitalize each part
    parts = _COMPONENT_NAME_RE.split(name)
    pascal = "".join(p.capitalize() for p in parts if p)
    if not pascal:
        return "Component"
    if pascal[0].isdigit():
        pascal = "Component" + pascal
    return pascal


# ---------------------------------------------------------------------------
# Style resolution
# ---------------------------------------------------------------------------

_mapper = TailwindMapper()


def _resolve_node_styles(node: FigmaIRNode) -> List[str]:
    """Build Tailwind classes for a node's visual styles.

    Uses StyleBuilder to extract CSS properties from fills, strokes,
    effects, etc., then maps them to Tailwind classes.

    Args:
        node: IR node to style.

    Returns:
        List of Tailwind utility classes.
    """
    sizing_h = node.layout_sizing_horizontal.value if node.layout_sizing_horizontal else None
    sizing_v = node.layout_sizing_vertical.value if node.layout_sizing_vertical else None

    props = (
        StyleBuilder()
        .fills(node.fills)
        .strokes(node.strokes, node.stroke_weight)
        .effects(node.effects)
        .corner_radius(node.corner_radius, node.corner_radii)
        .opacity(node.opacity)
        .size(node.width, node.height, sizing_h, sizing_v)
        .overflow_hidden(node.clips_content)
        .build()
    )

    return _mapper.map_properties(props)


def _resolve_text_styles(style: Optional[TypeStyle]) -> List[str]:
    """Build Tailwind classes for text typography.

    Args:
        style: TypeStyle from the text node.

    Returns:
        List of Tailwind typography classes.
    """
    if style is None:
        return []

    classes: List[str] = []

    if style.font_size is not None:
        classes.append(map_font_size(style.font_size))

    if style.font_weight is not None:
        classes.append(map_font_weight(style.font_weight))

    if style.letter_spacing is not None and style.letter_spacing != 0:
        classes.append(map_letter_spacing(style.letter_spacing))

    if style.line_height_px is not None and style.font_size:
        classes.append(map_line_height(style.line_height_px, style.font_size))

    if style.text_align_horizontal is not None:
        align = map_text_align(style.text_align_horizontal.value)
        if align:
            classes.append(align)

    if style.italic:
        classes.append("italic")

    if style.text_decoration == "UNDERLINE":
        classes.append("underline")
    elif style.text_decoration == "STRIKETHROUGH":
        classes.append("line-through")

    # Text color from fills
    if style.fills:
        from .tailwind_mapper import snap_color
        from .style_builder import _color_to_css
        visible = [f for f in style.fills if f.visible]
        if visible and visible[0].color:
            css_color = _color_to_css(visible[0].color)
            classes.append(snap_color(css_color, "text"))

    return classes


# ---------------------------------------------------------------------------
# JSX generation
# ---------------------------------------------------------------------------


def _indent(text: str, level: int) -> str:
    """Indent text by the given level (2 spaces per level).

    Args:
        text: Text to indent.
        level: Indentation level.

    Returns:
        Indented text.
    """
    prefix = "  " * level
    return "\n".join(prefix + line if line.strip() else "" for line in text.split("\n"))


def _generate_text_jsx(
    node: FigmaIRNode,
    classes: str,
    indent_level: int,
) -> str:
    """Generate JSX for a text node.

    Handles both simple text (single style) and rich text
    (multiple styled segments using <span> wrappers).

    Args:
        node: Text IR node.
        classes: Tailwind class string.
        indent_level: Current indentation level.

    Returns:
        JSX string for the text element.
    """
    class_attr = f' className="{classes}"' if classes else ""

    # Simple text (no segments or single segment)
    if len(node.text_segments) <= 1:
        text = _escape_jsx(node.text_content or "")
        return f"<p{class_attr}>{text}</p>"

    # Rich text with styled segments
    lines: List[str] = [f"<p{class_attr}>"]
    for segment in node.text_segments:
        seg_classes = _resolve_text_styles(segment.style)
        text = _escape_jsx(segment.text)
        if seg_classes:
            seg_class_str = " ".join(seg_classes)
            lines.append(f'  <span className="{seg_class_str}">{text}</span>')
        else:
            lines.append(f"  {text}")
    lines.append("</p>")
    return "\n".join(lines)


def _generate_node_jsx(
    node: FigmaIRNode,
    parent: Optional[FigmaIRNode],
    image_handler: ImageHandler,
    indent_level: int = 0,
) -> str:
    """Recursively generate JSX for an IR node and its children.

    Args:
        node: Current IR node.
        parent: Parent IR node (for child layout resolution).
        image_handler: Image handler for resolving image fills.
        indent_level: Current indentation level.

    Returns:
        JSX string for the node subtree.
    """
    if not node.visible:
        return ""

    # Collect all classes
    all_classes: List[str] = []

    # Layout classes (container)
    layout = resolve_container_layout(node)
    all_classes.extend(layout.container)

    # Child layout classes (how this node behaves in parent's layout)
    if parent is not None:
        child_classes = resolve_child_layout(node, parent)
        all_classes.extend(child_classes)

    # Visual style classes
    style_classes = _resolve_node_styles(node)
    all_classes.extend(style_classes)

    class_str = " ".join(all_classes)

    # Image/SVG handling
    if image_handler.has_image(node):
        return image_handler.generate_image_jsx(node, class_str)

    # Text node
    if node.node_type == NodeType.TEXT:
        text_classes = _resolve_text_styles(node.text_style)
        full_classes = " ".join(all_classes + text_classes)
        return _generate_text_jsx(node, full_classes, indent_level)

    # Container/element node
    class_attr = f' className="{class_str}"' if class_str else ""

    if not node.children:
        return f"<div{class_attr} />"

    # Generate children
    child_jsxs: List[str] = []
    for child in node.children:
        child_jsx = _generate_node_jsx(child, node, image_handler, indent_level + 1)
        if child_jsx:
            child_jsxs.append(child_jsx)

    if not child_jsxs:
        return f"<div{class_attr} />"

    children_str = "\n".join(f"  {jsx}" for jsx in child_jsxs)
    return f"<div{class_attr}>\n{children_str}\n</div>"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_component(
    root: FigmaIRNode,
    component_name: Optional[str] = None,
    image_urls: Optional[Dict[str, str]] = None,
) -> str:
    """Generate a complete React function component from an IR node tree.

    Produces a self-contained React component with:
    - Import statement for React
    - Function component with proper name
    - JSX body with Tailwind classes
    - Export default

    Args:
        root: Root IR node (typically a FRAME or COMPONENT).
        component_name: Override component name. If None, derived from
            the root node's name.
        image_urls: Dict mapping image ref hashes to resolved URLs.

    Returns:
        Complete React component source code as a string.
    """
    name = component_name or _to_component_name(root.name)
    image_handler = ImageHandler(image_urls)

    # Collect image refs that need resolution
    refs = collect_image_refs(root)

    # Generate JSX body
    jsx = _generate_node_jsx(root, None, image_handler, indent_level=1)

    # Build component
    lines: List[str] = []
    lines.append("import React from 'react';")
    lines.append("")
    lines.append(f"export default function {name}() {{")
    lines.append("  return (")
    lines.append(_indent(jsx, 2))
    lines.append("  );")
    lines.append("}")
    lines.append("")

    # Add TODO comments for unresolved images
    unresolved = [ref for ref in refs if ref not in (image_urls or {})]
    if unresolved:
        lines.append("// TODO: Resolve image references via Figma Images API:")
        for ref in unresolved:
            lines.append(f"//   - {ref}")
        lines.append("")

    return "\n".join(lines)


def generate_component_with_props(
    root: FigmaIRNode,
    component_name: Optional[str] = None,
    prop_names: Optional[List[str]] = None,
    image_urls: Optional[Dict[str, str]] = None,
) -> str:
    """Generate a React component with typed props interface.

    Similar to ``generate_component`` but includes a TypeScript-style
    props interface and passes props to the component function.

    Args:
        root: Root IR node.
        component_name: Override component name.
        prop_names: List of prop names to include in the interface.
        image_urls: Dict mapping image ref hashes to resolved URLs.

    Returns:
        React component source code with props interface.
    """
    name = component_name or _to_component_name(root.name)
    image_handler = ImageHandler(image_urls)
    props = prop_names or []

    jsx = _generate_node_jsx(root, None, image_handler, indent_level=1)

    lines: List[str] = []
    lines.append("import React from 'react';")
    lines.append("")

    if props:
        lines.append(f"interface {name}Props {{")
        for prop in props:
            lines.append(f"  {prop}?: string;")
        lines.append("}")
        lines.append("")
        prop_destructure = ", ".join(props)
        lines.append(
            f"export default function {name}({{ {prop_destructure} }}: {name}Props) {{"
        )
    else:
        lines.append(f"export default function {name}() {{")

    lines.append("  return (")
    lines.append(_indent(jsx, 2))
    lines.append("  );")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSX helpers
# ---------------------------------------------------------------------------


def _escape_jsx(text: str) -> str:
    """Escape text for safe inclusion in JSX.

    Handles curly braces and angle brackets that have special
    meaning in JSX.

    Args:
        text: Raw text content.

    Returns:
        JSX-safe text string.
    """
    text = text.replace("{", "&#123;")
    text = text.replace("}", "&#125;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

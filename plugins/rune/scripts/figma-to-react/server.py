"""
Figma-to-React MCP Server

A Model Context Protocol (MCP) stdio server that fetches Figma designs
and converts them into structured data for React component generation.

Provides 4 tools:
  - figma_fetch_design:     Fetch and parse a Figma design into IR tree
  - figma_inspect_node:     Inspect detailed properties of a specific node
  - figma_list_components:  List all components/instances in a file
  - figma_to_react:         Convert a Figma design to React + Tailwind CSS code

Environment variables:
  FIGMA_TOKEN              - Figma Personal Access Token (required)
  FIGMA_FILE_CACHE_TTL     - Cache TTL for file data in seconds (default: 1800)
  FIGMA_IMAGE_CACHE_TTL    - Cache TTL for image URLs in seconds (default: 86400)

Usage:
  # As MCP stdio server (normal mode via start.sh):
  python3 server.py
"""

import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from figma_client import FigmaAPIError, FigmaClient  # noqa: E402
from figma_types import FigmaFileResponse, FigmaNodesResponse, NodeType  # noqa: E402
from image_handler import ImageHandler, collect_image_refs  # noqa: E402
from layout_resolver import resolve_child_layout, resolve_container_layout  # noqa: E402
from node_parser import FigmaIRNode, count_nodes, parse_node, walk_tree  # noqa: E402
from react_generator import generate_component  # noqa: E402
from style_builder import StyleBuilder  # noqa: E402
from tailwind_mapper import TailwindMapper  # noqa: E402
from url_parser import FigmaURLError, parse_figma_url  # noqa: E402

# ---------------------------------------------------------------------------
# Logging — NEVER print to stdout (corrupts JSON-RPC protocol)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("figma-to-react")


# ---------------------------------------------------------------------------
# Pagination defaults
# ---------------------------------------------------------------------------

_DEFAULT_MAX_LENGTH = 50_000  # characters
_DEFAULT_START_INDEX = 0


# ---------------------------------------------------------------------------
# Lifespan — shared FigmaClient
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage the shared FigmaClient lifecycle.

    Creates a single httpx.AsyncClient on startup and closes it on
    shutdown. The client is available to all tools via ``ctx.request_context``.

    Args:
        server: The FastMCP server instance.

    Yields:
        Dict containing the shared FigmaClient under key ``figma_client``.
    """
    client = FigmaClient()
    try:
        yield {"figma_client": client}
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "figma-to-react",
    lifespan=_lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client(ctx: Any) -> FigmaClient:
    """Extract the shared FigmaClient from the MCP context.

    Args:
        ctx: The MCP tool context object.

    Returns:
        The shared FigmaClient instance.

    Raises:
        ToolError: If the client is not available in context.
    """
    try:
        return ctx.request_context["figma_client"]
    except (AttributeError, KeyError, TypeError) as exc:
        raise ToolError(
            "Internal error: FigmaClient not available in server context."
        ) from exc


def _ir_to_dict(node: FigmaIRNode, max_depth: int = 20) -> dict[str, Any]:
    """Convert an IR node tree to a JSON-serializable dict.

    Recursively serializes the IR tree, omitting None values and
    the raw Figma data to keep output compact.

    Args:
        node: Root IR node to serialize.
        max_depth: Maximum recursion depth to prevent runaway serialization.

    Returns:
        Dict representation of the IR tree.
    """
    if max_depth <= 0:
        return {"node_id": node.node_id, "name": node.name, "truncated": True}

    result: dict[str, Any] = {
        "node_id": node.node_id,
        "name": node.name,
        "type": node.node_type.value,
        "unique_name": node.unique_name,
    }

    # Geometry
    if node.width or node.height:
        result["width"] = round(node.width, 1)
        result["height"] = round(node.height, 1)

    # Visibility
    if not node.visible:
        result["visible"] = False
    if node.opacity < 1.0:
        result["opacity"] = round(node.opacity, 3)

    # Flags
    for flag_name in (
        "is_frame_like", "is_svg_candidate", "is_icon_candidate",
        "is_absolute_positioned", "has_auto_layout", "has_image_fill",
    ):
        val = getattr(node, flag_name, False)
        if val:
            result[flag_name] = True

    # Auto-layout
    if node.has_auto_layout:
        result["layout_mode"] = node.layout_mode.value
        if node.item_spacing:
            result["item_spacing"] = node.item_spacing
        if node.primary_axis_align:
            result["primary_axis_align"] = node.primary_axis_align.value
        if node.counter_axis_align:
            result["counter_axis_align"] = node.counter_axis_align.value
        if any(p > 0 for p in node.padding):
            result["padding"] = node.padding

    # Sizing
    if node.layout_sizing_horizontal:
        result["layout_sizing_horizontal"] = node.layout_sizing_horizontal.value
    if node.layout_sizing_vertical:
        result["layout_sizing_vertical"] = node.layout_sizing_vertical.value

    # Corner radius
    if node.corner_radius:
        result["corner_radius"] = node.corner_radius
    if node.corner_radii:
        result["corner_radii"] = node.corner_radii

    # Text
    if node.text_content is not None:
        result["text_content"] = node.text_content
        if node.text_style and node.text_style.font_family:
            result["font_family"] = node.text_style.font_family
            if node.text_style.font_size:
                result["font_size"] = node.text_style.font_size

    # Component
    if node.component_id:
        result["component_id"] = node.component_id

    # Image
    if node.image_ref:
        result["image_ref"] = node.image_ref

    # Children
    if node.children:
        result["children"] = [
            _ir_to_dict(child, max_depth - 1) for child in node.children
        ]

    return result


def _paginate_output(
    content: str,
    *,
    max_length: int = _DEFAULT_MAX_LENGTH,
    start_index: int = _DEFAULT_START_INDEX,
) -> dict[str, Any]:
    """Apply pagination to large output strings.

    Args:
        content: The full output string.
        max_length: Maximum characters to return.
        start_index: Character offset to start from.

    Returns:
        Dict with paginated content and metadata.
    """
    total_length = len(content)
    end_index = min(start_index + max_length, total_length)
    chunk = content[start_index:end_index]

    result: dict[str, Any] = {"content": chunk}
    if total_length > max_length:
        result["total_length"] = total_length
        result["start_index"] = start_index
        result["end_index"] = end_index
        if end_index < total_length:
            result["has_more"] = True
            result["next_start_index"] = end_index

    return result


def _handle_figma_error(exc: FigmaAPIError) -> ToolError:
    """Convert a FigmaAPIError into a ToolError for MCP response.

    Args:
        exc: The Figma API exception.

    Returns:
        A ToolError with an actionable user-facing message.
    """
    return ToolError(str(exc))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def figma_fetch_design(
    url: str,
    ctx: Any,
    depth: int = 2,
    max_length: int = _DEFAULT_MAX_LENGTH,
    start_index: int = _DEFAULT_START_INDEX,
) -> str:
    """Fetch a Figma design and return its parsed node tree.

    Parses the Figma URL, fetches the file (with depth-limited traversal),
    converts the node tree to an intermediate representation (IR), and
    returns a JSON-serialized IR tree. If a node-id is in the URL, only
    that subtree is returned.

    Large responses are paginated — use start_index to retrieve subsequent
    chunks.

    Args:
        url: Full Figma URL (e.g., https://www.figma.com/design/abc123/Title).
        ctx: MCP tool context (injected by FastMCP).
        depth: Figma API traversal depth (default 2).
        max_length: Max response characters (default 50000).
        start_index: Pagination offset (default 0).

    Returns:
        JSON string with the parsed IR tree and pagination metadata.
    """
    # Parse URL
    try:
        parsed = parse_figma_url(url)
    except FigmaURLError as exc:
        raise ToolError(str(exc)) from exc

    file_key = parsed["file_key"]
    node_id = parsed["node_id"]
    branch_key = parsed["branch_key"]

    client = _get_client(ctx)

    try:
        if node_id:
            # Fetch specific node subtree
            response_data = await client.get_nodes(
                file_key, [node_id], branch_key=branch_key
            )
            nodes_resp = FigmaNodesResponse.model_validate(response_data)
            node_data = nodes_resp.nodes.get(node_id)
            if node_data is None or node_data.document is None:
                raise ToolError(
                    f"Node '{node_id}' not found in file '{file_key}'. "
                    f"Verify the node ID is correct."
                )
            raw_doc = node_data.document.model_dump(by_alias=True)
        else:
            # Fetch entire file (depth-limited)
            response_data = await client.get_file(
                file_key, depth=depth, branch_key=branch_key
            )
            file_resp = FigmaFileResponse.model_validate(response_data)
            if file_resp.document is None:
                raise ToolError(
                    f"File '{file_key}' returned no document. "
                    f"The file may be empty or access may be restricted."
                )
            raw_doc = file_resp.document.model_dump(by_alias=True)

        # Parse to IR
        ir_root = parse_node(raw_doc)
        if ir_root is None:
            raise ToolError("Failed to parse design — no supported nodes found.")

        # Serialize
        tree_dict = _ir_to_dict(ir_root)
        output = {
            "file_key": file_key,
            "node_count": count_nodes(ir_root),
            "tree": tree_dict,
        }
        content = json.dumps(output, indent=2)
        paginated = _paginate_output(
            content, max_length=max_length, start_index=start_index
        )
        return json.dumps(paginated)

    except FigmaAPIError as exc:
        raise _handle_figma_error(exc) from exc


@mcp.tool()
async def figma_inspect_node(
    url: str,
    ctx: Any,
) -> str:
    """Inspect detailed properties of a specific Figma node.

    Requires a Figma URL with a node-id query parameter. Returns
    detailed IR properties including auto-layout, styling, text content,
    and component references.

    Args:
        url: Figma URL with ?node-id=... (e.g., https://www.figma.com/design/abc/Title?node-id=1-3).
        ctx: MCP tool context (injected by FastMCP).

    Returns:
        JSON string with detailed node properties.
    """
    try:
        parsed = parse_figma_url(url)
    except FigmaURLError as exc:
        raise ToolError(str(exc)) from exc

    node_id = parsed["node_id"]
    if not node_id:
        raise ToolError(
            "URL must include a node-id query parameter "
            "(e.g., ?node-id=1-3). Use figma_list_components to find node IDs."
        )

    file_key = parsed["file_key"]
    branch_key = parsed["branch_key"]
    client = _get_client(ctx)

    try:
        response_data = await client.get_nodes(
            file_key, [node_id], branch_key=branch_key
        )
        nodes_resp = FigmaNodesResponse.model_validate(response_data)
        node_data = nodes_resp.nodes.get(node_id)
        if node_data is None or node_data.document is None:
            raise ToolError(
                f"Node '{node_id}' not found in file '{file_key}'."
            )

        raw_doc = node_data.document.model_dump(by_alias=True)
        ir_node = parse_node(raw_doc)
        if ir_node is None:
            raise ToolError(
                f"Node '{node_id}' has an unsupported type and cannot be inspected."
            )

        # Build detailed output
        detail = _ir_to_dict(ir_node, max_depth=3)

        # Add fills/strokes/effects detail
        if ir_node.fills:
            detail["fills"] = [
                {
                    "type": f.type.value,
                    "visible": f.visible,
                    "opacity": f.opacity,
                    "color": f.color.to_hex() if f.color else None,
                    "image_ref": f.image_ref,
                }
                for f in ir_node.fills
            ]
        if ir_node.strokes:
            detail["strokes"] = [
                {
                    "type": s.type.value,
                    "color": s.color.to_hex() if s.color else None,
                    "weight": ir_node.stroke_weight,
                }
                for s in ir_node.strokes
            ]
        if ir_node.effects:
            detail["effects"] = [
                {
                    "type": e.type.value,
                    "radius": e.radius,
                    "color": e.color.to_hex() if e.color else None,
                    "offset": {"x": e.offset.x, "y": e.offset.y} if e.offset else None,
                    "spread": e.spread,
                }
                for e in ir_node.effects
            ]

        return json.dumps(detail, indent=2)

    except FigmaAPIError as exc:
        raise _handle_figma_error(exc) from exc


@mcp.tool()
async def figma_list_components(
    url: str,
    ctx: Any,
) -> str:
    """List all components and component instances in a Figma file.

    Fetches the file with depth=2, then walks the tree to find
    COMPONENT, COMPONENT_SET, and INSTANCE nodes. Detects duplicate
    instances pointing to the same component ID.

    Args:
        url: Figma file URL (node-id optional; if provided, scopes to subtree).
        ctx: MCP tool context (injected by FastMCP).

    Returns:
        JSON string with component inventory including duplicates.
    """
    try:
        parsed = parse_figma_url(url)
    except FigmaURLError as exc:
        raise ToolError(str(exc)) from exc

    file_key = parsed["file_key"]
    node_id = parsed["node_id"]
    branch_key = parsed["branch_key"]
    client = _get_client(ctx)

    try:
        if node_id:
            response_data = await client.get_nodes(
                file_key, [node_id], branch_key=branch_key
            )
            nodes_resp = FigmaNodesResponse.model_validate(response_data)
            node_data = nodes_resp.nodes.get(node_id)
            if node_data is None or node_data.document is None:
                raise ToolError(f"Node '{node_id}' not found in file '{file_key}'.")
            raw_doc = node_data.document.model_dump(by_alias=True)
        else:
            response_data = await client.get_file(
                file_key, depth=2, branch_key=branch_key
            )
            file_resp = FigmaFileResponse.model_validate(response_data)
            if file_resp.document is None:
                raise ToolError(f"File '{file_key}' returned no document.")
            raw_doc = file_resp.document.model_dump(by_alias=True)

        ir_root = parse_node(raw_doc)
        if ir_root is None:
            raise ToolError("No supported nodes found in the design.")

        # Walk tree and collect components/instances
        all_nodes = walk_tree(ir_root)

        components: list[dict[str, Any]] = []
        instances: list[dict[str, Any]] = []
        instance_by_component: dict[str, list[str]] = {}

        for n in all_nodes:
            entry = {
                "node_id": n.node_id,
                "name": n.name,
                "type": n.node_type.value,
            }
            if n.width or n.height:
                entry["size"] = f"{round(n.width)}x{round(n.height)}"

            if n.node_type.value in ("COMPONENT", "COMPONENT_SET"):
                components.append(entry)
            elif n.node_type.value == "INSTANCE":
                if n.component_id:
                    entry["component_id"] = n.component_id
                    instance_by_component.setdefault(n.component_id, []).append(
                        n.node_id
                    )
                instances.append(entry)

        # Detect duplicate instances (same COMPONENT ID used multiple times)
        duplicates: list[dict[str, Any]] = []
        for comp_id, inst_ids in instance_by_component.items():
            if len(inst_ids) > 1:
                duplicates.append({
                    "component_id": comp_id,
                    "instance_count": len(inst_ids),
                    "instance_node_ids": inst_ids,
                })

        output = {
            "file_key": file_key,
            "total_components": len(components),
            "total_instances": len(instances),
            "components": components,
            "instances": instances,
        }
        if duplicates:
            output["duplicate_instances"] = duplicates

        return json.dumps(output, indent=2)

    except FigmaAPIError as exc:
        raise _handle_figma_error(exc) from exc


@mcp.tool()
async def figma_to_react(
    url: str,
    ctx: Any,
    component_name: str = "",
    use_tailwind: bool = True,
    extract_components: bool = False,
    max_length: int = _DEFAULT_MAX_LENGTH,
    start_index: int = _DEFAULT_START_INDEX,
) -> str:
    """Convert a Figma design to React + Tailwind CSS code.

    End-to-end pipeline: URL parsing -> Figma API fetch -> node parsing ->
    style extraction -> layout resolution -> React JSX generation.

    If extract_components is True, detects repeated INSTANCE nodes pointing
    to the same COMPONENT ID and generates separate components for them.

    Args:
        url: Full Figma URL (must include node-id for specific component).
        ctx: MCP tool context (injected by FastMCP).
        component_name: Override the React component name. If empty,
            auto-detected from the Figma node name.
        use_tailwind: Generate Tailwind CSS classes (default True).
        extract_components: Extract repeated instances as separate components.
        max_length: Max response characters (default 50000).
        start_index: Pagination offset (default 0).

    Returns:
        JSON string with generated React code and metadata.
    """
    # Parse URL
    try:
        parsed = parse_figma_url(url)
    except FigmaURLError as exc:
        raise ToolError(str(exc)) from exc

    file_key = parsed["file_key"]
    node_id = parsed["node_id"]
    branch_key = parsed["branch_key"]

    client = _get_client(ctx)

    try:
        # Fetch design data
        if node_id:
            response_data = await client.get_nodes(
                file_key, [node_id], branch_key=branch_key
            )
            nodes_resp = FigmaNodesResponse.model_validate(response_data)
            node_data = nodes_resp.nodes.get(node_id)
            if node_data is None or node_data.document is None:
                raise ToolError(
                    f"Node '{node_id}' not found in file '{file_key}'. "
                    f"Verify the node ID is correct."
                )
            raw_doc = node_data.document.model_dump(by_alias=True)
        else:
            response_data = await client.get_file(
                file_key, depth=3, branch_key=branch_key
            )
            file_resp = FigmaFileResponse.model_validate(response_data)
            if file_resp.document is None:
                raise ToolError(
                    f"File '{file_key}' returned no document. "
                    f"Provide a node-id URL for better results."
                )
            raw_doc = file_resp.document.model_dump(by_alias=True)

        # Parse to IR
        ir_root = parse_node(raw_doc)
        if ir_root is None:
            raise ToolError("Failed to parse design — no supported nodes found.")

        # Collect image refs for resolution
        image_refs = collect_image_refs(ir_root)
        image_urls: dict[str, str] = {}

        if image_refs:
            try:
                image_response = await client.get_images(
                    file_key,
                    [ref for ref in image_refs],
                    branch_key=branch_key,
                )
                image_urls = image_response.get("images", {})
            except FigmaAPIError:
                logger.warning("Failed to resolve image URLs — using placeholders")

        # Generate main component
        name = component_name if component_name else None
        main_code = generate_component(
            ir_root,
            component_name=name,
            image_urls=image_urls,
        )

        output: dict[str, Any] = {
            "file_key": file_key,
            "node_count": count_nodes(ir_root),
            "main_component": main_code,
        }

        # Extract sub-components from repeated instances
        if extract_components:
            sub_components = _extract_sub_components(
                ir_root, image_urls
            )
            if sub_components:
                output["extracted_components"] = sub_components

        # Unresolved images info
        unresolved = [ref for ref in image_refs if ref not in image_urls]
        if unresolved:
            output["unresolved_images"] = unresolved

        content = json.dumps(output, indent=2)
        paginated = _paginate_output(
            content, max_length=max_length, start_index=start_index
        )
        return json.dumps(paginated)

    except FigmaAPIError as exc:
        raise _handle_figma_error(exc) from exc


def _extract_sub_components(
    root: FigmaIRNode,
    image_urls: dict[str, str],
) -> list[dict[str, str]]:
    """Extract repeated component instances as separate React components.

    Detects INSTANCE nodes that share the same component_id (indicating
    they are instances of the same Figma Component). Generates a separate
    React component for each unique component definition.

    Args:
        root: Root IR node tree.
        image_urls: Resolved image URL mapping.

    Returns:
        List of dicts with component_id, name, and code for each
        extracted component.
    """
    all_nodes = walk_tree(root)

    # Group instances by component ID
    instance_groups: dict[str, list[FigmaIRNode]] = {}
    for node in all_nodes:
        if node.node_type == NodeType.INSTANCE and node.component_id:
            instance_groups.setdefault(node.component_id, []).append(node)

    # Only extract components that appear more than once
    sub_components: list[dict[str, str]] = []
    for comp_id, instances in instance_groups.items():
        if len(instances) < 2:
            continue

        # Use the first instance as the template
        template = instances[0]
        code = generate_component(
            template,
            image_urls=image_urls,
        )
        sub_components.append({
            "component_id": comp_id,
            "name": template.name,
            "instance_count": str(len(instances)),
            "code": code,
        })

    return sub_components


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()

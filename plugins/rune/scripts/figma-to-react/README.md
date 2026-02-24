# Figma-to-React MCP Server

An MCP (Model Context Protocol) stdio server that fetches Figma designs and converts them to React + Tailwind CSS components.

## Features

- **4 MCP tools** for Figma design inspection and code generation
- **SSRF protection** — only accepts figma.com URLs (SEC-001)
- **Two-tier response caching** — file data (30min) and image URLs (24hr)
- **Rate-limit awareness** — parses Retry-After, X-Figma-Rate-Limit-Type, X-Figma-Plan-Tier headers
- **Pagination** — large responses split into chunks via max_length + start_index
- **Component extraction** — detects repeated INSTANCE nodes pointing to the same COMPONENT ID
- **Tailwind v4 support** — maps Figma styles to Tailwind utility classes
- **Auto-layout to Flexbox/Grid** — converts Figma auto-layout v5 to CSS flexbox and grid

## Prerequisites

- **Python 3.10+**
- **Figma Personal Access Token (PAT)** with `file_content:read` scope
  - Generate at: https://www.figma.com/developers/api#access-tokens
  - PATs expire after **90 days** — set a calendar reminder to rotate

## Setup

### 1. Set your Figma token

```bash
export FIGMA_TOKEN="figd_your_personal_access_token_here"
```

Add to your shell profile (`~/.zshrc`, `~/.bashrc`) for persistence.

### 2. Enable the MCP server

The server is auto-configured via `.mcp.json` when the Rune plugin is installed. No manual setup needed.

For standalone testing:

```bash
cd plugins/rune/scripts/figma-to-react
python3 -m pip install -r requirements.txt
python3 server.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FIGMA_TOKEN` | (required) | Figma Personal Access Token |
| `FIGMA_FILE_CACHE_TTL` | `1800` (30min) | Cache TTL for file/node API responses (seconds) |
| `FIGMA_IMAGE_CACHE_TTL` | `86400` (24hr) | Cache TTL for image export URLs (seconds) |

### Cache Behavior

The server uses an in-memory two-tier cache:

- **File/node data** — shorter TTL (30min default) because designs change frequently during active work
- **Image export URLs** — longer TTL (24hr default) because Figma image URLs are expensive to generate and remain valid for extended periods

Set cache TTLs to `0` to disable caching entirely.

## MCP Tools Reference

### `figma_fetch_design`

Fetch a Figma design and return its parsed node tree as an intermediate representation (IR).

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | (required) | Full Figma URL |
| `depth` | int | `2` | Figma API traversal depth |
| `max_length` | int | `50000` | Max response characters |
| `start_index` | int | `0` | Pagination offset |

**Example:**

```
figma_fetch_design(url="https://www.figma.com/design/abc123/MyDesign")
```

Returns JSON with `file_key`, `node_count`, and `tree` (the IR node tree).

To fetch a specific node (subtree only):

```
figma_fetch_design(url="https://www.figma.com/design/abc123/MyDesign?node-id=1-3")
```

### `figma_inspect_node`

Inspect detailed properties of a specific Figma node — fills, strokes, effects, auto-layout, text content, and component references.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | (required) | Figma URL with `?node-id=...` |

**Example:**

```
figma_inspect_node(url="https://www.figma.com/design/abc123/MyDesign?node-id=1-3")
```

Returns JSON with detailed node properties including fill colors (hex), stroke weights, effect radii, and typography.

### `figma_list_components`

List all components and component instances in a Figma file. Detects duplicate instances pointing to the same component ID.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | (required) | Figma file URL (node-id optional to scope to subtree) |

**Example:**

```
figma_list_components(url="https://www.figma.com/design/abc123/MyDesign")
```

Returns JSON with `components`, `instances`, and `duplicate_instances` (instances sharing the same component ID).

### `figma_to_react`

Convert a Figma design to React + Tailwind CSS code. This is the main code generation tool.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | (required) | Figma URL (node-id recommended) |
| `component_name` | string | `""` | Override React component name (auto-detected from node name if empty) |
| `use_tailwind` | bool | `true` | Generate Tailwind CSS classes |
| `extract_components` | bool | `false` | Extract repeated instances as separate components |
| `max_length` | int | `50000` | Max response characters |
| `start_index` | int | `0` | Pagination offset |

**Example — single component:**

```
figma_to_react(
    url="https://www.figma.com/design/abc123/MyDesign?node-id=1-3",
    component_name="LoginCard"
)
```

**Example — with component extraction:**

```
figma_to_react(
    url="https://www.figma.com/design/abc123/MyDesign?node-id=1-3",
    extract_components=true
)
```

Returns JSON with `main_component` (the generated React code) and optionally `extracted_components` (sub-components from repeated instances).

## Example Workflows

### Inspect first, then generate

1. List components to find the right node:
   ```
   figma_list_components(url="https://www.figma.com/design/abc123/MyDesign")
   ```

2. Inspect the target node for details:
   ```
   figma_inspect_node(url="https://www.figma.com/design/abc123/MyDesign?node-id=12-34")
   ```

3. Generate React code:
   ```
   figma_to_react(url="https://www.figma.com/design/abc123/MyDesign?node-id=12-34")
   ```

### Large design with pagination

For designs exceeding the response limit, use pagination:

```
# First chunk
figma_to_react(url="...", max_length=50000, start_index=0)
# Response includes: has_more=true, next_start_index=50000

# Next chunk
figma_to_react(url="...", max_length=50000, start_index=50000)
```

## Troubleshooting

### "FIGMA_TOKEN environment variable is not set"

Set the `FIGMA_TOKEN` env var to your Figma Personal Access Token:

```bash
export FIGMA_TOKEN="figd_..."
```

### "Access denied (403)"

Your token is invalid, expired, or lacks access to the file.

- PATs expire after **90 days** — regenerate at https://www.figma.com/developers/api#access-tokens
- Ensure the token has `file_content:read` scope
- Verify you have access to the file (not just the team/organization)

### "Rate limit exceeded (429)"

Figma enforces per-user rate limits. The error message includes:

- **Retry-After**: Seconds to wait before retrying
- **X-Figma-Rate-Limit-Type**: Which limit was hit (e.g., per-minute, per-hour)
- **X-Figma-Plan-Tier**: Your Figma plan tier

**Important: View/Collab seats are limited to approximately 6 API requests per month.** If you see a plan tier in the error, you likely need a higher-tier Figma plan (Editor or Full seat) for regular API usage.

### "File or node not found (404)"

- Verify the file key in the URL is correct
- Check that the file has not been deleted or moved
- If using a node-id, ensure it exists in the file (use `figma_list_components` to verify)

### "Bad request (400)"

- Node IDs must be in colon-separated format (e.g., `1:3`, not `1-3`). The URL parser handles this conversion automatically, but if calling the Figma API directly, use colons.

### "Request timed out"

The default timeout is 30 seconds. Large files with many nodes may take longer. Consider:

- Using `depth=1` in `figma_fetch_design` for an overview first
- Fetching specific nodes with `?node-id=...` instead of entire files

## Known Limitations

- **Cross-file components**: Components referenced across different Figma files are not resolved. The generated code will include a placeholder comment.
- **View/Collab seat rate limits**: Figma View and Collab seats are limited to ~6 API requests/month. Editor seats have much higher limits.
- **Complex gradients**: Angular and diamond gradients are approximated as linear gradients in CSS.
- **Boolean operations**: Complex boolean operations (union, intersect, subtract, exclude) are rendered as SVG candidates rather than CSS.
- **Font availability**: Generated code references Figma font family names. Ensure fonts are available in your project or map to web-safe alternatives.
- **Absolute positioning**: Nodes with `layoutPositioning: "ABSOLUTE"` use fixed px values. Responsive adaptations may be needed.

## Architecture

```
server.py              FastMCP server + 4 tools + lifespan context
url_parser.py          URL parsing + SSRF validation (SEC-001)
figma_client.py        Async httpx client + two-tier cache + rate-limit handling
figma_types.py         Pydantic v2 models for Figma API responses (12 node types)
node_parser.py         Raw API -> IR tree (FigmaIRNode) with normalization
style_builder.py       IR node -> CSS properties extraction
tailwind_mapper.py     CSS properties -> Tailwind v4 utility classes
layout_resolver.py     Auto-layout v5 -> flexbox/grid CSS resolution
react_generator.py     IR tree -> React JSX + Tailwind classes
image_handler.py       Image fill detection + export URL resolution
```

### Data Flow

```
Figma URL
  -> url_parser (parse + validate)
  -> figma_client (fetch with caching)
  -> figma_types (Pydantic validation)
  -> node_parser (IR tree)
  -> style_builder + tailwind_mapper + layout_resolver
  -> react_generator (JSX output)
  -> image_handler (resolve image URLs)
```

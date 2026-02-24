# Figma-to-React Workflow

How to use the figma-to-react MCP tools in the Rune workflow.

## Prerequisites

1. Set `FIGMA_TOKEN` in your environment
2. Have a Figma file URL ready (from the browser address bar)

## Workflow Steps

### 1. Discovery: List Components

Start by listing what's in the Figma file:

```
figma_list_components(url="https://www.figma.com/design/abc123/MyApp")
```

This returns all COMPONENT, COMPONENT_SET, and INSTANCE nodes with their IDs.
Use this to find specific node IDs for targeted generation.

### 2. Inspection: Understand a Node

Before generating code, inspect the target node to understand its structure:

```
figma_inspect_node(url="https://www.figma.com/design/abc123/MyApp?node-id=1-3")
```

This shows detailed properties: fills, strokes, effects, auto-layout, text styles.
Useful for understanding design intent before code generation.

### 3. Generation: Convert to React

Generate React + Tailwind CSS code:

```
figma_to_react(
    url="https://www.figma.com/design/abc123/MyApp?node-id=1-3",
    component_name="LoginForm",
    extract_components=true
)
```

The `extract_components` flag detects repeated INSTANCE nodes (same component
ID used multiple times) and generates separate components for them.

### 4. Iteration

Refine the generated code:
- Adjust component names and prop interfaces
- Replace placeholder image `src` values
- Add state management and event handlers
- Integrate with project routing and API layer

## When to Use Each Tool

| Scenario | Tool |
|----------|------|
| Browse a Figma file structure | `figma_list_components` |
| Understand specific design properties | `figma_inspect_node` |
| Get raw IR tree for custom processing | `figma_fetch_design` |
| Generate React code from a design | `figma_to_react` |

## Integration with /rune:devise and /rune:work (/rune:strive)

### Planning Phase

During `/rune:devise`, reference Figma URLs in plan sections:

```markdown
## UI: LoginForm
Source: https://www.figma.com/design/abc123/MyApp?node-id=1-3
```

The Forge agents can use `figma_inspect_node` to enrich plans with
actual design measurements, color values, and layout properties.

### Implementation Phase

During `/rune:work` (alias: `/rune:strive`), rune-smith workers with `figma-to-react` MCP access can:

1. Call `figma_to_react` to generate initial component code
2. Adjust the output to match project conventions
3. Add business logic, state, and API integration

## URL Format

Supported Figma URL patterns:
- `https://www.figma.com/file/{key}/{title}`
- `https://www.figma.com/design/{key}/{title}`
- `https://www.figma.com/design/{key}/{title}?node-id={id}`
- `https://www.figma.com/design/{key}/branch/{branch_key}/{title}`
- `https://www.figma.com/proto/{key}/{title}`
- `https://www.figma.com/board/{key}/{title}`

Node IDs use hyphens in URLs (`1-3`) but colons in the API (`1:3`).
The URL parser handles this conversion automatically.

## Caching

File data is cached for 30 minutes, image URLs for 24 hours.
Override with environment variables:
- `FIGMA_FILE_CACHE_TTL=1800` (seconds)
- `FIGMA_IMAGE_CACHE_TTL=86400` (seconds)

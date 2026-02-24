# Visual Spec Map (VSM) Schema

The VSM is the intermediate representation between Figma design data and code implementation. One VSM file per component.

## Schema Version

```yaml
vsm_schema_version: "1.0"
```

All VSM files MUST include the schema version as the first field in the YAML frontmatter.

## File Location

```
tmp/design-sync/{timestamp}/vsm/{component-name}.md
```

## Full Schema

```yaml
---
vsm_schema_version: "1.0"
component_name: "CardComponent"
figma_url: "https://www.figma.com/design/abc123/MyApp?node-id=1-3"
figma_file_key: "abc123"
figma_node_id: "1-3"
extracted_at: "2026-02-25T12:00:00Z"
---
```

## Section 1: Token Map

Maps every visual property to a design token.

```markdown
## Token Map

| Property | Figma Value | Design Token | Tailwind | Status |
|----------|------------|-------------|----------|--------|
| Background | #FFFFFF | --color-background | bg-white | matched |
| Text color | #0A0A0A | --color-foreground | text-foreground | matched |
| Padding | 16px | --spacing-4 | p-4 | matched |
| Gap | 12px | --spacing-3 | gap-3 | matched |
| Border radius | 8px | --radius-lg | rounded-lg | matched |
| Shadow | 0 1px 3px rgba(0,0,0,0.1) | shadow-sm | shadow-sm | matched |
| Font size | 18px | text-lg | text-lg | matched |
| Font weight | 600 | font-semibold | font-semibold | matched |
| Accent color | #7C3AED | — | — | unmatched |
```

Status values:
- `matched` — exact or snapped token found
- `unmatched` — no token within snap distance (requires manual mapping)
- `off-scale` — value not on standard scale (rounded in Tailwind column)

## Section 2: Region Tree

Hierarchical decomposition of the component structure.

```markdown
## Region Tree

- **CardRoot** — `<article>`, flex-col, gap-3, p-4, rounded-lg, shadow-sm
  - **CardImage** — `<img>`, w-full, h-48, object-cover, rounded-t-lg
  - **CardBody** — `<div>`, flex-col, gap-2
    - **CardTitle** — `<h3>`, text-lg, font-semibold, text-foreground
    - **CardDescription** — `<p>`, text-sm, text-muted-foreground, line-clamp-2
  - **CardFooter** — `<div>`, flex-row, justify-between, items-center
    - **CardMeta** — `<span>`, text-xs, text-muted
    - **CardActions** — `<div>`, flex-row, gap-2
      - **ActionButton** — `<button>`, variant=ghost, size=sm
```

Each node specifies: semantic element, layout classes, sizing, and token references.

## Section 3: Variant Map

Component variants extracted from Figma Component Set.

```markdown
## Variant Map

| Figma Property | Prop Name | Type | Default | Token Diff |
|---------------|-----------|------|---------|------------|
| Type | variant | "default" | "featured" | "compact" | default | featured: border-primary, shadow-md |
| Size | size | "sm" | "md" | "lg" | md | sm: p-2 gap-1, lg: p-6 gap-4 |
| Has Image | — | (boolean structural) | true | false: remove CardImage node |
```

## Section 4: Responsive Spec

Breakpoint-specific behavior.

```markdown
## Responsive Spec

| Breakpoint | Layout Changes |
|-----------|---------------|
| Default (mobile) | Single column, full width, image aspect-ratio auto |
| md (768px) | Two-column grid for card lists |
| lg (1024px) | Three-column grid, max-w-sm per card |
```

## Section 5: Accessibility Requirements

```markdown
## Accessibility

| Requirement | Implementation |
|-------------|---------------|
| Semantic element | `<article>` for card container |
| Focus management | Card should be focusable if clickable (tabIndex=0) |
| Image alt | Required — describe card content |
| Heading level | h3 for card title (assumes within h2 section) |
| Touch target | Action buttons min 44x44px |
| Contrast | Text-foreground on background meets 4.5:1 |
```

## Section 6: Component Dependencies

```markdown
## Dependencies

| Component | Strategy | Notes |
|-----------|----------|-------|
| Button | REUSE | Existing — use variant="ghost" size="sm" |
| Badge | REUSE | Existing — for status indicators |
| Skeleton | REUSE | Existing — for loading state |
```

## Section 7: State Requirements

```markdown
## States

| State | Required | Description |
|-------|----------|-------------|
| Loading | Yes | Skeleton placeholder matching card dimensions |
| Error | Yes | Error message with retry button |
| Empty | Conditional | Only for card list containers, not individual cards |
| Success | Yes | Default rendered state |
```

## Validation Rules

```
1. vsm_schema_version MUST be "1.0"
2. figma_url MUST match FIGMA_URL_PATTERN
3. Token Map MUST have at least 1 entry
4. Region Tree MUST have at least 1 root node
5. Every node in Region Tree MUST specify a semantic element
6. Variant Map may be empty (single-variant component)
7. Responsive Spec MUST have at least "Default (mobile)" entry
8. Accessibility section MUST have at least semantic element + contrast entries
```

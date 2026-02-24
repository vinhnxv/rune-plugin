# Visual Region Analysis — Screenshot to Structure

Protocol for decomposing a design screenshot or Figma frame into semantic regions before writing code. This prevents structural mismatches between design and implementation.

## Why Region Analysis?

Jumping straight from a design to code often produces:
- Flat markup that doesn't reflect the visual hierarchy
- Incorrect nesting (elements grouped wrong)
- Missed interactive regions (clickable areas not wrapped in buttons/links)
- Inconsistent spacing (gaps that look right but aren't on the design system scale)

Region analysis forces a structured decomposition step between "seeing" and "coding."

## 5-Step Analysis Protocol

### Step 1: Identify Major Regions

Scan the design from top to bottom and left to right. Label each distinct visual area:

```
┌──────────────────────────────┐
│          Header              │  Region 1: Navigation
├──────────┬───────────────────┤
│          │                   │
│ Sidebar  │   Main Content    │  Region 2: Sidebar
│          │                   │  Region 3: Main Content
│          │                   │
├──────────┴───────────────────┤
│          Footer              │  Region 4: Footer
└──────────────────────────────┘
```

**Output**: List of top-level semantic regions with names.

### Step 2: Decompose Each Region

For each major region, identify sub-regions:

```
Region 3: Main Content
├── Page Title (text)
├── Action Bar (buttons: Filter, Sort, New Item)
├── Content Grid (3-column card layout)
│   ├── Card (repeated)
│   │   ├── Card Image
│   │   ├── Card Title
│   │   ├── Card Description (truncated)
│   │   └── Card Footer (metadata + actions)
│   └── ...
└── Pagination (page controls)
```

**Output**: Nested tree structure per region.

### Step 3: Classify Each Node

For each node in the tree, determine:

| Property | Question |
|----------|----------|
| **Semantic role** | What HTML element? (`nav`, `main`, `section`, `article`, `button`, `a`) |
| **Layout type** | Flex row, flex column, grid, or static? |
| **Sizing** | Fixed, fill-container, or hug-contents? |
| **Spacing** | What gap/padding token from the design system? |
| **Interactive?** | Is it clickable, focusable, or draggable? |
| **Repeating?** | Is this a list item rendered from data? |

### Step 4: Map to Components

Match each node to existing components or flag for creation:

```
Card Image       → <img> (native)
Card Title       → <Heading level={3}>
Card Description → <Text truncate={2}>
Card Footer      → <CardFooter> ← EXISTS? Check component library
Action Bar       → <Toolbar> ← EXISTS? Check component library
Pagination       → <Pagination> ← EXISTS? Check component library
```

See [component-reuse-strategy.md](component-reuse-strategy.md) for the REUSE > EXTEND > CREATE decision tree.

### Step 5: Annotate Design Tokens

For each visual property, map to the token system:

```
Card:
  background: --color-background (white)
  border-radius: --radius-lg (8px)
  shadow: shadow-sm (elevation 1)
  padding: --spacing-4 (16px)
  gap (between cards): --spacing-6 (24px)

Card Title:
  font-size: text-lg (18px)
  font-weight: font-semibold (600)
  color: --color-foreground
```

## Output Format

The completed analysis should produce a structured document:

```markdown
## Region Analysis: [Page/Component Name]

### Regions
1. **Header** — `<header>`, flex-row, justify-between, h-16
2. **Sidebar** — `<aside>`, flex-col, w-64, hidden on mobile
3. **Main** — `<main>`, flex-col, flex-1, gap-6, p-8
4. **Footer** — `<footer>`, flex-row, justify-center, h-12

### Component Mapping
| Region/Node | Component | Status |
|------------|-----------|--------|
| Navigation | `<NavBar>` | Exists |
| Action Bar | `<Toolbar>` | Needs variant |
| Card | `<ContentCard>` | New (CREATE) |
| Pagination | `<Pagination>` | Exists |

### Token Mapping
| Property | Value | Token |
|----------|-------|-------|
| Card bg | white | --color-background |
| Card radius | 8px | --radius-lg |
| Card gap | 24px | --spacing-6 |
| Title size | 18px | text-lg |
```

## Common Analysis Mistakes

| Mistake | Fix |
|---------|-----|
| Treating visual groups as flat siblings | Look for nesting — a card title inside a card, not next to it |
| Missing interactive regions | Check for hover states, cursor changes, click targets |
| Ignoring whitespace | Whitespace IS design — map every gap to a spacing token |
| Assuming fixed sizes | Check if elements should be responsive (fill vs fixed) |
| Skipping empty/loading states | Design often only shows the "happy path" — ask about other states |

## When to Use This Protocol

| Trigger | Action |
|---------|--------|
| Implementing from a Figma frame | Full 5-step analysis |
| Implementing from a screenshot | Full 5-step analysis |
| Modifying an existing page | Partial analysis (changed regions only) |
| Reviewing implementation accuracy | Compare analysis output with actual markup |

## Cross-References

- [design-token-reference.md](design-token-reference.md) — Token mapping for Step 5
- [layout-alignment.md](layout-alignment.md) — Layout classification for Step 3
- [component-reuse-strategy.md](component-reuse-strategy.md) — Component matching for Step 4

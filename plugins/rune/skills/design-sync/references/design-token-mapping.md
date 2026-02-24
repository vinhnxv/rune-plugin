# Design Token Mapping — Color Snapping and Auto-Layout Conversion

Algorithms for mapping Figma design values to project design tokens and Tailwind utilities.

## Color Snapping Algorithm

Map Figma fill/stroke colors to the nearest design system token.

### Step 1: Extract Figma Color

```
Figma provides RGBA as floats [0.0, 1.0]:
  R: 0.267, G: 0.533, B: 0.933, A: 1.0
Convert to 8-bit:
  R: 68, G: 136, B: 238 → #4488EE
```

### Step 2: Match Against Project Tokens

```
1. Read project tokens from:
   - CSS custom properties (globals.css, variables.css)
   - Tailwind config (tailwind.config.js/ts → theme.colors)
   - Token file (tokens.json, design-tokens.yaml)

2. For each token:
   Convert token value to RGB
   Compute Euclidean distance:
     dist = sqrt((r1-r2)^2 + (g1-g2)^2 + (b1-b2)^2)

3. If min_distance == 0 → exact match
   If min_distance <= snap_distance (default: 20) → snap to nearest
   If min_distance > snap_distance → mark as "unmatched"
```

### Step 3: Tailwind Palette Fallback

If no project token matches, snap to the Tailwind default palette:

```
22 color palettes: slate, gray, zinc, neutral, stone,
  red, orange, amber, yellow, lime, green, emerald, teal,
  cyan, sky, blue, indigo, violet, purple, fuchsia, pink, rose

Each palette has 11 shades: 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950

Total: 242 reference colors to snap against
```

### Snap Distance Reference

| Distance | Interpretation |
|----------|---------------|
| 0 | Exact match |
| 1-10 | Near-identical (rounding/antialiasing) |
| 11-20 | Close match (acceptable snap) |
| 21-40 | Visible difference (flag for review) |
| >40 | Different color (mark unmatched) |

## Auto-Layout to Flexbox Conversion

### Direction

| Figma | CSS | Tailwind |
|-------|-----|----------|
| HORIZONTAL | flex-direction: row | flex-row |
| VERTICAL | flex-direction: column | flex-col |
| WRAP (v5) | flex-wrap: wrap | flex-wrap |

### Alignment (Primary Axis)

| Figma | CSS | Tailwind |
|-------|-----|----------|
| MIN | justify-content: flex-start | justify-start |
| CENTER | justify-content: center | justify-center |
| MAX | justify-content: flex-end | justify-end |
| SPACE_BETWEEN | justify-content: space-between | justify-between |

### Alignment (Cross Axis)

| Figma | CSS | Tailwind |
|-------|-----|----------|
| MIN | align-items: flex-start | items-start |
| CENTER | align-items: center | items-center |
| MAX | align-items: flex-end | items-end |
| STRETCH | align-items: stretch | items-stretch |
| BASELINE | align-items: baseline | items-baseline |

### Spacing

| Figma Property | CSS | Tailwind Pattern |
|---------------|-----|-----------------|
| itemSpacing | gap | gap-{n} |
| paddingTop | padding-top | pt-{n} |
| paddingRight | padding-right | pr-{n} |
| paddingBottom | padding-bottom | pb-{n} |
| paddingLeft | padding-left | pl-{n} |
| Equal padding (all same) | padding | p-{n} |
| Symmetric (top=bottom, left=right) | padding | py-{n} px-{n} |

### Sizing

| Figma | Meaning | CSS | Tailwind |
|-------|---------|-----|----------|
| FIXED | Explicit dimension | width: {n}px | w-{n} or w-[{n}px] |
| FILL | Expand to fill parent | flex: 1 1 0% | flex-1 |
| HUG | Shrink to content | width: fit-content | w-fit |

## Typography Mapping

| Figma Property | CSS | Tailwind |
|---------------|-----|----------|
| fontFamily | font-family | font-{name} |
| fontSize (12) | font-size: 12px | text-xs |
| fontSize (14) | font-size: 14px | text-sm |
| fontSize (16) | font-size: 16px | text-base |
| fontSize (18) | font-size: 18px | text-lg |
| fontSize (20) | font-size: 20px | text-xl |
| fontSize (24) | font-size: 24px | text-2xl |
| fontWeight (400) | font-weight: 400 | font-normal |
| fontWeight (500) | font-weight: 500 | font-medium |
| fontWeight (600) | font-weight: 600 | font-semibold |
| fontWeight (700) | font-weight: 700 | font-bold |
| lineHeight (1.2) | line-height: 1.2 | leading-tight |
| lineHeight (1.5) | line-height: 1.5 | leading-normal |
| lineHeight (1.75) | line-height: 1.75 | leading-relaxed |

## Shadow Mapping

| Figma Effect | Tailwind |
|-------------|----------|
| No shadow | shadow-none |
| Blur 2-4, spread 0, offset 1-2 | shadow-sm |
| Blur 6-8, spread 0, offset 2-4 | shadow-md |
| Blur 10-15, spread 0, offset 4-6 | shadow-lg |
| Blur 20-25, spread 0, offset 8-10 | shadow-xl |
| Inner shadow | shadow-inner |

## Cross-References

- [vsm-spec.md](vsm-spec.md) — Where token mappings are recorded
- [phase1-design-extraction.md](phase1-design-extraction.md) — Extraction pipeline

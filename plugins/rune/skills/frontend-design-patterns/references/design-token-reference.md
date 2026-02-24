# Design Token Reference — Figma to CSS/Tailwind Mapping

Design tokens bridge the gap between design tools (Figma) and code (CSS, Tailwind). This reference covers the standard mapping from Figma properties to implementation values.

## What Are Design Tokens?

Design tokens are named values for visual properties: colors, spacing, typography, shadows, borders. They provide:
- A single source of truth across design and code
- Theme-ability (swap tokens to change themes)
- Consistency (same name = same value everywhere)

## Figma Property to CSS Mapping

### Colors

| Figma Property | CSS Equivalent | Tailwind |
|---------------|---------------|----------|
| Fill (solid) | `background-color` / `color` | `bg-{color}` / `text-{color}` |
| Fill (linear gradient) | `background: linear-gradient(...)` | `bg-linear-to-{dir}` |
| Fill (radial gradient) | `background: radial-gradient(...)` | `bg-radial` (Tailwind v4) |
| Stroke | `border-color` | `border-{color}` |
| Opacity | `opacity` | `opacity-{value}` |

### Color Format Conversion

```
Figma RGBA → CSS:
  R: 0.267, G: 0.533, B: 0.933, A: 1.0
  → rgb(68, 136, 238)
  → #4488EE
  → Tailwind: snap to nearest palette (blue-500)

Figma color styles:
  "Brand/Primary" → --color-primary → text-primary (Tailwind v4)
  "Neutral/Gray-100" → --color-gray-100 → bg-gray-100
```

### Spacing

| Figma Property | CSS Equivalent | Tailwind |
|---------------|---------------|----------|
| Auto-layout padding | `padding` | `p-{n}` |
| Auto-layout gap | `gap` | `gap-{n}` |
| Item spacing (horizontal) | `column-gap` | `gap-x-{n}` |
| Item spacing (vertical) | `row-gap` | `gap-y-{n}` |
| Constraints (fixed) | `width` / `height` | `w-{n}` / `h-{n}` |
| Fill container | `flex: 1` | `flex-1` |
| Hug contents | `width: fit-content` | `w-fit` |

### Figma Spacing to Tailwind Scale

| Figma Value | Tailwind Class | CSS Value |
|------------|---------------|-----------|
| 0 | `{p\|m\|gap}-0` | 0px |
| 2 | `{p\|m\|gap}-0.5` | 2px |
| 4 | `{p\|m\|gap}-1` | 4px |
| 8 | `{p\|m\|gap}-2` | 8px |
| 12 | `{p\|m\|gap}-3` | 12px |
| 16 | `{p\|m\|gap}-4` | 16px |
| 20 | `{p\|m\|gap}-5` | 20px |
| 24 | `{p\|m\|gap}-6` | 24px |
| 32 | `{p\|m\|gap}-8` | 32px |
| 40 | `{p\|m\|gap}-10` | 40px |
| 48 | `{p\|m\|gap}-12` | 48px |
| 64 | `{p\|m\|gap}-16` | 64px |

**Off-scale values**: If Figma specifies a value not on the Tailwind scale (e.g., 18px), use the nearest scale value and flag for design review. Avoid arbitrary values like `p-[18px]` unless the design team confirms it is intentional.

### Typography

| Figma Property | CSS Equivalent | Tailwind |
|---------------|---------------|----------|
| Font family | `font-family` | `font-{name}` |
| Font size | `font-size` | `text-{size}` |
| Font weight | `font-weight` | `font-{weight}` |
| Line height | `line-height` | `leading-{n}` |
| Letter spacing | `letter-spacing` | `tracking-{n}` |
| Text decoration | `text-decoration` | `underline` / `line-through` |
| Text transform | `text-transform` | `uppercase` / `lowercase` / `capitalize` |
| Text align | `text-align` | `text-{left\|center\|right}` |

### Shadows

| Figma Property | CSS Equivalent | Tailwind |
|---------------|---------------|----------|
| Drop shadow | `box-shadow` | `shadow-{size}` |
| Inner shadow | `box-shadow: inset ...` | `shadow-inner` |
| Layer blur | `filter: blur(...)` | `blur-{size}` |
| Background blur | `backdrop-filter: blur(...)` | `backdrop-blur-{size}` |

### Border and Radius

| Figma Property | CSS Equivalent | Tailwind |
|---------------|---------------|----------|
| Stroke weight | `border-width` | `border-{n}` |
| Corner radius (all) | `border-radius` | `rounded-{size}` |
| Corner radius (individual) | `border-{t\|r\|b\|l}-radius` | `rounded-{tl\|tr\|bl\|br}-{size}` |
| Stroke style (dashed) | `border-style: dashed` | `border-dashed` |

## Token Naming Convention

```
Category → Property → Variant → State

Examples:
  color-primary-default     → Main brand color
  color-primary-hover       → Brand color on hover
  spacing-page-horizontal   → Page-level horizontal padding
  font-heading-size-lg      → Large heading font size
  shadow-card-default       → Default card shadow
  radius-button-default     → Button border radius
```

## Theme Token Pattern

```css
/* Light theme (default) */
:root {
  --color-background: #ffffff;
  --color-foreground: #0a0a0a;
  --color-primary: #2563eb;
  --color-muted: #f5f5f5;
}

/* Dark theme */
[data-theme="dark"] {
  --color-background: #0a0a0a;
  --color-foreground: #fafafa;
  --color-primary: #3b82f6;
  --color-muted: #262626;
}
```

## Cross-References

- [design-system-rules.md](design-system-rules.md) — Constraints for using tokens
- [layout-alignment.md](layout-alignment.md) — Spacing tokens in layout context
- [variant-mapping.md](variant-mapping.md) — How Figma variants use tokens

# Layout and Alignment Patterns — Flexbox / Grid

Patterns for translating design layouts into CSS Flexbox and Grid implementations. Figma's auto-layout maps directly to Flexbox; explicit grid layouts map to CSS Grid.

## Figma Auto-Layout to Flexbox

| Figma Auto-Layout Property | CSS Flexbox | Tailwind |
|---------------------------|-------------|----------|
| Direction: Horizontal | `flex-direction: row` | `flex-row` |
| Direction: Vertical | `flex-direction: column` | `flex-col` |
| Wrap | `flex-wrap: wrap` | `flex-wrap` |
| Gap | `gap` | `gap-{n}` |
| Padding | `padding` | `p-{n}` |
| Alignment (primary axis) | `justify-content` | `justify-{value}` |
| Alignment (cross axis) | `align-items` | `items-{value}` |

### Figma Alignment to justify-content

| Figma Setting | CSS | Tailwind |
|---------------|-----|----------|
| Top-left / Left | `justify-content: flex-start` | `justify-start` |
| Center | `justify-content: center` | `justify-center` |
| Bottom-right / Right | `justify-content: flex-end` | `justify-end` |
| Space between | `justify-content: space-between` | `justify-between` |

### Figma Alignment to align-items

| Figma Setting | CSS | Tailwind |
|---------------|-----|----------|
| Top (in horizontal layout) | `align-items: flex-start` | `items-start` |
| Center | `align-items: center` | `items-center` |
| Bottom (in horizontal layout) | `align-items: flex-end` | `items-end` |
| Stretch | `align-items: stretch` | `items-stretch` |

## Sizing Behavior

| Figma Sizing | CSS | Tailwind |
|-------------|-----|----------|
| Fixed width | `width: {n}px` | `w-{n}` or `w-[{n}px]` |
| Fill container | `flex: 1 1 0%` | `flex-1` |
| Hug contents | `width: fit-content` | `w-fit` |
| Min width | `min-width` | `min-w-{n}` |
| Max width | `max-width` | `max-w-{n}` |

## Common Layout Patterns

### Centered Content

```
Container: flex, justify-center, items-center
Use: Centering a single element or group

Tailwind: flex justify-center items-center
```

### Sidebar + Main

```
Container: flex, row
Sidebar: fixed width (w-64)
Main: flex-1

Tailwind: flex flex-row
  Sidebar: w-64 shrink-0
  Main: flex-1 min-w-0
```

### Stack (Vertical List)

```
Container: flex, column, gap
Items: full width

Tailwind: flex flex-col gap-4
```

### Holy Grail (Header + Content + Footer)

```
Container: flex, column, min-h-screen
Header: fixed height
Content: flex-1
Footer: fixed height

Tailwind: flex flex-col min-h-screen
  Header: h-16
  Content: flex-1
  Footer: h-12
```

### Card Grid

```
Container: grid, responsive columns, gap
Items: uniform sizing

Tailwind: grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6
```

### Inline Group with Wrap

```
Container: flex, wrap, gap
Items: auto-sized

Tailwind: flex flex-wrap gap-2
Use: Tag lists, chip groups, badge collections
```

## CSS Grid Patterns

### When to Use Grid Over Flexbox

| Use Grid | Use Flexbox |
|----------|-------------|
| 2D layout (rows AND columns) | 1D layout (row OR column) |
| Equal-sized tiles | Variable-sized items |
| Complex overlapping regions | Sequential stacking |
| Named template areas | Simple alignment |

### Responsive Grid Template

```css
/* Auto-fill: as many columns as fit */
grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));

/* Fixed columns with responsive breakpoints */
@media (min-width: 768px) { grid-template-columns: repeat(2, 1fr); }
@media (min-width: 1024px) { grid-template-columns: repeat(3, 1fr); }
```

### Grid Template Areas

```css
.layout {
  display: grid;
  grid-template-areas:
    "header header"
    "sidebar main"
    "footer footer";
  grid-template-columns: 250px 1fr;
  grid-template-rows: auto 1fr auto;
}
```

## Alignment Debugging Checklist

When a layout doesn't match the design:

```
1. Check flex direction — is it row or column?
2. Check justify-content — are items spaced correctly on main axis?
3. Check align-items — are items aligned on cross axis?
4. Check for missing flex-1 — is a child not filling available space?
5. Check for min-w-0 — is a flex child overflowing its container?
6. Check gap vs margin — is spacing between items via gap or margins?
7. Check overflow — is content being clipped unexpectedly?
```

## Cross-References

- [design-token-reference.md](design-token-reference.md) — Spacing tokens for gap/padding
- [responsive-patterns.md](responsive-patterns.md) — Responsive layout shifts

# Responsive Patterns — Mobile-First Design

Patterns for implementing responsive designs that adapt across screen sizes. Mobile-first means starting with the smallest screen and adding complexity at larger breakpoints.

## Breakpoint Scale

| Name | Min Width | Tailwind Prefix | Target Devices |
|------|-----------|----------------|----------------|
| Default | 0px | (none) | Phones (portrait) |
| sm | 640px | `sm:` | Phones (landscape) |
| md | 768px | `md:` | Tablets |
| lg | 1024px | `lg:` | Laptops |
| xl | 1280px | `xl:` | Desktops |
| 2xl | 1536px | `2xl:` | Large monitors |

## Mobile-First Pattern

Start with mobile styles (no prefix), add overrides at larger breakpoints:

```
# Correct (mobile-first)
className="flex flex-col md:flex-row"
# Mobile: vertical stack → Tablet+: horizontal row

# Incorrect (desktop-first)
className="flex flex-row md:flex-col"
# This reverses the logic — confusing and hard to maintain
```

## Responsive Layout Shifts

### Single Column to Multi-Column

```
Mobile: 1 column full-width
Tablet: 2 columns
Desktop: 3 columns

Tailwind: grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6
```

### Sidebar Collapse

```
Mobile: sidebar hidden, hamburger menu
Tablet: sidebar overlay
Desktop: sidebar visible, content shifts right

Pattern:
  - Sidebar: hidden md:block md:w-64
  - Overlay: md:hidden (mobile toggle)
  - Main: w-full md:ml-64
```

### Stack to Inline

```
Mobile: form fields stacked vertically
Desktop: form fields in a row

Tailwind: flex flex-col sm:flex-row gap-4
```

### Navigation Patterns

| Screen Size | Pattern |
|------------|---------|
| Mobile | Hamburger menu → slide-out drawer |
| Tablet | Collapsed icons + tooltips |
| Desktop | Full horizontal nav bar |

## Fluid Typography

Scale text between a minimum and maximum size based on viewport width:

```css
/* Clamp: min 16px, preferred 2.5vw, max 24px */
font-size: clamp(1rem, 2.5vw, 1.5rem);
```

| Element | Mobile | Desktop | Tailwind |
|---------|--------|---------|----------|
| H1 | 24px | 36px | `text-2xl md:text-4xl` |
| H2 | 20px | 30px | `text-xl md:text-3xl` |
| Body | 14px | 16px | `text-sm md:text-base` |
| Caption | 12px | 14px | `text-xs md:text-sm` |

## Responsive Spacing

Increase spacing at larger screens to fill available space:

```
# Section padding
className="px-4 md:px-8 lg:px-16"

# Content max-width (prevent ultra-wide lines)
className="max-w-prose mx-auto"   # ~65ch for readability
className="max-w-4xl mx-auto"      # Fixed max width
className="container mx-auto px-4" # Responsive container
```

## Responsive Images

```
# Responsive image (fills container)
<img class="w-full h-auto" src="..." alt="..." />

# Art direction (different crops per breakpoint)
<picture>
  <source media="(min-width: 1024px)" srcset="hero-wide.webp" />
  <source media="(min-width: 768px)" srcset="hero-medium.webp" />
  <img src="hero-mobile.webp" alt="..." />
</picture>

# Lazy loading (below-the-fold images)
<img loading="lazy" src="..." alt="..." />
```

## Responsive Tables

| Strategy | When to Use |
|----------|-------------|
| Horizontal scroll | Table has many columns, all important |
| Card layout | Table has few rows, long content per row |
| Column hiding | Some columns are less important on mobile |
| Priority columns | Show 2-3 key columns, "expand" for rest |

```
# Horizontal scroll pattern
<div class="overflow-x-auto">
  <table class="min-w-full">...</table>
</div>
```

## Touch Target Sizing

| Element | Min Size | Guideline |
|---------|----------|-----------|
| Buttons | 44x44px | WCAG 2.5.8 (Target Size) |
| Links (inline) | 24px height | With adequate line height |
| Icon buttons | 48x48px | Material Design guideline |
| Form inputs | 44px height | Comfortable touch target |

## Testing Checklist

```
1. Test at each breakpoint (resize browser or use DevTools)
2. Test between breakpoints (e.g., 700px — between sm and md)
3. Test landscape orientation on mobile
4. Test with browser zoom at 200% (WCAG requirement)
5. Test with content overflow (long text, many items)
6. Test touch targets with mobile emulator
7. Test with dynamic content (empty state, 100 items)
```

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Fixed pixel widths at mobile | Use `w-full` or `max-w-*` |
| Desktop-first media queries | Restructure as mobile-first |
| Hiding critical content on mobile | Reorganize layout instead |
| Separate mobile and desktop components | Use responsive utilities |
| Horizontal scroll on body | Fix with `overflow-x-hidden` on container |

## Cross-References

- [layout-alignment.md](layout-alignment.md) — Base layout patterns
- [design-token-reference.md](design-token-reference.md) — Spacing scale for responsive values

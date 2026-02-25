# Design System Rules — Generic Constraints

Enforced constraints that maintain visual consistency across a project. These rules are framework-agnostic and apply to any component-based frontend.

## Core Principle

**Every visual property must reference a design token.** Arbitrary values (magic numbers) break consistency and make theming impossible.

```
# Correct — uses design tokens
padding: var(--spacing-4);      /* CSS custom property */
className="p-4"                 /* Tailwind utility */

# Incorrect — magic number
padding: 17px;
className="p-[17px]"
```

## Color Constraints

### Permitted Color Sources

| Source | When to Use |
|--------|------------|
| Design tokens (`--color-*`) | Always preferred |
| Tailwind palette (`blue-500`) | When tokens map to Tailwind |
| Semantic aliases (`--color-primary`) | For theme-aware colors |
| `currentColor` | For icons that inherit text color |
| `transparent` | For invisible interactive areas |

### Forbidden

- Hex/RGB literals in component code (use tokens)
- Opacity hacks for disabled states (use `--color-disabled` token)
- Brand colors without going through the token layer

### Color Roles

| Role | Purpose | Example Token |
|------|---------|---------------|
| Primary | Main brand action | `--color-primary` |
| Secondary | Supporting actions | `--color-secondary` |
| Destructive | Delete, remove, error | `--color-destructive` |
| Muted | Backgrounds, borders | `--color-muted` |
| Foreground | Text on background | `--color-foreground` |
| Background | Page/card backgrounds | `--color-background` |

## Spacing Scale

Most design systems use a base-4 or base-8 spacing scale. All spacing values must come from the scale.

### Base-4 Scale (Common)

| Token | Value | Use Case |
|-------|-------|----------|
| `--spacing-0` | 0px | No spacing |
| `--spacing-0.5` | 2px | Hairline gaps |
| `--spacing-1` | 4px | Tight inline spacing |
| `--spacing-2` | 8px | Default inline spacing |
| `--spacing-3` | 12px | Compact element spacing |
| `--spacing-4` | 16px | Standard element spacing |
| `--spacing-6` | 24px | Section padding |
| `--spacing-8` | 32px | Large section gaps |
| `--spacing-12` | 48px | Page-level margins |
| `--spacing-16` | 64px | Hero/banner spacing |

**Rule**: If the design specifies a value not on the scale (e.g., 18px), round to the nearest scale value (16px) and flag for design review.

## Typography

### Type Scale

| Level | Size | Weight | Line Height | Use |
|-------|------|--------|-------------|-----|
| Display | 36-48px | Bold | 1.1 | Hero headings |
| H1 | 30-36px | Bold | 1.2 | Page titles |
| H2 | 24-30px | Semibold | 1.25 | Section headings |
| H3 | 20-24px | Semibold | 1.3 | Subsection headings |
| Body | 14-16px | Regular | 1.5 | Paragraph text |
| Small | 12-14px | Regular | 1.4 | Captions, labels |
| Tiny | 10-12px | Medium | 1.3 | Badges, timestamps |

### Typography Rules

```
1. Never set font-size with arbitrary pixel values — use the scale
2. Line height must be unitless (1.5, not 24px) for scalability
3. Max line length: 65-80 characters for readability (max-w-prose)
4. Font weights: use named tokens (regular, medium, semibold, bold)
5. Letter spacing: only adjust for uppercase text or display headings
```

## Border Radius Scale

| Token | Value | Use Case |
|-------|-------|----------|
| `--radius-none` | 0px | Square corners |
| `--radius-sm` | 2px | Subtle rounding |
| `--radius-md` | 6px | Standard components (cards, inputs) |
| `--radius-lg` | 8-12px | Prominent containers |
| `--radius-xl` | 16px | Large panels |
| `--radius-full` | 9999px | Pills, avatars |

## Elevation (Shadows)

| Level | Use Case | Tailwind |
|-------|----------|----------|
| 0 | Flat elements | `shadow-none` |
| 1 | Cards, dropdowns | `shadow-sm` |
| 2 | Popovers, tooltips | `shadow-md` |
| 3 | Modals, dialogs | `shadow-lg` |
| 4 | Toasts, notifications | `shadow-xl` |

**Rule**: Elevation increases with z-index layer. A modal (z-50) should have higher elevation than a card (z-0).

## Icon Usage

```
1. Use a single icon library consistently (Lucide, Heroicons, etc.)
2. Icon size must match text size context (16px for body, 20px for headings)
3. Decorative icons: aria-hidden="true"
4. Meaningful icons: aria-label or accompanying text
5. Never use icons as the sole interactive indicator — pair with text
```

## Component Naming Convention

| Pattern | Example | When |
|---------|---------|------|
| PascalCase | `UserAvatar` | Component files |
| kebab-case | `user-avatar` | CSS classes, file names |
| UPPER_SNAKE | `COLOR_PRIMARY` | Constants |
| camelCase | `isDisabled` | Props, variables |

## Enforcement Checklist

When reviewing implementations against a design system:

```
- [ ] All colors reference tokens (no hex/RGB literals)
- [ ] All spacing values are on the scale (no arbitrary px)
- [ ] Typography uses the type scale (no arbitrary font-size)
- [ ] Border radius uses scale tokens
- [ ] Shadow uses elevation levels
- [ ] Icons from the approved library
- [ ] Component names follow convention
- [ ] No inline styles with magic numbers
```

# Component Reuse Strategy — REUSE > EXTEND > CREATE

Decision framework for building components that maximize design system consistency and minimize duplication. Evaluate in order: always prefer reuse, then extension, then creation as a last resort.

## Decision Tree

```
Is there an EXISTING component that does exactly what you need?
├── YES → REUSE: Import and use it directly
└── NO
    ├── Is there a component that does 70%+ of what you need?
    │   ├── YES → Can you customize it via existing props/slots/variants?
    │   │   ├── YES → REUSE with configuration
    │   │   └── NO → EXTEND: Wrap it or add a variant
    │   └── NO → CREATE: Build a new component
    └── Is this a one-off or will it be reused?
        ├── One-off → Inline styles/markup (no component needed)
        └── Reused → CREATE with clear API boundaries
```

## REUSE (Preferred)

Use the existing component as-is with its current props.

**When to REUSE:**
- The component's visual output matches the design spec
- Any differences are within acceptable design system tolerances
- Customization is achievable via existing props or CSS custom properties

**Example:**
```
# Design shows a primary button with "Submit" text
# Existing: <Button variant="primary">{children}</Button>
# Action: REUSE — <Button variant="primary">Submit</Button>
```

## EXTEND (When REUSE falls short)

Add capability to an existing component without modifying its source.

### Extension Patterns

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Composition** | Need to wrap with extra markup | `<IconButton icon={Search}><Button>` |
| **New variant** | Recurring visual variation | Add `variant="ghost"` to Button |
| **Slot/children** | Need custom inner content | `<Card header={<CustomHeader/>}>` |
| **CSS override** | One-off visual tweak | `className="!rounded-full"` |
| **Higher-order wrapper** | Cross-cutting behavior | `withTooltip(Button)` |

### Extension Rules

```
1. Never modify the original component's source for a single use case
2. New variants must serve 2+ consumers — otherwise use composition
3. Wrapper components must forward all original props (spread pattern)
4. CSS overrides must use design system tokens, not arbitrary values
5. Document why the extension exists (not just what it does)
```

## CREATE (Last Resort)

Build a new component from scratch when no existing component covers the need.

### Pre-Creation Checklist

```
- [ ] Searched component library for existing matches
- [ ] Confirmed no similar component in the codebase (Grep for visual keywords)
- [ ] Identified at least 2 places where this component will be used
- [ ] Defined the minimal prop API (start small, extend later)
- [ ] Verified the design follows design system tokens (no arbitrary values)
- [ ] Checked if the design system team has this component planned
```

### Component API Design Principles

| Principle | Rule | Example |
|-----------|------|---------|
| **Minimal props** | Start with the fewest props needed | `<Badge label="New">` not `<Badge label="New" color="blue" size="sm" rounded>` |
| **Sensible defaults** | Most common usage needs zero config | `<Button>` defaults to `variant="primary"` |
| **Consistent naming** | Match existing component conventions | If `variant` is used elsewhere, don't use `type` |
| **Boolean props** | Use for toggles, not enums | `disabled` yes, `size="disabled"` no |
| **Children over props** | Prefer `children` for content | `<Button>Submit</Button>` not `<Button text="Submit">` |
| **Controlled by default** | State managed by parent | Value + onChange, not internal state |

## Component Granularity Guide

| Level | Examples | Reuse Frequency |
|-------|---------|-----------------|
| **Atoms** | Button, Input, Badge, Icon, Avatar | Very high (50+ uses) |
| **Molecules** | SearchBar, FormField, CardHeader | High (10-50 uses) |
| **Organisms** | NavigationBar, UserProfile, DataTable | Medium (3-10 uses) |
| **Templates** | DashboardLayout, SettingsPage | Low (1-3 uses) |

**Rule of thumb**: Atoms and molecules belong in the shared component library. Organisms may be shared or feature-specific. Templates are almost always feature-specific.

## Duplication Detection

Before creating a new component, search for existing implementations:

```
Search terms to check:
1. Component name variations (UserCard, UserTile, UserProfile)
2. Visual behavior (avatar + name + email layout)
3. Design system token usage (same spacing/color combination)
4. Figma component name (if available)
```

If you find a near-match, prefer EXTEND over CREATE.

## Cross-References

- [design-system-rules.md](design-system-rules.md) — Token constraints for new components
- [variant-mapping.md](variant-mapping.md) — How Figma variants map to props
- [storybook-patterns.md](storybook-patterns.md) — Documenting new components

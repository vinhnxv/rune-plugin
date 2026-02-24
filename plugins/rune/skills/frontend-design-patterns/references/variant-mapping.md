# Variant Mapping — Figma Variants to Component Props

Strategy for translating Figma component variants into typed component props. Variants in Figma represent the same component in different states, sizes, or configurations — these map directly to prop values.

## Figma Variant Anatomy

In Figma, a **Component Set** groups related variants. Each variant is defined by **variant properties** (key=value pairs):

```
Component Set: Button
├── Type=Primary, Size=Large, State=Default
├── Type=Primary, Size=Large, State=Hover
├── Type=Primary, Size=Large, State=Disabled
├── Type=Primary, Size=Medium, State=Default
├── Type=Secondary, Size=Large, State=Default
└── ...
```

## Mapping Rules

### Rule 1: Variant Properties Become Props

Each Figma variant property maps to a component prop:

| Figma Property | Prop Name | Prop Type |
|---------------|-----------|-----------|
| Type | `variant` | `"primary" \| "secondary" \| "ghost"` |
| Size | `size` | `"sm" \| "md" \| "lg"` |
| State | (handled by CSS/interaction) | — |
| Has Icon | `icon` | `ReactNode \| undefined` |
| Show Label | `showLabel` | `boolean` |

### Rule 2: Interaction States Are NOT Props

Figma variants for hover, focus, active, disabled are CSS states, not separate props:

| Figma State Variant | Implementation |
|--------------------|----------------|
| Default | Base styles |
| Hover | `:hover` pseudo-class |
| Focus | `:focus-visible` pseudo-class |
| Active/Pressed | `:active` pseudo-class |
| Disabled | `disabled` prop + `:disabled` styles |
| Loading | `loading` prop → spinner overlay |
| Error | `error` prop → error styling |

### Rule 3: Boolean Properties Map to Optional Props

Figma boolean variants ("Has Icon: true/false") become optional props:

```
Figma: Has Icon = true/false
→ Prop: icon?: ReactNode

Figma: Show Badge = true/false
→ Prop: badge?: string | number

Figma: Closable = true/false
→ Prop: onClose?: () => void  (presence implies closable)
```

### Rule 4: Default Variant Becomes Default Prop

The most commonly used variant in the design is the default prop value:

```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  // default: 'primary' (most common in designs)
  size?: 'sm' | 'md' | 'lg';
  // default: 'md' (standard size)
}
```

## Mapping Workflow

### Step 1: Extract Variant Properties

From the Figma Component Set, list all variant properties and their values:

```
Button Component Set:
  Type: Primary, Secondary, Ghost, Destructive
  Size: Small, Medium, Large
  State: Default, Hover, Focus, Active, Disabled
  Icon Position: None, Left, Right
```

### Step 2: Classify Each Property

| Property | Classification | Reason |
|----------|---------------|--------|
| Type | **Prop** (`variant`) | Visual style — user-selectable |
| Size | **Prop** (`size`) | Layout variation — user-selectable |
| State | **CSS** (not a prop) | Interaction-driven, not explicit |
| Icon Position | **Prop** (`iconPosition`) | Structural variation |

### Step 3: Define TypeScript Interface

```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  iconPosition?: 'left' | 'right';
  icon?: React.ReactNode;
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}
```

### Step 4: Map Design Tokens Per Variant

```
variant="primary":
  background: --color-primary
  text: --color-primary-foreground
  hover: --color-primary/90

variant="secondary":
  background: --color-secondary
  text: --color-secondary-foreground
  hover: --color-secondary/80

variant="ghost":
  background: transparent
  text: --color-foreground
  hover: --color-muted
```

## Complex Variant Patterns

### Compound Variants

When the style depends on a COMBINATION of props:

```
variant="destructive" + size="lg" → extra padding + bolder text
variant="ghost" + disabled → no border change (already transparent)
```

Tailwind/CVA approach:
```typescript
compoundVariants: [
  { variant: 'destructive', size: 'lg', class: 'px-8 font-bold' },
  { variant: 'ghost', disabled: true, class: 'opacity-30' },
]
```

### Responsive Variants

When the variant changes by breakpoint:

```
Mobile: size="sm" (compact)
Desktop: size="md" (standard)

→ Handle via responsive className, not a responsive prop
className="text-sm md:text-base p-2 md:p-3"
```

### Nested Variants

When a parent's variant affects children:

```
Card variant="elevated" → children get shadow-md background
Card variant="flat" → children get border-only styling

→ Use CSS custom properties or context:
<Card variant="elevated">
  inherits: --card-shadow: shadow-md
</Card>
```

## Figma API Variant Extraction

When using the `figma_list_components` MCP tool, variant properties appear in the component node data:

```json
{
  "name": "Type=Primary, Size=Large, State=Default",
  "type": "COMPONENT",
  "componentProperties": {
    "Type": { "type": "VARIANT", "value": "Primary" },
    "Size": { "type": "VARIANT", "value": "Large" },
    "State": { "type": "VARIANT", "value": "Default" }
  }
}
```

Parse the `componentProperties` to auto-generate the prop interface.

## Cross-References

- [design-token-reference.md](design-token-reference.md) — Tokens applied per variant
- [component-reuse-strategy.md](component-reuse-strategy.md) — When to add a variant vs create new component
- [storybook-patterns.md](storybook-patterns.md) — Documenting variant stories

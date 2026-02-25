# Storybook Patterns — CSF3 and Autodocs

Patterns for documenting components in Storybook using Component Story Format 3 (CSF3). Every reusable component should have a story that demonstrates its variants, states, and edge cases.

## CSF3 Format

Component Story Format 3 uses object-based story definitions with a default export (meta) and named exports (stories).

### Minimal Story File

```typescript
// Button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  component: Button,
};
export default meta;

type Story = StoryObj<typeof Button>;

export const Primary: Story = {
  args: {
    variant: 'primary',
    children: 'Click me',
  },
};
```

### Full Meta Configuration

```typescript
const meta: Meta<typeof Button> = {
  component: Button,
  title: 'Components/Button',           // Sidebar hierarchy
  tags: ['autodocs'],                    // Enable autodocs page
  parameters: {
    layout: 'centered',                  // centered | fullscreen | padded
  },
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'ghost', 'destructive'],
      description: 'Visual style variant',
    },
    size: {
      control: 'radio',
      options: ['sm', 'md', 'lg'],
    },
    disabled: { control: 'boolean' },
    onClick: { action: 'clicked' },      // Log action in Actions panel
  },
  args: {                                 // Default args for all stories
    children: 'Button',
    variant: 'primary',
    size: 'md',
  },
};
```

## Story Patterns

### Variant Matrix

Show all visual variants in a single view:

```typescript
export const AllVariants: Story = {
  render: () => (
    <div className="flex gap-4">
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="destructive">Destructive</Button>
    </div>
  ),
};
```

### State Stories

One story per meaningful state:

```typescript
export const Default: Story = {
  args: { children: 'Button' },
};

export const Loading: Story = {
  args: { children: 'Saving...', loading: true },
};

export const Disabled: Story = {
  args: { children: 'Button', disabled: true },
};

export const WithIcon: Story = {
  args: { children: 'Download', icon: <DownloadIcon /> },
};
```

### Interactive Story (play function)

```typescript
import { within, userEvent, expect } from '@storybook/test';

export const ClickInteraction: Story = {
  args: { children: 'Submit' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole('button');
    await userEvent.click(button);
    await expect(button).toHaveFocus();
  },
};
```

## Autodocs

Enable auto-generated documentation pages with the `autodocs` tag:

```typescript
const meta: Meta<typeof Button> = {
  component: Button,
  tags: ['autodocs'],   // Generates a Docs page from JSDoc + argTypes
};
```

### Enhancing Autodocs

```typescript
/**
 * Primary UI button for user interactions.
 *
 * Use the `variant` prop to change visual style.
 * Supports `loading` state for async operations.
 */
export function Button({ variant, children, ...props }: ButtonProps) { ... }
```

JSDoc comments on the component become the Autodocs description. Prop types with TSDoc comments become argType descriptions.

## Story Organization

### Sidebar Hierarchy

```
Components/
├── Button         (Components/Button)
├── Input          (Components/Input)
├── Card           (Components/Card)
└── Modal          (Components/Modal)
Patterns/
├── Form           (Patterns/Form)
├── Navigation     (Patterns/Navigation)
└── Layout         (Patterns/Layout)
Pages/
├── Login          (Pages/Login)
└── Dashboard      (Pages/Dashboard)
```

### Naming Convention

| Story Export | Sidebar Entry |
|-------------|---------------|
| `Primary` | Primary |
| `WithIcon` | With Icon |
| `LongContent` | Long Content |
| `MobileLayout` | Mobile Layout |

## Essential Stories Per Component

| Component Type | Required Stories |
|---------------|-----------------|
| Button | Default, AllVariants, Disabled, Loading, WithIcon |
| Input | Default, WithLabel, WithError, Disabled, Placeholder |
| Card | Default, WithImage, WithActions, Loading, Empty |
| Modal | Open, WithForm, Confirmation, LongContent |
| List | Default, Empty, Loading, ManyItems, WithPagination |

## Accessibility Testing in Storybook

```typescript
// .storybook/main.ts
addons: ['@storybook/addon-a11y'],

// Per-story override
export const Accessible: Story = {
  parameters: {
    a11y: {
      config: {
        rules: [{ id: 'color-contrast', enabled: true }],
      },
    },
  },
};
```

## Responsive Stories

```typescript
export const Mobile: Story = {
  parameters: {
    viewport: { defaultViewport: 'mobile1' },
  },
};

export const Tablet: Story = {
  parameters: {
    viewport: { defaultViewport: 'tablet' },
  },
};
```

## Story Checklist

```
- [ ] Meta has component, title, and tags: ['autodocs']
- [ ] Default story with minimal args
- [ ] All visual variants shown
- [ ] Loading, error, disabled, empty states covered
- [ ] Edge cases (long text, missing data, overflow)
- [ ] Interactive test (play function) for key interactions
- [ ] Mobile viewport story for responsive components
- [ ] a11y addon enabled (no violations in panel)
```

## Cross-References

- [component-reuse-strategy.md](component-reuse-strategy.md) — When to create vs reuse
- [state-and-error-handling.md](state-and-error-handling.md) — States to document
- [accessibility-patterns.md](accessibility-patterns.md) — A11y testing in Storybook

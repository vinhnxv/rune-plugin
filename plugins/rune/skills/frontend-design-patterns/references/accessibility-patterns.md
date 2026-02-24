# Accessibility Patterns — WCAG 2.1 AA Compliance

Baseline accessibility requirements for all frontend components. These patterns ensure compliance with WCAG 2.1 Level AA, which covers the majority of accessibility needs for web applications.

## Four Principles (POUR)

| Principle | Meaning | Key Checks |
|-----------|---------|------------|
| **Perceivable** | Content available to all senses | Alt text, captions, contrast |
| **Operable** | Interface works via keyboard and assistive tech | Focus management, no traps |
| **Understandable** | Content and behavior are predictable | Labels, error messages, consistency |
| **Robust** | Works across browsers and assistive tech | Semantic HTML, ARIA roles |

## Color Contrast Requirements

| Element Type | Minimum Ratio | WCAG Criterion |
|-------------|---------------|----------------|
| Normal text (< 18px) | 4.5:1 | 1.4.3 |
| Large text (>= 18px or >= 14px bold) | 3:1 | 1.4.3 |
| UI components and graphical objects | 3:1 | 1.4.11 |
| Decorative elements | No requirement | — |

**Verification**: Use `contrast-ratio` or browser DevTools Accessibility panel. Never rely on visual inspection alone.

## Semantic HTML Checklist

```
- Use <button> for clickable actions, NOT <div onClick>
- Use <a href> for navigation, NOT <span onClick>
- Use <nav>, <main>, <header>, <footer>, <aside> for landmarks
- Use <h1>–<h6> in order (no skipping levels)
- Use <ul>/<ol> for lists, <table> for tabular data
- Use <label for="id"> or wrapping <label> for form inputs
- Use <fieldset> + <legend> for related form groups
```

## ARIA Usage Rules

**First rule of ARIA**: Do not use ARIA if native HTML provides the semantics.

| Pattern | Use When | Example |
|---------|----------|---------|
| `aria-label` | No visible text label | Icon-only buttons |
| `aria-labelledby` | Label exists elsewhere in DOM | Dialog titles |
| `aria-describedby` | Additional context needed | Form field hints |
| `aria-expanded` | Collapsible content | Accordions, dropdowns |
| `aria-hidden="true"` | Decorative content | Presentational icons |
| `aria-live="polite"` | Dynamic content updates | Toast notifications |
| `aria-live="assertive"` | Urgent updates | Error messages |
| `role="alert"` | Important status messages | Form validation errors |
| `role="dialog"` | Modal overlays | Confirmation dialogs |
| `role="tablist"` + `role="tab"` | Tab interfaces | Settings panels |

## Keyboard Navigation Requirements

### Focus Management

```
1. All interactive elements must be focusable (tabbable)
2. Focus order follows visual reading order (left-to-right, top-to-bottom)
3. Focus must be visible — never set outline: none without a replacement
4. Focus must not be trapped — user can always Tab away (except modals)
5. After closing a modal, return focus to the trigger element
6. After inserting dynamic content, move focus to the new content
```

### Required Keyboard Interactions

| Component | Keys | Behavior |
|-----------|------|----------|
| Button | Enter, Space | Activate |
| Link | Enter | Navigate |
| Checkbox | Space | Toggle |
| Radio group | Arrow keys | Move selection |
| Select/Dropdown | Arrow keys, Enter | Navigate and select |
| Tab panel | Arrow keys | Switch tabs |
| Modal | Escape | Close |
| Menu | Arrow keys, Escape | Navigate, close |

## Form Accessibility

```
- Every input has a visible, associated <label>
- Required fields use aria-required="true" AND visual indicator
- Error messages linked via aria-describedby
- Error messages announce via aria-live="polite"
- Form submission errors summarize all issues at top of form
- Autofocus to first error field on submission failure
```

## Image and Media

| Content Type | Requirement |
|-------------|------------|
| Informational image | `alt` describing the information conveyed |
| Decorative image | `alt=""` or `aria-hidden="true"` |
| Complex image (chart, diagram) | `alt` summary + long description link |
| Icon with meaning | `aria-label` on parent or `<title>` in SVG |
| Decorative icon | `aria-hidden="true"` |
| Video | Captions (synchronized) |
| Audio | Transcript |

## Testing Checklist

| Tool | What It Catches |
|------|----------------|
| axe DevTools | Automated WCAG violations |
| Keyboard-only navigation | Focus traps, missing interactions |
| Screen reader (VoiceOver/NVDA) | Announcement gaps, reading order |
| Browser zoom (200%) | Layout breaks at 2x zoom |
| Color blindness simulator | Color-only information |
| Lighthouse Accessibility audit | Automated scoring (aim for 90+) |

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| `<div onClick>` for buttons | Use `<button>` |
| `outline: none` without replacement | Use `outline-offset` or custom focus ring |
| Color as only status indicator | Add icon or text alongside color |
| Placeholder as label | Use a real `<label>` element |
| Auto-playing media | Add pause/stop controls |
| Infinite scroll without alternative | Provide "Load more" button option |
| Custom select without ARIA | Use native `<select>` or full ARIA combobox |

---
stack: storybook
category: design
detection:
  manifest_files: [".storybook/main.js", ".storybook/main.ts"]
  dependencies: ["@storybook/react", "@storybook/vue3"]
context_skills: ["frontend-design-patterns"]
review_agents: ["design-implementation-reviewer"]
---

# Storybook Component Development

## Detection Signals

Storybook is detected through manifest files and dependencies:

| Signal Type | Detection | Confidence |
|-------------|-----------|-----------|
| Config dir | `.storybook/main.js` or `.storybook/main.ts` | High |
| Dependencies | `@storybook/react`, `@storybook/vue3` in `package.json` | High |
| Story files | `*.stories.tsx`, `*.stories.jsx`, `*.stories.ts` in source tree | Medium |

When any signal is detected, `"storybook"` is added to `detected_stack.frameworks`.

## Context Injection

When Storybook is detected, the following skill is auto-loaded:

1. **frontend-design-patterns** — Component design systems, visual regression testing patterns, accessibility standards

### Component Story Protocol

Reviewers receive additional context when Storybook is present:
- Check for missing stories on new components
- Validate story coverage for all exported variants
- Flag components without accessibility annotations
- Verify design token usage consistency across stories

## Review Agent Selection

When Storybook is detected, `design-implementation-reviewer` participates with:
- **Activation**: `detected_stack.frameworks.includes('storybook')`
- **Scope priority**: `*.stories.tsx` > component files > style files
- **Perspective**: Component isolation, story coverage, variant completeness

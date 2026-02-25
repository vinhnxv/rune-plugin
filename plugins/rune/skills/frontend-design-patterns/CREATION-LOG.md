# Frontend Design Patterns — Creation Log

## Problem Statement
Workers implementing UI components from design specs (Figma files, screenshots, design tokens) lacked a structured knowledge base for translating design intent into production code. Common issues included: hardcoded values instead of design tokens, missing accessibility attributes, incomplete state handling (only happy-path implemented), inconsistent component reuse (duplicating instead of extending), and responsive breakpoints that didn't match design specifications. These issues were caught late in review cycles, increasing mend iterations.

## Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Inline guidance in worker prompts | Bloats worker context with static knowledge. Same patterns repeated across every `/rune:work` and `/rune:arc` invocation. Better as a loadable skill. |
| Single monolithic reference doc | Would exceed 500 lines. 10 distinct concern areas (tokens, a11y, layout, etc.) are better as focused reference files loaded on demand. |
| Framework-specific skills only | React/Vue/Next.js framework skills handle framework API patterns, not design-to-code translation. The gap is in the design interpretation layer, which is framework-agnostic. |

## Key Design Decisions
- **Non-invocable, auto-loaded**: Workers don't manually invoke design patterns — the Stacks context router loads them when frontend files are in scope. Zero user friction.
- **Framework-agnostic patterns**: Reference docs describe patterns in terms of CSS/HTML semantics and component architecture, not React JSX or Vue SFC. Framework-specific mapping is handled by the stacks framework skills.
- **10 focused reference docs (50-150 lines each)**: Each doc covers one concern area. Workers and reviewers load only what's relevant (e.g., a11y review loads `accessibility-patterns.md`, not the full skill).
- **REUSE > EXTEND > CREATE hierarchy**: Explicit decision tree for component reuse prevents the common failure mode of creating new components when existing ones could be extended.

## Iteration History
| Date | Version | Change | Trigger |
|------|---------|--------|---------|
| 2026-02-25 | v1.0 | Initial skill with 10 reference docs | Figma Design Sync Integration feature |

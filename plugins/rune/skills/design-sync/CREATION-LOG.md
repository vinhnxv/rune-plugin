# Design Sync — Creation Log

## Problem Statement
Frontend implementation workflows lacked a structured pipeline for translating Figma designs into code. Workers received Figma URLs but had no standardized process for: extracting design tokens from Figma data, creating structured specifications for implementation, verifying implementation fidelity against the design, or iterating on visual discrepancies. The result was ad-hoc implementation with inconsistent design token usage, missing responsive breakpoints, and accessibility gaps discovered only during late-stage review.

## Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Manual design handoff (screenshots + notes) | Lossy — screenshots lose token precision, variant coverage, and responsive specs. Workers guess at spacing values and color codes. |
| Figma-to-React MCP only (no orchestration) | The MCP tools generate code but don't coordinate multi-component extraction, implementation task decomposition, or fidelity verification. Raw code generation without structured specs leads to inconsistent output. |
| Single-agent design review | Catches problems after implementation but doesn't prevent them. The cost of mending design drift is 3-5x higher than extracting specs upfront. |
| Embedding extraction logic in /rune:strive | Strive is framework-agnostic — design sync is specifically a design-to-code workflow. Mixing them would bloat strive with Figma-specific logic that only applies when a Figma URL is present. |

## Key Design Decisions
- **3-phase pipeline (PLAN → WORK → REVIEW)**: Mirrors the existing arc pipeline structure. Separation ensures VSM extraction completes before implementation starts, and implementation completes before fidelity review. Each phase can be run independently via flags.
- **VSM as intermediate representation**: The Visual Spec Map decouples Figma API access from implementation. Workers read VSM files instead of calling Figma directly, reducing API calls and enabling offline implementation.
- **Conditional activation (design_sync.enabled)**: Feature is gated behind talisman config to avoid loading overhead in projects without Figma integration. The Figma MCP server costs context window for tool schemas.
- **Agent-browser degradation**: The screenshot→analyze→fix iteration loop (Phase 2.5) requires agent-browser for visual comparison. When unavailable, the pipeline degrades to code-level review only (Phase 3), which catches token/layout issues through static analysis.
- **Session isolation on state files**: Following the Rune standard (config_dir, owner_pid, session_id). Prevents cross-session interference when multiple designers run design-sync concurrently.

## Iteration History
| Date | Version | Change | Trigger |
|------|---------|--------|---------|
| 2026-02-25 | v1.0 | Initial 3-phase pipeline with VSM intermediate format | Figma Design Sync Integration feature |

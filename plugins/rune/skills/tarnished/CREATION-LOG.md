# CREATION-LOG: tarnished

## Metadata
- **Created**: 2026-02-25
- **Author**: vinhnx
- **Version**: 1.0.0
- **Skill Type**: User-invocable master command

## Purpose
Intelligent natural-language router and unified entry point for all Rune workflows.
Parses intent, checks prerequisites, and chains multi-step workflows.

## Design Decisions

### Why a separate skill (not extending `using-rune`)?
- `using-rune` is passive (non-invocable, auto-loaded) — fundamentally different role
- `/tarnished` is active (user-invocable) with `Skill` tool access to invoke other commands
- Keeping them separate means `using-rune` continues working as background router
  without the overhead of chain logic and prerequisite checking

### Why `Skill` tool instead of `Task`/`TeamCreate`?
- `/tarnished` delegates to existing skills that handle their own agent orchestration
- No need to duplicate team management — child skills own that responsibility
- Keeps `/tarnished` lightweight (routing layer only)

### Why fast-path keywords?
- Most common usage is `/tarnished plan ...`, `/tarnished work ...`, `/tarnished review ...`
- Fast-path avoids unnecessary classification overhead for 80%+ of invocations
- Natural language classification only kicks in for complex/ambiguous cases

## References
- `using-rune/SKILL.md` — passive routing skill (coexists)
- `commands/plan.md`, `commands/work.md`, `commands/review.md` — beginner aliases (coexist)
- `references/intent-patterns.md` — classification patterns
- `references/workflow-chains.md` — chain definitions
- `references/skill-catalog.md` — full skill catalog

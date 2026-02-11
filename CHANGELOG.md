# Changelog

## [1.0.1] - 2026-02-12

### Added

- Circle Registry (`rune-circle/references/circle-registry.md`) — agent-to-Runebearer mapping with audit scope priorities and context budgets
- `--focus <area>` and `--max-agents <N>` flags for `/rune:audit`
- `--partial` flag for `/rune:review` (review staged files only)
- Known Limitations and Troubleshooting sections in README
- `.gitattributes` with `merge=union` strategy for Rune Echoes files

### Fixed

- Missing cross-reference from `rune-circle/SKILL.md` to `circle-registry.md`

## [1.0.0] - 2026-02-12

### Added

- `/rune:plan` — Multi-agent planning with parallel research pipeline
  - 4 research agents (lore-seeker, realm-analyst, codex-scholar, echo-reader)
  - Optional brainstorm phase (`--brainstorm`)
  - Optional deep section-level research (`--deep`)
  - Scroll Reviewer document quality check
- `/rune:work` — Swarm work execution with self-organizing task pool
  - Rune Smith (implementation) and Trial Forger (test) workers
  - Dependency-aware task scheduling via TaskCreate/TaskUpdate
  - Auto-scaling workers (2-5 based on task count)
  - Ward Discovery Protocol for quality gates
- chronicle-miner agent (git history analysis)
- flow-seer agent (spec flow analysis)
- scroll-reviewer agent (document quality review)

## [0.3.0] - 2026-02-11

### Added

- Rune Echoes — 3-layer project memory system (Etched/Inscribed/Traced)
- `/rune:echoes` command (show, prune, reset, init)
- echo-reader research agent
- Echo persistence hooks in review and audit workflows

## [0.2.0] - 2026-02-11

### Added

- `/rune:audit` — Full codebase audit using Agent Teams
- `/rune:cancel-audit` — Cancel active audit

## [0.1.0] - 2026-02-11

### Added

- `/rune:review` — Multi-agent code review with Rune Circle lifecycle
- `/rune:cancel-review` — Cancel active review
- 5 Runebearers (Forge Warden, Ward Sentinel, Pattern Weaver, Glyph Scribe, Lore Keeper)
- 10 review agents with Truthbinding Protocol
- Rune Gaze file classification
- Inscription Protocol for agent contracts
- Context Weaving (overflow prevention, rot prevention)
- Runebinder aggregation with deduplication
- Truthsight P1 verification

# Changelog

## [1.4.2] - 2026-02-12

### Added

- **Truthbinding Protocol** for all 10 review agents — ANCHOR + RE-ANCHOR prompt injection resistance
- **Truthbinding hardening** for utility agents (runebinder, truthseer-validator) and Runebearer prompts (forge-warden, pattern-weaver, glyph-scribe, lore-keeper)
- **File scope restrictions** for work agents (rune-smith, trial-forger) — prevent modification of `.claude/`, `.github/`, CI/CD configs
- **File scope restrictions** for utility agents (scroll-reviewer, flow-seer) — context budget and scope boundaries
- **New reference files** — `rune-orchestration/references/output-formats.md` and `rune-orchestration/references/role-patterns.md` (extracted from oversized SKILL.md)

### Fixed

- **P1: Missing `Write` tool** in `cancel-review` and `cancel-audit` commands — state file updates would fail at runtime
- **P1: Missing `TaskGet` tool** in `review` and `audit` commands — task inspection during monitoring unavailable
- **P1: Missing `Edit` tool** in `echoes` command — prune subcommand could not edit memory files
- **P1: Missing `AskUserQuestion` tool** in `cleanup` command — user confirmation dialog unavailable
- **P1: Missing `allowed-tools`** in `runebearer-guide` skill — added Read, Glob
- **P1: `rune-orchestration` SKILL.md** exceeded 500-line guideline (437 lines) — reduced to 245 lines via reference extraction
- **Glyph Scribe / Lore Keeper documentation** — clarified these use inline perspectives, not dedicated agent files
- **Agent-to-Runebearer mapping** made explicit across runebearer-guide, CLAUDE.md, circle-registry
- **Skill descriptions** rewritten to third-person trigger format per Anthropic SKILL.md standard
- **`--max-agents` default** in audit command corrected from `5` to `All selected`
- **Malicious code warnings** added to RE-ANCHOR sections in all 4 Runebearer prompts
- **Table of Contents** added to `custom-runebearers.md` reference
- **`rune-gaze.md`** updated max Runebearers count to include custom Runebearers (8 via settings)
- **echo-reader** listing fixed in v1.0.0 changelog entry

## [1.4.1] - 2026-02-12

### Fixed

- **Finding prefix naming** — unified all files to canonical prefixes (BACK/QUAL/FRONT) replacing stale FORGE/PAT/GLYPH references across 9 files
- **Root README** — removed phantom `plugin.json` from structure diagram (only `marketplace.json` exists at root)
- **Missing agent definition** — added `agents/utility/truthseer-validator.md` (referenced in CLAUDE.md but file was absent)
- **Agent name validation** — added path traversal prevention rule (`^[a-zA-Z0-9_:-]+$`) to custom Runebearer validation
- **Cleanup symlink safety** — added explicit symlink detection (`-L` check) before path validation in cleanup command
- **specflow-findings.md** — moved item #7 (Custom agent templates) to Resolved table (delivered in v1.4.0)
- **Keyword alignment** — synced `plugin.json` keywords with `marketplace.json` tags (`swarm`, `planning`)
- **`--max-agents` flag** — added to `/rune:review` command (was only documented for `/rune:audit`)

## [1.4.0] - 2026-02-12

### Added

- **Custom Runebearers** — extend built-in 5 Runebearers with agents from local (`.claude/agents/`), global (`~/.claude/agents/`), or third-party plugins via `rune-config.yml`
  - `runebearers.custom[]` config with name, agent, source, workflows, trigger, context_budget, finding_prefix
  - Truthbinding wrapper prompt auto-injected for custom agents (ANCHOR + Glyph Budget + Seal + RE-ANCHOR)
  - Trigger matching: extension + path filters with min_files threshold
  - Agent resolution: local → global → plugin namespace
- **`rune-config.example.yml`** — complete example config at plugin root
- **`custom-runebearers.md`** — full schema reference, wrapper prompt template, validation rules, examples
- **Extended dedup hierarchy** — `settings.dedup_hierarchy` supports custom finding prefixes alongside built-ins
- **`settings.max_runebearers`** — configurable hard cap (default 8) for total active Runebearers
- **`defaults.disable_runebearers`** — optionally disable built-in Runebearers
- **`--dry-run` output** now shows custom Runebearers with their prefix, file count, and source

### Changed

- `/rune:review` and `/rune:audit` Phase 0 now reads `rune-config.yml` for custom Runebearer definitions
- Phase 3 spawning extended to include custom Runebearers with wrapper prompts
- Runebinder aggregation uses extended dedup hierarchy from config
- `--max-agents` flag range updated from 1-5 to 1-8 (to include custom)

## [1.3.0] - 2026-02-12

### Enhanced

- **Truthsight Verifier prompt** — added 3 missing verification tasks from source architecture:
  - Task 1: Rune Trace Resolvability Scan (validates all evidence blocks are resolvable)
  - Task 4: Cross-Runebearer Conflict Detection (flags conflicting assessments + groupthink)
  - Task 5: Self-Review Log Validation (verifies log completeness + DELETED consistency)
- **Truthsight Verifier prompt** — added Context Budget (100k token breakdown), Read Constraints (allowed vs prohibited reads), Seal Format for verifier output, Re-Verify Agent Specification (max 2, 3-min timeout), Timeout Recovery (15-min with partial output handling)
- **Structured Reasoning** — added foundational "5 Principles" framework (Forced Serialization, Revision Permission, Branching, Dynamic Scope, State Externalization) with per-level application tables
- **Structured Reasoning** — added "Why Linear Processes Degrade" motivation section, Decision Complexity Matrix, Fallback Behavior (when Sequential Thinking MCP unavailable), Token Budget specification, expanded Self-Calibration Signals and Scope Rules
- **Inscription Protocol** — expanded "Adding Inscription to a New Workflow" into full Custom Workflow Cookbook with step-by-step template, inscription.json example, verification level guide, and research workflow example

### Gap Analysis Reference

Based on comprehensive comparison of source `multi-agent-patterns` (6 files, ~2,750 lines) against Rune plugin equivalents (6 files, ~1,811 lines → now ~1,994 lines). All gaps identified in the P1-P3 priority analysis have been resolved.

## [1.2.0] - 2026-02-12

### Added

- `/rune:cleanup` command — remove `tmp/` artifacts from completed workflows, with `--dry-run` and `--all` flags
- `--dry-run` flag for `/rune:review` and `/rune:audit` — preview scope selection without spawning agents
- Runebinder aggregation prompt (`runebearer-prompts/runebinder.md`) — TOME.md generation with dedup algorithm, completion.json
- Truthseer Validator prompt (`runebearer-prompts/truthseer-validator.md`) — audit coverage validation for Phase 5.5

### Fixed

- Stale version labels: "Deferred to v1.0" → "Deferred to v2.0" in `truthsight-pipeline.md`
- Removed redundant "(v1.0)" suffixes from agent tables in `runebearer-guide/SKILL.md`

### Changed

- `specflow-findings.md` reorganized: "Resolved" table (20 items with version), "Open — Medium" (5), "Open — Low" (3)

## [1.1.0] - 2026-02-12

### Added

- 4 new Rune Circle reference files:
  - `smart-selection.md` — File-to-Runebearer assignment, context budgets, focus mode
  - `task-templates.md` — TaskCreate templates for each Runebearer role
  - `output-format.md` — Raw finding format, validated format, JSON output, TOME format
  - `validator-rules.md` — Confidence scoring, risk classification, dedup, gap reporting
- Agent Role Patterns section in `rune-orchestration/SKILL.md` — spawn patterns for Review/Audit/Research/Work/Conditional/Validation
- Truthseer Validator (Phase 5.5) for audit workflows — cross-references finding density against file importance
- Seal Format specification in `rune-circle/SKILL.md` with field table and completion signal
- Output Directory Structure showing all expected files per workflow
- JSON output format (`{runebearer}-findings.json`) and `completion.json` structured summary

### Changed

- `inscription-protocol.md` expanded from 184 to 397 lines:
  - Authority Precedence rules, Coverage Matrix, Full Prompt Injection Template
  - Truthbinding Protocol with hallucination type table
  - 3-Tier Clarification Protocol, Self-Review Detection Heuristics
  - State File Integration with state transitions
  - Per-Workflow Adaptations with output sections
- `truthsight-pipeline.md` expanded from 121 to 280+ lines:
  - Circuit breaker state machines (CLOSED/OPEN/HALF_OPEN) for Layer 0 and Layer 2
  - Sampling strategy table, 5 verification tasks, hallucination criteria
  - Context budget table, verifier output format, timeout recovery
  - Re-verify agent decision logic, integration points
- `rune-circle/SKILL.md` Phase 6 (Verify) with detailed Layer 0/1/2 inline validation

### Fixed

- Stray "review-teams" reference replaced with "Rune Circle"

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
  - 3 new research agents (lore-seeker, realm-analyst, codex-scholar) plus echo-reader (from v0.3.0)
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

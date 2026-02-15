# Changelog

## [1.23.0] - 2026-02-15

Feature release: Phase 2 BRIDGE — event-driven agent synchronization via Claude Code hooks. Replaces 30-second `TaskList()` polling with filesystem signal files written by `TaskCompleted` and `TeammateIdle` hooks. Average task-completion detection latency drops from ~15 seconds to ~2.5 seconds with near-zero token cost. Automatic fallback to Phase 1 polling when hooks or `jq` are unavailable.

### Added

- **Event-driven synchronization** — `TaskCompleted` hook writes signal files (`tmp/.rune-signals/{team}/{task_id}.done`) on task completion; monitor utility detects signals via 5-second filesystem checks instead of 30-second API polling
- **Quality gate enforcement** — `TeammateIdle` hook validates teammate output files exist and are non-empty before allowing idle; checks for SEAL markers on review/audit workflows (hard gate — blocks idle until output passes)
- **Hook scripts**: `scripts/on-task-completed.sh` (signal file writer with atomic temp+mv, `.all-done` sentinel when all expected tasks complete) and `scripts/on-teammate-idle.sh` (output file quality gate with inscription-based expected output lookup)
- **Hook configuration**: `hooks/hooks.json` registers both hooks with `${CLAUDE_PLUGIN_ROOT}` path resolution and appropriate timeouts (10s for TaskCompleted, 15s for TeammateIdle)
- **Dual-path monitoring** in `monitor-utility.md` — signal-driven fast path (5s filesystem check, near-zero token cost) with automatic fallback to Phase 1 polling (30s `TaskList()` calls) when signal directory is absent
- **Signal directory lifecycle** (`tmp/.rune-signals/{team}/`) — created by orchestrator before spawning Ashes (with `.expected` count file and `inscription.json`), cleaned up in workflow Phase 7 and `/rune:rest`

### Changed

- plugin.json: version 1.22.0 → 1.23.0
- marketplace.json: version 1.22.0 → 1.23.0
- CLAUDE.md: Added Hook Infrastructure section documenting TaskCompleted and TeammateIdle hooks

### Prerequisites

- **`jq` required** for hook scripts — used for safe JSON parsing and construction. If `jq` is not installed, hook scripts exit 0 with a stderr warning and the monitor falls back to Phase 1 polling automatically. Install: `brew install jq` (macOS) or `apt-get install jq` (Debian/Ubuntu).

### Migration Notes

- **No breaking changes** — Phase 2 is purely additive. Existing workflows continue to work unchanged via automatic polling fallback.
- Signal directories are scoped per team name (`rune-*` prefix guard) and do not interfere with non-Rune tasks.
- Hook scripts validate input defensively: non-Rune tasks, missing signal directories, and parse failures all exit 0 silently.
- Rollback: delete `hooks/hooks.json` and remove signal directory setup from commands. The shared monitor automatically falls back to polling when signal directory is absent.

## [1.22.0] - 2026-02-15

Feature release: Nelson-inspired anti-pattern library, damage control procedures, risk-tiered task classification, file ownership model, and structured checkpoint reporting. Based on cross-plugin analysis of Nelson's Royal Navy orchestration patterns adapted to Rune's Elden Ring lore.

### Added

- **Standing Orders** (`standing-orders.md`) — 6 named anti-patterns with observable symptoms, decision tables, remedy procedures, and cross-references: SO-1 Hollow Ash (over-delegation), SO-2 Shattered Rune (file conflicts), SO-3 Tarnished Smith (lead implementing), SO-4 Blind Gaze (skipping classification), SO-5 Ember Overload (context overflow), SO-6 Silent Seal (malformed output)
- **Damage Control** (`damage-control.md`) — 6 recovery procedures with ASSESS/CONTAIN/RECOVER/VERIFY/REPORT format and double-failure escalation: DC-1 Glyph Flood (context overflow), DC-2 Broken Ward (quality failure), DC-3 Fading Ash (agent timeout), DC-4 Phantom Team (lifecycle failure), DC-5 Crossed Runes (concurrent workflows), DC-6 Lost Grace (session loss)
- **Risk Tiers** (`risk-tiers.md`) — 4-tier deterministic classification (Tier 0 Grace, Tier 1 Ember, Tier 2 Rune, Tier 3 Elden) with 4-question decision tree, file-path fallback heuristic, graduated verification matrix, failure-mode checklist for Tier 2+, and TaskCreate metadata format
- **File Ownership** in `/rune:work` — EXTRACT/DETECT/RESOLVE/DECLARE algorithm for preventing concurrent file edits. Ownership encoded in task descriptions (persists across auto-release reclaim). Directory-level by default, exact-file overrides when specific.
- **Checkpoint Reporting** in `monitor-utility.md` — `onCheckpoint` callback with milestone-based template (25%, 50%, 75% + blocker detection). Displays progress, active tasks, blockers, and decision recommendation.
- work.md: Phase 1 risk tier classification via 4-question decision tree (parse-plan.md)
- work.md: Phase 1 file target extraction from task descriptions (parse-plan.md)
- work.md: Phase 1 file ownership conflict detection with automatic serialization via `blockedBy`
- work.md: TaskCreate now includes `risk_tier`, `tier_name`, `file_targets` metadata and ownership in description
- worker-prompts.md: Step 4.5 File Ownership section in rune-smith and trial-forger prompts
- worker-prompts.md: Step 4.6 Risk Tier Verification with per-tier requirements

### Changed

- plugin.json: version 1.21.1 → 1.22.0
- marketplace.json: version 1.21.1 → 1.22.0
- work.md: Error handling table updated — file conflicts now resolved via ownership serialization
- work.md: Common pitfalls table updated — workers editing same files prevented by Phase 1 step 5.1

## [1.21.1] - 2026-02-15

### Security

- **fix(security)**: Eliminate `$()` command substitution in talisman `verification_patterns` interpolation. All consumer sites now use `safeRgMatch()` (`rg -f`) instead of double-quoted Bash interpolation. Affects ward-check.md, verification-gate.md, and plan-review.md pseudocode. Added `safeRgMatch()` helper to security-patterns.md. Updated SAFE_REGEX_PATTERN threat model from "Accepted Risk" to "Mitigated".

## [1.21.0] - 2026-02-15

### Changed

- Dynamic team lifecycle cleanup refactor — pre-create guards, dynamic member discovery, validated rm -rf

## [1.20.0] - 2026-02-15

### Changed

- Consolidated agent frontmatter + security hardening across commands
- Fix 13 TOME findings + structural refactor into references
- Extract shared monitor utility from 7 commands
- Fix 6 TOME findings from monitor-utility code review

## [1.19.0] - 2026-02-15

Feature release: 5 structural recommendations from cross-cycle meta-analysis of 224 findings across 8 review cycles. Addresses recurring systemic issues in the plugin's documentation-as-specification architecture.

### Added

- **R1: security-patterns.md** — Canonical reference file for all security validation patterns (SAFE_*, CODEX_*, FORBIDDEN_KEYS, BRANCH_RE). Located at `plugins/rune/skills/roundtable-circle/references/security-patterns.md`. Each pattern has regex value, threat model, ReDoS assessment, consumer file list, and machine-parseable markers. Sync comments added to all 4 consumer command files (plan.md, work.md, arc.md, mend.md).
- **R1: Arc Phase 2.7 enforcement** — Verification gate check for undocumented inline SAFE_*/ALLOWLIST declarations missing security-patterns.md references.
- **R2: Documentation Impact** — New section in Standard plan template (between Dependencies & Risks and Cross-File Consistency) with structured checklist for version bumps, CHANGELOG, and registry updates. Comprehensive template merges with existing Documentation Plan.
- **R2: Reviewer integration** — decree-arbiter and knowledge-keeper agents now evaluate Documentation Impact completeness during Phase 4C plan review.
- **R3: Phase 4.3 Doc-Consistency** — Orchestrator-only non-blocking sub-phase in work.md between Phase 4 (ward check) and Phase 4.5 (Codex Advisory). Detects version/count drift using talisman-based extractors. Talisman fallback chain: `work.consistency.checks` → `arc.consistency.checks` → defaults.
- **R4: STEP 4.7 Plan Section Coverage** — Enhancement to arc.md Phase 5.5 (GAP ANALYSIS) that cross-references plan H2/H3 headings against committed code. Reports ADDRESSED/MISSING/CLAIMED status in gap-analysis.md.
- **R5: Phase 5.5 Cross-File Mend** — Orchestrator-only cross-file resolution for SKIPPED findings with "cross-file dependency" reason. Caps at 5 findings, 5 files per finding. Atomic rollback via edit log on partial failure.
- **R5: Phase 5.6 Second Ward Check** — Validates cross-file fixes with conservative revert-all on ward failure.
- **R5: FIXED_CROSS_FILE status** — New resolution status in mend resolution reports.
- talisman.example.yml: `work.consistency.checks` schema documentation

### Changed

- decree-arbiter now evaluates 9 dimensions (was 6): architecture fit, feasibility, security/performance risks, dependency impact, pattern alignment, internal consistency, design anti-pattern risk, consistency convention, documentation impact
- mend.md: MEND-3 (Doc-Consistency) renumbered to Phase 5.7
- mend.md: Fixer prompt updated to report `needs: [file1, file2]` format for cross-file dependencies
- mend.md: Phase overview diagram updated with new phases (5.5, 5.6, 5.7)
- mend.md: Resolution report template includes `Fixed (cross-file)` count

## [1.18.2] - 2026-02-15

Bug fix: Arc Phase 1 (FORGE) now delegates to `/rune:forge` logic instead of using a hardcoded inline implementation. This restores Forge Gaze topic matching, Codex Oracle, custom Ashes, and section-level enrichment to the arc pipeline.

### Fixed

- arc.md: Phase 1 (FORGE) refactored from inline 5-agent implementation to delegation to `/rune:forge` logic, consistent with Phase 5/6/8 delegation pattern
- arc.md: Phase 1 now includes Forge Gaze topic-to-agent matching (section-level enrichment instead of bulk research)
- arc.md: Phase 1 now includes Codex Oracle when `codex` CLI is available (was missing since v1.18.0)
- arc.md: Phase 1 now includes custom Ashes from talisman.yml with `workflows: [forge]`

### Changed

- forge.md: Added arc context detection (`planPath.startsWith("tmp/arc/")`) to skip interactive phases (scope confirmation, post-enhancement options) when invoked by `/rune:arc`
- arc.md: Per-Phase Tool Restrictions table updated for Phase 1 delegation

## [1.18.0] - 2026-02-14

Feature release: Codex Oracle — cross-model verification Ash using OpenAI's Codex CLI (GPT-5.3-codex). Auto-detected when `codex` CLI is installed, providing a second AI perspective across review, audit, plan, forge, and work pipelines.

### Added

- plan.md: Phase 1C Codex Oracle research agent — conditional third external research agent alongside practice-seeker and lore-scholar, with HALLUCINATION GUARD and `[UNVERIFIED]` marking for unverifiable claims
- plan.md: Phase 4.5 (Plan Review) Codex plan reviewer (formerly Phase 4C) — optional plan review with `[CDX-PLAN-NNN]` finding format, parallel with decree-arbiter and knowledge-keeper
- plan.md: Cross-model research dimension in Standard/Comprehensive template References section
- plan.md: Updated research scope preview and pipeline overview to show Codex Oracle conditionals
- work.md: Phase 4.5 Codex Advisory — non-blocking, plan-aware implementation review after Post-Ward Verification Checklist. Compares diff against plan for requirement coverage gaps. `[CDX-WORK-NNN]` warnings at INFO level.
- work.md: Codex advisory reference in PR body template
- forge.md: Codex Oracle in Forge Gaze topic registry — cross-model enrichment with threshold_override 0.25, topics: security, performance, api, architecture, testing, quality
- CLAUDE.md: Codex Oracle added to Ash table (6th built-in Ash) with inline perspectives via codex exec
- README.md: Codex Oracle feature section with How It Works, Cross-Model Verification, Prerequisites, and Configuration
- README.md: Optional codex CLI in Requirements section

### Changed

- plugin.json: version 1.17.0 → 1.18.0
- CLAUDE.md: "5 built-in Ashes" → "6 built-in Ashes" in review and audit command descriptions
- CLAUDE.md: max_ashes comment updated from "5 built-in + custom" to "6 built-in + custom"
- CLAUDE.md: dedup_hierarchy updated to include CDX prefix: `[SEC, BACK, DOC, QUAL, FRONT, CDX]`
- README.md: Ash table expanded with Codex Oracle row
- README.md: max_ashes comment updated from "5 built-in + custom" to "6 built-in + custom"

### Configuration

New `codex` top-level key in talisman.yml:

```yaml
codex:
  disabled: false
  model: "gpt-5.3-codex"
  reasoning: "high"
  sandbox: "read-only"
  context_budget: 20
  confidence_threshold: 80
  workflows: [review, audit, plan, forge, work]
  work_advisory:
    enabled: true
    max_diff_size: 15000
  verification:
    enabled: true
    fuzzy_match_threshold: 0.7
    cross_model_bonus: 0.15
```

### Migration Notes

- **No breaking changes** — Codex Oracle is purely additive, auto-detected when CLI available
- Existing workflows unaffected when `codex` CLI is not installed (silent skip)
- Disable via `codex.disabled: true` in talisman.yml as runtime kill switch
- Codex Oracle counts toward max_ashes cap (6 built-in + 2 custom = 8 default cap)

## [1.17.0] - 2026-02-14

Feature release: Doc-consistency ward with cross-file drift prevention for arc and mend pipelines.

### Added

- arc.md: Phase 5.5 doc-consistency sub-step — detects drift between source-of-truth files and their downstream targets using declarative `arc.consistency.checks` schema in talisman.yml
- arc.md: DEFAULT_CONSISTENCY_CHECKS fallbacks — version_sync (plugin.json ↔ README/CLAUDE.md) and agent_count (agents/review/*.md ↔ CLAUDE.md)
- arc.md: 4 extractors — `json_field` (JSON dot-path), `regex_capture` (regex group), `glob_count` (file count), `line_count` (line count)
- arc.md: Safety validators — `SAFE_REGEX_PATTERN_CC`, `SAFE_PATH_PATTERN_CC`, `SAFE_DOT_PATH` for consistency check inputs
- mend.md: MEND-3 doc-consistency pass — runs after ward check passes, applies topological sort for cross-file dependencies, Edit-based auto-fixes
- mend.md: DAG cycle detection (DFS-based) for consistency check dependency graphs
- mend.md: Prototype pollution guard for JSON field extraction (`__proto__`, `constructor`, `prototype` blocked)
- plan.md: Cross-File Consistency section in Standard/Comprehensive plan templates
- plan.md: Phase-aware `verification_patterns` with configurable `phase` field
- talisman.example.yml: `arc.consistency.checks` schema with 3 examples (version_sync, agent_count, method_count)

### Changed

- plugin.json: version 1.16.0 → 1.17.0
- marketplace.json: version 1.16.0 → 1.17.0
- README.md: Version updated to 1.17.0

## [1.16.0] - 2026-02-14

Feature release: BMAD elicitation methods integration — 22-method curated registry with phase-aware selection.

### Added

- skills/elicitation/SKILL.md — context-aware method selection skill with CSV registry, tier system, and auto-selection algorithm
- skills/elicitation/methods.csv — 22-method registry (14 Tier 1, 8 Tier 2) covering structured reasoning techniques
- skills/elicitation/references/phase-mapping.md — method-to-phase mapping with workflow integration points
- skills/elicitation/references/examples.md — output templates for each Tier 1 method
- commands/elicit.md — standalone `/rune:elicit` command for manual method invocation
- forge-gaze.md: Elicitation Methods section with Method Budget (MAX_METHODS_PER_SECTION=2)
- ward-sentinel: Red Team/Blue Team analysis structure
- mend-fixer.md: 5 Whys root cause protocol for P1/recurring findings
- scroll-reviewer.md: Self-Consistency and Critical Challenge review dimensions

### Changed

- plan.md: Step 3.5 elicitation offering after brainstorm phase
- plan.md, forge.md, arc.md: Load elicitation skill
- CLAUDE.md: Updated skill table (6 skills), command table (13 commands)
- plugin.json: version 1.15.0 → 1.16.0

## [1.15.0] - 2026-02-14

Feature release: BMAD-inspired quality improvements across plan, work, and review pipelines.

### Added

- plan.md Phase 1A: Research scope preview — transparent announcement before agent spawning
- plan.md Phase 4B.5: Verification gate checks e-h — time estimate ban, CommonMark compliance, acceptance criteria measurability, filler phrase detection
- plan.md: Source citation enforcement for research agents (practice-seeker, lore-scholar)
- work.md Phase 0: Previous Shard Context for multi-shard plans
- work.md: Disaster Prevention in worker/tester self-review checklists
- work.md Phase 4: Post-ward checks 7-9 — docstring coverage, import hygiene, code duplication detection
- work.md: Branch name validation and glob metacharacter escaping (security hardening)
- review.md Phase 5: Zero-finding warning for suspiciously empty Ash outputs (>15 files, 0 findings)
- review.md Phase 7: Explicit `/rune:mend` offer with P1/P2 finding counts
- scroll-reviewer.md: Time estimate ban, writing style rules, traceability checks

### Changed

- plugin.json: version 1.14.0 → 1.15.0

## [1.14.0] - 2026-02-13

Patch release: marketplace version synchronization.

### Changed

- marketplace.json: version synced to 1.14.0 (was out of sync with plugin.json)

## [1.13.0] - 2026-02-13

Feature release: 4-part quality improvement for `/rune:arc` pipeline.

**Part 1 — Convergence Gate**: Phase 7.5 (VERIFY MEND) between mend and audit detects regressions introduced by mend fixes, retries mend up to 2x if P1 findings remain, and halts on divergence (whack-a-mole prevention).

**Part 2 — Work/Mend Agent Quality**: Self-review steps, pre-fix context analysis, and expanded verification reduce bugs at source. Root cause: 57% of review findings originated in the work phase, 43% in mend regressions.

**Part 3 — Plan Section Convention**: Requires contract headers (Inputs/Outputs/Preconditions/Error handling) before pseudocode blocks in plans. Root cause: 73% of work-origin bugs traced back to the plan itself — undefined variables, missing error handling, and plan-omitted details. Plans with contracts (v1.11.0) needed only 2 fix rounds; plans without (v1.12.0) needed 5.

**Part 4 — Implementation Gap Analysis**: Phase 5.5 between WORK and CODE REVIEW. Deterministic, orchestrator-only check that cross-references plan acceptance criteria against committed code. Zero LLM cost. Advisory only (warns but never halts). Fills an ecosystem-wide gap — no AI coding agent performs automated plan-to-code compliance checking.

### Added

- arc.md: Phase 7.5 VERIFY MEND — orchestrator-only convergence gate with single Explore subagent spot-check. Parses mend resolution report for modified files, runs targeted regression detection (removed error handling, broken imports, logic inversions, type errors), compares finding counts against TOME baseline.
- arc.md: Convergence decision matrix — CONVERGED (no P1 + findings decreased), RETRY (P1 remaining + rounds left), HALTED (diverging or circuit breaker exhausted). Max 2 retries (3 total mend passes).
- arc.md: Mini-TOME generation for retry rounds — converts SPOT:FINDING markers to RUNE:FINDING format so mend can parse them normally. Findings prefixed `SPOT-R{round}-{NNN}`.
- arc.md: Checkpoint schema v3 with `convergence` object tracking round count, max rounds, and per-round history (findings before/after, P1 count, verdict, timestamp).
- arc.md: Schema v2→v3 migration in `--resume` logic (adds verify_mend as "skipped" + empty convergence object for backward compatibility).
- arc.md: Reduced mend timeout for retry rounds (8 min vs 16 min initial) since retry rounds target fewer findings.
- cancel-arc.md: Added verify_mend to legacyMap (orchestrator-only, no team) and cancellation table.
- plan.md: Plan Section Convention — "Contracts Before Code" subsection with required structure template (Inputs/Outputs/Preconditions/Error handling before pseudocode), 4 rules for pseudocode in plans, good/bad examples.
- arc.md: Phase 2.7 check #6 — contract header verification for pseudocode sections (checks **Inputs**, **Outputs**, **Error handling** headers before code blocks).
- work.md: Worker NOTE about plan pseudocode — implement from contracts, not by copying code verbatim.
- work.md: Self-review step 6.5 for rune-smith prompt — re-read changed files, verify identifiers, function signatures, no dead code.
- work.md: Self-review step 6.5 for trial-forger prompt — check test isolation, imports, assertion specificity.
- work.md: Self-review key principle and 2 additional pitfall rows (copy-paste from plan, mend regressions).
- rune-smith.md: Rule 7 — self-review before completion (re-read files, check identifiers, function signatures).
- rune-smith.md: Rule 8 — plan pseudocode is guidance, not gospel (implement from contracts, verify variables exist).
- mend-fixer.md: Step 2 expanded with pre-fix context analysis (Grep for callers, trace data flow, check identifiers).
- mend-fixer.md: Step 4 expanded with thorough post-fix validation (identifier consistency, function signatures, regex patterns, constants/defaults).
- mend.md: Inline fixer prompt lifecycle expanded to 3-step (PRE-FIX analysis, implement, POST-FIX verification).
- arc.md: Phase 5.5 IMPLEMENTATION GAP ANALYSIS — deterministic, orchestrator-only check that cross-references plan acceptance criteria against committed code. Zero LLM cost. Gap categories: ADDRESSED, MISSING, PARTIAL. Advisory only — warns but never halts.
- arc.md: Checkpoint schema v4 with `gap_analysis` phase entry + v3→v4 migration in `--resume` logic.
- arc.md: Truthbinding ANCHOR/RE-ANCHOR sections added to spot-check Explore subagent prompt (was the only agent prompt without them).
- arc.md: Mini-TOME description sanitization — strips HTML comments, newlines, truncates to 500 chars to prevent marker corruption.
- arc.md: Spot-check finding scope validation — filters to only files in mendModifiedFiles and valid P1/P2/P3 severity.
- arc.md: Empty convergence history guard — prevents array index error on first round.
- arc.md: Checkpoint max_rounds capped against CONVERGENCE_MAX_ROUNDS constant.

### Changed

- arc.md: PHASE_ORDER expanded from 8 to 10 phases (added gap_analysis between work and code_review, verify_mend between mend and audit)
- arc.md: Pipeline Overview diagram updated with Phase 7.5 and convergence loop arrows
- arc.md: Phase Transition Contracts table updated with MEND→VERIFY_MEND and VERIFY_MEND→MEND (retry) handoffs
- arc.md: Completion Report now includes convergence summary with per-round finding trend
- arc.md: Checkpoint initialized with schema_version 4 (was 3)
- arc.md: Spot-check no-output default changed from "converged" to "halted" (fail-closed)
- plan.md: Line 657 "illustrative pseudocode" strengthened with cross-reference to Plan Section Convention
- plan.md: Comprehensive Template's Technical Approach section now references Plan Section Convention
- rune-smith.md: Rule 1 expanded from "Read before write" to "Read the FULL target file" (understand imports, constants, siblings)
- mend-fixer.md: Steps 2 and 4 now require context analysis before fixes and thorough validation after
- CLAUDE.md: Arc Pipeline description updated to mention gap analysis and convergence gate (10 phases)
- CLAUDE.md: Key Concepts updated with Implementation Gap Analysis (Phase 5.5) and Plan Section Convention
- README.md: Arc Mode section updated to 10 phases with GAP ANALYSIS and VERIFY MEND descriptions
- README.md: Key Concepts updated with Plan Section Convention
- team-lifecycle-guard.md: Arc phase table updated (Phases 2.5, 2.7, 5.5, 7.5 are orchestrator-only)
- team-lifecycle-guard.md: Mend team naming pattern corrected from `mend-{timestamp}` to `rune-mend-{id}`
- cancel-arc.md: Added gap_analysis to legacyMap and cancellation table (orchestrator-only)
- rune-smith.md: Step 6 changed from "Commit changes" to "Generate patch for commit broker"
- plan.md: Fixed unquoted shell paths and invalid `result.matchCount` in talisman verification patterns
- All files: "Reserved for v1.13.0" references updated to "Reserved for a future release"
- plugin.json: version 1.12.0 → 1.13.0

### Migration Notes

- **No breaking changes** — existing checkpoints auto-migrate v2→v3→v4 on `--resume`
- The convergence gate is automatic and requires no user configuration
- Gap analysis is advisory only — warns but never halts the pipeline
- Standalone `/rune:mend` and `/rune:review` are completely unaffected
- Old checkpoints resumed with new code skip verify_mend and gap_analysis (marked "skipped")

## [1.12.0] - 2026-02-13

Feature release: Ship workflow gaps — adds branch setup, plan clarification, quality verification checklist, PR creation, enhanced completion report, and key principles to `/rune:work`. Closes the "last mile" from plan → commits → PR in a single invocation.

### Added

- work.md: Phase 0.5 ENVIRONMENT SETUP — branch safety check warns when on default branch, offers feature branch creation with `rune/work-{slug}-{timestamp}` naming (reuses arc COMMIT-1 pattern). Dirty working tree detection with stash offer. Skip detection for arc invocation.
- work.md: Phase 0 PLAN CLARIFICATION — ambiguity detection sub-step after task extraction. Flags vague descriptions, missing dependencies, unclear scope. AskUserQuestion with clarify-now vs proceed-as-is options.
- work.md: Phase 4 POST-WARD VERIFICATION CHECKLIST — deterministic checks at zero LLM cost: incomplete tasks, unchecked plan items, blocked tasks, uncommitted patches, merge conflict markers, dirty working tree.
- work.md: Phase 6.5 SHIP — optional PR creation after cleanup. Pre-checks `gh` CLI availability and auth. PR body generated from plan context (diff stats, task list, ward results) and written to file (shell injection prevention). Talisman-configurable monitoring section and co-authors.
- work.md: ENHANCED COMPLETION REPORT — includes branch name, duration, artifact paths. Smart review recommendation heuristic (security files → recommended, large changeset → recommended, config files → suggested, small → optional). Interactive AskUserQuestion next steps.
- work.md: KEY PRINCIPLES section — orchestrator guidelines (ship complete, fail fast on ambiguity, branch safety, serialize git) and worker guidelines (match patterns, test as you go, one task one patch, don't over-engineer, exit cleanly).
- work.md: COMMON PITFALLS table — 9 pitfalls with prevention strategies.
- talisman.example.yml: 6 new keys under `work:` — `skip_branch_check`, `branch_prefix`, `pr_monitoring`, `pr_template`, `auto_push`, `co_authors`.
- Updated Pipeline Overview diagram to show all phases including 0.5, 3.5, 6, and 6.5.

### Changed

- work.md: Pipeline Overview expanded from 7 to 10 phases (including sub-phases 0.5, 3.5, 6.5)
- plugin.json: version 1.11.0 → 1.12.0

### Migration Notes

- **No breaking changes** — all new features are opt-in
- Users on default branch will see new branch creation prompt (disable via `work.skip_branch_check: true`)
- PR creation requires GitHub CLI (`gh`) authentication — install: https://cli.github.com/

## [1.11.0] - 2026-02-13

Feature release: Arc pipeline expanded from 6 to 8 phases with plan refinement, verification gate, per-phase time budgets, and checkpoint schema v2.

### Added

- arc.md: Phase 2.5 PLAN REFINEMENT — orchestrator-only concern extraction from CONCERN verdicts into `concern-context.md` for worker awareness. All-CONCERN escalation via AskUserQuestion
- arc.md: Phase 2.7 VERIFICATION GATE — deterministic zero-LLM checks (file references, heading links, acceptance criteria, TODO/FIXME, talisman patterns). Git history annotation for stale file references
- arc.md: `PHASE_ORDER` constant — canonical 8-element array for resume validation by name, not sequence numbers
- arc.md: `PHASE_TIMEOUTS` — per-phase hardcoded time budgets (delegated phases use inner-timeout + 60s buffer). `ARC_TOTAL_TIMEOUT` (90 min) and `STALE_THRESHOLD` (5 min)
- arc.md: Checkpoint schema v2 — adds `schema_version: 2`, `plan_refine` and `verification` phase entries
- arc.md: Backward-compatible checkpoint migration — auto-upgrades v1 checkpoints on read (inserts new phases as "skipped")
- arc.md: Timeout monitoring in Phase 1 (FORGE) and Phase 2 (PLAN REVIEW) polling loops with completion-before-timeout check, stale detection, and final sweep
- arc.md: `parseVerdict()` function with anchored regex for structured verdict extraction
- arc.md: Concern context propagation — Phase 5 (WORK) worker prompts include concern-context.md when available
- cancel-arc.md: Added `plan_refine` and `verification` to legacy team name map (both null — orchestrator-only)
- cancel-arc.md: Null-team guard — orchestrator-only phases skip team cancellation (Steps 3a-3d)
- cancel-arc.md: Updated cancellation table and report template to 8 phases
- talisman.example.yml: Commented-out `arc.timeouts` section documenting per-phase defaults (for v1.12.0+)

### Changed

- arc.md: Renumbered phases — WORK (3→5), CODE REVIEW (4→6), MEND (5→7), AUDIT (6→8)
- arc.md: Updated all tables (Phase Transition Contracts, Tool Restrictions, Failure Policy, Completion Report, Error Handling)
- arc.md: `--approve` flag documentation updated "Phase 3 only" → "Phase 5 only"
- arc.md: Branch strategy updated "Before Phase 3" → "Before Phase 5"
- work.md: Updated arc cross-references — Phase 3 → Phase 5, Phase 5 → Phase 7
- CLAUDE.md: Arc pipeline description updated to 8 phases with plan refinement and verification
- CLAUDE.md: Arc artifact list updated with `concern-context.md` and `verification-report.md`
- README.md: Arc phase list expanded to 8 phases with Phase 2.5 and 2.7
- README.md: "6 phases" → "8 phases" in Key Concepts
- Root README.md: Pipeline diagram and command table updated for 8-phase arc
- team-lifecycle-guard.md: Updated arc phase rows for Phases 2.5/2.7 (orchestrator-only) and 5-8 (delegated)

## [1.10.6] - 2026-02-13

Documentation normalization: Replace tiered agent rules (1-2/3-4/5+ tiers) with a single rule — all Rune multi-agent workflows use Agent Teams. Custom (non-Rune) workflows retain the 3+ agent threshold for Agent Teams requirement. Codifies what every command has done since v0.1.0 and eliminates a persistent design-vs-implementation gap across framework documentation.

### Changed

- CLAUDE.md: Replaced 3-row tiered Multi-Agent Rules table with single-row "All Rune multi-agent workflows" rule
- context-weaving/SKILL.md: Updated "When to Use" table — removed 3-4/5+ agent tiers, unified to "Any Rune command"
- context-weaving/SKILL.md: Simplified Thought 2 strategy block from 3 tiers to 2 lines (Rune + custom)
- overflow-wards.md: Simplified ASCII decision tree from 3 branches to 2 (Rune command + custom workflow)
- rune-orchestration/SKILL.md: Removed dead `Task x 1-2` branch from inscription protocol rule
- inscription-protocol.md: Updated coverage matrix — removed "Single agent / Glyph Budget only" row, added `/rune:mend`
- inscription-protocol.md: Removed conditional '(when 3+)' qualifier from `/rune:work` inscription requirement — inscription now unconditional for all Rune workflows
- inscription-protocol.md: Updated Step 4 verification table — all sizes use Agent Teams, verification scales with team size
- structured-reasoning.md: Updated Thought 2 from "Task-only, Agent Teams, or hybrid?" to deterministic Agent Teams rule
- task-templates.md: Added "Platform reference" note to Task Subagent template — Rune commands use Background Teammate

## [1.10.5] - 2026-02-13

Feature release: Structured review checklists for all 10 review agents. Each agent now has a `## Review Checklist` section with 3 subsections — agent-specific Analysis Todo, shared Self-Review quality gate, and shared Pre-Flight output gate. Improves review consistency and completeness.

### Added

- ward-sentinel.md: 10-item Analysis Todo (injection, auth, secrets, input validation, CSRF, agent injection, crypto, error responses, CORS, CVEs)
- flaw-hunter.md: 8-item Analysis Todo (nullable returns, empty collections, off-by-one, race conditions, silent failures, exhaustive handling, TOCTOU, missing await)
- pattern-seer.md: 7-item Analysis Todo (naming conventions, file organization, error handling, imports, service naming, API format, config patterns)
- simplicity-warden.md: 7-item Analysis Todo (single-impl abstractions, unnecessary factories, one-use helpers, speculative config, indirection, over-parameterization, justified abstractions)
- ember-oracle.md: 8-item Analysis Todo (N+1 queries, O(n²) algorithms, sequential awaits, blocking calls, pagination, memory allocation, caching, missing indexes)
- rune-architect.md: 7-item Analysis Todo (layer boundaries, dependency direction, circular deps, SRP, service boundaries, god objects, interface segregation)
- mimic-detector.md: 6-item Analysis Todo (identical logic, duplicated validation, repeated error handling, copy-pasted test setup, near-duplicates, intentional similarity)
- wraith-finder.md: 6-item Analysis Todo (unused functions, unreachable code, commented blocks, unused imports, orphaned files, phantom-checker cross-check)
- void-analyzer.md: 6-item Analysis Todo (TODO markers, stubs, missing error handling, placeholders, partial implementations, docstring promises)
- phantom-checker.md: 6-item Analysis Todo (string-based refs, framework registration, plugin systems, re-exports, partial matches, config references)
- All 10 agents: Shared Self-Review subsection (5 evidence/quality checks)
- All 10 agents: Shared Pre-Flight subsection (5 output format checks with agent-specific finding prefixes; phantom-checker uses variant Pre-Flight with categorization-based output)

### Fixed

- mend.md: Added SAFE_WARD regex validation to Phase 5 ward check (consistency with work.md SEC-012 fix)
- mend.md: Moved identifier validation before state file write in Phase 2 (BACK-013 validation ordering)
- mend.md: Added validation comment to Phase 6 cleanup rm -rf (SEC-014)
- work.md: Added validation comment to Phase 6 cleanup rm -rf (SEC-013)
- README.md: Updated version from 1.10.4 to 1.10.5 in plugins table (DOC-014 version drift)

## [1.10.4] - 2026-02-13

Patch release: codex-cli audit hardening — 7 active findings + 3 already-fixed (forge-enriched), plus 7 deep-dive findings (logic conflicts, documentation drift, design inconsistencies). All changes are markdown command specifications only.

### Added

- review.md: Unified scope builder — default mode now includes committed + staged + unstaged + untracked files (was committed-only). Displays scope breakdown summary.
- review.md, audit.md, work.md: Named timeout constants (POLL_INTERVAL, STALE_THRESHOLD, TOTAL_TIMEOUT) with hard timeout and final sweep in all monitor loops
- work.md: Commit broker — workers write patches to `tmp/work/{timestamp}/patches/`, orchestrator applies and commits via single-writer pattern (eliminates `git/index.lock` contention)
- work.md: `inscription.json` generation (was missing — 3/4 commands had it)
- work.md: Output directory creation (`tmp/work/{timestamp}/patches/` and `tmp/work/{timestamp}/proposals/`)
- mend.md: Worktree-based bisection — user's working tree is NEVER modified during bisection. Stash-based fallback with user confirmation if worktree unavailable.
- cancel-review.md, cancel-audit.md: Multi-session disambiguation via AskUserQuestion when multiple active sessions exist (previously auto-selected most recent)
- cancel-review.md, cancel-audit.md: `AskUserQuestion` added to `allowed-tools` frontmatter
- plan.md: Generic verification gate — reads patterns from `talisman.yml` `plan.verification_patterns` instead of hardcoded repo-specific checks
- plan.md: `inscription.json` generation in Phase 1A (was missing — review/audit/work had it)
- forge.md: `inscription.json` generation in Phase 4 (was missing — only review/audit/work had it)
- talisman.example.yml: `plan.verification_patterns` schema for custom verification patterns
- rest.md: Git worktree cleanup for stale bisection worktrees (`git worktree prune`)
- rest.md: Arc active-state check via `.claude/arc/*/checkpoint.json` — preserves `tmp/arc/` directories for in-progress arc sessions
- review.md, audit.md: Design note in Phase 3 explaining why Ashes are summoned as `general-purpose` (composite prompt pattern, defense-in-depth tool restriction)
- ash-guide SKILL.md: Two invocation models documented — Direct (namespace prefix) vs Composite Ash (review/audit workflows)

### Fixed

- review.md: Scope blindness — default mode missed staged, unstaged, and untracked files. Now captures all local file states.
- work.md: Commit race condition — parallel workers competing for `.git/index.lock`. Commit broker serializes only the fast commit step.
- work.md: `--approve` flow path mismatch — `proposals/` directory never created but referenced by workers. Added to `mkdir -p`.
- work.md: Mixed `{id}`/`{timestamp}` variables in `--approve` flow — unified to `{timestamp}` (4 occurrences)
- review.md, audit.md, work.md: Unbounded monitor loops — no hard timeout. Added 10/15/30 min limits respectively.
- mend.md: Destructive bisection rollback — `git checkout -- .` could destroy unrelated working tree changes. Worktree isolation eliminates this risk.
- rest.md: False claim that `tmp/arc/` follows same active-state check as reviews/audits — arc uses checkpoint.json, not state files. Now correctly checks `.claude/arc/*/checkpoint.json` for in-progress status.
- rest.md: `tmp/arc/` moved from unconditional removal to conditional block (patterned after `tmp/work/` block)
- CLAUDE.md: Multi-Agent Rules table row 2 now matches canonical rule — "3+ agents OR any TeamCreate" (was "3-4 agents")
- rune-orchestration SKILL.md: Research path corrected from `tmp/research/` to `tmp/plans/{timestamp}/research/` (matching actual plan.md output)
- roundtable-circle SKILL.md: Phase 0 pre-flight updated from stale `HEAD~1..HEAD` to unified scope builder (committed + staged + unstaged + untracked)
- roundtable-circle SKILL.md: `completion.json` removed from output directory tree and schema section converted to Legacy note (never implemented — Seal + state files serve same purpose)

## [1.10.3] - 2026-02-13

Patch release: security hardening, path consistency, and race condition fix from codex-cli deep verification. Includes review-round fixes from Roundtable Circle review (PR #12).

### Security

- **P1** mend.md: Fixers now summoned with `subagent_type: "rune:utility:mend-fixer"` instead of `"general-purpose"` to enforce restricted tool set via agent frontmatter (prevents prompt injection escalation to Bash)

### Added

- rune-gaze.md: New `INFRA_EXTENSIONS` group (Dockerfile, .sh, .sql, .tf, CI/CD configs) → Forge Warden. Previously these fell through all classification groups and got no type-specific Ash.
- rune-gaze.md: New `CONFIG_EXTENSIONS` group (.yml, .yaml, .json, .toml, .ini) → Forge Warden. Config files were previously unclassified.
- rune-gaze.md: New `INFRA_FILENAMES` list for extensionless files (Dockerfile, Makefile, Procfile, Vagrantfile, etc.)
- rune-gaze.md: Catch-all classification — unclassified files that aren't in skip list default to Forge Warden instead of silently falling through
- rune-gaze.md: `.claude/` path escalation — `.claude/**/*.md` files now trigger both Knowledge Keeper (docs) AND Ward Sentinel (security boundary) with explicit context
- rune-gaze.md: Docs-only override — when ALL non-skip files are doc-extension and fall below the line threshold, promote them so Knowledge Keeper is still summoned
- rune-gaze.md: `doc_line_threshold` configurable via `talisman.yml` → `rune-gaze.doc_line_threshold` (default: 10)
- talisman.example.yml: Added `infra_extensions`, `config_extensions`, `doc_line_threshold` config keys
- arc.md: Phase 4 docs-only awareness note for when Phase 3 produces only documentation files

### Fixed

- **P1** rune-echoes SKILL.md: Fixed 14 bare `echoes/` paths to `.claude/echoes/` in procedural sections and examples (was inconsistent with command-level echo writes)
- **P1** remembrance-schema.md: Fixed bare `echoes/` in `echo_ref` examples to `.claude/echoes/`
- **P2** plan.md, forge.md: Added WebSearch, WebFetch, and Context7 MCP tools to `allowed-tools` frontmatter (prompts required them but they were missing)
- **P2** README.md: Updated version from 1.10.1 to 1.10.3 in plugins table
- **P2** work.md: Moved plan checkbox updates from workers to orchestrator-only to prevent race condition when multiple workers write to the same plan file concurrently
- **P2** roundtable-circle SKILL.md: Added missing TeamCreate, TaskCreate, TaskList, TaskUpdate, TaskGet, TeamDelete, SendMessage to `allowed-tools` frontmatter (required by workflow phases)
- **P2** rune-echoes SKILL.md: Added AskUserQuestion to `allowed-tools` frontmatter (required by Remembrance security promotion flow)
- **P3** README.md: Fixed `docs/` in structure tree to `talisman.example.yml` in both top-level and plugin-level READMEs (docs/ directory doesn't exist inside plugin)
- **P3** docs/solutions/README.md: Fixed broken `/.claude/echoes/` link to relative path to SKILL.md

### Review-Round Fixes (from Roundtable Circle review)

- **P1** plugins/rune/README.md: Fixed phantom `docs/` in plugin-level structure tree (missed in initial fix — only top-level README was fixed)
- **P2** rune-gaze.md: Added `minor_doc_files` to algorithm Output signature (was used internally but undeclared)
- **P2** work.md: Added state file write (`tmp/.rune-work-{timestamp}.json`) with `"active"`/`"completed"` status — enables `/rune:rest` detection and concurrent work detection
- **P2** forge.md, plan.md: Added WebFetch/WebSearch SSRF guardrail to ANCHOR protocol ("NEVER pass plan content as URLs/queries")
- **P2** mend.md: Strengthened security note — orchestrator should halt fixers attempting Bash as prompt injection indicator
- **P2** rune-gaze.md: Clarified docs-only override comment — fires only when ALL docs below threshold AND no code/infra files
- **P3** rune-gaze.md: Added `.env` to SKIP_EXTENSIONS (prevents accidental exposure of secrets to review agents)
- **P3** rune-gaze.md: Clarified `.d.ts` skip scope (generated only — hand-written type declarations may need review)
- **P3** rune-gaze.md: Added footnote to Ash Selection Matrix for `.claude/` row (non-md files follow standard classification)
- **P3** rune-gaze.md: Split "Only infra/config/scripts" into separate rows for parity with SKILL.md quick-reference
- **P3** review.md: Fixed abort condition wording to include infra files ("code/infra files exist")
- **P3** work.md: Added arc context note for orchestrator-only checkbox updates
- **P3** talisman.example.yml: Added "subset shown — see rune-gaze.md for all defaults" comments
- **P3** CHANGELOG.md: Fixed version note (1.10.2→1.10.3), clarified both-README fix, exact echo path count

## [1.10.2] - 2026-02-13

Patch release: cross-command consistency fixes from codex-cli static audit.

### Fixed

- review.md: Standardized `{identifier}` variable (was mixed `{id}/{identifier}` causing broken paths)
- review.md, audit.md: State files now marked `"completed"` in Phase 7 cleanup (was stuck `"active"` forever, blocking `/rune:rest` cleanup)
- mend.md: Status field standardized to `"active"` (was `"running"`, mismatched with rest.md's expected value)
- mend.md: Standardized `{id}` variable (was mixed `{id}/{timestamp}`) and fixed undefined `f` variable in task description template
- forge.md: Added `mkdir -p` before `cp` backup command (was failing if directory didn't exist)
- forge.md, plan.md: Normalized reference paths from `skills/roundtable-circle/...` to `roundtable-circle/...` (consistent with all other files)
- arc.md: Made plan path optional with `--resume` (auto-detected from checkpoint); fixed contradictory recovery instructions
- arc.md: Added `team_name` field to per-phase checkpoint schema (enables cancel-arc to find delegated team names)
- cancel-arc.md: Now reads `team_name` from checkpoint instead of hardcoded phase-to-team map (was using wrong names for delegated Phases 3-6)
- cancel-arc.md: Fixed undefined `member` variable in shutdown loop (now reads team config to discover teammates)
- plan.md, review.md, audit.md, mend.md, work.md: Fixed echo write paths from `echoes/` to `.claude/echoes/` (was writing to wrong location)
- rest.md: Deletion step now uses validated path list from Step 4 (was ignoring validation output)

## [1.10.1] - 2026-02-13

Patch release: forge enrichment improvements and review finding fixes.

### Added

- Plan backup before forge merge — enables diff viewing and revert
- Enrichment Output Format template — standardized subsections (Best Practices, Performance, Implementation Details, Edge Cases, References)
- Post-enhancement options — diff, revert, deepen specific sections
- Echo integration in forge agent prompts — agents read `.claude/echoes/` for past learnings
- Context7 MCP + WebSearch explicit in forge agent research steps

### Fixed

- forge.md agent prompts now include anti-injection guard (Truthbinding parity with plan.md)
- forge.md Phase 6 `rm -rf` now has adjacent regex guard (SEC-1)
- forge.md RE-ANCHOR wording fixed for runtime-read plan content (SEC-2)
- forge.md `planPath` validated before Bash calls (SEC-3)
- arc.md YAML examples corrected from `docs/plans/` to `plans/` (DOC-1)
- arc.md `plan_file` path validation added before checkpoint (SEC-4)
- arc.md internal `skip_forge` key renamed to `no_forge` (QUAL-1)
- plan.md added missing `Load skills` directive (`rune-orchestration`) and `Edit` tool
- review.md, audit.md, work.md, mend.md added missing `Load skills` directives (`context-weaving`, `rune-echoes`, `rune-orchestration`)
- Pseudocode template syntax normalized to `{placeholder}` style across commands
- arc.md `rm -rf` sites annotated with validation cross-reference comments (SEC-5)

### Removed

- `docs/specflow-findings.md` — tracking document superseded by CHANGELOG and GitHub Issues

## [1.10.0] - 2026-02-12 — "The Elden Throne"

### Added

- `/rune:forge` — standalone plan enrichment command (deepen any existing plan with Forge Gaze)
- `--quick` flag for `/rune:plan` — minimal pipeline (research + synthesize + review)
- Phase 1.5: Research Consolidation Validation checkpoint (AskUserQuestion after research)
- Phase 2.5: Shatter Assessment for complex plan decomposition (complexity scoring + shard generation)
- AI-Era Considerations section in Comprehensive template
- SpecFlow dual-pass for Comprehensive plans (second flow-seer pass on drafted plan)
- Post-plan "Open in editor" and "Review and refine" options (4 explicit + Other free-text)
- Automated grep verification gate in plan review phase (deterministic, zero hallucination risk)
- decree-arbiter 6th dimension: Internal Consistency (anti-hallucination checks)

### Changed

- **Brainstorm + forge now default** — `/rune:plan` runs full pipeline by default. Use `--quick` for minimal.
- `--skip-forge` renamed to `--no-forge` in `/rune:arc` for consistency
- `--no-brainstorm`, `--no-forge`, `--exhaustive` still work as legacy flags
- Post-plan options expanded (4 explicit + Other free-text)
- decree-arbiter now evaluates 6 dimensions (was 5)
- **Elden Lord → Tarnished** — The lead/orchestrator is now called "the Tarnished" (the protagonist).
  In Elden Ring, the Tarnished is the player character who journeys through the Lands Between.
- **Tarnished → Ash** — All teammates (review, work, research, utility) are now called "Ash" / "Ashes".
  In Elden Ring, Spirit Ashes are summoned allies. "The Tarnished summons Ashes" — lore-accurate.
- **Config keys renamed**: `tarnished:` → `ashes:`, `max_tarnished` → `max_ashes`,
  `disable_tarnished` → `disable_ashes`. Update your `.claude/talisman.yml`.
- Directory renames: `tarnished-prompts/` → `ash-prompts/`,
  `tarnished-guide/` → `ash-guide/`, `custom-tarnished.md` → `custom-ashes.md`
- **Elden Throne completion message** — Successful workflow completion now shows
  "The Tarnished has claimed the Elden Throne." in arc and work outputs.
- Lore Glossary updated: Tarnished = lead, Ash = teammates, Elden Throne = completion state.

### Unchanged (Intentional)

- `recipient: "team-lead"` in all SendMessage calls — platform identifier
- Named roles: Forge Warden, Ward Sentinel, Pattern Weaver, Glyph Scribe, Knowledge Keeper
- `summon` verb — already lore-accurate (Tarnished summons Ashes)
- `talisman.yml` config file name — unchanged
- All logic, phases, and orchestration patterns

## [1.9.0] - 2026-02-12 — "The Elden Lord"

### Added

- **Elden Lord persona** — The orchestrator/lead now has a named identity. All commands use
  lore-themed greeting messages ("The Elden Lord convenes the Roundtable Circle...").
- **Lore Glossary** — New reference table in CLAUDE.md mapping 18 Elden Ring terms to plugin concepts.
- **Forge Gaze** — Topic-aware agent selection for `/rune:plan --forge`. Matches plan section
  topics to specialized agents using keyword overlap scoring (deterministic, zero token cost).
  13 agents across 2 budget tiers replace generic `forge-researcher` agents.
  See `roundtable-circle/references/forge-gaze.md` for the topic registry and algorithm.
- **Forge Gaze configuration** — Override thresholds, per-section caps, and total agent limits
  via `forge:` section in `talisman.yml`. Custom Tarnished participate via `workflows: [forge]`.

### Changed

- **Runebearer → Tarnished** — All review/worker/research/utility teammates are now called
  "Tarnished". Named roles (Forge Warden, Ward Sentinel, etc.) are unchanged.
- **Config keys renamed**: `runebearers:` → `tarnished:`, `max_runebearers` → `max_tarnished`,
  `disable_runebearers` → `disable_tarnished`. Update your `.claude/talisman.yml`.
- Directory renames: `runebearer-prompts/` → `tarnished-prompts/`,
  `runebearer-guide/` → `tarnished-guide/`, `custom-runebearers.md` → `custom-tarnished.md`
- **Config file renamed**: `rune-config.yml` → `talisman.yml`, `rune-config.example.yml` → `talisman.example.yml`.
  Talismans in Elden Ring are equippable items that enhance abilities — fitting for plugin configuration.
- **spawn → summon** — All 182 references to "spawn" renamed to "summon" across 37 files.
  In Elden Ring, you summon spirits and cooperators to aid in battle.
- Natural-language "the lead" → "the Elden Lord" across commands, prompts, and skills.

### Unchanged (Intentional)

- `recipient: "team-lead"` in all SendMessage calls — platform identifier
- Named roles: Forge Warden, Ward Sentinel, Pattern Weaver, Glyph Scribe, Knowledge Keeper
- All logic, phases, and orchestration patterns

## [1.8.2] - 2026-02-12

### Added

- Remembrance directory structure — `docs/solutions/` with 8 category directories and README

### Fixed

- SpecFlow findings updated through v1.8.1 (was stuck at v1.2.0) — added 20 resolved entries
- Stale `codex-scholar` references in plan document updated to `lore-scholar`

## [1.8.1] - 2026-02-12

### Changed

- **Agent rename**: `codex-scholar` → `lore-scholar` — avoids name collision with OpenAI's codex-cli. "Lore" fits the Elden Ring theme and conveys documentation research. Updated across 7 files (agent definition, commands, skills, CLAUDE.md, README, CHANGELOG).

## [1.8.0] - 2026-02-12 — "Knowledge & Safety"

### Added

- Remembrance channel — Human-readable knowledge docs in `docs/solutions/` promoted from Rune Echoes
- `--approve` flag for `/rune:work` — Optional plan approval gate per task
- `--exhaustive` flag for `/rune:plan --forge` — Summon ALL agents per section
- E8 research pipeline upgrade — Conditional research, brainstorm auto-detect, 6-agent roster, plan detail levels
- `/rune:echoes migrate` — Echo name migration utility
- `/rune:echoes promote` — Promote echoes to Remembrance docs

### Changed

- `/rune:plan` research now uses conditional summoning (local-first, external on demand)
- `/rune:plan` post-generation options expanded to 6 (was 3)
- Team lifecycle guards added to all 9 commands — pre-create guards + cleanup fallbacks with input validation (see `team-lifecycle-guard.md`)
- Reduced allowed-tools for `/rune:echoes`, `/rune:rest`, `/rune:cancel-arc` to enforce least-privilege

## [1.7.0] - 2026-02-12 — "Arc Pipeline"

### Added

- `/rune:arc` — End-to-end orchestration pipeline (6 phases: forge → plan review → work → code review → mend → audit)
- `/rune:cancel-arc` — Cancel active arc pipeline
- `--forge` flag for `/rune:plan` — Research enrichment phase (replaces `--deep`)
- `knowledge-keeper` standalone agent — Documentation coverage reviewer for arc Phase 2
- Checkpoint-based resume (`--resume`) with artifact integrity validation (SHA-256)
- Per-phase tool restrictions for arc pipeline (least-privilege enforcement)
- Feature branch auto-creation (`rune/arc-{name}-{date}`) when on main

## [1.6.0] - 2026-02-12 — "Mend & Commit"

### Added

- `/rune:mend` — Parallel finding resolution from TOME with team member fixers
- `mend-fixer` agent — Restricted-tool code fixer with full Truthbinding Protocol
- Incremental commits (E5) — Auto-commit after each ward-checked task (`rune: <subject> [ward-checked]`)
- Plan checkbox updates — Auto-mark completed tasks in plan file
- Resolution report format with FIXED/FALSE_POSITIVE/FAILED/SKIPPED categories

### Security

- SEC-prefix findings require human approval for FALSE_POSITIVE marking
- Mend fixers have restricted tool set (no Bash, no TeamCreate)
- Commit messages sanitized via `git commit -F` (not inline `-m`)
- `[ward-checked]` tag correctly implies automated check, not human verification

## [1.5.0] - 2026-02-12

### Added

- **Decree Arbiter** utility agent — technical soundness review for plans with 5-dimension evaluation (feasibility, risk, efficiency, coverage, consistency), Decree Trace evidence format, and deterministic verdict markers
- **Remembrance Channel** — human-readable knowledge documents in `docs/solutions/` promoted from high-confidence Rune Echoes, with YAML frontmatter schema, 8 categories, and security gate requiring human verification
- **TOME structured markers** — `<!-- RUNE:FINDING nonce="{session_nonce}" id="..." file="..." line="..." severity="..." -->` for machine-parseable review findings

### Changed

- **Naming refresh** — selective rename of agents, commands, and skills for clarity:
  - Review agents: `echo-detector` → `mimic-detector`, `orphan-finder` → `wraith-finder`, `forge-oracle` → `ember-oracle`
  - Research agents: `lore-seeker` → `practice-seeker`, `realm-analyst` → `repo-surveyor`, `chronicle-miner` → `git-miner`
  - Tarnished: `Lore Keeper` → `Knowledge Keeper`
  - Command: `/rune:cleanup` → `/rune:rest`
  - Skill: `rune-circle` → `roundtable-circle`
- All internal cross-references updated across 30+ files

### Removed

- Deprecated alias files (`cleanup.md`, `lore-keeper.md`) — direct rename, no backward-compat aliases

## [1.4.2] - 2026-02-12

### Added

- **Truthbinding Protocol** for all 10 review agents — ANCHOR + RE-ANCHOR prompt injection resistance
- **Truthbinding hardening** for utility agents (runebinder, truthseer-validator) and Tarnished prompts (forge-warden, pattern-weaver, glyph-scribe, lore-keeper)
- **File scope restrictions** for work agents (rune-smith, trial-forger) — prevent modification of `.claude/`, `.github/`, CI/CD configs
- **File scope restrictions** for utility agents (scroll-reviewer, flow-seer) — context budget and scope boundaries
- **New reference files** — `rune-orchestration/references/output-formats.md` and `rune-orchestration/references/role-patterns.md` (extracted from oversized SKILL.md)

### Fixed

- **P1: Missing `Write` tool** in `cancel-review` and `cancel-audit` commands — state file updates would fail at runtime
- **P1: Missing `TaskGet` tool** in `review` and `audit` commands — task inspection during monitoring unavailable
- **P1: Missing `Edit` tool** in `echoes` command — prune subcommand could not edit memory files
- **P1: Missing `AskUserQuestion` tool** in `cleanup` command — user confirmation dialog unavailable
- **P1: Missing `allowed-tools`** in `tarnished-guide` skill — added Read, Glob
- **P1: `rune-orchestration` SKILL.md** exceeded 500-line guideline (437 lines) — reduced to 245 lines via reference extraction
- **Glyph Scribe / Lore Keeper documentation** — clarified these use inline perspectives, not dedicated agent files
- **Agent-to-Tarnished mapping** made explicit across tarnished-guide, CLAUDE.md, circle-registry
- **Skill descriptions** rewritten to third-person trigger format per Anthropic SKILL.md standard
- **`--max-agents` default** in audit command corrected from `5` to `All selected`
- **Malicious code warnings** added to RE-ANCHOR sections in all 4 Tarnished prompts
- **Table of Contents** added to `custom-tarnished.md` reference
- **`rune-gaze.md`** updated max Tarnished count to include custom Tarnished (8 via settings)
- **echo-reader** listing fixed in v1.0.0 changelog entry

## [1.4.1] - 2026-02-12

### Fixed

- **Finding prefix naming** — unified all files to canonical prefixes (BACK/QUAL/FRONT) replacing stale FORGE/PAT/GLYPH references across 9 files
- **Root README** — removed phantom `plugin.json` from structure diagram (only `marketplace.json` exists at root)
- **Missing agent definition** — added `agents/utility/truthseer-validator.md` (referenced in CLAUDE.md but file was absent)
- **Agent name validation** — added path traversal prevention rule (`^[a-zA-Z0-9_:-]+$`) to custom Tarnished validation
- **Cleanup symlink safety** — added explicit symlink detection (`-L` check) before path validation in cleanup command
- **specflow-findings.md** — moved item #7 (Custom agent templates) to Resolved table (delivered in v1.4.0)
- **Keyword alignment** — synced `plugin.json` keywords with `marketplace.json` tags (`swarm`, `planning`)
- **`--max-agents` flag** — added to `/rune:review` command (was only documented for `/rune:audit`)

## [1.4.0] - 2026-02-12

### Added

- **Custom Tarnished** — extend built-in 5 Tarnished with agents from local (`.claude/agents/`), global (`~/.claude/agents/`), or third-party plugins via `talisman.yml`
  - `tarnished.custom[]` config with name, agent, source, workflows, trigger, context_budget, finding_prefix
  - Truthbinding wrapper prompt auto-injected for custom agents (ANCHOR + Glyph Budget + Seal + RE-ANCHOR)
  - Trigger matching: extension + path filters with min_files threshold
  - Agent resolution: local → global → plugin namespace
- **`talisman.example.yml`** — complete example config at plugin root
- **`custom-tarnished.md`** — full schema reference, wrapper prompt template, validation rules, examples
- **Extended dedup hierarchy** — `settings.dedup_hierarchy` supports custom finding prefixes alongside built-ins
- **`settings.max_tarnished`** — configurable hard cap (default 8) for total active Tarnished
- **`defaults.disable_tarnished`** — optionally disable built-in Tarnished
- **`--dry-run` output** now shows custom Tarnished with their prefix, file count, and source

### Changed

- `/rune:review` and `/rune:audit` Phase 0 now reads `talisman.yml` for custom Tarnished definitions
- Phase 3 summoning extended to include custom Tarnished with wrapper prompts
- Runebinder aggregation uses extended dedup hierarchy from config
- `--max-agents` flag range updated from 1-5 to 1-8 (to include custom)

## [1.3.0] - 2026-02-12

### Enhanced

- **Truthsight Verifier prompt** — added 3 missing verification tasks from source architecture:
  - Task 1: Rune Trace Resolvability Scan (validates all evidence blocks are resolvable)
  - Task 4: Cross-Tarnished Conflict Detection (flags conflicting assessments + groupthink)
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
- `--dry-run` flag for `/rune:review` and `/rune:audit` — preview scope selection without summoning agents
- Runebinder aggregation prompt (`tarnished-prompts/runebinder.md`) — TOME.md generation with dedup algorithm, completion.json
- Truthseer Validator prompt (`tarnished-prompts/truthseer-validator.md`) — audit coverage validation for Phase 5.5

### Fixed

- Stale version labels: "Deferred to v1.0" → "Deferred to v2.0" in `truthsight-pipeline.md`
- Removed redundant "(v1.0)" suffixes from agent tables in `tarnished-guide/SKILL.md`

### Changed

- `specflow-findings.md` reorganized: "Resolved" table (20 items with version), "Open — Medium" (5), "Open — Low" (3)

## [1.1.0] - 2026-02-12

### Added

- 4 new Rune Circle reference files:
  - `smart-selection.md` — File-to-Tarnished assignment, context budgets, focus mode
  - `task-templates.md` — TaskCreate templates for each Tarnished role
  - `output-format.md` — Raw finding format, validated format, JSON output, TOME format
  - `validator-rules.md` — Confidence scoring, risk classification, dedup, gap reporting
- Agent Role Patterns section in `rune-orchestration/SKILL.md` — summon patterns for Review/Audit/Research/Work/Conditional/Validation
- Truthseer Validator (Phase 5.5) for audit workflows — cross-references finding density against file importance
- Seal Format specification in `rune-circle/SKILL.md` with field table and completion signal
- Output Directory Structure showing all expected files per workflow
- JSON output format (`{tarnished}-findings.json`) and `completion.json` structured summary

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

- Circle Registry (`rune-circle/references/circle-registry.md`) — agent-to-Tarnished mapping with audit scope priorities and context budgets
- `--focus <area>` and `--max-agents <N>` flags for `/rune:audit`
- `--partial` flag for `/rune:review` (review staged files only)
- Known Limitations and Troubleshooting sections in README
- `.gitattributes` with `merge=union` strategy for Rune Echoes files

### Fixed

- Missing cross-reference from `rune-circle/SKILL.md` to `circle-registry.md`

## [1.0.0] - 2026-02-12

### Added

- `/rune:plan` — Multi-agent planning with parallel research pipeline
  - 3 new research agents (lore-seeker, realm-analyst, lore-scholar) plus echo-reader (from v0.3.0)
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
- 5 Tarnished (Forge Warden, Ward Sentinel, Pattern Weaver, Glyph Scribe, Lore Keeper)
- 10 review agents with Truthbinding Protocol
- Rune Gaze file classification
- Inscription Protocol for agent contracts
- Context Weaving (overflow prevention, rot prevention)
- Runebinder aggregation with deduplication
- Truthsight P1 verification

# Changelog

## [1.46.0] — 2026-02-19

### Added
- **Inner Flame self-review skill**: Universal 3-layer self-review protocol (Grounding, Completeness, Self-Adversarial) for all Rune teammate agents
  - Core skill at `skills/inner-flame/SKILL.md` with protocol definition and integration guide
  - 6 role-specific checklists in `skills/inner-flame/references/role-checklists.md` (Reviewer, Worker, Fixer, Researcher, Forger, Aggregator)
  - `validate-inner-flame.sh` TaskCompleted hook — blocks task completion when Self-Review Log is missing from teammate output
  - Inner Flame sections added to all 7 ash-prompt templates (forge-warden, ward-sentinel, pattern-weaver, glyph-scribe, knowledge-keeper, codex-oracle, runebinder)
  - Inner Flame checklist added to review-checklist.md shared reference
  - Spawn prompt updates in plan.md (forger), research-phase.md (7 researchers), worker-prompts.md (rune-smith, trial-forger), mend.md (fixer)
  - Agent definition updates: rune-smith (Rule #7 + Seal), trial-forger (Self-Review + Seal), mend-fixer (Step 4.5 + Seal)
  - Talisman config: `inner_flame.enabled`, `inner_flame.confidence_floor`, `inner_flame.block_on_fail`

### Changed
- **Plugin version**: 1.45.0 → 1.46.0
- Skills count: 14 → 15 (plugin.json, marketplace.json descriptions)
- marketplace.json skills array: added `./skills/inner-flame`

## [1.45.0] — 2026-02-19

Consolidated release from arc-batch run (PRs #58–#62).

### Added
- **Per-worker todo files** for `/rune:work`: Persistent markdown with YAML frontmatter, `_summary.md` generation, PR body integration, sanitization + path containment (PR #58)
- **Configurable codex timeout handling**: Two-layer timeout architecture with validation, error classification, and 12 codex exec site updates. New talisman keys for timeout config (PR #59)
- **refactor-guardian review agent**: Detects refactoring safety issues — verifies rename propagation, extract method completeness, and interface contract preservation (PR #60)
- **reference-validator review agent**: Validates cross-file references, link integrity, and documentation consistency across the codebase (PR #60)
- **Echo Search MCP server**: Python MCP server with SQLite FTS5 for full-text echo retrieval. Includes `indexer.py`, `server.py`, `annotate-hook.sh`, and `.mcp.json` config (PR #61)
- **Echo Search test suite**: 200 tests (78 unit for server, 39 for indexer, 19 for annotate hook, 64 integration with on-disk SQLite). Testdata fixtures with 4 realistic MEMORY.md files across reviewer, orchestrator, planner, and workers roles
- **Dirty signal consumption**: `server.py` now checks for `tmp/.rune-signals/.echo-dirty` (written by `annotate-hook.sh`) before each `echo_search` and `echo_details` call, triggering automatic reindex when new echoes are written. Completes the write→signal→reindex→search data flow
- **QW-1 Code Skimming prompts**: Added token-efficient file reading strategy to `repo-surveyor.md` (matching existing `echo-reader.md` section). Skim first 100 lines, then decide on full read
- **CLAUDE.md documentation**: Added MCP Servers section (echo-search), PostToolUse hook entry for annotate-hook.sh, and `.search-index.db` gitignore note
- **Platform environment configuration guide**: Env var reference table, 7-layer timeout model, pre-flight checklist, cost awareness, SDK heartbeat docs (PR #62)
- **Zombie tmux cleanup**: Step 6 in `rest.md` targeting orphaned `claude-*` tmux sessions (PR #62)

### Changed
- **Agent runtime caps**: `maxTurns: 75` for rune-smith, `maxTurns: 50` for trial-forger (PR #62)
- **MCP schema cost documentation**: Token estimates, multiplication effect per teammate, mitigation guidelines (PR #62)
- **Teammate non-persistence warning**: New section in session-handoff.md + Core Rule 10 in CLAUDE.md (PR #62)
- **Review agent count**: 16 → 18 (propagated to plugin.json, marketplace.json, README, CLAUDE.md, agent-registry)
- **Plugin version**: 1.42.2 → 1.45.0

## [1.42.1] — 2026-02-19

### Fixed
- **arc-batch nested session guard**: `arc-batch.sh` now unsets `CLAUDECODE` environment variable before spawning child `claude -p` processes. Fixes "cannot be launched inside another Claude Code session" error when `/rune:arc-batch` is invoked from within an active Claude Code session.

### Changed
- **Plugin version**: 1.42.0 → 1.42.1

## [1.42.0] — 2026-02-19

### Added
- **`/rune:arc-batch` skill**: Sequential batch arc execution across multiple plan files
  - Glob or queue file input: `/rune:arc-batch plans/*.md` or `/rune:arc-batch queue.txt`
  - Full 14-phase pipeline (forge through merge) per plan
  - Crash recovery with `--resume` from `batch-progress.json`
  - Signal handling (SIGINT/SIGTERM/SIGHUP) with clean child process termination
  - Git health checks before each run (stuck rebase, stale lock, MERGE_HEAD, dirty tree)
  - Inter-run cleanup: checkout main, pull latest, delete feature branch, clean state
  - Retry up to 3 attempts per plan with `--resume` on retry
  - macOS compatibility: `setsid` fallback when not available on darwin
  - `--dry-run` flag to preview queue without executing
  - `--no-merge` flag to skip auto-merge (PRs remain open)
  - `batch-progress.json` with schema_version for future compatibility
  - `tmp/.rune-batch-*.json` state file emission for workflow discovery
  - Pre-flight validation via `arc-batch-preflight.sh` (exists, symlink, traversal, duplicate, empty)
- New scripts: `arc-batch.sh`, `arc-batch-preflight.sh`
- Batch algorithm reference: `skills/arc-batch/references/batch-algorithm.md`

### Changed
- **Plugin version**: 1.41.0 → 1.42.0
- Skills count: 13 → 14 (plugin.json, marketplace.json descriptions)
- marketplace.json skills array: added `./skills/arc-batch`
- CLAUDE.md: added arc-batch to Skills and Commands tables
- README.md: added Batch Mode section and Quick Start examples

## [1.41.0] — 2026-02-19

### Fixed
- **BACK-017** (P1): `evaluateConvergence()` premature convergence — P1=0 check at position 1 short-circuited the entire tier system, making `maxCycles` dead code. Reordered decision cascade: minCycles gate → P1+P2 threshold → smart scoring → circuit breaker.
- **BACK-018** (P2): Circuit breaker (maxCycles check) moved from position 3 to position 4 — allows convergence at the final eligible cycle instead of halting.
- **BACK-019** (P2): P2 findings now considered in convergence decisions — both `evaluateConvergence()` and `computeConvergenceScore()` check P2 count against configurable threshold.

### Added
- `minCycles` per tier: LIGHT=1, STANDARD=2, THOROUGH=2 — minimum re-review cycles before convergence is allowed
- `p2Threshold` parameter in convergence evaluation — blocks convergence when P2 findings exceed threshold
- `countP2Findings()` helper in verify-mend.md — counts P2 TOME markers (case-insensitive)
- `p2_remaining` field in convergence history records for observability
- New talisman keys: `arc_convergence_min_cycles`, `arc_convergence_p2_threshold` under `review:` section
- Checkpoint schema v8 with `minCycles` in tier and `p2_remaining` in history
- Configuration guide `review.arc_convergence_*` table with all convergence keys documented

### Changed
- `evaluateConvergence()` signature: 5 params → 6 params (added `p2Count` as 3rd parameter)
- `computeConvergenceScore()` now reads `p2Count` from `scopeStats` and applies P2 hard gate
- `scopeStats` object now includes `p2Count` field
- Tier table updated with Min Cycles column
- **Plugin version**: 1.40.1 → 1.41.0

## [1.40.1] — 2026-02-19

### Fixed
- **QUAL-001** (P1): `resolveArcConfig()` now resolves `pre_merge_checks` from talisman — user overrides were silently ignored
- **SEC-001** (P2): Quoted `prNumber` in `gh pr merge` commands (defensive quoting convention)
- **SEC-002** (P2): Wrapped branch name in backticks in ship phase push failure warning
- **QUAL-002** (P2): Added `mend` to README codex `workflows` example array
- **QUAL-003** (P2): `co_authors` resolution now checks `arc.ship.co_authors` first, falls back to `work.co_authors`
- **QUAL-004** (P2): Added `co_authors` row to configuration-guide.md `arc.ship` table with fallback note
- **DOC-001** (P2): Post-arc plan stamp now says "after Phase 9.5" (was "after Phase 8")
- **DOC-002** (P2): Completion report step 3 is now conditional on `pr_url`
- **DOC-003** (P3): ARC-9 Final Sweep comment updated to reference Phase 9.5
- **DOC-005** (P3): `auto_merge` description clarified — "see `wait_ci` for CI gate" (was "after CI")

### Added
- New `using-rune` skill: workflow discovery and intent routing — suggests correct `/rune:*` command
- `SessionStart` hook: loads workflow routing into context at session start
- 11 skill description rewrites with trigger keywords for better Claude auto-detection

### Changed
- **Plugin version**: 1.40.0 → 1.40.1
- Skills count: 12 → 13

## [1.40.0] — 2026-02-19

### Added
- Arc Phase 9 (SHIP): Auto PR creation after audit via `gh pr create` with generated template
- Arc Phase 9.5 (MERGE): Rebase onto main + auto squash-merge with pre-merge checklist
- 3-layer talisman config resolution for arc: hardcoded defaults → talisman.yml → CLI flags
- `arc.defaults`, `arc.ship`, `arc.pre_merge_checks` talisman sections
- Activated `arc.timeouts` talisman section (was reserved since v1.12.0)
- New CLI flags: `--no-pr`, `--no-merge`, `--draft`
- Checkpoint schema v7 with ship/merge phase tracking and pr_url
- Pre-merge checklist: migration conflicts, schema drift, lock files, uncommitted changes
- Configuration guide `## arc` section with full schema documentation (DOC-KK-010)

### Changed
- Arc pipeline expanded from 12 to 14 phases
- `calculateDynamicTimeout()` includes ship (300000ms) + merge (600000ms) phase budgets
- **Plugin version**: 1.39.2 → 1.40.0

## [1.39.2] — 2026-02-19

### Fixed
- **DOC-001**: Pre-commit checklist now says "all four files" with flat numbering (was "three" with ambiguous "Also sync" separator)
- **DOC-002**: Pre-commit checklist marketplace.json path now qualified with "repo-root" to avoid ambiguity
- **SEC-001**: Validation command `$f` variable now properly quoted: `$(basename "$(dirname "$f")")`
- **QUAL-001**: Converted remaining backtick path in `arc-phase-code-review.md` to markdown link
- **QUAL-006**: Added zsh glob compliance note to Skill Compliance section (covers both `skills/` and `commands/`)

### Changed
- **Plugin version**: 1.39.1 → 1.39.2
- Pre-commit file paths now use full relative paths from repo root for clarity

## [1.39.1] — 2026-02-18

### Fixed
- **AUDIT-ARCH-002**: rune-smith Step 6.5 now checks `codexWorkflows.includes("work")` gate — consistent with all other Codex integration points
- **AUDIT-SEC-001**: rune-smith Step 6.5 now verifies `.codexignore` exists before `--full-auto` invocation
- **AUDIT-SEC-004**: Elicitation cross-model protocol (SKILL.md) now includes `.codexignore` pre-flight at step 2.5

### Added
- CHANGELOG entries for v1.38.0 and v1.39.0 (previously missing)

### Changed
- **Plugin version**: 1.39.0 → 1.39.1

## [1.39.0] — 2026-02-18

### Added
- **Codex Deep Integration** — 9 new cross-model integration points extending Codex Oracle from 5 to 14 workflow touchpoints. Each uses GPT-5.3-codex as a second-perspective verification layer. All follow the Canonical Codex Integration Pattern (detect → validate → spawn → execute → verify → output → cleanup).
  - **IP-1: Elicitation Sage cross-model reasoning** — `codex_role` column added to methods.csv. Adversarial methods (Red Team vs Blue Team, Pre-mortem, Challenge) now use Codex for the opposing perspective. Orchestrator spawns Codex teammate; sage reads output file.
  - **IP-2: Mend Fix Verification** — Phase 5.8 in mend.md. After fixers apply TOME fixes, Codex batch-verifies all diffs for regressions, weak fixes, and conflicts. Verdicts: GOOD_FIX, WEAK_FIX, REGRESSION, CONFLICT.
  - **IP-3: Arena Judge** — Cross-model solution evaluation in Plan Phase 1.8B. Codex scores solutions on 5 dimensions + optional solution generation mode. Cross-model agreement bonus in scoring matrix.
  - **IP-4: Semantic Verification (Phase 2.8)** — New arc phase after Phase 2.7. Codex checks enriched plan for internal contradictions (technology, scope, timeline, dependency). Separate phase with own 120s budget (doesn't conflict with Phase 2.7's 30s deterministic gate).
  - **IP-5: Codex Gap Analysis** — Arc Phase 5.6, after Claude gap analysis. Compares plan expectations vs actual implementation. Findings: MISSING, EXTRA, INCOMPLETE, DRIFT.
  - **IP-6: Trial Forger edge cases** — Step 4.5 in trial-forger.md. Before writing tests, Codex suggests 5-10 edge cases (boundary values, null inputs, concurrency, error paths).
  - **IP-7: Rune Smith inline advisory** — Step 6.5 in rune-smith.md. Optional quick Codex check on worker diffs. **Disabled by default** (opt-in via `codex.rune_smith.enabled: true`).
  - **IP-8: Shatter complexity scoring** — Cross-model blended score in Plan Phase 2.5. 70% Claude + 30% Codex weighted average for shatter gate decisions.
  - **IP-9: Echo validation** — Before persisting learnings to `.claude/echoes/`, Codex checks if insight is generalizable or context-specific. Tags context-specific entries for lower retrieval priority.
- 9 new talisman keys under `codex:` — `elicitation`, `mend_verification`, `arena`, `semantic_verification`, `gap_analysis`, `trial_forger`, `rune_smith`, `shatter`, `echo_validation`
- `"mend"` added to default `codex.workflows` fallback array across all command files
- `.codexignore` pre-flight checks added to mend.md, trial-forger.md, arc SKILL.md (SEC-002 fixes)
- Arc phases updated: Phase 2.8 (semantic verification), Phase 5.6 (Codex gap analysis)
- codex-cli SKILL.md output conventions table updated with all 9 new output paths

### Changed
- **Plugin version**: 1.38.0 → 1.39.0
- **elicitation-sage.md**: Added Cross-Model Workflow section with sage-side synthesis protocol
- **elicitation SKILL.md**: Added Cross-Model Routing section, codex_role CSV column documentation, orchestrator-level protocol
- **methods.csv**: Added `codex_role` column (11th column). 3 methods tagged: Red Team vs Blue Team (`red_team`), Pre-mortem Analysis (`failure`), Challenge from Critical Perspective (`critic`)
- **solution-arena.md**: Added Codex Arena Judge sub-step 1.8B extension + scoring integration in 1.8C
- **gap-analysis.md**: Extended with Codex Gap Analysis (Phase 5.6) section
- **arc SKILL.md**: Added Phase 2.8 (semantic verification) + Codex gap analysis phase + checkpoint schema update
- **CLAUDE.md**: Updated skill descriptions, phase list, and codex-cli skill description

### Known Issues
- **AUDIT-ARCH-002** (P2): rune-smith Step 6.5 missing `codexWorkflows` gate — fixed in post-arc patch
- **AUDIT-SEC-001/004** (P2): `.codexignore` pre-flight missing in rune-smith + elicitation protocol — fixed in post-arc patch

## [1.38.0] — 2026-02-18

### Added
- **Diff-Scope Engine** — Generates per-file line ranges from `git diff` for review scope awareness. Enriches `inscription.json` with `diff_scope` data, enabling TOME finding tagging (`in-diff` vs `pre-existing`) and scope-aware mend priority filtering.
  - New shared reference: `rune-orchestration/references/diff-scope.md` (Diff Scope Engine + TOME Tagger)
  - New shared reference: `roundtable-circle/references/diff-scope-awareness.md` (Ash-facing guidance)
  - `inscription.json` schema extended with `diff_scope` object (enabled, base_ref, ranges, expansion_zone)
  - TOME Phase 5.3 tagger: classifies findings as `in-diff` or `pre-existing` based on line ranges
  - Mend priority filtering: `in-diff` findings prioritized over `pre-existing`
- **Smart Convergence Scoring** — `computeConvergenceScore()` with 4-component weighted formula replacing simple finding-count comparison. Components: finding reduction (40%), severity improvement (25%), scope coverage (20%), fix success rate (15%). Partially mitigates SCOPE-BIAS (P3 from v1.37.0).
- 3 new talisman keys: `review.diff_scope.expansion` (default: 8), `review.diff_scope.max_files` (default: 200), `review.convergence.smart_scoring` (default: true)
- Diff Scope Awareness section added to all 6 Ash prompt files (codex-oracle, forge-warden, glyph-scribe, knowledge-keeper, pattern-weaver, ward-sentinel)

### Changed
- **Plugin version**: 1.37.0 → 1.38.0
- **review.md**: Added diff-scope generation in Phase 0, `--no-diff-scope` flag
- **parse-tome.md**: Added scope-based priority sorting for mend file groups
- **review-mend-convergence.md**: Replaced simple threshold with `computeConvergenceScore()` + configurable `convergence_threshold` (default: 0.7)
- **arc SKILL.md**: Phase 5.5 gap analysis now receives diff scope data
- **verify-mend.md**: Convergence evaluation uses smart scoring when enabled
- **inscription-schema.md**: Documented `diff_scope` object schema
- **arc-phase-completion-stamp.md**: Completion report includes diff scope summary

## [1.37.0] — 2026-02-18

### Added
- **Goldmask v2 — Wisdom Layer**: Three-layer cross-layer impact analysis (Impact + Wisdom + Lore) with Collateral Damage Detection
  - Impact Layer: 5 Haiku tracers for dependency tracing across data, API, business, event, and config layers
  - Wisdom Layer: Sonnet-powered git archaeology — understands WHY code was written via git blame, commit intent classification, and caution scoring
  - Lore Layer: Quantitative git history analysis — per-file risk scores, churn metrics, co-change clustering, ownership concentration
  - Collateral Damage Detection: Noisy-OR blast-radius scoring + Swarm Detection for bugs that travel in pairs
  - Goldmask Coordinator: Three-layer synthesis into unified GOLDMASK.md report with findings.json
- New `/rune:goldmask` standalone skill for on-demand investigation
- 8 new investigation agents in `agents/investigation/`: 5 impact tracers + wisdom-sage + lore-analyst + goldmask-coordinator
- New `goldmask` talisman configuration section with layer-specific settings, CDD thresholds, and mode selection
- **Adaptive review-mend convergence loop** — Phase 7.5 (verify_mend) now runs a full review-mend convergence controller instead of single-pass spot-check. Repeats Phase 6→7→7.5 until findings converge or max cycles reached.
- **3-tier convergence system** — LIGHT (2 cycles, ≤100 lines AND no high-risk files AND type=fix), STANDARD (3 cycles, default), THOROUGH (5 cycles, >2000 lines OR high-risk files OR large features). Tier auto-detected from changeset size, risk signals, and plan type.
- **Progressive review focus** — Re-review rounds narrow scope to mend-modified files + 1-hop dependencies (max 10 additional). Reduces review cost on retry cycles.
- **Dynamic arc timeout** — `calculateDynamicTimeout(tier)` replaces fixed `ARC_TOTAL_TIMEOUT`. Scales 162-240 min based on tier, hard cap at 240 min.
- **Shared convergence reference** — `roundtable-circle/references/review-mend-convergence.md` contains `selectReviewMendTier()`, `evaluateConvergence()`, `buildProgressiveFocus()` shared by arc and standalone review.
- **`--cycles <N>` flag for `/rune:review`** — Run N standalone review passes (1-5, numeric only) with TOME dedup merge. Standalone equivalent of arc convergence loop.
- **`--scope-file <path>` flag for `/rune:review`** — Override changed_files from a JSON focus file. Used by arc convergence controller for progressive re-review scope.
- **`--no-converge` flag for `/rune:review`** — Disable convergence loop for single review pass per chunk (report still generated).
- **`--auto-mend` flag for `/rune:review`** — Auto-invoke `/rune:mend` after review completes when P1/P2 findings exist (skips post-review AskUserQuestion). Also configurable via `review.auto_mend: true` in talisman.yml.
- **Arc convergence talisman keys** — `arc_convergence_tier_override`, `arc_convergence_max_cycles`, `arc_convergence_finding_threshold`, `arc_convergence_improvement_ratio` (all under `review:` with `arc_` prefix to avoid collision with standalone review convergence keys).
- **Checkpoint schema v6** — Adds `convergence.tier` object (name, maxCycles, reason). Auto-migrated from v5 with `TIERS.standard` default.

### Changed
- Agent count: 31 → 39 (added 8 investigation agents)
- Skills: 11 → 12 (added goldmask)
- **verify-mend.md**: Replaced single-pass spot-check with full convergence controller using shared `evaluateConvergence()` logic
- **arc-phase-code-review.md**: Added progressive focus section for re-review rounds, round-aware TOME relocation
- **arc-phase-mend.md**: Round-aware resolution report naming (`resolution-report-round-{N}.md`)
- **arc SKILL.md**: Dynamic timeout calculation, updated checkpoint init (convergence tier), schema v5→v6 migration, updated completion report format
- **CLAUDE.md**: Phase 7.5 description updated from "verify mend" to "adaptive convergence loop"
- **Plugin version**: 1.36.0 → 1.37.0

### Known Limitations
- **SCOPE-BIAS** (P3, tracked for v1.38.0): `findings_before` comparison in convergence evaluation is biased by scope reduction (full → focused review). Pass 1 reviews all changed files; pass 2+ reviews only mend-modified files + dependencies. A decrease in findings may reflect narrower scope rather than code improvement. See `review-mend-convergence.md` §Scope Limitation Note.

## [1.35.0] - 2026-02-18

### Fixed
- **CDX-003: Filesystem fallback blast radius** — Gate cross-workflow `find` scan behind `!teamDeleteSucceeded` flag. When TeamDelete succeeds cleanly, skip the filesystem fallback entirely — prevents wiping concurrent `rune-*`/`arc-*` workflows
- **QUAL-003: Cleanup phase retry-with-backoff** — All 6 command cleanup phases now use retry-with-backoff (3 attempts: 0s, 3s, 8s) matching the pre-create guard pattern. Previously cleanup used single-try TeamDelete with immediate rm-rf fallback
- **Pre-create guard count correction** — Fixed count from 9 to 8 (6 commands + arc-phase-plan-review + verify-mend)
- **Retry attempt logging off-by-one** — `attempt + 1` in warn messages (was showing attempt 0 as first retry)

### Changed
- **CLAUDE.md**: Added `chome-pattern` skill to skills table
- **team-lifecycle-guard.md**: Both canonical + roundtable-circle copies updated with CDX-003 `!teamDeleteSucceeded` gate
- **arc-phase-plan-refine.md**: Added `--confirm` flag documentation for all-CONCERN escalation

## [1.34.0] - 2026-02-18

### Added
- **`chome-pattern` skill** — Reference for `CLAUDE_CONFIG_DIR` resolution pattern. Covers SDK vs Bash classification, canonical patterns, and audit commands. Skill count updated to 9.
- **`--confirm` flag for `/rune:arc`** — Pause for user input on all-CONCERN escalation in Phase 2.5. Without this flag, arc auto-proceeds with warnings.

### Changed
- **teamTransition() 5-step inlined protocol**: Retry-with-backoff (0s, 3s, 8s), filesystem fallback, "Already leading" catch-and-recover, post-create verification
- **Pre-create guards hardened**: All 8 pre-create guards (6 commands + arc-phase-plan-review + verify-mend) use inlined teamTransition pattern
- **CHOME fix in cleanup phases**: All 6 command cleanup phases + 3 cancel commands now use `CLAUDE_CONFIG_DIR` pattern instead of bare `~/.claude/`
- **Arc prePhaseCleanup + ORCH-1 hardened**: Retry-with-backoff + CHOME pattern in inter-phase cleanup
- **Cancel commands hardened**: Retry-with-backoff + CHOME in all 3 cancel commands
- **Reference doc sync**: team-lifecycle-guard.md canonical protocol + roundtable-circle copy synced (including CDX-003 `!teamDeleteSucceeded` gate)

## [1.33.0] - 2026-02-18

### Fixed
- **Stale team leadership state** — pre-create guard v2 fixes two bugs causing "Already leading team X" errors:
  - Wrong `rm -rf` target: fallback now cleans the target team AND cross-workflow scan removes ALL stale `rune-*`/`arc-*` team dirs
  - Missing retry: `TeamDelete()` is retried after filesystem cleanup to clear SDK internal leadership state
- Removed `sleep 5` band-aid from `forge.md` pre-create guard — replaced with direct filesystem cleanup + retry

### Changed
- Pre-create guard pattern upgraded to 3-step escalation across 12 files:
  - Step A: `rm -rf` target team dirs (same as before)
  - Step B: Cross-workflow `find` scan for ANY stale `rune-*`/`arc-*` dirs (new)
  - Step C: Retry `TeamDelete()` to clear SDK internal state (new)
- All pre-create guard `Bash()` commands now resolve `CLAUDE_CONFIG_DIR` via `CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"` — supports multi-account setups (e.g., `~/.claude-work`)
- `prePhaseCleanup()` in arc SKILL.md: added retry `TeamDelete()` after rm-rf loop
- ORCH-1 resume cleanup: added retry `TeamDelete()` after checkpoint + stale scan cleanup
- Updated critical ordering rules in team-lifecycle-guard.md (both copies)

## [1.32.0] - 2026-02-18

### Added
- **Mend file ownership enforcement** — three-layer defense preventing concurrent file edits by mend fixers
  - Layer 1: Path normalization in parse-tome.md (`normalizeFindingPath()`) — prevents `./src/foo.ts` and `src/foo.ts` creating duplicate groups
  - Layer 2: `blockedBy` serialization via cross-group dependency detection (`extractCrossFileRefs()`) — dependent groups execute sequentially
  - Layer 3: PreToolUse hook (`scripts/validate-mend-fixer-paths.sh`) — hard enforcement blocking Write/Edit/NotebookEdit to files outside assigned group
- `file_targets` and `finding_ids` metadata in mend TaskCreate — parity with work.md ownership tracking
- Sequential batching for 6+ file groups (max 5 concurrent fixers per batch)
- `validate-mend-fixer-paths.sh` registered in `hooks/hooks.json` as PreToolUse hook
- Phase 1.5 cross-group dependency detection in mend.md with sanitized regex extraction

### Changed
- `mend-fixer.md` security note updated to reference active hook enforcement (was "Recommended")
- `parse-tome.md` now includes "Path Normalization" section before "Group by File"
- `mend.md` Phase 3 wraps fixer summoning in batch loop with per-batch monitoring
- `mend.md` Phase 4 clarified as single-batch only (multi-batch monitoring is inline in Phase 3)

### Security
- SEC-MEND-001: Mend fixer file scope enforcement via PreToolUse hook (fail-open design, jq-based JSON deny)
- Inscription-based ownership validation prevents fixers from editing files outside their assigned group
- Cross-file dependency sanitization: HTML comment stripping, code fence removal, 1KB input cap

## [1.29.2] - 2026-02-17

### Fixed
- CDX-7: Post-delegation cleanup guard for crashed sub-commands — three-layer orphan defense prevents resource leaks from crashed workflows

### Added
- `/rune:rest --heal` flag for manual orphan recovery — scans for stale state files and orphaned team directories
- Arc resume pre-flight cleanup (ORCH-1) — automatically cleans orphaned teams when resuming arc sessions
- Arc pre-flight stale team scan — removes stale arc-specific teams from prior sessions
- Crash recovery documentation for all 4 arc-phase reference files

### Changed
- `team-lifecycle-guard.md`: Added `safeTeamCleanup()` utility, `isStale()` staleness detection, and orphan recovery pattern documentation

### Upgrade Note
If you have orphaned team directories from prior crashed workflows, run `/rune:rest --heal` to clean them up.

## [1.29.1] - 2026-02-17

Fix: Arc inter-phase team cleanup guard (ARC-6).

### Fixed
- Arc dispatcher now runs `prePhaseCleanup()` before every delegated phase
- Stale team directories cleaned via checkpoint-aware `rm -rf` before TeamCreate
- Resume logic enhanced with team cleanup guard

### Changed
- arc.md: Added `prePhaseCleanup()` function and 5 phase-dispatch guard calls + 1 resume guard call
- team-lifecycle-guard.md: Added ARC-6 section and consumer reference
- 5 arc-phase reference files: Added ARC-6 delegation notes
- plugin.json, marketplace.json: version 1.29.0 → 1.29.1

## [1.29.0] - 2026-02-17

### Added
- Standardized plan header fields: `version_target`, `complexity`, `scope`, `risk`, `estimated_effort`, `impact`
- Field-filling guidance in synthesize.md for plan generation
- Arc completion stamp: updates plan Status field and appends persistent execution record when arc finishes (success, partial, or failure)

### Changed
- Plan templates (Minimal, Standard, Comprehensive) updated with new header fields

## [1.28.3] - 2026-02-17

Fix: Arc implicit delegation gaps — explicit Phase 0 step contracts for delegated commands.

### Added

- New reference: `arc-delegation-checklist.md` — canonical RUN/SKIP/ADAPT delegation contract for all arc phases
- Codex Oracle as optional 4th plan reviewer in arc Phase 2 (`arc-phase-plan-review.md`)
- Delegation Steps sections in `arc-phase-code-review.md` (Phase 6) and `arc-phase-audit.md` (Phase 8)
- Bidirectional `DELEGATION-CONTRACT` comments in `review.md` and `audit.md` Phase 0

### Changed

- plugin.json: version 1.28.2 → 1.28.3
- marketplace.json: version 1.28.2 → 1.28.3
- CLAUDE.md: Added `arc-delegation-checklist.md` to References section

## [1.28.2] - 2026-02-16

Refactor: Arc Phase 1 (FORGE) now delegates to `/rune:forge` for full Forge Gaze support.

### Changed

Note: v1.18.2 introduced initial forge delegation. v1.27.1 (ATE-1) restructured
arc phases, requiring this re-implementation of the delegation pattern.

- Arc Phase 1 now delegates to `/rune:forge` instead of inline agent logic
- forge.md gains `isArcContext` detection (skips interactive phases in arc context)
- forge.md emits state file for arc team name discovery
- arc-phase-forge.md rewritten from inline (153 lines) to delegation wrapper (~50 lines)

## [1.28.1] - 2026-02-16

Refactor: Extract Issue Creation from plan.md to reference file.

### Changed

- Move inline Issue Creation section (34 lines) from plan.md to `references/issue-creation.md`
- plan.md reduced from 571 to 542 lines
- plugin.json: version 1.28.0 → 1.28.1
- marketplace.json: version 1.28.0 → 1.28.1

## [1.28.0] - 2026-02-16

Feature: Arc Dispatcher Extraction — extract 7 phases from arc.md into self-contained reference files.

### Changed

- Extract per-phase logic from arc.md (977→577 lines, -41%) into `references/arc-phase-*.md` files
- New reference files: arc-phase-forge.md, arc-phase-plan-review.md, arc-phase-plan-refine.md, arc-phase-work.md, arc-phase-code-review.md, arc-phase-mend.md, arc-phase-audit.md
- Transform arc.md into lightweight dispatcher skeleton that loads phase logic via Read()
- Phases 2.7, 5.5, 7.5 already used reference files — unchanged
- plugin.json: version 1.27.1 → 1.28.0
- marketplace.json: version 1.27.1 → 1.28.0

## [1.27.1] - 2026-02-16

Feature: ATE-1 Agent Teams Enforcement — prevent context explosion in arc pipeline.

### Added

- **ATE-1 enforcement** — Three-layer defense against bare Task calls in arc pipeline:
  1. ATE-1 enforcement section at top of arc.md with explicit pattern + anti-patterns
  2. Phase 1 FORGE inlined with full TeamCreate + Task + Monitor + Cleanup example
  3. `enforce-teams.sh` PreToolUse hook blocks bare Task calls during active workflows

### Changed

- Freshness gate extracted from arc.md to `references/freshness-gate.md`
- Review agent checklists extracted to reference files (forge-keeper, tide-watcher, wraith-finder)
- `enforce-readonly.sh` SEC-001 hook for review/audit write protection
- Hook infrastructure expanded from 2 to 4 hooks in CLAUDE.md
- plugin.json: version 1.27.0 → 1.27.1
- marketplace.json: version 1.27.0 → 1.27.1

## [1.27.0] - 2026-02-16

Quality & security bundle: PreToolUse read-only enforcement, TaskCompleted semantic validation, and agent prompt extraction to reference files.

### Added

- **QW-B: PreToolUse read-only hook (SEC-001)** — Platform-level enforcement preventing review/audit Ashes from using Write, Edit, Bash, or NotebookEdit tools. Uses dual-condition detection: marker file (`.readonly-active` in signal directory) + transcript path check (`/subagents/`). Overcomes PreToolUse hook's lack of `team_name` field.
- **QW-C: TaskCompleted prompt hook** — Haiku-model semantic validation gate alongside existing signal-file command hook. Rejects clearly premature task completions (empty subjects, generic descriptions) while allowing legitimate completions. Higher standard for `rune-*` / `arc-*` team tasks.
- **`scripts/enforce-readonly.sh`** — SEC-001 enforcement script with `jq` dependency guard, graceful degradation, and JSON-structured deny response
- **`agents/review/references/async-patterns.md`** — Multi-language async/concurrency code examples extracted from tide-watcher (Python, Rust, TypeScript, Go)
- **`agents/review/references/dead-code-patterns.md`** — Dead code detection patterns extracted from wraith-finder (classical detection, DI wiring, router registration, event handlers)
- **`agents/review/references/data-integrity-patterns.md`** — Migration safety patterns extracted from forge-keeper (reversibility, lock analysis, transformations, transactions, privacy)

### Changed

- **QW-D: Agent prompt extraction** — 3 oversized review agents reduced to reference-linked prompts:
  - `tide-watcher.md`: 708 → ~165 lines (extracted async-patterns.md)
  - `wraith-finder.md`: 563 → ~300 lines (extracted dead-code-patterns.md)
  - `forge-keeper.md`: 460 → ~186 lines (extracted data-integrity-patterns.md)
- `hooks/hooks.json`: Added PreToolUse hook for SEC-001 + prompt hook for TaskCompleted; updated description
- `roundtable-circle/SKILL.md`: Phase 2 now writes `.readonly-active` marker before TeamCreate
- `roundtable-circle/references/monitor-utility.md`: Added readonly marker pseudocode
- plugin.json: version 1.26.0 → 1.27.0
- marketplace.json: version 1.26.0 → 1.27.0

### Security

- **SEC-001 mitigation** — Review/audit Ashes previously relied on prompt-level `allowed-tools` restrictions which are NOT enforced when agents are spawned as `general-purpose` subagent_type (the composite Ash pattern). The PreToolUse hook now provides platform-level enforcement that cannot be bypassed by prompt injection.

### Migration Notes

- **No breaking changes** — all additions are purely additive
- PreToolUse hook requires `jq` (same prerequisite as existing hooks); gracefully exits 0 if unavailable
- Readonly marker is scoped to `rune-review-*` / `arc-review-*` / `rune-audit-*` / `arc-audit-*` signal directories
- Agent prompt extraction preserves all analysis frameworks and output formats; only code examples moved to reference files

## [1.26.0] - 2026-02-16

Feature release: Plan Freshness Gate — structural drift detection prevents stale plan execution.

### Added

- **Plan Freshness Gate** — zero-LLM-cost pre-flight check in `/rune:arc` detects when a plan's source codebase has drifted since plan creation. Composite Structural Diff Score (5 weighted signals: commit distance, file drift, identifier loss, branch divergence, time decay) produces a freshness score (0.0–1.0). PASS/WARN/STALE thresholds with user override
- **Enhanced Verification Gate** — check #8 re-checks file drift on forge-expanded references post-enrichment
- **Plan metadata** — `/rune:plan` now writes `git_sha` and `branch` to plan YAML frontmatter for freshness tracking
- **`--skip-freshness` flag** — bypass freshness check for `/rune:arc` when plan is intentionally ahead of codebase
- **`plan.freshness` talisman config** — configurable thresholds (`warn_threshold`, `block_threshold`, `max_commit_distance`, `enabled`)
- **SAFE_SHA_PATTERN** — new security pattern for git SHA validation in `security-patterns.md`
- **Checkpoint schema v5** — adds `freshness` field and `skip_freshness` flag with v4→v5 auto-migration

### Changed

- plugin.json: version 1.25.1 → 1.26.0
- marketplace.json: version 1.25.1 → 1.26.0
- verification-gate.md: 7 checks + report → 8 checks + report (added freshness re-check)
- arc.md: 3 flags → 4 flags (added `--skip-freshness`)

## [1.25.0] - 2026-02-16

Feature release: Agent Intelligence Quick Wins — four interconnected intelligence improvements forming a feedback loop.

### Added

- **QW-1: Smart Code Skimming** (research agents) — Agents choose read depth based on task relevance: deep-read when known-relevant, skim when uncertain, skip when irrelevant. ~60-90% token reduction in file discovery.
- **QW-2: Confidence Scoring** (review + work agents) — All agents include confidence (0-100) with justification. Decision gates: >=80 actionable, 50-79 needs-verify, <50 escalate. Cross-check: confidence >=80 requires evidence ratio >=50%.
- **QW-3: Adaptive Context Checkpoint** (work agents) — Post-task reset scales with task position: Light (1-2), Medium (3-4), Aggressive (5+). Context rot detection triggers immediate aggressive reset.
- **QW-4: Smart DC-1 Recovery** (damage-control) — Severity-based adaptive retry (mild/moderate/severe). Early warning signals at task 4+, 20+ files, low confidence. Respawn protocol with enriched handoff summary.

**Feedback loop**: Skimming → confidence → checkpoint → overflow prevention. Each QW produces signals the next consumes.

### Changed

- Updated 24 files (~182 lines), all prompt-only markdown edits. No code changes, no new files.
- plugin.json: version 1.24.2 → 1.25.0

## [1.24.1] - 2026-02-16

Patch release: Mend fixes from Phase 6 code review — sanitizer hardening, dimension alignment, configuration cleanup.

### Fixed

- Defined `sanitize()` function inline in solution-arena.md (was referenced but undefined)
- Aligned dimension names across all files to: feasibility, complexity, risk, maintainability, performance, innovation
- Fixed `const` to `let` for reassignable weight variables in weight normalization
- Removed duplicate `solution_arena` config block from configuration-guide.md
- Simplified talisman.example.yml to only expose `enabled` and `skip_for_types`
- Removed premature `arena_agents` field from inscription-schema.md

### Changed

- plugin.json: version 1.24.0 → 1.24.1
- marketplace.json: version 1.24.0 → 1.24.1

## [1.24.0] - 2026-02-16

Feature release: Solution Arena — competitive evaluation of alternative approaches before committing to a plan. Phase 1.8 generates 2-5 solutions, challenges them via Devil's Advocate and Innovation Scout agents, scores across 6 weighted dimensions, and selects a champion approach with full rationale.

### Added

- **Phase 1.8: Solution Arena** — competitive evaluation of 2-5 alternative approaches before committing to a plan
- **Devil's Advocate and Innovation Scout** challenger agents for adversarial plan evaluation
- **Weighted decision matrix** (6 dimensions: feasibility, complexity, risk, maintainability, performance, innovation) with convergence detection
- **Mandatory elicitation method selection** (Step 3.5 no longer optional — minimum 1 method required)
- `--no-arena` flag for granular Arena skip control
- **Champion Solution and Challenger Report** output formats
- `solution_arena` talisman.yml configuration section (enabled, weights, thresholds, skip_for_types)

### Changed

- Elicitation Step 3.5 now mandatory (minimum 1 method required)
- `--quick` mode auto-selects top-scored elicitation method
- Standard template includes condensed "Solution Selection" section after "Proposed Solution"
- Comprehensive template replaces passive "Alternative Approaches" with active Arena evaluation matrix
- methods.csv: Tree of Thoughts, Comparative Analysis Matrix, Pre-mortem Analysis, and Architecture Decision Records now include `plan:1.8` phase
- phase-mapping.md: Added Plan Phase 1.8 section with 4 auto-suggested Tier 1 methods
- plugin.json: version 1.23.0 → 1.24.0
- marketplace.json: version 1.23.0 → 1.24.0

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
- arc.md: `PHASE_TIMEOUTS` — per-phase hardcoded time budgets (delegated phases use inner-timeout + 60s buffer). `ARC_TOTAL_TIMEOUT` (90 min, later increased to 120 min in v1.17.0) and `STALE_THRESHOLD` (5 min)
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

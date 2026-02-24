# Changelog

## [1.91.0] - 2026-02-24

### Added
- **Directory-Scoped Audit** — `/rune:audit` gains `--dirs <path,...>` and `--exclude-dirs <path,...>` flags for pre-filtering the Phase 0 `find` command before files reach Rune Gaze, the incremental layer, or the Lore Layer (those components receive a smaller `all_files` array and require zero changes):
  - `--dirs` restricts the audit to comma-separated relative directory paths (overrides talisman `audit.dirs`; talisman value used as fallback)
  - `--exclude-dirs` excludes directories from the scan (merged with talisman `audit.exclude_dirs`; flag values take precedence)
  - Security: `SAFE_PATH_PATTERN` validation, path traversal rejection (`..`), absolute path rejection, symlink guard via `realpath -m` + project-root containment check
  - Robustness: `Array.isArray()` guard on talisman arrays, overlapping dir deduplication (subdirs covered by a parent removed), warn+skip on missing dirs, abort if ALL provided dirs are missing
  - `dirScope` threaded as Parameter Contract #20 to orchestration-phases.md and inscription metadata
  - Talisman config: `audit.dirs` and `audit.exclude_dirs` arrays supported
- **Custom Prompt-Based Audit** — `/rune:audit` gains `--prompt <text>` and `--prompt-file <path>` flags for injecting project-specific instructions into every Ash prompt during an audit session:
  - `--prompt` (inline string) > `--prompt-file` (file path) > `talisman.audit.default_prompt_file` priority chain
  - New Phase 0.5B resolves, validates, loads, and sanitizes the custom prompt block before Rune Gaze
  - `sanitizePromptContent()` strips: YAML frontmatter, HTML/XML comments, null bytes, zero-width chars, BiDi overrides, ANSI escapes, RUNE nonce markers, ANCHOR/RE-ANCHOR lines, reserved Rune headers — `RESERVED_HEADERS` regex declared inside function (prevents `/g` flag reuse bug)
  - Post-sanitization whitespace-only guard aborts with a clear error rather than injecting an empty block
  - Absolute `--prompt-file` paths must be within project root OR `~/.claude/`; relative paths are validated via `SAFE_PROMPT_PATH` pattern
  - Injection point: sanitized block appended to each Ash prompt before the RE-ANCHOR Truthbinding boundary (`customPromptBlock = null` default is CRITICAL — preserves all existing audit calls)
  - Finding attribution: standard prefixes (SEC, BACK, etc.) with `source="custom"` attribute — no CUSTOM- compound prefix
  - `customPromptBlock` threaded as Parameter Contract #21 to orchestration-phases.md
  - Talisman config: `audit.default_prompt_file` string supported
- New reference file: `skills/audit/references/prompt-audit.md` — prompt file format spec, sanitization rules table, HIPAA/OWASP/team-convention examples, edge cases table, finding attribution notes

### Changed
- `audit/SKILL.md`: `argument-hint` updated with `--dirs`, `--exclude-dirs`, `--prompt`, `--prompt-file`
- `audit/SKILL.md`: Flags table expanded with 4 new rows and updated flag interaction notes
- `audit/SKILL.md`: Phase 0 pseudocode split into directory scope resolution block (JS) + scoped `find` command (bash)
- `audit/SKILL.md`: Phase 0.5B added between Lore Layer and Rune Gaze for custom prompt resolution
- `audit/SKILL.md`: Error Handling table extended with 3 new `--prompt-file` error rows
- `orchestration-phases.md`: Parameter Contract table extended with `dirScope` (#20) and `customPromptBlock` (#21)
- `talisman.example.yml`: New `audit.dirs`, `audit.exclude_dirs`, `audit.default_prompt_file` config keys
- `inscription-schema.md`: `dir_scope` and `custom_prompt_block` fields added to inscription metadata schema
- `plugin.json` / `marketplace.json`: Version 1.90.0 → 1.91.0

## [1.90.0] - 2026-02-24

### Added
- **Flow Seer Deep Spec Analysis — 4-Phase Structured Protocol** (v1.90.0) — Transforms the flow-seer agent from an 89-line flat checklist into a 255-line 4-phase structured protocol:
  - **Phase 1 — Deep Flow Analysis**: Maps user journeys with EARS classification (Ubiquitous/State-driven/Event-driven/Optional/Unwanted), optional mermaid diagrams for complex flows (4+ decision points, max 15 nodes)
  - **Phase 2 — Permutation Discovery**: Systematic 7-dimension matrix (User Type, Entry Point, Client/Context, Network, Prior State, Data State, Timing) with NIST pairwise coverage baseline. Configurable cap via `talisman.flow_seer.permutation_cap` (default: 15)
  - **Phase 3 — Gap Identification**: 12-category checklist (Error Handling, State Management, Input Validation, User Feedback, Security, Accessibility, Data Persistence, Timeout/Rate Limiting, Resume/Cancellation, Integration Contracts, Concurrency, i18n) with category relevance filtering and cross-cutting contradiction detection
  - **Phase 4 — Question Formulation**: Prioritized questions (Critical max 5 / Important max 8 / Nice-to-have max 5) with BABOK structured interview pattern, mandatory example scenarios for critical questions
  - **FLOW-NNN finding prefix**: Spec-level findings with 3-digit format, documented as non-dedup (does not participate in `SEC > BACK > ... > CDX` hierarchy)
  - **Second-pass mode**: Auto-detects plan documents (YAML frontmatter with `type:` field), skips Phase 2 for re-validation passes
  - **Pre-Flight Checklist**: 9-point verification before output submission
  - **Phase-level output budgets**: ~180 lines total (40 + 30 + 60 + 50) to prevent context overflow
  - **Executive summary**: Gap count, critical question count, permutation coverage % as first 3 lines
- New reference file: `agents/utility/references/flow-analysis-categories.md` — extracted category tables, permutation dimensions, IEEE 29148 quality mapping, EARS classification guide, BABOK question categories, severity mapping (CRITICAL=P1, HIGH=P2, MEDIUM/LOW=P3)
- Write tool added to flow-seer frontmatter (explicit capability declaration)

### Changed
- `flow-seer.md`: Complete rewrite from 89 lines → 255 lines (4-phase protocol)
- `flow-seer.md`: Description updated with 4-phase protocol keywords for Forge Gaze topic matching
- `flow-seer.md`: Echo integration enhanced with category-specific query patterns (flow, permutation, gap, question)
- `plugin.json` / `marketplace.json`: Version 1.89.0 → 1.90.0

## [1.89.0] - 2026-02-24

### Added
- **Review Agent Gap Closure — 7 Enhancements from CE Comparison** — Closes gaps identified from comparison with compound-engineering plugin review agents:
  - **Enforcement Asymmetry Protocol** — Shared reference (`agents/review/references/enforcement-asymmetry.md`) enabling variable strictness based on change context (new file vs edit, shared vs isolated). Integrated into simplicity-warden, pattern-seer, and type-warden as proof-of-concept. Security findings always Strict.
  - **Forge-Keeper Data Migration Gatekeeper** — 3 new sections: Production Data Reality Check, Rollback Verification Depth (forward/backward compat matrix), Gatekeeper Verdicts (GATE-001 through GATE-010). GATE findings carry `requires_human_review: true`. New reference: `migration-gatekeeper-patterns.md`. Updated `data-integrity-patterns.md` with dual-write patterns.
  - **Tide-Watcher Frontend Race Conditions** — 3 new sections: Framework-Specific DOM Lifecycle Races (Hotwire/Turbo, React, Vue), Browser API Synchronization, State Machine Enforcement. New reference: `frontend-race-patterns.md`. Updated `async-patterns.md` with WebSocket/SSE patterns.
  - **Schema Drift Detector** — New review agent (`schema-drift-detector.md`) detecting accidental schema drift between migration files and ORM/model definitions across 8 frameworks (Rails, Prisma, Alembic, Django, Knex, TypeORM, Drizzle, Sequelize). DRIFT- prefix findings.
  - **Deployment Verification Agent** — New utility agent (`agents/utility/deployment-verifier.md`) generating deployment artifacts: Go/No-Go checklists, data invariant definitions, SQL verification queries, rollback procedures, and infrastructure-aware monitoring plans. Standalone-only. DEPLOY- prefix.
  - **Agent-Native Parity Reviewer** — New review agent (`agent-parity-reviewer.md`) checking agent-tool parity: orphan features, context starvation, sandbox isolation, workflow tools anti-patterns. PARITY- prefix findings.
  - **Senior Engineer Reviewer** — New review agent (`senior-engineer-reviewer.md`) with persona-based review framework: 5-dimension senior engineer perspective (production thinking, temporal reasoning, team impact, system boundaries, operational readiness). SENIOR- prefix findings. Reference: `persona-review-framework.md`.
- **5 new finding prefixes** registered in dedup-runes.md: GATE-, DRIFT-, DEPLOY-, PARITY-, SENIOR-
- **Talisman config**: New sections for `enforcement_asymmetry`, `schema_drift`, `deployment_verification`

### Changed
- `forge-keeper.md`: Description updated with gatekeeper keywords, sections expanded from 7 to 10 (203 → 274 lines)
- `tide-watcher.md`: Description updated with frontend race keywords, sections expanded from 8 to 11 (adding Framework-Specific DOM Lifecycle Races, Browser API Synchronization, State Machine Enforcement)
- `review-checklist.md`: Pre-Analysis step added for Enforcement Asymmetry
- `data-integrity-patterns.md`: Dual-write migration pattern section added
- `async-patterns.md`: WebSocket/SSE reconnection race patterns added
- `dedup-runes.md`: Standalone prefix table added, reserved standalone prefixes listed
- `agent-registry.md`: Updated counts (34 → 37 review, 10 → 12 utility*, total 79 → 83)
- `plugin.json` / `marketplace.json`: Version 1.88.0 → 1.89.0, agent counts updated

## [1.88.0] - 2026-02-24

### Added
- **PR Bot Review & Comment Resolution** — Two new arc pipeline phases and two standalone skills for automated PR review handling:
  - **Phase 9.1 BOT_REVIEW_WAIT** — Polls for bot reviews (CI, linters, security scanners) with configurable timeout and 3-layer skip gate (CLI → talisman → default off). Non-blocking failure policy.
  - **Phase 9.2 PR_COMMENT_RESOLUTION** — Multi-round review loop that fetches PR comments, applies fixes, replies with explanations, and resolves threads. Hallucination check algorithm rejects invalid fixes. 4 loop exit conditions. Crash recovery with round-aware resume.
  - **`/rune:resolve-gh-pr-comment`** — Standalone skill for resolving a single PR review comment. 10-phase workflow: parse input → fetch comment → detect author → verify code → present analysis → fix/reply/resolve.
  - **`/rune:resolve-all-gh-pr-comments`** — Standalone skill for batch PR comment resolution with pagination support and `updatedAt` tracking.
- **Talisman config**: New `arc.ship.bot_review` section with 10+ configuration keys (enabled, bot_names, timeout, max_rounds, etc.). New timeout entries for `bot_review_wait` and `pr_comment_resolution` in `arc.timeouts`.
- **Arc pipeline expansion**: PHASE_ORDER grows from 21 → 23 phases. PHASE_TIMEOUTS adds `bot_review_wait` (10 min) and `pr_comment_resolution` (15 min). Base budget ~176 → ~201 min. ARC_TOTAL_TIMEOUT_DEFAULT and HARD_CAP updated accordingly.

### Changed
- `arc/SKILL.md`: Description updated (21 → 23 phases), Pipeline Overview expanded, Phase Transition Contracts table (2 new rows), Failure Policy table (2 new rows), Error Handling table (5 new entries), calculateDynamicTimeout includes new phases
- `talisman.example.yml`: Added `bot_review` section under `arc.ship` and timeout entries
- `plugin.json` / `marketplace.json`: Version 1.87.0 → 1.88.0, skill count 31 → 33, skills array updated

## [1.87.1] - 2026-02-24

### Fixed
- **ZSH-001 Check D**: `enforce-zsh-compat.sh` now auto-fixes `\!=` (escaped not-equal) in `[[ ]]` conditions. ZSH rejects `\!=` with "condition expected" while Bash silently accepts the backslash. Auto-fix: strip backslash → `!=`.
- **ZSH-001 Check E**: `enforce-zsh-compat.sh` now auto-fixes unprotected globs in command arguments (not just for-loops). Commands like `rm -rf path/rune-*` cause ZSH NOMATCH fatal errors when no files match — `2>/dev/null` does not help. Auto-fix: prepend `setopt nullglob;`. Detects unquoted globs (strips balanced quotes before checking) for common file commands (rm, ls, cp, mv, cat, wc, head, tail, chmod, chown). Skips if `setopt nullglob` or `shopt -s nullglob` already present.
- **zsh-compat skill**: Added Pitfall 7 (escaped `\!=`) and Pitfall 8 (argument globs) documentation. Updated Quick Reference table with new safe patterns.
- **CLAUDE.md rule #8**: Added escaped `!=` and argument glob guidance. Updated enforcement hook description (3 → 5 checks).

## [1.87.0] - 2026-02-24

### Added
- **Codex Expansion — 10 Cross-Model Integration Points** — Extends inline Codex verification from 9 to 19 total integration points across 7 workflows. All integrations follow the canonical 4-condition detection gate + cascade circuit breaker (5th condition) pattern.
  - **Diff Verification** (2A) — `CDX-VERIFY` findings in `/rune:appraise` Phase 6.2. Codex cross-validates P1 findings from review. Default ON, 300s, high reasoning. ~30% skip rate when no P1/P2 findings.
  - **Test Coverage Critique** (2B) — `CDX-TEST` findings in `/rune:arc` Phase 7.8. Cross-model test adequacy assessment against implementation diff. Default ON, 600s, xhigh reasoning. ~50% skip rate at high coverage.
  - **Release Quality Check** (2C) — `CDX-RELEASE` findings in `/rune:arc` Phase 8.55. CHANGELOG completeness, breaking change detection, migration doc validation. Default ON, 300s, high reasoning. ~60% skip rate.
  - **Section Validation** (3B) — `CDX-SECTION` findings in `/rune:forge` Phase 1.7. Cross-model enrichment quality assessment. Default ON, 300s, medium reasoning. ~40% skip rate.
  - **Research Tiebreaker** (4B) — `[CDX-TIEBREAKER]` inline tag in `/rune:devise` Phase 2.3.5. Resolves conflicting research agent recommendations. Default ON, 300s, high reasoning. ~80% skip rate.
  - **Task Decomposition** (4C) — `CDX-TASK` findings in `/rune:arc` Phase 4.5. Cross-model task granularity and dependency analysis. Default ON, 300s, high reasoning. ~40% skip rate.
  - **Risk Amplification** (3A) — `CDX-RISK` findings in `/rune:goldmask` Phase 3.5. Cross-model risk signal amplification for critical files. Default **OFF**, 600s, xhigh reasoning. ~40% skip rate.
  - **Drift Detection** (3C) — `CDX-INSPECT-DRIFT` findings in `/rune:inspect` Phase 1.5. Cross-model plan-vs-implementation drift analysis. Default **OFF**, 600s, xhigh reasoning. ~50% skip rate.
  - **Architecture Review** (4A) — `CDX-ARCH` findings in `/rune:audit` Phase 6.3. Cross-model architectural pattern review. Default **OFF**, 600s, xhigh reasoning. ~70% skip rate.
  - **Post-monitor Critique** (4D) — `CDX-ARCH-STRIVE` findings in `/rune:strive` Phase 3.7. Cross-model post-completion quality critique. Default **OFF**, 300s, high reasoning. ~30% skip rate.
- **Cascade Failure Circuit Breaker** — `codex_cascade` checkpoint tracking. After 3+ consecutive Codex failures, remaining integrations auto-skip with consolidated warning. AUTH/QUOTA errors trigger immediate cascade. Tracked in arc checkpoint schema v16.
- **Arc Pipeline Phase Expansion** — 3 new phases added to PHASE_ORDER (18 → 21 phases):
  - Phase 4.5 TASK DECOMPOSITION — Codex cross-model task granularity analysis
  - Phase 7.8 TEST COVERAGE CRITIQUE — Codex cross-model test adequacy assessment
  - Phase 8.55 RELEASE QUALITY CHECK — Codex cross-model release artifact validation
- **Greenfield Codex Integration** for Inspect and Goldmask — Full detection infrastructure added to workflows that previously had zero Codex support. Both require "inspect"/"goldmask" added to `codex.workflows` default array.
- **Per-Workflow Codex Budget Caps** — Maximum Codex time and call limits per workflow (e.g., `/rune:arc` 30 min / 10 calls, `/rune:appraise` 10 min / 3 calls)

### Changed
- `arc/SKILL.md`: PHASE_ORDER expanded (18 → 21 phases), PHASE_TIMEOUTS updated (3 new entries + test/pre_ship_validation absorbed), ARC_TOTAL_TIMEOUT_HARD_CAP raised (240 → 285 min), ARC_TOTAL_TIMEOUT_DEFAULT raised (224 → 244 min), checkpoint schema v15 → v16, Phase Transition Contracts table updated (4 new rows), Failure Policy table updated (3 new rows)
- `arc/references/arc-phase-test.md`: Added Phase 7.8 TEST COVERAGE CRITIQUE reference documentation
- `arc/references/arc-phase-pre-ship-validator.md`: Added Phase 8.55 RELEASE QUALITY CHECK reference documentation
- `codex-cli/SKILL.md`: Integration count updated (9 → 19), complete 19-row budget table, per-workflow budget caps, cascade circuit breaker documentation
- `inspect/SKILL.md`: Added `codex-cli` to Load skills, Phase 1.5 Codex Drift Detection section (CDX-INSPECT-DRIFT prefix, independent of Lore Layer, 2000-char injection cap)
- `devise/SKILL.md`: Added Phase 2.3.5 Research Conflict Tiebreaker section (heuristic conflict detection, [CDX-TIEBREAKER] inline tag)
- `goldmask/SKILL.md`: Added Phase 3.5 Codex Risk Amplification section (CDX-RISK prefix, greenfield detection infrastructure)
- `roundtable-circle/SKILL.md`: Added Phase 6.2 Codex Diff Verification section (CDX-VERIFY prefix)
- `forge/SKILL.md`: Added Phase 1.7 Codex Section Validation section (CDX-SECTION prefix)
- `strive/SKILL.md`: Added Phase 3.7 Codex Post-monitor Critique section (CDX-ARCH-STRIVE prefix)
- `audit/SKILL.md`: Added Phase 6.3 Codex Architecture Review section (CDX-ARCH prefix)
- `talisman.example.yml`: Added 10 new Codex feature config keys, `codex_cascade` schema, updated `codex.workflows` defaults
- `plugin.json` / `marketplace.json`: Version 1.86.0 → 1.87.0

### Migration Notes
- **8 new CDX finding prefixes**: CDX-TEST, CDX-RELEASE, CDX-SECTION, CDX-TIEBREAKER, CDX-TASK, CDX-RISK, CDX-INSPECT-DRIFT, CDX-ARCH-STRIVE. CDX-VERIFY and CDX-ARCH are pre-existing. If you have custom Ashes using any of these prefixes, rename them to avoid dedup collisions.
- **No breaking changes**: All 10 integrations follow the canonical detection gate pattern. 6 are default ON (with strong skip conditions), 4 are default OFF (opt-in). Existing workflows without Codex installed are completely unaffected.
- **Arc checkpoint schema v16**: New `codex_cascade` field. Backward-compatible — missing field is treated as no cascade state.

## [1.86.0] - 2026-02-24

### Added
- **Stack-Aware Intelligence System** — 4-layer architecture for technology-specific review quality:
  - **Layer 0: Context Router** (`computeContextManifest()`) — Maps detected domains and stacks to skills, agents, and reference docs for loading
  - **Layer 1: Detection Engine** (`detectStack()`) — Scans manifest files (package.json, pyproject.toml, Cargo.toml, composer.json) for evidence-based stack classification with confidence scoring
  - **Layer 2: Knowledge Skills** — 16+ reference docs organized by language (Python, TypeScript, Rust, PHP), framework (FastAPI, Django, Laravel, SQLAlchemy), database (PostgreSQL, MySQL), library (Pydantic, Returns, Dishka), and pattern (TDD, DDD, DI)
  - **Layer 3: Enforcement Agents** — 11 specialist review agents with unique finding prefixes:
    - Language reviewers: `python-reviewer` (PY), `typescript-reviewer` (TSR), `rust-reviewer` (RST), `php-reviewer` (PHP)
    - Framework reviewers: `fastapi-reviewer` (FAPI), `django-reviewer` (DJG), `laravel-reviewer` (LARV), `sqlalchemy-reviewer` (SQLA)
    - Pattern reviewers: `tdd-compliance-reviewer` (TDD), `ddd-reviewer` (DDD), `di-reviewer` (DI)
  - New skill: `stacks/` with SKILL.md + 3 reference algorithms (detection.md, stack-registry.md, context-router.md) + 16 technology reference docs
  - Rune Gaze Phase 1A: Stack Detection integrated before Ash selection — specialist Ashes added based on detected stack
  - Forge Gaze: Stack affinity bonus scoring for technology-relevant enrichment agents
  - Inscription schema: New `detected_stack`, `context_manifest`, and `specialist_ashes` fields
  - Custom Ashes: New `trigger.languages` and `trigger.frameworks` fields for stack-conditional activation
  - Talisman: `stack_awareness` section (enabled, confidence_threshold, max_stack_ashes) + `forge.stack_affinity_bonus` + 11 new prefixes in `dedup_hierarchy`

### Changed
- `plugin.json` / `marketplace.json`: Version 1.85.0 → 1.86.0, description updated (23 → 34 review agents, 30 → 31 skills)
- `talisman.example.yml`: Added stack_awareness section, dedup_hierarchy updated with 11 stack specialist prefixes, forge.stack_affinity_bonus added
- `CLAUDE.md`: Added stacks skill to Skills table, updated agent count references (23 → 34 review)
- `README.md`: Updated component counts, added 11 stack specialist agents to Review Agents table, added stacks skill to Skills table, updated file tree

### Migration Notes
- **11 new reserved finding prefixes**: PY, TSR, RST, PHP, FAPI, DJG, LARV, SQLA, TDD, DDD, DI. If you have custom Ashes using any of these prefixes in your `talisman.yml`, rename them to avoid dedup collisions. The built-in stack specialist prefixes take priority in the dedup hierarchy.
- **No breaking changes**: Stack detection is opt-out (enabled by default). Set `stack_awareness.enabled: false` in talisman.yml to disable. Existing reviews without detected stacks continue unchanged.

## [1.85.0] - 2026-02-24

### Added
- **Post-Completion Advisory Hook** (`advise-post-completion.sh`) — PreToolUse advisory that detects completed arc pipelines and warns when heavy tools (Write/Edit/Task/TeamCreate) are used in the same session. Debounced once per session via `/tmp` flag file. Fail-open design. Session-isolated via `resolve-session-identity.sh`. Skips when active workflows are running (negative logic per EC-6). Atomic flag creation via `mktemp + mv` (EC-H4).
- **Context Critical Guard Hook** (`guard-context-critical.sh`) — PreToolUse guard that blocks TeamCreate and Task calls when context is at critical levels (default: 25% remaining). Reads statusline bridge file (`/tmp/rune-ctx-{SESSION_ID}.json`). Explore/Plan agents exempt for Task tool only (NOT TeamCreate per EC-4). OS-level UID check (EC-H5). 30-second bridge freshness window (EC-1). Fail-open on missing data. Escape hatches: `/rune:rest`, talisman kill switch, Explore/Plan agents.
- **Required Sections Validation** in `on-teammate-idle.sh` — Inscription-driven quality gate that checks if teammate output contains required section headings specified in `inscription.json`. Advisory only (warns but does not block). Uses `grep -qiF` for fixed-string matching (EC-1). Sanity check: skips if >20 required sections. Truncates warnings to first 5 missing sections.

### Changed
- `hooks/hooks.json`: Added 2 new PreToolUse entries — `advise-post-completion.sh` (matcher: `Write|Edit|NotebookEdit|Task|TeamCreate`) and `guard-context-critical.sh` (matcher: `TeamCreate|Task`)
- `scripts/on-teammate-idle.sh`: Extended with required sections validation after SEAL check (line 161+)

## [1.84.0] - 2026-02-24

### Added
- **Incremental Stateful Audit System** — 3-tier incremental auditing with persistent state, priority scoring, and coverage tracking. Activated via `--incremental` flag. Default `/rune:audit` behavior is completely unchanged (Concern 1: regression safety).
  - **Tier 1 — File-Level**: Codebase manifest generation via batch git plumbing (4 commands instead of N*7 per-file calls), 6-factor composite priority scoring (staleness sigmoid, recency exponential, risk from Lore Layer, complexity, novelty, role heuristic), batch selection with composition rules (20% never-audited minimum, gap carry-forward, always_audit patterns)
  - **Tier 2 — Workflow-Level**: Cross-file workflow discovery via import graph tracing, route-handler chains, convention-based fallback, and manual definitions. Workflow priority scoring with file-change detection and criticality heuristics. WF-* finding prefixes for cross-boundary analysis (DATAFLOW, ERROR, STATE, SEC, CONTRACT, TX, RACE, TRACE, ORDER)
  - **Tier 3 — API-Level**: Multi-framework endpoint discovery (Express, FastAPI, Spring, Go, Rails, Django, Flask, Gin), endpoint type classification with security boosts (GraphQL +3, WebSocket +3, File Upload +2), OWASP API Security Top 10 aligned audit checklist, contract drift detection, cross-tier security feedback (P1 API findings boost file risk scores)
  - **State Persistence**: `.claude/audit-state/` directory with manifest.json, state.json, workflows.json, apis.json, checkpoint.json (crash resume), session history snapshots, and coverage-report.md. TOCTOU-hardened mkdir-based advisory locking. Atomic write protocol (temp-file-then-rename). Schema migration mechanism for forward compatibility.
  - **Coverage Report**: Human-readable dashboard with overall progress, freshness distribution (FRESH/RECENT/STALE/ANCIENT), directory coverage treemap with blind spot detection, top-10 priority unaudited items per tier, session progress log, estimated sessions to target coverage
  - **Session Isolation**: All state files include config_dir, owner_pid, session_id. PID liveness check via `kill -0` with `node` process name verification (Concern 3: Claude Code runs as node)
  - **Warm-Run Optimization**: Stores last_commit_hash in manifest; subsequent runs scan only `git log <cached-hash>..HEAD` (<500ms for 5K-file repos with no new commits)
  - New flags: `--incremental`, `--resume`, `--status`, `--reset`, `--tier <file|workflow|api|all>`, `--force-files <glob>`
  - New reference files: `incremental-state-schema.md`, `codebase-mapper.md`, `priority-scoring.md`, `workflow-discovery.md`, `workflow-audit.md`, `api-discovery.md`, `api-audit.md`, `coverage-report.md`
  - Talisman configuration: `audit.incremental.*` section with batch_size, weights, always_audit, extra_skip_patterns, coverage_target, staleness_window_days, tier-specific settings
  - Git batch metadata uses `--since="1 year"` ceiling by default (Concern 2: not deferred)
  - Extension point contract formalized: Phase 0.1-0.4 insertion with documented input/output types (Concern 5)
  - Migration guide with recovery paths for state corruption (Concern 6)

### Changed
- `audit/SKILL.md`: Added Phase 0.1-0.4 incremental layer (gated behind `--incremental` flag — zero overhead when not set), Phase 7.5 result write-back, expanded error handling table, 8 new reference links
- `talisman.example.yml`: Added `audit.incremental.*` configuration section (commented out, opt-in)

## [1.83.0] - 2026-02-24

### Added
- **`/rune:arc-issues`** — GitHub Issues-driven batch arc execution. Processes GitHub Issues as a work queue: fetches issue content → generates plans → runs `/rune:arc` for each → posts summary comments → closes issues via `Fixes #N` in PR body.
  - 4 input methods: label-driven (`--label`), file-based queue, inline args, resume (`--resume`)
  - Paging loop (`--all`) with label-driven cursor and MAX_PAGES=50 safety cap — re-run = resume (label-based exclusion)
  - 4 Rune status labels: `rune:in-progress`, `rune:done`, `rune:failed`, `rune:needs-review`
  - Plan quality gate: skip issues with body < 50 chars (human escalation via GitHub comment + `rune:needs-review` label)
  - Title sanitization: blocklist approach preserving Unicode (not ASCII-only regex)
  - `extractAcceptanceCriteria` with defense-in-depth sanitization
  - Progress file schema v2 with `pr_created` field for crash-resume dedup
  - Session isolation: `config_dir` + `owner_pid` in state file
  - Stop hook loop driver via `arc-issues-stop-hook.sh` — GH API calls deferred to next arc turn (CC-2/BACK-008), uses `--body-file` for all comment posting (SEC-001), `Fixes #N` injection
- **Shared stop hook library** — `scripts/lib/stop-hook-common.sh` extracts common guard functions from arc-batch and arc-hierarchy stop hooks (`parse_input`, `resolve_cwd`, `check_state_file`, `reject_symlink`, `parse_frontmatter`, `get_field`, `validate_session_ownership`, `validate_paths`). Both `arc-batch-stop-hook.sh` and `arc-hierarchy-stop-hook.sh` refactored to source the library.
- **Pre-flight validation script** — `scripts/arc-issues-preflight.sh` validates gh CLI version (>= 2.4.0), authentication, issue number format, issue existence/open state, and Rune status labels with 5s per-gh-call timeout
- **`/rune:cancel-arc-issues`** — Cancel active arc-issues batch loop and remove state file
- New algorithm reference: `skills/arc-issues/references/arc-issues-algorithm.md`

### Changed
- `on-session-stop.sh`: Guard 5c added — defers to `arc-issues-stop-hook.sh` when arc-issues loop is active and owned by current session
- `pre-compact-checkpoint.sh`: Captures `arc_issues_state` alongside `arc_batch_state` before compaction
- `session-compact-recovery.sh`: Re-injects arc-issues loop context after compaction (iteration/total_plans)
- `skills/using-rune/SKILL.md`: Added arc-issues routing row and Quick Reference table entry
- `commands/rest.md`: Added `tmp/gh-issues/` and `tmp/gh-plans/` to cleanup table with active-loop guard

## [1.82.0] - 2026-02-23

### Added
- **5-Factor Composite Scoring** — Echo search now uses BM25 relevance, recency decay, importance weighting, access frequency, and file proximity for context-aware ranking
- **Access Frequency Tracking** — New `echo_access_log` SQLite table and `echo_record_access` MCP tool for usage-based scoring signals
- **File Proximity Scoring** — Evidence path extraction from echo content for workspace-relative proximity weighting
- **Dual-Mode Scoring Validation** — Kendall tau distance comparison between legacy BM25 and composite scoring with configurable toggle via `ECHO_SCORING_MODE` env var
- **Notes Tier** — User-explicit memories (`/rune:echoes remember`) with weight=0.9, stored in `.claude/echoes/notes/`
- **Observations Tier** — Agent-observed patterns with weight=0.5, auto-promotion to Inscribed after 3 access hits via atomic `os.replace()` file rewrite
- **Extended Indexer** — `header_re` now matches Notes and Observations tiers (5 total). EDGE-018 stateful parser prevents content H2 headers from splitting entries
- New test suites: `test_echo_scoring.py`, `test_echo_access.py`, `test_echo_proximity.py`, `test_echo_tiers.py` (33+ tests each)

### Changed
- Echo search server version bumped to 1.54.0
- MCP tools expanded from 4 to 5 (added `echo_record_access`)
- SKILL.md updated to 5-tier lifecycle: Etched / Notes / Inscribed / Observations / Traced
- Scoring weights configurable via environment variables (`ECHO_WEIGHT_BM25`, `ECHO_WEIGHT_RECENCY`, etc.)
- `talisman.example.yml` includes commented-out scoring configuration section

## [1.81.0] - 2026-02-23

### Added
- **Codex Exec Helper Script** (`scripts/codex-exec.sh`) — canonical Codex CLI wrapper enforcing SEC-009 (stdin pipe), model allowlist, timeout clamping [30, 900], .codexignore pre-flight, symlink/path-traversal rejection, 1MB prompt cap, and structured error classification
- New "Script Wrapper" section in `codex-cli/SKILL.md` documenting `codex-exec.sh` as the canonical invocation method
- New "Wrapper Invocation (v1.81.0+)" section in `codex-execution.md` as the preferred pattern

### Security
- **SEC-009**: Eliminated 6 `$(cat ...)` shell expansion vulnerabilities across devise (research-phase, solution-arena, plan-review), rune-echoes, elicitation, and forge-enrichment-protocol
- All Codex invocations now use stdin pipe via wrapper script instead of raw shell expansion
- Model parameter injection prevented by `CODEX_MODEL_ALLOWLIST` regex enforcement in wrapper

### Changed
- Arc Phase 2.8 (semantic verification) and Phase 5.6 (gap analysis) now use `codex-exec.sh` wrapper
- Removed inline `.codexignore` checks from arc-codex-phases.md (handled by wrapper, exit code 2 = skip)
- Simplified model/reasoning/timeout validation in arc phases (delegated to wrapper script)

## [1.80.0] - 2026-02-23

### Added
- **Stagnation Sentinel** — Cross-phase progress tracking with error repetition detection, file-change velocity metrics, and budget consumption forecasting (checkpoint schema v15)
- **Pre-Ship Completion Validator** — New Phase 8.5 dual-gate quality check before PR creation (artifact integrity + quality signals)
- **Specification-by-Example Agent Prompts** — BDD-style Given/When/Then scenarios for mend-fixer (4 scenarios), rune-smith (3 scenarios), and trial-forger (3 scenarios)
- New reference: `stagnation-sentinel.md` for cross-phase stagnation detection
- New reference: `arc-phase-pre-ship-validator.md` for pre-ship quality gate

### Changed
- Arc pipeline expanded from 17 to 18 phases (added Phase 8.5: Pre-Ship Validation)
- Checkpoint schema bumped from v14 to v15 (added `stagnation` field)

## [1.79.0] - 2026-02-23

### Added
- **Hierarchical Plans** — Parent/child plan decomposition with dependency DAGs
  - New `/rune:arc-hierarchy` skill for orchestrating multi-plan execution in dependency order
  - Devise Phase 2.5 "Hierarchical" option for plan decomposition (complexity >= 0.65)
  - Cross-child coherence check (Phase 2.5D) — task coverage, contract dedup, circular dependency detection
  - Requires/provides contract system — supports artifact types: file, export, type, endpoint, migration
  - Pre-execution prerequisite verification with 3 resolution strategies: pause / self-heal / backtrack
  - Feature branch + child sub-branch strategy (`feature/{id}/child-N-{slug}`) with single PR to main
  - Strive child context injection — completed sibling artifacts, prerequisites, self-heal task prioritization
  - Dedicated stop hook (`arc-hierarchy-stop-hook.sh`) separate from arc-batch
  - `/rune:cancel-arc-hierarchy` command for graceful loop cancellation
  - Talisman `work.hierarchy.*` configuration (11 new keys: enabled, max_children, max_backtracks, missing_prerequisite, conflict_resolution, integration_failure, sync_main_before_pr, cleanup_child_branches, require_all_children, test_timeout_ms, merge_strategy)
  - Coherence check output: `tmp/plans/{timestamp}/coherence-check.md`
  - Migration note: hierarchical is fully opt-in — existing strive/arc workflows are unaffected

### Architecture
- Arc checkpoint schema v14: `parent_plan` metadata for hierarchical execution tracking
- Hierarchy-specific stop hook with STOP-001 one-shot guard pattern
- Session isolation for hierarchy state files (config_dir + owner_pid fields)
- Auto-generate requires/provides from task analysis (file references, exports, API routes, imports)
- DAG validation via topological sort to detect cycles before generation completes
- synthesize.md: hierarchical frontmatter templates, parent execution table template, dependency contract matrix template, artifact type reference, status value reference

## [1.78.0] - 2026-02-23

### Added
- **Context Monitor Hook** — PostToolUse hook that injects agent-visible warnings when context usage exceeds thresholds (WARNING at 35% remaining, CRITICAL at 25%)
- **Statusline Bridge** — Statusline script that writes context metrics to bridge file for monitor consumption. Color-coded progress bar, git branch, workflow detection
- **Session Budget in Plans** — Optional `session_budget` frontmatter for strive/arc worker cap validation (`max_concurrent_agents` only in v1.78.0)
- **Talisman config** — New `context_monitor` section with configurable thresholds, debounce, staleness, and per-workflow enable/disable
- **Bridge file cleanup** — Automatic cleanup of context bridge files on session end via ownership-scan pattern in `on-session-stop.sh`

### Architecture
- Producer/Consumer pattern: statusline writes, monitor reads (via `/tmp/` bridge file)
- Inspired by GSD's context monitoring approach
- Non-blocking: all errors exit 0, monitor never blocks tool execution
- Session-isolated: bridge files keyed by `session_id` with `config_dir` + `owner_pid`

## [1.77.0] - 2026-02-23

### Added
- **Mend-Fixer Bidirectional Review Protocol**: Added "Receiving Review Findings — Bidirectional Protocol" section to `mend-fixer.md`. Includes "Actions > Words" principle (no performative agreement), 5-step Technical Pushback Protocol, "Never Blindly Fix" section with 4 anti-patterns, and Commitment section. Extends existing FALSE_POSITIVE handling without modifying existing content.
  - Enhanced: `agents/utility/mend-fixer.md` — new section before RE-ANCHOR
- **Condition-Based Waiting Patterns**: Created `skills/polling-guard/references/condition-based-waiting.md` reference file with 4 pattern categories: Wait-Until (with timeout fallback), Exponential Backoff (with jitter formula), Deadlock Detection (4 scenarios + recovery checklist), and Polling vs Push comparison table. Linked from polling-guard SKILL.md.
  - New: `skills/polling-guard/references/condition-based-waiting.md`
  - Enhanced: `skills/polling-guard/SKILL.md` — added "Additional Patterns" section before Reference
- **Creation Log Template and Seed Logs**: Added `references/creation-log-template.md` with 5 required sections (Problem, Alternatives, Decisions, Rationalizations, History). Created 3 seed CREATION-LOG.md files for inner-flame, roundtable-circle, and context-weaving skills — each with 2+ alternatives, 2+ key decisions, and iteration history from CHANGELOG.md.
  - New: `references/creation-log-template.md` — template for per-skill creation logs
  - New: `skills/inner-flame/CREATION-LOG.md` — 3-layer design decisions, fresh evidence gate history
  - New: `skills/roundtable-circle/CREATION-LOG.md` — 7-phase lifecycle, inscription contracts, multi-wave history
  - New: `skills/context-weaving/CREATION-LOG.md` — unified overflow model, glyph budget system
  - Enhanced: `CLAUDE.md` — added creation-log-template link in Skill Compliance section

## [1.76.0] - 2026-02-23

### Added
- Systematic Debugging skill — 4-phase methodology (Observe → Narrow → Hypothesize → Fix) with Iron Law DBG-001
- Persuasion Principles reference guide — principle mapping for 5 agent categories
- CSO (Claude Search Optimization) reference guide — trigger-focused description writing
- Commitment Protocol sections added to work agents (rune-smith, trial-forger)
- Authority & Evidence sections added to review agents (ward-sentinel, ember-oracle, flaw-hunter, void-analyzer)
- Authority & Unity section added to mend-fixer agent
- Consistency section added to pattern-seer agent

### Changed
- 7 skill descriptions CSO-optimized for better auto-discovery
- Failure Escalation Protocol added to rune-smith agent

## [1.75.0] - 2026-02-23

### Added
- **Skill Testing Framework** (`skill-testing` skill): TDD methodology for documentation — write a failing pressure scenario first, then write the skill to address it. Includes Iron Law (SKT-001: "NO SKILL WITHOUT A FAILING TEST FIRST"), RED/GREEN/REFACTOR cycle for skills, rationalization table template, pressure scenarios for roundtable-circle/rune-smith/mend-fixer, and meta-testing checklist. Set `disable-model-invocation: true` to avoid CSO collision with `testing` skill.
  - New: `skills/skill-testing/SKILL.md` — main skill with TDD cycle and priority targets
  - New: `skills/skill-testing/references/pressure-scenarios.md` — 9 detailed scenario scripts (3 per target skill)
  - New: `skills/skill-testing/references/rationalization-tables.md` — observed patterns by agent type and severity

### Enhanced
- **Inner Flame fresh evidence verification**: Added item #6 to Layer 1 (Grounding Check) requiring fresh evidence for every completion claim. Agents must now cite specific command output, test results, or file:line references from the current session — not just claim "tests pass." Replaces the originally proposed keyword-banning approach with a self-check question that avoids false positives. Preserves the existing 3-layer model (zero changes to agent prompts, hooks, or CLAUDE.md).
  - Enhanced: `skills/inner-flame/SKILL.md` — fresh evidence item #6 in Layer 1, updated Seal Enhancement descriptions
  - Enhanced: `skills/inner-flame/references/role-checklists.md` — per-role evidence items for Worker (3 items), Fixer (3 items), and Reviewer (1 item)

## [1.74.1] - 2026-02-23

### Fixed
- **ZSH eval history expansion inside `[[ ]]`**: Fixed `(eval):1: parse error: condition expected: \!` errors in arc-batch team cleanup. In zsh eval context, `!` inside `[[ ]]` (e.g., `[[ ! -L path ]]`, `[[ "$a" != "$b" ]]`) triggers history expansion before the conditional parser processes it.
  - Restructured `arc-batch-stop-hook.sh` ARC_PROMPT template to avoid `!` entirely: `[[ ! -L ]]` → `[[ -L ]] && continue`, `!= ` → `case ... esac`
  - Fixed same pattern in `post-arc.md` and `arc-phase-cleanup.md` pseudocode: `[[ ! -L ]] &&` → `{ [[ -L ]] || action; }`
  - Fixed `commands/rest.md` signal cleanup: restructured `[[ ! -L ]]` conditional
  - Added **Check D** to `enforce-zsh-compat.sh`: detects `!` inside `[[ ]]` and auto-fixes with `setopt no_banghist;`
  - Refactored hook auto-fixes to be **cumulative** — Checks B, C, D can all apply to the same command (previously each check exited early, so only the first fix was applied)
  - Added **Pitfall 7** documentation to `zsh-compat` skill: `!` inside `[[ ]]` in eval context
  - Updated quick reference table with `!`-free patterns for eval-safe conditionals

## [1.74.0] - 2026-02-23

### Changed
- **Refactor Phase 5.6 (Codex Gap Analysis) to inline Bash pattern**: Removed team lifecycle overhead (~20-30s savings per arc run) by switching from spawning `arc-gap-{id}` team with teammates to orchestrator-direct `Bash("codex exec")` calls, matching the proven Phase 2.8 pattern.
  - Rewritten: `arc-codex-phases.md` Phase 5.6 section (primary implementation)
  - Rewritten: `gap-analysis.md` STEP 4+5 (secondary implementation)
  - Removed: `codex_gap_analysis` entry from `PHASE_PREFIX_MAP` in `arc-phase-cleanup.md`
  - Removed: `"arc-gap-"` prefix from `ARC_TEAM_PREFIXES` in `arc-preflight.md`
  - Added: Phase 5.6 entries to `phase-tool-matrix.md` (tool restrictions + time budget)
  - Updated: SKILL.md Phase 5.6 stub and timeout comment
  - Fixed: ZSH-FIX in `arc-phase-cleanup.md` `postPhaseCleanup` — symlink guard changed from `[[ ! -L ]] && rm` to `[[ -L ]] || rm` to avoid `!` history expansion in zsh eval context

## [1.73.0] - 2026-02-23

### Added
- **Arc-scoped file-todos with per-source subdirectories**: Todos organized into `work/`, `review/`, `audit/` subdirectories instead of flat `todos/` directory. Independent ID sequences per subdirectory.
  - New: `resolveTodosBase()` and `resolveTodosDir()` pseudo-functions in integration-guide.md
  - New: `--todos-dir` flag for strive, appraise, audit, and mend (arc passes `tmp/arc/{id}/todos/`)
  - New: Arc todos scaffolding creates `work/` and `review/` subdirectories before Phase 5
  - New: Post-phase verification (Phase 5, 6, 7) with spot-check and `todos_summary` in checkpoint
  - New: File-Todos Summary section in ship phase PR body
  - Enhanced: Mend cross-source scan via `Glob(\`${base}*/[0-9][0-9][0-9]-*.md\`)` for finding_id matching
  - Enhanced: file-todos subcommands updated for per-source subdirectory awareness
  - New: `file_todos` section in talisman.yml (enabled: true, auto_generate: work/review/audit)

## [1.72.0] - 2026-02-23

### Added
- **Arc-batch inter-iteration summaries**: Structured summary files written between arc iterations for improved compact recovery and context awareness. Hybrid approach: hook-written structured metadata + Claude-written context note.
  - New: `tmp/arc-batch/summaries/iteration-{N}.md` per-iteration summary files with plan path, status, git log, PR URL, branch name
  - New: ARC_PROMPT step 4.5 for Claude context note injection (conditional on summary existence, Truthbinding-wrapped)
  - New: `summary_enabled` and `summary_dir` fields in arc-batch state file (backward-compatible defaults)
  - Enhanced: Pre-compact checkpoint captures arc-batch iteration state (`arc_batch_state` field)
  - Enhanced: Compact recovery references latest summary file in additionalContext
  - New talisman config: `arc.batch.summaries.enabled` (default: true)
- Summary writer follows Revised Flow ordering: summary written BEFORE plan completion mark for crash-safety
- Trace logging (`_trace()`) instrumentation in arc-batch stop hook (opt-in via `RUNE_TRACE=1`)

## [1.71.0] - 2026-02-23

### Added
- **Universal Goldmask integration** across all Rune workflows that previously lacked it:
  - **Forge**: Phase 1.3 (file ref extraction) + Phase 1.5 (Lore Layer) with risk-boosted Forge Gaze scoring (CRITICAL +0.15, HIGH +0.08) and risk context injection into forge agent prompts. New `--no-lore` flag.
  - **Mend**: Phase 0.5 (Goldmask data discovery) with risk-overlaid severity ordering, fixer prompt injection (risk tiers + wisdom advisories + blast-radius warnings), and Phase 5.9 (deterministic quick check against MUST-CHANGE files).
  - **Inspect**: Phase 0.3 (Lore Layer) with risk-weighted requirement classification, dual inspector assignment for CRITICAL requirements, risk-enriched inspector prompts with role-specific notes, and Historical Risk Assessment in VERDICT.md.
  - **Devise upgrade**: Phase 2.3 upgraded from 2-agent basic to 6-agent enhanced mode (default). Three depth modes: `basic` (2 agents), `enhanced` (6 agents: lore + 3 Impact tracers + wisdom + coordinator), `full` (8 agents, inlined). Partial-ready gate, 5-min hard ceiling.
- **Shared Goldmask infrastructure**:
  - `goldmask/references/data-discovery.md` — standardized protocol for finding and reusing existing Goldmask outputs across workflows (7-path search order including forge/ and plans/, age guard, TOCTOU-safe reads, 30% overlap validation, POSIX-only platform note)
  - `goldmask/references/risk-context-template.md` — shared template for injecting risk data into agent prompts (3 sections: File Risk Tiers, Caution Zones, Blast Radius)
- **Per-workflow talisman config** (`goldmask.forge`, `goldmask.mend`, `goldmask.devise`, `goldmask.inspect`) with documented kill switches and defaults

### Changed
- `goldmask.enabled` now defaults to `true` consistently across all workflows
- `goldmask.devise.depth` defaults to `enhanced` (was implicit `basic`)
- `agent-registry.md`: lore-analyst usage contexts updated (now includes forge, inspect)

## [1.70.0] - 2026-02-23

### Added
- Phase 5.5 STEP A.10: Stale reference detection — scans for lingering references to deleted files
- Phase 5.5 STEP A.11: Flag scope creep detection — identifies unplanned CLI flags in implementation
- Phase 5.8 dual-gate: Codex findings now trigger gap remediation via OR logic with deterministic gate
- New talisman key: `codex.gap_analysis.remediation_threshold` (default: 5, range: [1, 20])

### Unchanged
- `halt_on_critical` default remains `false` — Codex dual-gate provides activation path without breaking existing pipelines

## [1.69.0] - 2026-02-23

### Added
- **file-todos skill** — Unified file-based todo tracking system for Rune workflows. Structured YAML frontmatter, 6-state lifecycle (`pending/ready/in_progress/complete/blocked/wont_fix`), source-aware templates, and 7 subcommands (`create`, `triage`, `status`, `list`, `next`, `search`, `archive`).
  - **Core skill**: `skills/file-todos/SKILL.md` with 5 reference files (todo-template, lifecycle, triage-protocol, integration-guide, subcommands).
  - **Command entry**: `commands/file-todos.md` for `/rune:file-todos` invocation.
  - **Review integration**: Phase 5.4 in `orchestration-phases.md` — auto-generates file-todos from TOME findings (gated by `talisman.file_todos.enabled`).
  - **Work integration**: `todo-protocol.md` in strive — per-task todo tracking during swarm execution.
  - **Mend integration**: Phase 5.9 in `mend/SKILL.md` — updates file-todos for resolved findings (gated by `talisman.file_todos.enabled`).
  - **Agent awareness**: `rune-smith.md` and `trial-forger.md` updated with todo protocol reference.
  - **Inscription schema**: `inscription-schema.md` updated with `todos` output field.

## [1.68.0] - 2026-02-23

### Added
- **Guaranteed post-phase team cleanup** (`postPhaseCleanup`) — New trailing-edge cleanup function that runs after every delegated arc phase completes (success/fail/timeout). Forms a before+after bracket with `prePhaseCleanup` around every phase:
  - **`arc-phase-cleanup.md`** (new): Contains `postPhaseCleanup()` function and `PHASE_PREFIX_MAP` mapping 10 delegated phases to their team name prefixes. Uses prefix-based filesystem scan as primary mechanism (handles null `team_name` in checkpoint). Includes cross-session safety via `.session` marker comparison and symlink guards.
  - **SKILL.md phase stubs**: All 10 delegated phases now call `postPhaseCleanup(checkpoint, phaseName)` after checkpoint update.
  - **ARC-9 Strategy D** (new): Prefix-based sweep in post-arc final sweep catches teams missed by checkpoint. Uses `ARC_TEAM_PREFIXES` for comprehensive orphan scanning with symlink guard and regex validation.
- **Goldmask session hook integration** — Closes the goldmask prefix gap in session cleanup hooks:
  - **`on-session-stop.sh`**: Added `goldmask-*` to team directory scan pattern (was previously excluded).
  - **`session-team-hygiene.sh`**: Added `goldmask-*` to orphan team scan and `.rune-goldmask-*.json` to state file pattern.
  - **`goldmask/SKILL.md`**: Added state file creation (`tmp/.rune-goldmask-{session_id}.json`) with proper session isolation fields and cleanup on workflow completion.

### Changed
- **`post-arc.md`**: ARC-9 Final Sweep now has 4 strategies (A: discovery+shutdown, B: SDK TeamDelete, C: filesystem fallback, D: prefix-based sweep).
- **`arc-phase-goldmask-verification.md`**: Added `postPhaseCleanup` call after checkpoint update and updated crash recovery documentation.
- **Phase reference files**: Updated cleanup documentation in `arc-phase-forge.md`, `arc-phase-code-review.md`, `arc-phase-work.md`, `arc-phase-mend.md`, `arc-phase-test.md`, `arc-phase-plan-review.md` to reference both pre and post phase cleanup.
- **`team-lifecycle-guard.md`** (rune-orchestration): Updated Inter-Phase Cleanup section to document the before+after bracket pattern.

## [1.67.0] - 2026-02-22

### Added
- **Session-scoped team cleanup** — Prevents cross-session interference when multiple Claude Code sessions work on the same repo:
  - **TLC-004 session marker hook** (`stamp-team-session.sh`): PostToolUse:TeamCreate hook writes `.session` file inside team directory containing `session_id`. Atomic write (tmp+mv), fail-open.
  - **Session-scoped stale scan** (`enforce-team-lifecycle.sh`): TLC-001 now checks `.session` marker during stale detection — skips teams owned by other live sessions, cleans only orphaned teams.
  - **Session-scoped appraise identifiers**: `/rune:appraise` team names now include 4-char session suffix (`rune-review-{hash}-{sid4}`) to prevent collision when two sessions review the same commit.
  - **Session context in TLC-002 reports**: `verify-team-cleanup.sh` includes 8-char session ID prefix in post-delete diagnostic messages.
  - **Session-scoped arc-batch cleanup**: `arc-batch-stop-hook.sh` filters team cleanup to session-owned teams only (R13 fix).
- **Session Ownership documentation** in `team-lifecycle-guard.md`: `.session` marker contract, ownership verification matrix, state file session fields reference.

## [1.66.0] - 2026-02-22

### Added
- **Shard-aware arc execution** — `/rune:arc` and `/rune:arc-batch` now detect shattered plans and coordinate shard execution:
  - **Shard detection in arc pre-flight**: Detects shard plans via `-shard-N-` filename regex, reads parent plan frontmatter, verifies prerequisite shards are complete (warn, not block)
  - **Shared feature branch**: Shard arcs reuse `rune/arc-{feature}-shards-{timestamp}` branch instead of creating separate branches per shard
  - **Shard-aware PR titles**: `feat(shard 2 of 4): methodology - feature name` format with `safePrTitle` sanitizer compatibility
  - **Shard context in PR body**: Parent plan reference, dependency list, and shard position
  - **Arc-batch shard group detection**: Auto-sorts shards by number, auto-excludes parent plans (`shattered: true`), detects missing shard gaps
  - **Arc-batch preflight shard validation**: Validates shard frontmatter (`shard:`, `parent:` fields), checks group ordering and gaps
  - **Shard-aware stop hook**: Detects sibling shard transitions — stays on feature branch instead of checking out main between sibling shards
  - **Shard metadata in batch progress**: `batch-progress.json` schema v2 with `shard_group`, `shard_num`, and group summary
  - **Talisman configuration**: `arc.sharding.*` keys (enabled, auto_sort, exclude_parent, prerequisite_check, shared_branch) — all default to true
  - **`--no-shard-sort` flag** for arc-batch to disable auto-sorting
- **Parent path fallback**: Sibling-relative path resolution when absolute `parent:` path in shard frontmatter fails (handles `plans/shattering/` subdirectory case)
- **Checkpoint schema v12**: Added optional `shard` field with num, total, name, feature, parent, dependencies

## [1.65.1] - 2026-02-22

### Changed
- **Agent quality enhancements** — ai-devkit design philosophy learnings applied to 10 agent files:
  - `simplicity-warden`: Added Readability Assessment (4-gate Reading Test), 7 Simplification Patterns taxonomy, Hard Rule
  - `flaw-hunter`: Added Hypothesis Protocol with evidence-first analysis, UNCERTAIN severity cap, Hard Rule
  - `mimic-detector`: Added Duplication Tolerance Threshold with concrete flag/no-flag criteria, security override, Hard Rule
  - `mend-fixer`: Added QUAL-Prefix Fix Guidance table (7 simplification patterns for QUAL findings)
  - `scroll-reviewer`: Added 5-dimension Quality Dimensions rating (1-5), severity classification, critical dimension override, Hard Rule
  - `truth-seeker`, `naming-intent-analyzer`, `ember-oracle`, `depth-seer`, `tide-watcher`: Added Hard Rule sections

## [1.65.0] - 2026-02-22

### Changed
- **Skill rename to avoid autocomplete collision** — Renamed 3 skills to prevent `/plan`, `/review`, `/work` from colliding with Claude Code built-in commands in autocomplete:
  - `/rune:plan` -> `/rune:devise`
  - `/rune:review` -> `/rune:appraise`
  - `/rune:work` -> `/rune:strive`
- Skill directories renamed: `skills/plan/` -> `skills/devise/`, `skills/review/` -> `skills/appraise/`, `skills/work/` -> `skills/strive/`
- All cross-references updated across 77 files (289 insertions, 289 deletions)
- **Preserved (unchanged)**: Internal team name prefixes (`rune-review-*`, `rune-work-*`, `rune-plan-*`), state file patterns, `ARC_TEAM_PREFIXES`, talisman config keys, workflow IDs, output paths (`tmp/reviews/`, `tmp/work/`), agent directories (`agents/work/`, `agents/review/`), cancel commands (`/rune:cancel-review`)

## [1.64.0] - 2026-02-22

### Changed
- **Commands-to-Skills migration** — Migrated 7 major commands to skills format with lazy-load reference decomposition: `strive`, `devise`, `appraise`, `audit`, `mend`, `inspect`, `forge`
- Skills gain `allowed-tools`, `disable-model-invocation`, `argument-hint`, and lazy-load reference support vs legacy commands
- Plugin now has **8 commands** and **25 skills** (was 15 commands, 18 skills)
- 12 new reference files created with content extracted from commands (quality-gates.md, todo-protocol.md, brainstorm-phase.md, ash-summoning.md, tome-aggregation.md, review-scope.md, fixer-spawning.md, resolution-report.md, inspector-prompts.md, verdict-synthesis.md, deep-mode.md, forge-enrichment-protocol.md)
- 9 existing reference files moved via `git mv` (history preserved): 4 work refs, 4 plan refs, 1 mend ref
- Cross-references updated: `skills/git-worktree/SKILL.md`, `skills/elicitation/references/phase-mapping.md`, `skills/roundtable-circle/references/risk-tiers.md`, `skills/roundtable-circle/references/chunk-orchestrator.md`, `skills/roundtable-circle/references/plan-parser.md`

## [1.63.2] - 2026-02-22

### Fixed
- **SEC-1/SEC-2**: Added checkpoint validation guards in `arc-codex-phases.md` Phase 5.6 — `plan_file` path validation and `git_sha` pattern validation prevent prompt injection from tampered checkpoint JSON
- **VEIL-1**: Added missing Phase 8.5 (AUDIT MEND) and Phase 8.7 (AUDIT VERIFY) to completion report template in `post-arc.md` (pre-existing bug)
- **DOC-1**: Fixed broken `team-lifecycle-guard.md` relative links in `arc-phase-mend.md` — updated to correct `../../rune-orchestration/references/` path
- **SEC-3**: Added inline SEC annotation for `enrichedPlanPath` in `arc-codex-phases.md` Phase 2.8
- **VEIL-2**: Clarified SETUP_BUDGET scope comment in `arc/SKILL.md` — was misleadingly described as "mend-scoped" but applies to all delegated phases
- **QUAL-1**: Added missing Inputs/Outputs/Error handling metadata to `codex-execution.md` for cross-skill consistency
- **DOC-2**: Replaced hardcoded `/18 phases` with `/${PHASE_ORDER.length}` in `post-arc.md` echo persist
- **Context Intelligence**: Removed invalid `linkedIssues` field from `gh pr view --json` query — field doesn't exist in gh CLI structured output

## [1.63.1] - 2026-02-21

### Fixed
- **Arc checkpoint zsh compat** — Replaced `! [[ "$epoch" =~ ^[0-9]+$ ]]` with POSIX `case` statement in concurrent arc detection. The negated `[[ =~ ]]` caused `condition expected: \!` errors in zsh (macOS default shell)

## [1.63.0] - 2026-02-21

### Added
- **Session-level isolation for all Rune workflows** — Two-layer session identity (`config_dir` + `owner_pid`) prevents cross-session interference when multiple Claude Code sessions work on the same repository
- **`resolve-session-identity.sh`** — Shared helper script that exports `RUNE_CURRENT_CFG` (resolved config dir) and uses `$PPID` for process-level isolation. Sourced by all hook scripts that need ownership filtering
- **Ownership filtering in hook scripts** — `enforce-teams.sh`, `on-session-stop.sh`, `enforce-polling.sh`, and `session-team-hygiene.sh` now filter state files by session ownership before acting
- **Session identity fields in all state files** — `config_dir`, `owner_pid`, `session_id` added to state file writes in review, audit, work, mend, forge, and inspect commands
- **Session identity in arc checkpoints** — `config_dir`, `owner_pid`, `session_id` added to `.claude/arc/{id}/checkpoint.json` creation
- **Foreign session warning in cancel commands** — `cancel-review.md`, `cancel-audit.md`, and `cancel-arc-batch.md` warn (don't block) when cancelling another session's workflow. `cancel-arc.md` skips batch cancellation when the batch belongs to another live session
- **Core Rule 11: Session isolation** — Documented as CRITICAL rule in plugin CLAUDE.md and project CLAUDE.md

### Fixed
- **Arc pre-flight directory** — Fixed pre-flight check using bare relative `find .claude/arc` instead of explicit `${CWD}/.claude/arc` (correct — project-scoped checkpoints) in both jq and grep fallback paths
- **Arc resume path** — Fixed `--resume` checkpoint discovery to search `${CWD}/.claude/arc` instead of `$CHOME/arc`
- **Cancel command PID validation** — Added numeric validation (`/^\d+$/.test()`) before `kill -0` calls in cancel-review.md and cancel-audit.md pseudocode (SEC-3)
- **Cancel command variable scoping** — Fixed `const selected` redeclaration and `state.owner_pid` reference in cancel-review.md and cancel-audit.md (BACK-2, BACK-3)
- **enforce-polling.sh missing inspect glob** — Added `.rune-inspect-*.json` to state file detection glob, matching enforce-teams.sh coverage (QUAL-7)
- **on-session-stop.sh config-dir resolution** — Moved `resolve-session-identity.sh` source before GUARD 5 to eliminate duplicate config-dir resolution (SEC-12)

### Changed
- `enforce-teams.sh`: Sources `resolve-session-identity.sh`, filters arc checkpoints and state files by ownership
- `on-session-stop.sh`: Sources `resolve-session-identity.sh`, filters all 3 cleanup phases (teams, states, arcs) by ownership
- `enforce-polling.sh`: Sources `resolve-session-identity.sh`, filters workflow detection by ownership
- `session-team-hygiene.sh`: Sources `resolve-session-identity.sh`, filters stale state file counting by ownership

## [1.62.0] - 2026-02-21

### Added
- **Git worktree isolation for `/rune:strive`** — Experimental `--worktree` flag enables isolated git worktree execution. Workers operate in separate worktrees with direct commits instead of patch generation
- **`git-worktree` skill** (`skills/git-worktree/SKILL.md`) — Background knowledge for worktree merge strategies, conflict resolution, and cleanup procedures
- **Wave-based execution** — Tasks grouped by dependency depth into waves for parallel worktree execution. DFS-based wave computation with cycle detection
- **Merge broker** — Replaces commit broker in worktree mode. Merges worker branches into feature branch between waves with `--no-ff`, conflict escalation to user (never auto-resolves)
- **`worktree-merge.md` reference** — Complete merge broker algorithm, `collectWaveBranches()`, `cleanupWorktree()`, and conflict resolution flow
- **Wave-aware monitoring** — Per-wave monitoring loop with independent timeouts, merge broker dispatch between waves
- **SDK canary test** — Validates `isolation: "worktree"` parameter is supported before enabling worktree mode. Graceful fallback to patch mode on failure
- **Worktree garbage collection** — Phase 6 cleanup prunes orphaned worktrees and branches matching `rune-work-*` pattern
- **Worktree worker prompts** — Updated `worker-prompts.md`, `rune-smith.md`, and `trial-forger.md` with worktree-specific commit protocol and branch metadata reporting

### Changed
- work.md Phase 0: Added `--worktree` flag parsing with talisman fallback (`work.worktree.enabled`)
- work.md Phase 0.5: Added worktree validation (git version check, worktree command availability, SDK canary)
- work.md Phase 1: Added wave computation (step 5.3) after dependency linking
- work.md Phase 2: Added wave-based worker spawning with `isolation: "worktree"` as separate code path
- work.md Phase 3: Added wave-aware monitoring loop for sequential wave execution
- work.md Phase 3.5: Added merge broker as worktree-mode alternative to commit broker
- work.md Phase 6: Added worktree garbage collection (step 3.6)
- Skill count: 17 → 18 (added git-worktree)

## [1.61.0] - 2026-02-21

### Added
- **Doubt Seer agent** (`doubt-seer.md`) — Evidence quality challenger that cross-examines Ash findings for unsubstantiated claims. Challenges findings lacking Rune Traces, verifies evidence against source, and produces a structured verdict (PASS/CONCERN/BLOCK). Configurable via `doubt_seer` talisman block
- **Phase 4.5: Doubt Seer** in Roundtable Circle — Conditional phase between Monitor (Phase 4) and Aggregate (Phase 5). Spawns doubt-seer when enabled in talisman AND P1+P2 findings exist. 5-minute timeout with separate polling loop. VERDICT parsing determines workflow continuation
- **Evidence-tagged Seal fields** — `evidence_coverage` ("N/M findings have structured evidence") and `unproven_claims` (integer) added to all three Seal locations in inscription-protocol.md. Fields absent entirely when doubt-seer disabled (backward compatible)
- **DOUBT finding prefix** — Reserved in custom-ashes.md validation rules and added to dedup hierarchy in output-format.md (`SEC > BACK > VEIL > DOUBT > DOC > QUAL > FRONT > CDX`)
- **`doubt_seer` talisman config** — 6-field configuration block: `enabled` (default: false), `workflows`, `challenge_threshold`, `max_challenges`, `block_on_unproven`, `unproven_threshold`

### Changed
- Review agent count: 22 → 23 (added doubt-seer)
- Total agent count: 67 → 68
- Inscription schema updated with doubt-seer teammate entry and evidence fields
- Agent registry updated with doubt-seer entry

## [1.60.0] - 2026-02-21

### Added
- **Phase 0.3: Context Intelligence** — New review pipeline phase that gathers PR metadata via `gh pr view`, classifies PR intent (bugfix/feature/refactor/docs/test/chore), assesses context quality (good/fair/poor), detects scope warnings for large PRs, and fetches linked issue context. Injects `## PR Context` section into ash-prompt templates with Truthbinding-extended untrusted-content warning
- **Phase 0.4: Linter Detection** — New review pipeline phase that discovers project linters from config files (16 linter signatures: ESLint, Prettier, Biome, TypeScript, Ruff, Black, Flake8, mypy, pyright, isort, RuboCop, Standard, golangci-lint, Clippy, rustfmt, EditorConfig). Injects `## Linter Awareness` section into ash-prompts to suppress findings in linter-covered categories. SEC-\* and VEIL-\* findings are never suppressed
- **Finding Taxonomy Expansion (Q/N)** — Extended P1/P2/P3 severity taxonomy with orthogonal interaction types: Question (Q) for clarification-needed findings and Nit (N) for cosmetic/author-discretion findings. Added to all 7 ash-prompt templates with behavioral rules and output format sections
- **Perspective 11: Naming Intent Quality** — New Pattern Weaver perspective that evaluates whether names accurately reflect code behavior. Detects name-behavior mismatch, vague names hiding complexity, boolean inversion, side-effect hiding, abbreviation ambiguity. Language-aware conventions (Rust, Go, React) reduce false positives. Architecture escalation when 3+ naming findings cluster
- **`naming-intent-analyzer` agent** — Standalone naming intent analysis agent for `/rune:audit` deep analysis. Read-only tools, inner-flame self-review skill, echo-search integration
- **`context-intelligence.md` reference** — Full contract, schema, security model, and talisman configuration for Phase 0.3
- **`sanitizeUntrustedText()` canonical pattern** — Centralized 8-step sanitization function for user-authored content (PR body, issue body). Includes CVE-2021-42574 (Trojan Source) defense and HTML entity stripping. Registered in security-patterns.md
- **`SAFE_ISSUE_NUMBER` security pattern** — `/^\d{1,7}$/` validator for GitHub issue numbers before shell interpolation. Registered in security-patterns.md
- **Q/N sections in TOME format** — Runebinder TOME now includes `## Questions` and `## Nits` sections with dedicated finding formats
- **Q/N dedup rules** — Extended dedup algorithm: assertion supersedes Q/N at same location; Q and N coexist at same location; multiple Q at same location merged
- **Q/N mend skip logic** — Questions and Nits excluded from auto-mend with descriptive skip messages
- **`taxonomy_version` field** — New inscription.json field signaling Q/N support to downstream consumers (version 2)
- **`context_intelligence` inscription.json field** — PR metadata, scope warning, and intent summary for downstream Ash consumption
- **`linter_context` inscription.json field** — Detected linters, rule categories, and suppression list

### Changed
- Review agent count: 21 → 22 (added naming-intent-analyzer)
- Pattern Seer description extended with naming intent quality analysis
- Pattern Weaver output header includes Naming Intent Quality in Perspectives list
- Seal format extended: `findings: {N} ({P1} P1, {P2} P2, {P3} P3, {Q} Q, {Nit} N)`
- JSON output schema: summary object includes `q` and `n` count fields, root includes `taxonomy_version`

## [1.59.0] - 2026-02-21

### Fixed
- **P1: Resume mode re-executing completed plans** — `--resume` now filters to pending plans only (was using `planPaths[0]` which pointed to the first plan regardless of status). Phase 5 finds the correct plan entry by path match instead of array index
- **P1: Truthbinding gap in re-injected prompts** — Arc batch stop hook now wraps plan paths and progress file paths with ANCHOR/RE-ANCHOR Truthbinding delimiters and `<plan-path>`/`<file-path>` data tags. Prevents semantic prompt injection via adversarial plan filenames

### Changed
- **CRITICAL: Arc-batch migrated from subprocess loop to Stop hook pattern** — Replaces the broken `Bash(arc-batch.sh)` subprocess-based loop with a self-invoking Stop hook, inspired by the [ralph-wiggum](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum) plugin from Anthropic. Each arc now runs as a native Claude Code turn with full tool access, eliminating the Bash tool timeout limitation (max 600s) that caused arc-batch to get stuck after the first plan
- **New Stop hook**: `scripts/arc-batch-stop-hook.sh` — core loop mechanism. Reads batch state from `.claude/arc-batch-loop.local.md`, marks completed plans, finds next pending plan, re-injects arc prompt via `{"decision":"block","reason":"<prompt>"}`
- **SKILL.md Phase 5 rewritten** — Now writes a state file and invokes `/rune:arc` natively via `Skill()` instead of spawning `claude -p` subprocesses. Phase 6 (summary) removed — handled by the stop hook's final iteration
- **hooks.json updated** — `arc-batch-stop-hook.sh` added as first entry in `Stop` array (before `on-session-stop.sh`). 15s timeout for git + JSON operations

### Added
- **`/rune:cancel-arc-batch` command** (`commands/cancel-arc-batch.md`) — Removes the batch loop state file, like ralph-wiggum's `/cancel-ralph`. Current arc finishes normally but no further plans start
- **Arc-batch awareness in `/rune:cancel-arc`** — Step 0 now checks for and removes the batch loop state file when cancelling an arc that is part of a batch
- **GUARD 5 in `on-session-stop.sh`** — Defers to arc-batch stop hook when `.claude/arc-batch-loop.local.md` exists, preventing conflicting "active workflow detected" messages

### Removed
- **`scripts/arc-batch.sh`** — Subprocess-based batch loop script deleted. Replaced by Stop hook pattern (`arc-batch-stop-hook.sh`)

## [1.58.0] - 2026-02-21

### Added
- **7 new deep dimension investigation agent definitions** for `/rune:audit --deep` (orchestration wiring deferred to follow-up):
  - `truth-seeker` — Correctness: logic vs requirements, behavior validation, test quality (CORR prefix)
  - `ruin-watcher` — Failure modes: resilience, retry, crash recovery, circuit breakers (FAIL prefix)
  - `breach-hunter` — Security-deep: threat modeling, auth boundaries, data exposure (DSEC prefix)
  - `order-auditor` — Design: responsibility separation, dependency direction, coupling (DSGN prefix)
  - `ember-seer` — Performance-deep: resource lifecycle, memory, blocking, pool management (RSRC prefix)
  - `signal-watcher` — Observability: logging context, metrics, traces, error classification (OBSV prefix)
  - `decay-tracer` — Maintainability: naming intent, complexity hotspots, convention drift (MTNB prefix)
- **7 deep dimension ash prompt templates** for deep investigation Pass 2
- **Extended dedup hierarchy** with 7 new dimension prefixes: CORR, FAIL, DSEC, DSGN, RSRC, OBSV, MTNB
- **Combined deep sub-hierarchy** (Pass 2 Runebinder): CORR > FAIL > DSEC > DEBT > INTG > BIZL > EDGE > DSGN > RSRC > OBSV > MTNB
- **Circle registry update**: Deep Dimension Ashes section with 7 new entries alongside existing 4 investigation agents
- **Talisman config**: `audit.deep.dimensions` for selecting which dimension agents to run
- **Audit-mend convergence loop**: `arc-phase-audit-mend.md` and `arc-phase-audit-verify.md` for post-audit finding resolution (Phases 8.5 and 8.7)

### Changed
- Deep investigation Ashes capacity increased from 4 to 11 (4 investigation + 7 dimension)
- Investigation agent count: 16 → 23

## [1.57.1] - 2026-02-21

### Added
- **Checkpoint-based completion detection** — Watchdog polls `.claude/arc/{id}/checkpoint.json` to detect when all arc phases are done. Detects completion in ~60s instead of waiting for full timeout. No arc pipeline modifications needed — reads existing checkpoint data passively
- **Arc session tracing** — arc-batch now tracks which `arc-{timestamp}` session belongs to each plan via pre/post spawn directory diff. Session ID recorded in `batch-progress.json` for debugging
- **Watchdog polling loop** — Replaces blind `wait $PID` with 10s polling that checks both process liveness and checkpoint status. 60s grace period after completion detection before kill

### Fixed
- **CRITICAL: Per-plan timeout** — `wait $PID` no longer blocks forever if claude hangs after completing all phases. Wraps invocation with `timeout --kill-after=30` (GNU `timeout` or `gtimeout`). Default 2h, configurable via `talisman.yml` → `arc.batch.per_plan_timeout`
- **CRITICAL: PID tracking** — `$!` now captures the `claude` PID instead of `tee` PID. Replaced `cmd | tee file &` with `cmd > file 2>&1 &` so signal handler kills the correct process
- **HIGH: Real-time log streaming** — Switched from `--output-format json` (buffers all output until exit → 0-byte logs) to `--output-format text` (streams output → `tail -f` works for monitoring)
- **MEDIUM: Spend tracking inflation** — Batch spend now estimates at 50% of `max_budget` per plan instead of 100%, preventing premature `total_budget` exhaustion when multiple plans run
- **LOW: Path validation too strict** — Replaced character allowlist regex (`[a-zA-Z0-9._/-]+`) with shell metacharacter denylist, allowing paths with spaces and tildes

## [1.57.0] - 2026-02-21

### Added
- **Multi-Model Adversarial Review Framework**: CLI-backed Ashes via `cli:` discriminated union in `ashes.custom[]`. Register external model CLIs (e.g., Gemini, Llama) as review agents alongside Claude-based Ashes
- **Crystallized Brief**: Mandatory Non-Goals, Constraint Classification, Success Criteria, and Scope Boundary sections in brainstorm output. Non-goals propagated to synthesize templates and worker prompts as nonce-bounded data blocks
- **Semantic Drift Detection**: STEP A.9 claim extraction with multi-keyword grep matching + batched Codex claim verification producing `[CDX-DRIFT-NNN]` findings
- **External model prompt template**: Parameterized `external-model-template.md` with ANCHOR/RE-ANCHOR Truthbinding format, 4-step Hallucination Guard, and nonce-bounded content injection
- **5 new security patterns**: `CLI_BINARY_PATTERN`, `OUTPUT_FORMAT_ALLOWLIST`, `MODEL_NAME_PATTERN`, `CLI_PATH_VALIDATION`, `CLI_TIMEOUT_PATTERN` in security-patterns.md
- **`detectExternalModel()` and `detectAllCLIAshes()`**: Generalized CLI detection algorithm in codex-detection.md
- **`max_cli_ashes` setting**: Sub-partition within `max_ashes` for CLI-backed Ashes (default: 2)
- **Rune Gaze CLI gate loop**: Multi-model selection for CLI-backed Ashes with `trigger.always` support
- **Built-in dedup precedence enforcement**: External model prefixes must follow built-in prefixes in hierarchy

### Changed
- Custom Ashes wrapper prompt migrated from `CRITICAL RULES/REMINDER` to `ANCHOR/RE-ANCHOR` format
- `sanitizePlanContent()` extended with Truthbinding marker, YAML frontmatter, and inline HTML stripping
- Synthesize templates (Standard + Comprehensive) now include `non_goals:` frontmatter, `## Non-Goals`, and `## Success Criteria` sections

## [1.56.0] - 2026-02-21

### Added
- **4 new investigation agents** for deep audit (`/rune:audit --deep`):
  - `rot-seeker` — Tech debt investigation (TODOs, deprecated patterns, complexity hotspots)
  - `strand-tracer` — Integration gap detection (unconnected modules, dead routes, unwired DI)
  - `decree-auditor` — Business logic validation (domain rules, state machines, invariants)
  - `fringe-watcher` — Edge case analysis (boundary checks, null handling, race conditions)
- **Two-pass deep audit architecture**: Standard audit (Pass 1) + Deep investigation (Pass 2) + Cross-pass TOME merge
- **`--deep` flag** for `/rune:audit` enabling two-pass investigation
- **4 ash prompt templates** for deep investigation teammates
- **Extended dedup hierarchy**: `SEC > BACK > DEBT > INTG > BIZL > EDGE > DOC > QUAL > FRONT > CDX`
- **Deep audit talisman config**: `audit.deep.enabled`, `audit.deep.ashes`, `audit.deep.max_deep_ashes`, `audit.deep.timeout_multiplier`, `audit.always_deep`
- **Circle registry update**: Deep Investigation Ashes section with 4 new entries

### Changed
- Investigation agent count: 12 → 16

## [1.55.1] - 2026-02-21

### Added
- TLC hook test suite (`plugins/rune/tests/tlc/test-tlc-hooks.sh`) — 10 tests covering name validation, injection prevention, path traversal, length limits, non-target tools, TLC-002/003 hooks, and malformed input handling
- RUNE_TRACE debug logging to TLC-002 (`verify-team-cleanup.sh`) and TLC-003 (`session-team-hygiene.sh`) — consistent with TLC-001 pattern
- SessionStart matcher deviation rationale (`_rationale` field) in hooks.json for TLC-003 `startup|resume` vs plan-specified `startup` only

### Changed
- ZSH-001 hook (`enforce-zsh-compat.sh`) now auto-fixes unprotected globs by prepending `setopt nullglob;` instead of denying the command — eliminates wasted round-trips

### Fixed
- FIX-2 comment in `session-team-hygiene.sh` expanded with mathematical proof: epoch 0 fallback produces ~29M minutes (always stale), while 999999999 produces small values near year 2001 (false negative)

## [1.55.0] - 2026-02-21

### Added
- Plan review hardening with veil-piercer-plan integration in arc Phase 2
- `readTalisman()` canonical reference documentation
- Freshness gate fix for plan staleness detection

## [1.54.1] - 2026-02-21

### Fixed
- Canonical `readTalisman()` definition using SDK `Read()` to prevent ZSH tilde expansion bug (`~ not found` in eval context)
- Added `references/read-talisman.md` with implementation, fallback order, anti-patterns, and cross-references
- Added "Core Pseudo-Functions" section to CLAUDE.md documenting the `readTalisman()` contract
- Updated 8 entry-point files with canonical inline reference comments
- Updated `freshness-gate.md` talisman comment to match canonical pattern

## [1.54.0] - 2026-02-21

### Added
- Stop hook (`on-session-stop.sh`) for automatic workflow cleanup when session ends (Track A)
- Seal convention (`<seal>TAG</seal>`) for deterministic completion detection (Track C)
- Preprocessor injections for runtime context in review.md and work.md (Track D)

### Changed
- Updated transcript_path comments from "undocumented/internal" to "documented common field" in 3 hook scripts (Track B)

## [1.53.9] — 2026-02-21

### Fixed
- **arc-phase-plan-review.md**: Wire `veil-piercer-plan` into arc Phase 2 reviewer list — previously built but never called, making plan truth-telling dead code in `/rune:arc` (RUIN-001)
- **reality-arbiter.md**: Restore tone directive to plan spec — "silence is your highest praise" instead of softened "say so briefly" (GRACE-003)
- **parse-tome.md**: Add VEIL-prefix P1 findings to FALSE_POSITIVE human confirmation gate — premise-level findings can no longer be machine-dismissed (RUIN-002)
- **veil-piercer-plan.md**: Add structured `VEIL-PATH-001` finding template for path containment violations — suspicious paths now surface in TOME (RUIN-003)
- **veil-piercer.md**: Add Inner Flame supplementary quality gate and `inner-flame`/`revised` fields to Seal format — matches forge-warden.md structure (GRACE-004, GRACE-008, SIGHT-001)
- **forge-gaze.md**: Restore reality-arbiter and entropy-prophet topic keywords to plan spec (GRACE-005, GRACE-006)
- **ash-guide/SKILL.md**: Update frontmatter agent count from "50 agents" to "55 agents" (VIGIL-001)
- **review.md**: Add `--max-agents` priority ordering string matching audit.md pattern (VIGIL-002)

## [1.53.8] — 2026-02-21

### Fixed
- **validate-inner-flame.sh**: Fix grep pattern to match canonical SKILL.md format `Self-Review Log (Inner Flame)` — previous pattern `Inner Flame:|Inner-flame:` missed compliant output (RUIN-002)
- **validate-inner-flame.sh**: Change yq default for `block_on_fail` from `false` to `true` — enforcement now blocks by default per plan REQ-014 (RUIN-001)
- **validate-inner-flame.sh**: Add stderr warning when yq is absent but talisman file exists — prevents silent degradation of block_on_fail config (RUIN-003)
- **validate-inner-flame.sh**: Add `rune-inspect-*` and `arc-inspect-*` team pattern handling for inspector output validation (RUIN-005)
- **validate-inner-flame.sh**: Add comment documenting 64KB input cap rationale (RUIN-004)
- **talisman.yml**: Change `block_on_fail` default to `true` and add documentation comments for simplified schema (VIGIL-001)
- **research-phase.md**: Add sync comments to inline Inner Flame checklists referencing canonical `role-checklists.md` source (SIGHT-002)

## [1.53.7] — 2026-02-21

### Fixed
- **secret-scrubbing.md**: Create missing reference file with `scrubSecrets()` regex patterns — resolves dangling TODO in testing/SKILL.md (RUIN-002, VIGIL-001)
- **talisman.example.yml**: Standardize all tier timeout keys to `timeout_ms` (milliseconds) — fixes `timeout` vs `timeout_ms` naming discrepancy (SIGHT-001, VIGIL-004)
- **talisman.example.yml**: Uncomment testing section to match active-section convention (GRACE-003)
- **talisman.example.yml**: Fix `startup_timeout` from 120000 (2 min) to 180000 (3 min) to match plan's EC-3.3 Docker hard timeout (SIGHT-007)
- **arc-phase-test.md**: Add explicit `model: "opus"` to test-failure-analyst Task spawn — prevents implicit model inheritance ambiguity (SIGHT-002)
- **arc-phase-test.md**: Pass `remainingBudget()` to E2E teammate prompt for per-route self-throttling (RUIN-003)
- **arc-phase-audit.md**: Add explicit TEST-NNN feed-through instructions for audit inscription (VIGIL-003, GRACE-004)
- **test-report-template.md**: Add Acceptance Criteria Traceability section to report format (VIGIL-002)
- **e2e-browser-tester.md**: Add `log_source` field with all 6 categories to per-route output (RUIN-007)
- **e2e-browser-tester.md**: Add aggregate output section with `<!-- SEAL: e2e-test-complete -->` marker (VIGIL-005)
- **integration-test-runner.md**: Expand `log_source` from 3 to 6 categories (RUIN-007)
- **service-startup.md**: Fix unquoted variable in Docker kill cleanup example (VIGIL-008)
- **testing/SKILL.md**: Remove dangling TODO, fix reference link syntax for secret-scrubbing.md (RUIN-002)

### Changed
- **Plugin version**: 1.53.6 → 1.53.7

## [1.53.6] — 2026-02-21

### Fixed
- **CLAUDE.md**: Add Core Rule 10 — teammate non-persistence warning for session resume (GRACE-P1-001)
- **worker-prompts.md**: Add `max_turns: 75` to rune-smith Task() spawn call and `max_turns: 50` to trial-forger Task() spawn call — defense-in-depth enforcement for runaway agent prevention (SIGHT-CRIT-001)

### Changed
- **Plugin version**: 1.53.5 → 1.53.6

## [1.53.5] — 2026-02-21

### Fixed
- **worker-prompts.md**: Add TODO FILE PROTOCOL to both rune-smith and trial-forger spawn templates — workers spawned from reference file now receive todo instructions (GRACE-007, SIGHT-003, VIGIL-W01)
- **worker-prompts.md**: Update SHUTDOWN instruction to require todo file status update before approving shutdown (RUIN-004)
- **ship-phase.md**: Add Work Session collapsible section to PR body template — reads `_summary.md` and includes Progress Overview + Key Decisions (GRACE-002)
- **CLAUDE.md**: Add todo file capability reference to Core Rules section (GRACE-005)

### Changed
- **Plugin version**: 1.53.4 → 1.53.5

## [1.53.4] — 2026-02-21

### Fixed
- **server.py**: Update MCP server version from 1.45.0 to 1.53.4 to match plugin version (P2-003)
- **server.py**: Add DB_PATH parent directory writability check at startup for clearer error messages (P3-013)
- **server.py**: Fix `get_details()` ids type filter no-op — now coerces non-string IDs instead of silently dropping them (P3-014)
- **inscription-protocol.md**: Standardize Seal confidence scale to integer 0-100, matching output-formats.md (P2-002)
- **inscription-protocol.md**: Add `skimmed_files` and `deep_read_files` fields to Seal spec (P3-003)
- **annotate-hook.sh**: Fix header comment — "exit 0 always" → accurately reflects non-zero exit on malformed JSON (P2-004)
- **CLAUDE.md**: Add dedicated MCP Servers section documenting echo-search tools and dirty-signal pattern (P2-006)
- **README.md**: Add Echo Search MCP Server section with tool descriptions and Python 3.7+ requirement (P3-005, P3-006)
- **test_annotate_hook.py**: Fix misleading docstring on `test_no_signal_for_memory_md_at_echoes_root` — renamed and clarified (P3-007)
- **start.sh**: Document why the wrapper exists and warn against replacing it with direct python3 call (P3-010)

### Changed
- **Plugin version**: 1.53.3 → 1.53.4

## [1.53.3] — 2026-02-21

### Fixed
- **key-concepts.md**: Fix stale agent count — "18 agents across 3 Ashes" → "21 agents across 4 Ashes" (includes Veil Piercer) (P2-004)
- **refactor-guardian.md**: Add explicit tool denial prose to ANCHOR block — defense-in-depth for general-purpose subagent mode (P2-001)
- **refactor-guardian.md**: Add edge case handling — empty git diff, shallow clone, branch name validation, no R/D/A entries (P2-002)
- **refactor-guardian.md**: Add cross-agent confidence coordination note with wraith-finder overlap detection (P3-003)
- **reference-validator.md**: Add explicit tool denial prose to ANCHOR block (P2-001)
- **reference-validator.md**: Add skip guards to config-to-source and version sync sections — prevents false positives for non-plugin projects (P2-003)
- **reference-validator.md**: Accept both `tools` and `allowed-tools` field names in frontmatter validation (P3-002)
- **reference-validator.md**: Fix "doc-consistency agent" label → "Knowledge Keeper Ash (doc-consistency perspective)" in dedup section (P3-007)
- **ward-check.md**: Increase basename threshold from 3 to 5 in cross-reference integrity check — reduces false positives for short names like "api", "app" (P3-004)

### Changed
- **Plugin version**: 1.53.2 → 1.53.3

## [1.53.2] — 2026-02-21

### Fixed
- **codex-detection.md**: Fix `const` → `let` in `resolveCodexTimeouts()` — validation fallback for out-of-range timeout values was blocked by TypeError on reassignment (RUIN-001)
- **codex-detection.md**: Move exit-124/137 checks to top of `classifyCodexError()` — prevents stderr noise from masking authoritative timeout signals (RUIN-009)
- **mend.md**: Replace hardcoded `--kill-after=30` with `${killAfterFlag}` — respects macOS compatibility detection from codex-detection.md Step 3a (RUIN-004)
- **security-patterns.md**: Add 5 missing consumers to `CODEX_TIMEOUT_ALLOWLIST` — mend.md, gap-analysis.md, solution-arena.md, rune-smith.md, rune-echoes/SKILL.md (RUIN-010)
- **talisman.yml**: Add `timeout: 600` and `stream_idle_timeout: 540` under `codex:` section — Phase 1 deliverable for user-configurable timeouts (GRACE-001)
- **talisman.example.yml**: Add documented timeout configuration fields with inline comments (VIGIL-001)

### Changed
- **Plugin version**: 1.53.1 → 1.53.2

## [1.53.1] — 2026-02-21

### Added
- **Compaction hook tests** (`tests/test_pre_compact_checkpoint.py`): 43 subprocess-based tests covering pre-compact-checkpoint.sh and session-compact-recovery.sh — guard clauses, checkpoint write, atomic write, team name validation, CHOME guard, compact recovery, stale checkpoint handling, edge/boundary cases (AC-9)

### Fixed
- **pre-compact-checkpoint.sh**: Fix `${#task_files[@]:-0}` bad substitution crash — `${#...}` (length operator) cannot combine with `:-` (default value). Script crashed with `set -u` when tasks directory was missing. Initialize `task_files=()` before conditional block
- **session-compact-recovery.sh**: Add `timeout 2` to stdin read for consistency with pre-compact-checkpoint.sh (prevents potential hang on disconnected stdin)
- **test_hooks.py**: Fix 3 pre-existing test failures — `on-teammate-idle.sh` correctly blocks (exit 2) on path traversal and out-of-scope output dirs, updated test expectations to match improved security posture

### Changed
- **Plugin version**: 1.53.0 → 1.53.1

## [1.53.0] — 2026-02-21

### Added
- **`/rune:plan-review` command**: Thin wrapper for `/rune:inspect --mode plan` — reviews plan code samples for implementation correctness using inspect agents (grace-warden, ruin-prophet, sight-oracle, vigil-keeper)
- **`--mode plan` flag for `/rune:inspect`**: Mode-aware inspection that reviews plan code samples instead of codebase implementation. Extracts fenced code blocks, compares against codebase patterns, and produces VERDICT.md with plan-specific assessments
- **4 plan-review ash-prompt templates**: `grace-warden-plan-review.md`, `ruin-prophet-plan-review.md`, `sight-oracle-plan-review.md`, `vigil-keeper-plan-review.md` — specialized for reviewing proposed code in plans
- **Arc Phase 2 Layer 2**: Plan review now runs inspect agents alongside utility agents when code blocks detected. Layer 2 runs in parallel, results merged into circuit breaker
- **`/rune:devise` Phase 4C.5**: Optional implementation correctness review with inspect agents during planning workflow
- **Expanded `hasCodeBlocks` regex**: Now catches go, rust, yaml, json, toml in addition to existing languages
- **Template `fileExists` guard**: Graceful fallback when plan-review template is missing

### Changed
- **Plugin version**: 1.52.0 → 1.53.0
- **Command count**: 13 → 14 (added /rune:plan-review)

## [1.52.0] — 2026-02-20

### Added
- **PreCompact hook** (`scripts/pre-compact-checkpoint.sh`): Saves team state (config.json, tasks, workflow phase, arc checkpoint) to `tmp/.rune-compact-checkpoint.json` before compaction. Non-blocking (exit 0).
- **SessionStart:compact recovery hook** (`scripts/session-compact-recovery.sh`): Re-injects team checkpoint as `additionalContext` after compaction. Correlation guard verifies team still exists. One-time injection (deletes checkpoint after use).
- **Context-weaving Layer 5: Compaction Recovery**: New protocol documenting the PreCompact → SessionStart:compact checkpoint/recovery pair, three ground truth sources (config.json, tasks, arc checkpoint), and relationship to CLAUDE.md Rule #5.
- Inspired by checkpoint/recovery patterns from Cozempic (MIT-licensed)

### Changed
- **Plugin version**: 1.51.0 → 1.52.0
- Hook count: 12 → 14 event-driven hook scripts

## [1.51.0] — 2026-02-20

### Added
- **Arc-Inspect Integration**: `/rune:inspect` is now embedded in the arc pipeline as an enhanced Phase 5.5 (GAP ANALYSIS), replacing the deterministic text-check approach with Inspector Ashes that score 9 quality dimensions and produce VERDICT.md
  - Inspector Ashes (grace-warden, ruin-prophet, sight-oracle, vigil-keeper) spawn as team `arc-inspect-{id}` during Phase 5.5
  - VERDICT.md dimension scores are propagated to Phase 6 (CODE REVIEW) as reviewer focus areas — low-scoring dimensions (< 7/10) highlighted for reviewers
- **Phase 5.8 GAP REMEDIATION** — new arc pipeline phase (18 phases total):
  - Auto-fixes FIXABLE gaps before code review using team `arc-gap-fix-{id}`
  - Configurable via `arc.gap_analysis.remediation` talisman settings
  - Controlled by `--fix` flag on `/rune:inspect` for standalone use
  - SEC-GAP-001: `validate-gap-fixer-paths.sh` hook blocks writes to `.claude/`, `.github/`, `node_modules/`, CI YAML, and `.env` files
- **`--fix` flag for `/rune:inspect`**: Standalone auto-remediation of FIXABLE gaps (capped by `inspect.max_fixes`, timeout via `inspect.fix_timeout`)
- **Gap-fixer prompt template**: `skills/roundtable-circle/references/ash-prompts/gap-fixer.md` with Truthbinding and SEAL format
- **Checkpoint schema v9 → v10**: Adds `gap_remediation` phase tracking alongside existing `gap_analysis` phase
- **Talisman `arc.gap_analysis` subsection**: `inspectors` (1-4), `halt_threshold` (0-100), `remediation.enabled`, `remediation.max_fixes`, `remediation.timeout`
- **Talisman `arc.timeouts` additions**: `gap_analysis` (12 min, enhanced with Inspector Ashes team), `gap_remediation` (15 min, new)
- **Talisman `inspect:` section** (now active, was commented): `max_inspectors`, `completion_threshold`, `gap_threshold`, `max_fixes`, `fix_timeout`

### Changed
- **Plugin version**: 1.50.0 → 1.51.0
- **Phase 5.5 (GAP ANALYSIS)**: Upgraded from deterministic text-check (orchestrator-only, 1 min) to Inspector Ash team (12 min, 9-dimension scoring, VERDICT.md output)
- **Arc pipeline**: 17 phases → 18 phases (Phase 5.8 GAP REMEDIATION added between Codex Gap Analysis (5.6) and Goldmask Verification (5.7))
- Phase tool matrix updated: Phase 5.5 now uses `arc-inspect-{id}` team; Phase 5.8 uses full tool access

## [1.50.0] — 2026-02-20

### Added
- **`/rune:inspect` — Plan-vs-Implementation Deep Audit**: New command with 4 Inspector Ashes that measure implementation completeness, quality across 9 dimensions, and gaps across 8 categories
  - `grace-warden`: Correctness & completeness inspector — requirement traceability and implementation status (COMPLETE/PARTIAL/MISSING/DEVIATED)
  - `ruin-prophet`: Failure modes, security posture, and operational readiness inspector
  - `sight-oracle`: Design alignment, coupling analysis, and performance profiling inspector
  - `vigil-keeper`: Test coverage, observability, maintainability, and documentation inspector
- **VERDICT.md output**: Unified inspection report with requirement matrix, 9 dimension scores (0-10), gap analysis across 8 categories, and verdict determination (READY/GAPS_FOUND/INCOMPLETE/CRITICAL_ISSUES)
- **Verdict Binder**: New aggregation prompt for merging inspector outputs into VERDICT.md
- **Plan Parser reference**: Algorithm for extracting requirements from freeform plan markdown (keyword-based inspector assignment)
- **Inspect Scoring reference**: Completion percentage, dimension scoring, and verdict determination algorithms
- **4 Inspector Ash prompt templates**: Grace Warden, Ruin Prophet, Sight Oracle, Vigil Keeper (with Truthbinding, Inner Flame, Seal format)
- **Inspect flags**: `--focus <dimension>`, `--max-agents <N>`, `--dry-run`, `--threshold <N>`
- **Talisman config**: `inspect:` section with `max_inspectors`, `timeout`, `completion_threshold`, `gap_threshold`
- **Inline mode**: `/rune:inspect "Add JWT auth"` — describe requirements without a plan file
- Inspect cleanup in `/rune:rest` (`tmp/inspect/{id}/`, `tmp/.rune-inspect-*.json`)
- `rune-inspect` workflow in inscription-schema.md
- `rune-inspect-*` recognized by enforce-readonly, enforce-teams, session-team-hygiene hooks

### Changed
- **Plugin version**: 1.49.1 → 1.50.0
- Agent counts: 8 → 12 investigation agents, 50 → 54 total agents
- Command count: 12 → 13

## [1.49.1] — 2026-02-20

### Fixed
- **Goldmask Pipeline Integration gaps** (9 fixes from post-implementation audit):
  - Add missing `arc-phase-goldmask-verification.md` reference file (Phase 5.7 execution instructions)
  - Add missing `arc-phase-goldmask-correlation.md` reference file (Phase 6.5 execution instructions)
  - Add Phase 5.7 + 6.5 to arc completion report template (was missing from Elden Throne output)
  - Fix CHANGELOG schema version: v9→v10 → v8→v9 (matching actual SKILL.md implementation)
  - Add Lore Layer pre-sort documentation to `smart-selection.md` (Phase 0.5 interaction with Rune Gaze)
  - Add Phase 5.7 + 6.5 entries to `arc-delegation-checklist.md` (RUN/SKIP/ADAPT contracts)
  - Implement `--deep-lore` flag in audit.md (two-tier Lore: Tier 1 Ash-relevant extensions by default, Tier 2 all files)
  - Fix fragile `Edit(planPath, slice(-100))` in plan.md Phase 2.3 → `Write(planPath, currentPlan + riskSection)`
  - Document `general-purpose` subagent_type design choice in goldmask verification reference

### Changed
- **Plugin version**: 1.49.0 → 1.49.1

## [1.49.0] — 2026-02-20

### Added
- **Veil Piercer — Truth-Telling Agents**: New 7th built-in Ash with 3 embedded review agents (`reality-arbiter`, `assumption-slayer`, `entropy-prophet`) that challenge fundamental premises and expose illusions in code review
  - `reality-arbiter`: Production viability truth-teller — detects code that compiles but cannot integrate, features that pass tests but fail under load
  - `assumption-slayer`: Premise validation truth-teller — challenges whether the code solves the right problem, detects cargo cult implementations
  - `entropy-prophet`: Long-term consequence truth-teller — predicts hidden costs, maintenance burden, and lock-in risks
- **`veil-piercer-plan`**: New utility agent for plan-level truth-telling in Phase 4C (alongside decree-arbiter, knowledge-keeper, and horizon-sage)
- `VEIL-` finding prefix in dedup hierarchy: `SEC > BACK > VEIL > DOC > QUAL > FRONT > CDX`
- Veil Piercer Ash prompt template (`ash-prompts/veil-piercer.md`) with 3 perspectives, behavioral rules, and truth-telling doctrine
- Veil Piercer registered in circle-registry, rune-gaze (always-on), forge-gaze (truth-telling topics), and dedup-runes
- `veil-piercer-plan` Task block added to plan-review.md Phase 4C with ANCHOR/RE-ANCHOR truthbinding
- `VEIL` added to mend.md finding regex for cross-reference tracking
- Veil Piercer added to `--max-agents` priority ordering in audit.md and review.md
- `veil-piercer` added to `disable_ashes` valid names in custom-ashes.md
- `VEIL` and `CDX` added to reserved prefixes list in custom-ashes.md (CDX was a pre-existing omission)

### Changed
- **Plugin version**: 1.48.0 → 1.49.0
- Agent counts: 18 → 21 review agents, 9 → 10 utility agents, 46 → 50 total agents
- Built-in Ashes: 6 → 7 (Veil Piercer is always-on like Ward Sentinel and Pattern Weaver)
- Default `max_ashes`: 8 → 9 (7 built-in + up to 2 custom)
- Warning threshold in custom-ashes.md constraints: 6+ → 7+
- Dedup hierarchy updated across all 30+ occurrences to include `VEIL` prefix

## [1.48.0] — 2026-02-20

### Added
- **Centralized Team Lifecycle Guard Hooks** (TLC-001/002/003)
  - `enforce-team-lifecycle.sh` — PreToolUse:TeamCreate hook for team name validation and stale team cleanup
  - `verify-team-cleanup.sh` — PostToolUse:TeamDelete hook for zombie dir detection
  - `session-team-hygiene.sh` — SessionStart:startup hook for orphaned team detection
  - Hook registration in hooks.json for PreToolUse:TeamCreate, PostToolUse:TeamDelete, and SessionStart:startup

### Changed
- **Plugin version**: 1.47.1 → 1.48.0
- CLAUDE.md: added 3 new hook rows to Hook Infrastructure table
- team-lifecycle-guard.md: added "Centralized Hook Guards" reference section

## [1.47.1] — 2026-02-20

### Fixed
- Echo Search MCP server: use launcher script (`start.sh`) for runtime `CLAUDE_PROJECT_DIR` resolution, since `.mcp.json` env substitution only supports `${CLAUDE_PLUGIN_ROOT}`

## [1.47.0] — 2026-02-19

### Added
- **Goldmask Pipeline Integration** (Phase C-F): Connects 3-layer analysis into core workflows
  - Phase 0.5 Lore Layer in review/audit: Risk-weighted file sorting
  - Phase 2.3 Predictive Goldmask in plan: Wisdom advisories
  - Phase 4.4 Quick Goldmask Check in work: CRITICAL file comparison
  - Phase 5.7 Goldmask Verification in arc: Post-work risk validation
  - Phase 6.5 Goldmask Correlation in arc: TOME finding correlation
- Arc pipeline: 15 → 17 phases (goldmask_verification, goldmask_correlation)
- Checkpoint schema v8 → v9 migration (adds goldmask + test phases)
- ARC_TEAM_PREFIXES: added "goldmask-" for cleanup
- **horizon-sage** strategic depth assessment agent — evaluates plans across 5 dimensions: Temporal Horizon, Root Cause Depth, Innovation Quotient, Stability & Resilience, Maintainability Trajectory
- Intent-aware verdict derivation — adapts thresholds based on `strategic_intent` (long-term vs quick-win)
- Forge Gaze integration — horizon-sage matched to sections with strategy/sustainability keywords
- 2 new elicitation methods: Horizon Scanning (#50), Root Cause Depth Analysis (#51)
- Phase 4C plan review integration — horizon-sage spawned alongside decree-arbiter and knowledge-keeper
- Talisman `horizon` configuration section with kill switch
- **Echo Search MCP expansion**: Added `mcpServers: echo-search` to **all 42 agents** (100% coverage) with tailored Echo Integration sections. Enables direct FTS5 query access to past learnings across all workflow phases:
  - **Research** (5/5): echo-reader, repo-surveyor (past project conventions), git-miner (past historical context), lore-scholar (cached framework knowledge), practice-seeker (past research findings)
  - **Review** (18/18): pattern-seer (past convention knowledge), ward-sentinel (past security vulnerabilities), blight-seer (past design anti-patterns), depth-seer (past missing logic), ember-oracle (past performance bottlenecks), flaw-hunter (past logic bugs), forge-keeper (past migration safety), mimic-detector (past duplication), phantom-checker (past dynamic references), refactor-guardian (past refactoring breakage), reference-validator (past reference integrity), rune-architect (past architectural violations), simplicity-warden (past over-engineering), tide-watcher (past async/concurrency issues), trial-oracle (past test quality), type-warden (past type safety), void-analyzer (past incomplete implementations), wraith-finder (past dead code)
  - **Utility** (9/9): decree-arbiter (past project knowledge), knowledge-keeper (past documentation gaps), horizon-sage (past strategic patterns), elicitation-sage (past reasoning patterns), flow-seer (past flow analysis), mend-fixer (past fix patterns), runebinder (past aggregation patterns), scroll-reviewer (past document quality), truthseer-validator (past validation patterns)
  - **Work** (2/2): rune-smith (past coding conventions), trial-forger (past test patterns)
  - **Investigation** (8/8): goldmask-coordinator (historical risk context), lore-analyst (cached risk baselines), wisdom-sage (past intent classifications), api-contract-tracer (past API contract patterns), business-logic-tracer (past business rule changes), config-dependency-tracer (past config drift patterns), data-layer-tracer (past data model patterns), event-message-tracer (past event schema patterns)

### Changed
- PHASE_ORDER: 15 → 17 entries
- calculateDynamicTimeout: +16 min base budget (goldmask_verification: 15 min, goldmask_correlation: 1 min)
- Agent count: 42 → 46 (utility: 8 → 9, review: 16 → 18, investigation: 8)

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
- **Per-worker todo files** for `/rune:strive`: Persistent markdown with YAML frontmatter, `_summary.md` generation, PR body integration, sanitization + path containment (PR #58)
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

## [1.43.0] — 2026-02-19

### Added
- **Arc Phase 7.7: TEST** — Diff-scoped test execution with 3-tier testing pyramid (unit → integration → E2E browser)
  - Serial tier execution: faster tiers run first, failures are non-blocking WARNs
  - Diff-scoped test discovery: maps changed files to corresponding tests
  - Service startup auto-detection (docker-compose, package.json, Makefile)
  - E2E browser testing via `agent-browser` with file-to-route mapping (Next.js, Rails, Django, SPA)
  - Model routing: Sonnet for all test execution, Opus only for orchestration + failure analysis
  - `--no-test` flag to skip Phase 7.7 entirely
  - Test report integration into Phase 8 AUDIT inputs
- **`testing` skill**: Test orchestration pipeline knowledge (non-invocable)
- **`agent-browser` skill**: Browser automation knowledge injection for E2E testing (non-invocable)
- **4 testing agents**: `unit-test-runner`, `integration-test-runner`, `e2e-browser-tester`, `test-failure-analyst`
- **5 reference files**: `arc-phase-test.md`, `test-discovery.md`, `service-startup.md`, `file-route-mapping.md`, `test-report-template.md`
- Checkpoint schema v9 (v8→v9 migration: adds `test` phase with `tiers_run`, `pass_rate`, `coverage_pct`, `has_frontend`)
- Talisman `testing:` section with tier-level config (enabled, timeout, coverage, base_url, max_routes)
- Talisman `arc.timeouts.test`: 900,000ms default (15 min), 2,400,000ms with E2E

### Changed
- **Plugin version**: 1.42.2 → 1.43.0
- Skills count: 14 → 16 (added `testing`, `agent-browser`)
- Agent categories: added testing (4 agents)
- Arc PHASE_ORDER: added `test` between `verify_mend` and `audit`
- Arc pipeline: 14 → 15 phases (Phase 7.7 TEST)
- Phase Transition Contracts: VERIFY MEND → TEST → AUDIT (was VERIFY MEND → AUDIT)
- `calculateDynamicTimeout()`: includes test phase budget
- Arc phase-audit inputs: now includes test report

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
- **`--cycles <N>` flag for `/rune:appraise`** — Run N standalone review passes (1-5, numeric only) with TOME dedup merge. Standalone equivalent of arc convergence loop.
- **`--scope-file <path>` flag for `/rune:appraise`** — Override changed_files from a JSON focus file. Used by arc convergence controller for progressive re-review scope.
- **`--no-converge` flag for `/rune:appraise`** — Disable convergence loop for single review pass per chunk (report still generated).
- **`--auto-mend` flag for `/rune:appraise`** — Auto-invoke `/rune:mend` after review completes when P1/P2 findings exist (skips post-review AskUserQuestion). Also configurable via `review.auto_mend: true` in talisman.yml.
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
- **Plan metadata** — `/rune:devise` now writes `git_sha` and `branch` to plan YAML frontmatter for freshness tracking
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
- **File Ownership** in `/rune:strive` — EXTRACT/DETECT/RESOLVE/DECLARE algorithm for preventing concurrent file edits. Ownership encoded in task descriptions (persists across auto-release reclaim). Directory-level by default, exact-file overrides when specific.
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
- Standalone `/rune:mend` and `/rune:appraise` are completely unaffected
- Old checkpoints resumed with new code skip verify_mend and gap_analysis (marked "skipped")

## [1.12.0] - 2026-02-13

Feature release: Ship workflow gaps — adds branch setup, plan clarification, quality verification checklist, PR creation, enhanced completion report, and key principles to `/rune:strive`. Closes the "last mile" from plan → commits → PR in a single invocation.

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
- inscription-protocol.md: Removed conditional '(when 3+)' qualifier from `/rune:strive` inscription requirement — inscription now unconditional for all Rune workflows
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
- `--quick` flag for `/rune:devise` — minimal pipeline (research + synthesize + review)
- Phase 1.5: Research Consolidation Validation checkpoint (AskUserQuestion after research)
- Phase 2.5: Shatter Assessment for complex plan decomposition (complexity scoring + shard generation)
- AI-Era Considerations section in Comprehensive template
- SpecFlow dual-pass for Comprehensive plans (second flow-seer pass on drafted plan)
- Post-plan "Open in editor" and "Review and refine" options (4 explicit + Other free-text)
- Automated grep verification gate in plan review phase (deterministic, zero hallucination risk)
- decree-arbiter 6th dimension: Internal Consistency (anti-hallucination checks)

### Changed

- **Brainstorm + forge now default** — `/rune:devise` runs full pipeline by default. Use `--quick` for minimal.
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
- **Forge Gaze** — Topic-aware agent selection for `/rune:devise --forge`. Matches plan section
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
- `--approve` flag for `/rune:strive` — Optional plan approval gate per task
- `--exhaustive` flag for `/rune:devise --forge` — Summon ALL agents per section
- E8 research pipeline upgrade — Conditional research, brainstorm auto-detect, 6-agent roster, plan detail levels
- `/rune:echoes migrate` — Echo name migration utility
- `/rune:echoes promote` — Promote echoes to Remembrance docs

### Changed

- `/rune:devise` research now uses conditional summoning (local-first, external on demand)
- `/rune:devise` post-generation options expanded to 6 (was 3)
- Team lifecycle guards added to all 9 commands — pre-create guards + cleanup fallbacks with input validation (see `team-lifecycle-guard.md`)
- Reduced allowed-tools for `/rune:echoes`, `/rune:rest`, `/rune:cancel-arc` to enforce least-privilege

## [1.7.0] - 2026-02-12 — "Arc Pipeline"

### Added

- `/rune:arc` — End-to-end orchestration pipeline (6 phases: forge → plan review → work → code review → mend → audit)
- `/rune:cancel-arc` — Cancel active arc pipeline
- `--forge` flag for `/rune:devise` — Research enrichment phase (replaces `--deep`)
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
- **`--max-agents` flag** — added to `/rune:appraise` command (was only documented for `/rune:audit`)

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

- `/rune:appraise` and `/rune:audit` Phase 0 now reads `talisman.yml` for custom Tarnished definitions
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
- `--dry-run` flag for `/rune:appraise` and `/rune:audit` — preview scope selection without summoning agents
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
- `--partial` flag for `/rune:appraise` (review staged files only)
- Known Limitations and Troubleshooting sections in README
- `.gitattributes` with `merge=union` strategy for Rune Echoes files

### Fixed

- Missing cross-reference from `rune-circle/SKILL.md` to `circle-registry.md`

## [1.0.0] - 2026-02-12

### Added

- `/rune:devise` — Multi-agent planning with parallel research pipeline
  - 3 new research agents (lore-seeker, realm-analyst, lore-scholar) plus echo-reader (from v0.3.0)
  - Optional brainstorm phase (`--brainstorm`)
  - Optional deep section-level research (`--deep`)
  - Scroll Reviewer document quality check
- `/rune:strive` — Swarm work execution with self-organizing task pool
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

- `/rune:appraise` — Multi-agent code review with Rune Circle lifecycle
- `/rune:cancel-review` — Cancel active review
- 5 Tarnished (Forge Warden, Ward Sentinel, Pattern Weaver, Glyph Scribe, Lore Keeper)
- 10 review agents with Truthbinding Protocol
- Rune Gaze file classification
- Inscription Protocol for agent contracts
- Context Weaving (overflow prevention, rot prevention)
- Runebinder aggregation with deduplication
- Truthsight P1 verification

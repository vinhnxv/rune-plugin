# Rune

Multi-agent engineering orchestration for [Claude Code](https://claude.ai/claude-code). Plan, work, review, and audit using Agent Teams.

Each Ash teammate gets its own 200k context window, eliminating single-context bottlenecks.

## Claude Code Install

```bash
/plugin marketplace add https://github.com/vinhnxv/rune-plugin
/plugin install rune
```

Restart Claude Code after installation to load the plugin.

### Local Development

```bash
claude --plugin-dir /path/to/rune-plugin
```

> [!WARNING]
> **Rune is a token-intensive multi-agent system.** Each workflow summons multiple agents with their own 200k context windows, consuming tokens rapidly. A single `/rune:arc` or `/rune:audit` run can burn through a significant portion of your weekly usage limit.
>
> **We recommend Claude Max ($200/month) or higher.** If you are on a lower-tier subscription, a single Rune session could exhaust your entire week's usage allowance. Use `--dry-run` to preview scope before committing to a full run.

## Quick Start

```bash
# End-to-end pipeline: freshness check → forge → plan review → refinement → verification → semantic verification → task decomposition → work → gap analysis → codex gap analysis → gap remediation → goldmask verification → code review → goldmask correlation → mend → verify mend → test → test coverage critique → pre-ship validation → release quality check → ship → merge
/rune:arc plans/my-plan.md
/rune:arc plans/my-plan.md --no-forge             # Skip research enrichment
/rune:arc plans/my-plan.md --approve              # Require human approval per task
/rune:arc plans/my-plan.md --skip-freshness       # Bypass plan freshness check
/rune:arc plans/my-plan.md --resume               # Resume from checkpoint
/rune:arc plans/my-plan.md --no-pr                # Skip PR creation (Phase 9)
/rune:arc plans/my-plan.md --no-merge             # Skip auto-merge (Phase 9.5)
/rune:arc plans/my-plan.md --draft                # Create PR as draft

# Plan a feature (brainstorm + research + forge + review by default)
/rune:devise                     # Full pipeline
/rune:devise --quick             # Quick: research + synthesize + review only

# Deepen an existing plan with Forge Gaze enrichment
/rune:forge plans/my-plan.md     # Deepen specific plan
/rune:forge                      # Auto-detect recent plan

# Execute a plan with swarm workers
/rune:strive plans/feat-user-auth-plan.md
/rune:strive plans/my-plan.md --approve  # Require human approval per task

# Run a multi-agent code review (changed files only)
/rune:appraise

# Resolve findings from a review TOME
/rune:mend tmp/reviews/abc123/TOME.md

# Run a full codebase audit (all files)
/rune:audit
/rune:audit --focus security    # Security-only audit
/rune:audit --max-agents 3      # Limit to 3 Ashes

# Incremental stateful audit (v1.84.0+)
/rune:audit --incremental               # Prioritized batch audit with persistent state
/rune:audit --incremental --status       # Coverage dashboard (no audit performed)
/rune:audit --incremental --resume       # Resume interrupted batch
/rune:audit --incremental --tier file    # File-level only
/rune:audit --incremental --tier workflow # Workflow-level only
/rune:audit --incremental --tier api     # API endpoint-level only
/rune:audit --incremental --reset        # Clear state, start fresh
/rune:audit --incremental --deep         # Incremental batch + deep investigation

# Preview scope without summoning agents
/rune:appraise --dry-run
/rune:audit --dry-run

# Interactive structured reasoning (Tree of Thoughts, Pre-mortem, Red Team, 5 Whys)
/rune:elicit
/rune:elicit "Which auth approach is best for this API?"

# Batch arc execution (multiple plans, sequential)
/rune:arc-batch plans/*.md              # Process all matching plans
/rune:arc-batch batch-queue.txt         # Read plans from queue file
/rune:arc-batch plans/*.md --dry-run    # Preview queue without running
/rune:arc-batch plans/*.md --no-merge   # PRs created but not merged
/rune:arc-batch --resume                # Resume interrupted batch

# GitHub Issues-driven batch arc execution (issues → plans → arc → PRs → close)
/rune:arc-issues --label "rune:ready"                   # Process all issues with label (FIFO)
/rune:arc-issues --label "rune:ready" --all             # Page through ALL matching issues
/rune:arc-issues --label "rune:ready" --dry-run         # Preview issues without running
/rune:arc-issues --label "rune:ready" --all --page-size 5  # Custom page size (default 10)
/rune:arc-issues issues-queue.txt                       # File-based queue (URLs, #N, bare numbers)
/rune:arc-issues 42 55 78                               # Inline issue numbers
/rune:arc-issues --resume                               # Resume from batch-progress.json
/rune:arc-issues --cleanup-labels                       # Remove orphaned rune:in-progress labels

# Inspect plan vs implementation (deep audit)
/rune:inspect plans/my-plan.md          # Inspect a plan file
/rune:inspect "Add JWT auth with rate limiting"  # Inspect inline description
/rune:inspect plans/my-plan.md --dry-run         # Preview scope
/rune:inspect plans/my-plan.md --focus security  # Focus on security dimension
/rune:inspect plans/my-plan.md --fix             # Auto-fix FIXABLE gaps
/rune:inspect plans/my-plan.md --mode plan       # Review plan code samples only

# Review plan code samples for correctness
/rune:plan-review plans/my-plan.md               # Thin wrapper for /rune:inspect --mode plan

# Cancel active workflows
/rune:cancel-review
/rune:cancel-audit
/rune:cancel-arc
/rune:cancel-arc-issues    # Cancel arc-issues batch and optionally cleanup orphaned labels

# Clean up tmp/ artifacts from completed workflows
/rune:rest
/rune:rest --dry-run          # Preview what would be removed
/rune:rest --heal             # Recover orphaned teams from crashed workflows

# Manage agent memory
/rune:echoes show     # View memory state
/rune:echoes init     # Initialize memory for this project
/rune:echoes prune    # Prune stale entries
/rune:echoes promote  # Promote echoes to Remembrance docs
/rune:echoes migrate  # Migrate echo names after upgrade
```

## Arc Mode (End-to-End Pipeline)

When you run `/rune:arc`, Rune chains 23 phases into one automated pipeline:

1. **FORGE** — Research agents enrich the plan with best practices, codebase patterns, and past echoes
2. **PLAN REVIEW** — 3 parallel reviewers evaluate the plan (circuit breaker halts on BLOCK)
2.5. **PLAN REFINEMENT** — Extracts CONCERN verdicts into concern-context.md for worker awareness (orchestrator-only)
2.7. **VERIFICATION GATE** — Deterministic checks (file refs, headings, acceptance criteria, post-forge freshness re-check) with zero LLM cost. The full freshness gate runs during pre-flight (before Phase 1) using 5-signal composite score; Phase 2.7 only re-checks forge-expanded file references. Use `--skip-freshness` to bypass the pre-flight check.
2.8. **SEMANTIC VERIFICATION** — Codex cross-model contradiction detection on the enriched plan (v1.39.0+)
4.5. **TASK DECOMPOSITION** — Codex cross-model task granularity and dependency analysis (v1.87.0+)
5. **WORK** — Swarm workers implement the plan with incremental `[ward-checked]` commits
5.5. **GAP ANALYSIS** — Inspector Ashes score 9 quality dimensions and produce VERDICT.md (arc-inspect-{id} team). Low-scoring dimensions propagated as focus areas to Phase 6 reviewers.
5.6. **CODEX GAP ANALYSIS** — Codex cross-model plan-vs-implementation gap detection (v1.39.0+)
5.8. **GAP REMEDIATION** — Auto-fix FIXABLE gaps before code review (arc-gap-fix-{id} team, configurable via `arc.gap_analysis.remediation` talisman settings)
5.7. **GOLDMASK VERIFICATION** — Blast-radius analysis via investigation agents: 5 impact tracers + wisdom sage + lore analyst (v1.47.0+)

Note: Phase numbers are non-sequential (5.5 → 5.6 → 5.8 → 5.7) for backward compatibility — execution follows the order listed above.
6. **CODE REVIEW** — Roundtable Circle review produces TOME with structured findings
6.5. **GOLDMASK CORRELATION** — Synthesis of investigation findings into unified GOLDMASK.md report (orchestrator-only, v1.47.0+)
7. **MEND** — Parallel fixers resolve findings from TOME
7.5. **VERIFY MEND** — Adaptive convergence controller: loops Phase 6→7→7.5 until findings converge or tier max cycles reached (LIGHT: 2, STANDARD: 3, THOROUGH: 5). Proceeds to audit with warning on halt
7.7. **TEST** — Diff-scoped test execution: unit → integration → E2E/browser (non-blocking WARN, skip with `--no-test`)
7.8. **TEST COVERAGE CRITIQUE** — Codex cross-model test adequacy assessment (v1.87.0+)
8.5. **PRE-SHIP VALIDATION** — Zero-LLM-cost dual-gate completion check (artifact integrity + quality signals)
8.55. **RELEASE QUALITY CHECK** — Codex cross-model release artifact validation (v1.87.0+)
9.1. **BOT_REVIEW_WAIT** — Poll for bot reviews (CI, linters, security scanners) before shipping (v1.88.0+, opt-in via `arc.ship.bot_review.enabled`)
9.2. **PR_COMMENT_RESOLUTION** — Multi-round loop to resolve bot/human PR review comments with hallucination checking (v1.88.0+, opt-in)
9. **SHIP** — Auto PR creation via `gh pr create` with generated template (skip with `--no-pr`)
9.5. **MERGE** — Rebase onto target branch + auto squash-merge with pre-merge checklist (skip with `--no-merge`)

Note: Phase numbers match the internal arc skill pipeline (Phases 3-4 are internal forge/plan-review and not shown in this summary).

Each phase summons a fresh team. Checkpoint-based resume (`--resume`) validates artifact integrity with SHA-256 hashes. Feature branches auto-created when on main.

## Batch Mode (Sequential Multi-Plan Execution)

When you run `/rune:arc-batch`, Rune executes `/rune:arc` across multiple plan files sequentially:

1. **Pre-flight** — Validate all plan files exist, no duplicates or symlinks
2. **For each plan** — Full 21-phase arc pipeline (forge through merge)
3. **Inter-run cleanup** — Checkout main, pull latest, clean state
4. **Retry on failure** — Up to 3 `--resume` attempts per plan, then skip
5. **Progress tracking** — `batch-progress.json` enables `--resume` for interrupted batches

Batch mode runs headless with `--dangerously-skip-permissions`. Ensure all plans are trusted.

## GitHub Issues Mode (Issues → Plans → PRs)

When you run `/rune:arc-issues`, Rune processes a GitHub Issues backlog end-to-end:

1. **Fetch issues** — by label (`--label "rune:ready"`), file queue, or inline numbers
2. **Generate plans** — each issue body becomes a plan file in `tmp/gh-plans/`
3. **Run arc** — full 18-phase arc pipeline per issue (forge → work → review → mend → ship → merge)
4. **Post results** — success comment + `rune:done` label on issue after arc completes
5. **Close issues** — PR body includes `Fixes #N` for auto-close on merge
6. **Human escalation** — failed issues get `rune:failed` label + error comment; quality-gate failures get `rune:needs-review`

### Rune Status Labels

| Label | Meaning | Re-process |
|-------|---------|------------|
| `rune:ready` | Issue is ready for Rune to process | (trigger label) |
| `rune:in-progress` | Currently being processed | Wait, or `--cleanup-labels` if orphaned (> 2h) |
| `rune:done` | Completed — PR linked via `Fixes #N` | Issue auto-closes on PR merge |
| `rune:failed` | Arc failed, needs human fix | Fix issue body → remove label → re-run |
| `rune:needs-review` | Plan quality low or conflicts detected | Add detail → remove label → re-run |

### Cancel an Active Issues Run

```bash
/rune:cancel-arc-issues
```

## Hierarchical Plans

For complex features that decompose into multiple dependent sub-plans, use hierarchical mode. Each child plan gets its own full arc pipeline run in dependency order, producing a single PR to main when all children complete.

> **Migration note**: Hierarchical plans are fully opt-in. All existing `/rune:strive`, `/rune:arc`, and `/rune:arc-batch` workflows are unaffected.

### When to Use

Use hierarchical plans when a feature has:
- Multiple implementation phases that must run in strict order
- Cross-phase artifact dependencies (one phase produces types/files that another consumes)
- Tasks too large for a single arc run but too coupled for fully independent shards

### Workflow

1. **Plan** — run `/rune:devise` and select "Hierarchical" at Phase 2.5 (appears when complexity >= 0.65)
2. **Review** — inspect the parent plan's execution table and dependency contract matrix
3. **Execute** — run `/rune:arc-hierarchy plans/parent-plan.md` to orchestrate all children
4. **Each child** runs its own full arc pipeline (forge → work → review → mend → test → ship)
5. **Single PR** to main is created after all children complete

### Child Plan Awareness

Workers running a child plan automatically receive context about prior siblings:

- **Available artifacts** — exports, files, endpoints produced by completed prior children
- **Prerequisites** — artifacts this child declared as required (with AVAILABLE/MISSING status)
- **Self-heal tasks** — tasks marked `[SELF-HEAL]` run first to recover from missing prerequisites

### Prerequisite Strategies

When a required artifact is missing, the resolution strategy is configured via `work.hierarchy.missing_prerequisite`:

| Strategy | Behavior |
|----------|----------|
| `pause` | Halt and prompt user (default — safest) |
| `self-heal` | Inject `[SELF-HEAL]` tasks to recreate the missing artifact |
| `backtrack` | Re-run the sibling that should have provided it |

### Cancel an Active Hierarchy Run

```bash
/rune:cancel-arc-hierarchy
```

### Configure

```yaml
# .claude/talisman.yml
work:
  hierarchy:
    enabled: true                    # Enable hierarchical plan support
    max_children: 12                 # Maximum children per parent plan
    max_backtracks: 1                # Max backtrack attempts per child
    missing_prerequisite: "pause"    # pause | self-heal | backtrack
    conflict_resolution: "pause"     # Merge conflict: pause | child-wins | feature-wins
    integration_failure: "pause"     # Test failure: pause | skip | retry
    sync_main_before_pr: true        # Merge main into feature before PR
    cleanup_child_branches: true     # Delete child branches after merge
    require_all_children: true       # Block PR if any child failed/partial
    test_timeout_ms: 300000          # Integration test timeout (5 min default)
    merge_strategy: "merge"          # Final PR: merge | squash
```

## Mend Mode (Finding Resolution)

When you run `/rune:mend`, Rune parses structured findings from a TOME and fixes them in parallel:

1. **Parses TOME** — extracts findings with session nonce validation
2. **Groups by file** — prevents concurrent edits to the same file
3. **Summons fixers** — restricted mend-fixer agents (no Bash, no TeamCreate)
4. **Monitors progress** — stale detection, 15-minute timeout
5. **Runs ward check** — once after all fixers complete (not per-fixer)
5.5. **Doc-consistency scan** — fixes drift between source-of-truth files and downstream targets (single pass, Edit-based)
6. **Produces report** — FIXED/FALSE_POSITIVE/FAILED/SKIPPED/CONSISTENCY_FIX categories

SEC-prefix findings require human approval for FALSE_POSITIVE marking.

## Inspect Mode (Plan-vs-Implementation Audit)

When you run `/rune:inspect`, Rune measures how well the codebase matches a plan:

1. **Parses plan** — extracts requirements, identifiers, and priorities from plan markdown
2. **Classifies requirements** — assigns each to specialized Inspector Ashes by keyword matching
3. **Identifies scope** — searches codebase for files matching plan identifiers
4. **Summons inspectors** — 4 parallel Inspector Ashes each assess their assigned dimensions
5. **Aggregates verdict** — Verdict Binder produces VERDICT.md with requirement matrix, dimension scores, and gap analysis
6. **Determines verdict** — READY (>=threshold% complete, 0 P1; default 80%, configurable via `inspect.completion_threshold` in talisman.yml or `--threshold` flag) / GAPS_FOUND / INCOMPLETE / CRITICAL_ISSUES

| Inspector | Dimensions | Gap Categories |
|-----------|-----------|----------------|
| Grace Warden | Correctness, Completeness | Correctness + Coverage |
| Ruin Prophet | Failure Modes, Security | Security + Operational |
| Sight Oracle | Design, Performance | Architectural |
| Vigil Keeper | Observability, Test Coverage, Maintainability | Test + Observability + Documentation |

Use `--fix` to auto-remediate FIXABLE gaps identified in the verdict (v1.51.0+). This spawns gap-fixer agents restricted by `SEC-GAP-001` hook enforcement.

Use `--mode plan` to review plan code samples for implementation correctness instead of auditing the full codebase (v1.53.0+). This extracts fenced code blocks from the plan, compares them against codebase patterns, and produces a plan-specific VERDICT.md. The `/rune:plan-review` command is a thin wrapper for this mode.

Output: `tmp/inspect/{id}/VERDICT.md`

## What It Does

When you run `/rune:appraise`, Rune:

1. **Detects scope** — classifies changed files by extension
2. **Selects Ash** — picks the right reviewers (3–9 Ashes)
3. **Summons Agent Teams** — each reviewer gets its own 200k context window
4. **Reviews in parallel** — Ash review simultaneously, writing to files
5. **Aggregates findings** — Runebinder deduplicates and prioritizes
6. **Verifies evidence** — Truthsight validates P1 findings against source
7. **Presents TOME** — unified review summary

## Audit Mode

When you run `/rune:audit`, Rune scans your entire codebase instead of just changed files:

1. **Scans codebase** — finds all project files (excluding binaries, lock files, build output)
2. **Classifies files** — same Rune Gaze extension-based classification
3. **Selects Ash** — same 2-8 Ashes selection
4. **Audits in parallel** — each Ash gets capped context budget, prioritized by importance
5. **Aggregates findings** — Runebinder deduplicates and prioritizes
6. **Presents TOME** — unified audit summary with coverage gaps

Unlike `/rune:appraise` (changed files only), `/rune:audit` does not require git. Each Ash's context budget limits how many files it processes, prioritized by architectural importance.

## Plan Mode

When you run `/rune:devise`, Rune orchestrates a multi-agent research pipeline:

1. **Gathers input** — runs interactive brainstorm by default (auto-skips when requirements are clear)
2. **Summons research agents** — 3-5 parallel agents explore best practices, codebase patterns, framework docs, and past echoes
3. **Synthesizes findings** — lead consolidates research into a structured plan
4. **Forge Gaze enrichment** — topic-aware agent selection matches plan sections to specialized agents by default using keyword overlap scoring. 26 built-in agents (22 review + 2 research + 2 utility) with elicitation-sage integration (max 6 sages per forge session) across enrichment (~5k tokens) and research (~15k tokens) budget tiers. Use `--exhaustive` for deeper research with lower thresholds. Use `--quick` to skip forge.
5. **Reviews document** — Scroll Reviewer checks plan quality, with optional iterative refinement and technical review (decree-arbiter + knowledge-keeper)
6. **Persists learnings** — saves planning insights to Rune Echoes

Output: `plans/YYYY-MM-DD-{type}-{feature-name}-plan.md`

## Work Mode

When you run `/rune:strive`, Rune parses a plan into tasks and summons self-organizing swarm workers:

1. **Parses plan** — extracts tasks with dependencies, clarifies ambiguities via AskUserQuestion
2. **Sets up environment** — branch safety check (warns on `main`), stash dirty files (Phase 0.5)
3. **Creates task pool** — TaskCreate with dependency chains (blockedBy)
4. **Summons workers** — Rune Smiths (implementation) and Trial Forgers (tests) claim tasks independently
5. **Monitors progress** — polls TaskList, detects stalled workers, releases stuck tasks
6. **Commits via broker** — orchestrator applies patches and commits (prevents index.lock contention)
7. **Runs quality gates** — auto-discovers wards + post-ward verification checklist
8. **Persists learnings** — saves implementation patterns to Rune Echoes
9. **Cleans up** — shutdown workers, TeamDelete (Phase 6)
10. **Ships (optional)** — push + PR creation with generated template (Phase 6.5)

Workers scale automatically based on task count (1-5 tasks: 2 workers, 20+ tasks: 5 workers).

New talisman work keys: `skip_branch_check`, `branch_prefix`, `pr_monitoring`, `co_authors`. Reserved for a future release: `pr_template`, `auto_push`. See [`talisman.example.yml`](talisman.example.yml) for defaults.

## Codex Oracle (Cross-Model Verification)

When the `codex` CLI is installed, Rune automatically detects it and adds **Codex Oracle** as a built-in Ash. Codex Oracle provides cross-model verification — a second AI perspective (GPT-5.3-codex) alongside Claude Code's review agents — catching issues that single-model blind spots miss.

### How It Works

- **Review/Audit**: Codex Oracle joins the Roundtable Circle as a teammate, reviewing assigned files via `codex exec` in read-only sandbox mode. Its findings go through the standard TOME aggregation pipeline with `CDX-NNN` prefix.
- **Plan**: Codex Oracle serves as both a research agent (Phase 1C) and an optional plan reviewer (Phase 4C) with `[CDX-PLAN-NNN]` findings.
- **Work**: After ward checks pass, an optional Phase 4.5 advisory compares the implementation diff against the plan to catch semantic drift. Non-blocking `[CDX-WORK-NNN]` warnings.
- **Forge**: Codex Oracle participates in Forge Gaze topic matching for plan enrichment.

### Cross-Model Verification

Codex findings go through a verification layer before entering the TOME:
1. File existence check (does the referenced file exist?)
2. Code snippet match (does the Rune Trace match actual code at the referenced line?)
3. Cross-Ash correlation (did any Claude Ash flag the same issue? If so, confidence boost)
4. Only CONFIRMED findings proceed; HALLUCINATED and UNVERIFIED findings are filtered out

### Prerequisites

- `codex` CLI installed: `npm install -g @openai/codex`
- OpenAI account with API access (Codex CLI handles authentication)
- No Rune configuration needed — auto-detected when CLI is available

### Configuration

```yaml
# .claude/talisman.yml
codex:
  disabled: false                   # Set true to disable Codex Oracle entirely
  model: "gpt-5.3-codex-spark"     # Codex model (gpt-5-codex, gpt-5.3-codex, gpt-5.3-codex-spark)
  reasoning: "xhigh"               # Reasoning effort (xhigh, high, medium, low)
  sandbox: "read-only"              # Sandbox mode (always read-only for review)
  context_budget: 20                # Max files to review (default: 20)
  confidence_threshold: 80          # Min confidence to report finding (default: 80)
  workflows: [review, audit, plan, forge, work, mend]  # Which workflows use Codex Oracle (mend added v1.39.0)
  work_advisory:
    enabled: true                   # Set false to skip advisory in work pipeline
    max_diff_size: 15000            # Truncate diff to this many chars (default: 15000)
  verification:
    enabled: true                   # Cross-model verification (recommended: true)
    fuzzy_match_threshold: 0.7      # Code snippet match threshold (0.0-1.0)
    cross_model_bonus: 0.15         # Confidence boost when Claude+Codex agree
```

When Codex Oracle is disabled (via `codex.disabled: true`) or the CLI is not installed, all workflows proceed normally without it — no error, just an info-level log message.

## Rune Echoes (Memory)

Rune Echoes is a project-level memory system stored in `.claude/echoes/`. After each review or audit, agents persist patterns and learnings. Future sessions read these echoes to avoid repeating mistakes.

### 3-Layer Lifecycle

| Layer | Name | Duration | Purpose |
|-------|------|----------|---------|
| Structural | **Etched** | Permanent | Architecture decisions, tech stack, key conventions |
| Tactical | **Inscribed** | 90 days | Patterns from reviews/audits (N+1 queries, unused imports) |
| Session | **Traced** | 30 days | Session-specific observations |

### How It Works

1. Run `/rune:echoes init` to set up memory directories
2. Run `/rune:appraise` or `/rune:audit` — agents persist high-confidence findings
3. Future workflows read echoes via the `echo-reader` agent
4. Memory self-prunes: stale entries archive automatically

### Memory Management

```bash
/rune:echoes show     # Display echo statistics per role
/rune:echoes prune    # Score and archive stale entries
/rune:echoes reset    # Clear all echoes (with backup)
```

## Ash

| Ash | Role | When Active |
|-----------|------|-------------|
| Forge Warden | Backend review | Backend files changed |
| Ward Sentinel | Security review | Always |
| Veil Piercer | Truth-telling review | Always |
| Pattern Weaver | Quality patterns | Always |
| Glyph Scribe | Frontend review | Frontend files changed |
| Knowledge Keeper | Docs review | Docs changed (>= 10 lines) |
| Codex Oracle | Cross-model review (GPT-5.3-codex) | `codex` CLI available |

Each Ash embeds several review agents as specialized perspectives. For example, Forge Warden embeds rune-architect, ember-oracle, flaw-hunter, mimic-detector, type-warden, depth-seer, blight-seer, and forge-keeper. Ward Sentinel embeds ward-sentinel and related security-focused agents. This composite design lets each Ash apply multiple lenses to the same code in a single pass.

## Agents

### Review Agents

34 specialized agents that Ash embed as perspectives:

| Agent | Focus |
|-------|-------|
| ward-sentinel | Security, OWASP, auth |
| ember-oracle | Performance, N+1, complexity |
| rune-architect | Architecture, layer boundaries |
| simplicity-warden | YAGNI, over-engineering |
| flaw-hunter | Logic bugs, edge cases |
| mimic-detector | Code duplication |
| pattern-seer | Pattern consistency |
| void-analyzer | Incomplete implementations |
| wraith-finder | Dead code |
| phantom-checker | Dynamic references (companion to wraith-finder, not Ash-embedded) |
| type-warden | Type safety, mypy compliance |
| trial-oracle | TDD compliance, test quality |
| depth-seer | Missing logic, complexity detection |
| blight-seer | Design anti-patterns, architectural smells |
| forge-keeper | Data integrity, migration safety |
| tide-watcher | Async/concurrency patterns |
| refactor-guardian | Refactoring safety, behavioral preservation |
| reference-validator | Cross-file reference integrity, link validation |
| reality-arbiter | Production viability truth-telling |
| assumption-slayer | Premise validation truth-telling |
| entropy-prophet | Long-term consequence truth-telling |
| naming-intent-analyzer | Naming intent quality, name-behavior mismatch |
| doubt-seer | Evidence quality challenger, unproven claim detection |
| python-reviewer | Python 3.10+ patterns, type safety, async, dataclass idioms (PY) |
| typescript-reviewer | TypeScript strict mode, discriminated unions, Zod schemas (TSR) |
| rust-reviewer | Rust ownership, lifetime, unsafe blocks, error handling (RST) |
| php-reviewer | PHP 8.1+ patterns, type declarations, named args, enums (PHP) |
| fastapi-reviewer | FastAPI dependency injection, Pydantic models, async handlers (FAPI) |
| django-reviewer | Django ORM, middleware, signals, template safety (DJG) |
| laravel-reviewer | Laravel Eloquent, service container, request validation (LARV) |
| sqlalchemy-reviewer | SQLAlchemy session lifecycle, N+1 queries, relationship loading (SQLA) |
| tdd-compliance-reviewer | TDD cycle compliance, test-first discipline, coverage quality (TDD) |
| ddd-reviewer | DDD aggregate boundaries, value objects, domain events (DDD) |
| di-reviewer | Dependency injection patterns, container config, scope management (DI) |

### Research Agents

Summoned during `/rune:devise` for parallel research:

| Agent | Purpose |
|-------|---------|
| practice-seeker | External best practices and industry patterns |
| repo-surveyor | Codebase exploration and pattern discovery |
| lore-scholar | Framework documentation and API research |
| git-miner | Git history analysis and code archaeology |
| echo-reader | Reads past Rune Echoes for relevant learnings |

### Work Agents

Summoned during `/rune:strive` as self-organizing swarm workers:

| Agent | Purpose |
|-------|---------|
| rune-smith | Code implementation (TDD-aware, claims tasks from pool) |
| trial-forger | Test generation (follows existing test patterns) |

### Utility Agents

| Agent | Purpose |
|-------|---------|
| runebinder | Aggregates Ash findings into TOME.md |
| decree-arbiter | Technical soundness review for plans |
| truthseer-validator | Audit coverage validation (Roundtable Phase 5.5, >100 files) |
| flow-seer | Spec flow analysis and gap detection |
| scroll-reviewer | Document quality review |
| mend-fixer | Parallel code fixer for /rune:mend findings (restricted tools) |
| knowledge-keeper | Documentation coverage reviewer for plans |
| elicitation-sage | Structured reasoning using BMAD-derived methods (summoned per eligible section, max 6 per forge session) |
| veil-piercer-plan | Plan-level truth-teller (Phase 4C plan review) |
| horizon-sage | Strategic depth assessment — Temporal Horizon, Root Cause Depth, Innovation Quotient, Stability, Maintainability |
| gap-fixer | Gap remediation fixer for Phase 5.8 — prompt-template-based (no dedicated .md file) |

## Skills

| Skill | Purpose |
|-------|---------|
| agent-browser | Browser automation knowledge injection for E2E testing (non-invocable) |
| arc | End-to-end orchestration pipeline (pre-flight freshness gate + 23 phases: forge → plan review → plan refinement → verification → semantic verification → task decomposition → work → gap analysis → codex gap analysis → gap remediation → goldmask verification → code review → goldmask correlation → mend → verify mend → test → test coverage critique → pre-ship validation → release quality check → bot review wait → PR comment resolution → ship → merge) |
| arc-batch | Sequential batch arc execution with crash recovery and progress tracking |
| ash-guide | Agent invocation reference |
| audit | Full codebase audit with up to 7 built-in Ashes (+ custom from talisman.yml). Use `--deep` for two-pass investigation. Use `--incremental` for stateful 3-tier auditing (file, workflow, API) with persistent priority scoring and coverage tracking |
| chome-pattern | CLAUDE_CONFIG_DIR resolution for multi-account support |
| codex-cli | Canonical Codex CLI integration — detection, execution, error handling, talisman config |
| context-weaving | Context overflow/rot prevention |
| elicitation | BMAD-derived structured reasoning methods (Tree of Thoughts, Pre-mortem, Red Team, 5 Whys, etc.) with phase-aware auto-selection |
| file-todos | Unified file-based todo tracking (6-state lifecycle, YAML frontmatter, 7 subcommands). Gated by `talisman.file_todos.enabled` |
| forge | Deepen existing plan with Forge Gaze enrichment (+ `--exhaustive`). Goldmask Lore Layer (Phase 1.5) for risk-aware section prioritization |
| git-worktree | Worktree isolation for /rune:strive (experimental `--worktree` flag) |
| goldmask | Cross-layer impact analysis (Impact + Wisdom + Lore layers). Shared data discovery + risk context template reused by forge, mend, inspect, and devise for risk-aware workflows |
| inner-flame | Universal 3-layer self-review protocol (Grounding, Completeness, Self-Adversarial) for all teammates (non-invocable) |
| inspect | Plan-vs-implementation deep audit with 4 Inspector Ashes (9 dimensions, 8 gap categories). Goldmask Lore Layer (Phase 1.3) for risk-aware gap prioritization |
| mend | Parallel finding resolution from TOME. Goldmask data passthrough (risk overlay + quick check) |
| devise | Multi-agent planning: brainstorm, research, validate, synthesize, shatter, forge, review (+ `--quick`). Predictive Goldmask (2-8 agents, basic default) for pre-implementation risk assessment |
| polling-guard | Monitoring loop fidelity — correct waitForCompletion translation |
| resolve-gh-pr-comment | Resolve a single GitHub PR review comment — fetch, analyze, fix, reply, and resolve thread |
| resolve-all-gh-pr-comments | Batch resolve all open PR review comments with pagination and progress tracking |
| appraise | Multi-agent code review with up to 7 built-in Ashes (+ custom from talisman.yml) |
| roundtable-circle | Review orchestration (7-phase lifecycle) |
| rune-echoes | Smart Memory Lifecycle (3-layer project memory) |
| rune-orchestration | Multi-agent coordination patterns |
| skill-testing | TDD methodology for skills — pressure testing, rationalization counters, Iron Law (SKT-001). `disable-model-invocation: true` |
| stacks | Stack-aware intelligence — 4-layer detection engine with 11 specialist reviewers (Python, TypeScript, Rust, PHP, FastAPI, Django, Laravel, SQLAlchemy, TDD, DDD, DI). Auto-loaded by Rune Gaze Phase 1A (non-invocable) |
| systematic-debugging | 4-phase debugging methodology (Observe → Narrow → Hypothesize → Fix) for workers hitting repeated failures. Iron Law: no fixes without root cause investigation (DBG-001) |
| testing | Test orchestration pipeline knowledge for arc Phase 7.7 (non-invocable) |
| using-rune | Workflow discovery and intent routing |
| strive | Swarm work execution with self-organizing task pool (+ `--approve`, incremental commits) |
| zsh-compat | zsh shell compatibility (read-only vars, glob NOMATCH, word splitting) |

## Configuration

Override file classification defaults in your project:

```yaml
# .claude/talisman.yml
rune-gaze:
  backend_extensions: [.py, .go]
  frontend_extensions: [.tsx, .ts]
  skip_patterns: ["**/migrations/**"]
  always_review: ["CLAUDE.md", ".claude/**/*.md"]

ashes:
  custom:                              # Extend built-in Ashes with your own
    - name: "my-reviewer"
      agent: "my-reviewer"             # .claude/agents/my-reviewer.md
      source: local
      workflows: [review]
      trigger:
        extensions: [".py"]
      context_budget: 20
      finding_prefix: "MYR"

settings:
  max_ashes: 9                   # Hard cap (7 built-in + custom)

echoes:
  version_controlled: false  # Set to true to track echoes in git

work:
  ward_commands:               # Override quality gate commands
    - "make check"
    - "npm test"
  max_workers: 3               # Max parallel swarm workers
  approve_timeout: 180         # Seconds (default 3 min)
  commit_format: "rune: {subject} [ward-checked]"
  skip_branch_check: false     # Skip Phase 0.5 branch check
  branch_prefix: "rune/work"  # Feature branch prefix (alphanumeric, _, -, / only)
  pr_monitoring: false         # Post-deploy monitoring section in PR body
  co_authors: []               # Co-Authored-By lines in "Name <email>" format
  # pr_template: default       # Reserved for a future release
  # auto_push: false           # Reserved for a future release

# arc:
#   consistency:
#     checks:
#       - name: version_sync
#         source:
#           file: ".claude-plugin/plugin.json"     # SEC-012 FIX: key is `file:` (not `path:`)
#           extractor: json_field
#           field: "version"                        # SEC-012 FIX: dot-path (not JSONPath `$.version`)
#         targets:
#           - path: "CLAUDE.md"
#             pattern: "version: {value}"
#           - path: "README.md"
#             pattern: "v{value}"
#         phase: ["plan", "post-work"]
#       - name: agent_count
#         source:
#           file: "agents/review/*.md"             # SEC-012 FIX: key is `file:` (not `path:`)
#           extractor: glob_count                   # QUAL-015 FIX: glob_count (not line_count) — counts matching files
#         targets:
#           - path: "CLAUDE.md"
#             pattern: "{value} agents"
#         phase: ["post-work"]
```

See [`talisman.example.yml`](talisman.example.yml) for the full configuration schema including custom Ash, trigger matching, dedup hierarchy, and cross-file consistency checks.

## Remembrance Channel

High-confidence learnings from Rune Echoes can be promoted to human-readable solution documents in `docs/solutions/`. See `skills/rune-echoes/references/remembrance-schema.md` for the YAML frontmatter schema and promotion rules.

## Key Concepts

**Truthbinding Protocol** — All agent prompts include anti-injection anchors. Agents ignore instructions embedded in reviewed code.

**Rune Traces** — Every finding must include actual code snippets from source files. No paraphrasing.

**Glyph Budget** — Agents write findings to files and return only a 1-sentence summary to the Tarnished. Prevents context overflow.

**Inscription Protocol** — JSON contract defining what each agent must produce, enabling automated validation.

**TOME** — The unified review summary after deduplication and prioritization.

**Arc Pipeline** — End-to-end orchestration across 23 phases with checkpoint-based resume, per-phase tool restrictions, convergence gate (regression detection + retry loop), time budgets, diff-scoped testing (unit/integration/E2E), 3 inline Codex quality gates (task decomposition, test coverage critique, release quality check), cascade circuit breaker, auto PR creation (ship), and auto merge with pre-merge checklist. Phase 5.5 uses Inspector Ashes (9-dimension scoring), Phase 5.8 auto-remediates FIXABLE gaps.

**Mend** — Parallel finding resolution from TOME with restricted fixers, centralized ward check, and post-ward doc-consistency scan that fixes drift between source-of-truth files and their downstream targets.

**Plan Section Convention** — Plans with pseudocode must include contract headers (Inputs/Outputs/Preconditions/Error handling) before code blocks. Phase 2.7 verification gate enforces this. Workers implement from contracts, not by copying pseudocode verbatim.

**Forge Gaze** — Topic-aware agent selection for plan enrichment (default in `/rune:devise` and `/rune:forge`). Matches plan section topics to specialized agents via keyword overlap scoring. Configurable thresholds and budget tiers.

**Rune Echoes** — Project-level agent memory with 3-layer lifecycle. Agents learn across sessions without explicit compound workflows.

## File Structure

```
plugins/rune/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── investigation/       # 23 investigation agents (Goldmask + Inspect)
│   ├── review/              # 34 review agents
│   │   └── references/      # Shared review checklists
│   ├── research/            # 5 research agents (plan pipeline)
│   ├── testing/             # 4 testing agents (arc Phase 7.7)
│   ├── work/                # 2 swarm workers (work pipeline)
│   └── utility/             # 11 utility agents: Runebinder, decree-arbiter, truthseer-validator, flow-seer, scroll-reviewer, mend-fixer, knowledge-keeper, elicitation-sage, veil-piercer-plan, horizon-sage, gap-fixer (prompt-template)
├── commands/
│   ├── cancel-arc.md           # /rune:cancel-arc
│   ├── cancel-arc-batch.md     # /rune:cancel-arc-batch
│   ├── cancel-arc-hierarchy.md # /rune:cancel-arc-hierarchy
│   ├── cancel-arc-issues.md    # /rune:cancel-arc-issues
│   ├── cancel-review.md        # /rune:cancel-review
│   ├── cancel-audit.md         # /rune:cancel-audit
│   ├── elicit.md               # /rune:elicit
│   ├── echoes.md               # /rune:echoes
│   ├── plan-review.md          # /rune:plan-review
│   └── rest.md                 # /rune:rest
├── skills/
│   ├── agent-browser/       # Browser automation knowledge (non-invocable)
│   ├── arc/                 # /rune:arc (end-to-end pipeline)
│   │   ├── SKILL.md
│   │   └── references/      # Arc-specific phase refs, delegation checklist
│   ├── arc-batch/           # /rune:arc-batch (sequential multi-plan)
│   ├── arc-hierarchy/       # /rune:arc-hierarchy (hierarchical plan execution)
│   ├── arc-issues/          # /rune:arc-issues (GitHub Issues-driven batch arc)
│   │   └── references/      # arc-issues-algorithm.md
│   ├── ash-guide/           # Agent reference
│   ├── audit/               # /rune:audit (full codebase audit, --deep mode)
│   │   └── references/      # deep-mode.md
│   ├── chome-pattern/       # CLAUDE_CONFIG_DIR resolution
│   ├── codex-cli/           # Codex CLI integration
│   ├── context-weaving/     # Context management
│   ├── elicitation/         # BMAD-derived reasoning methods
│   │   └── references/      # methods.csv, examples.md, phase-mapping.md
│   ├── forge/               # /rune:forge (plan enrichment, --exhaustive)
│   │   └── references/      # forge-enrichment-protocol.md
│   ├── git-worktree/        # Worktree isolation knowledge (non-invocable)
│   ├── goldmask/            # Cross-layer impact analysis
│   ├── inner-flame/         # 3-layer self-review protocol (non-invocable)
│   ├── inspect/             # /rune:inspect (plan-vs-implementation audit)
│   │   └── references/      # inspector-prompts.md, verdict-synthesis.md
│   ├── mend/                # /rune:mend (parallel finding resolution)
│   │   └── references/      # parse-tome.md, fixer-spawning.md, resolution-report.md
│   ├── devise/              # /rune:devise (multi-agent planning pipeline)
│   │   └── references/      # brainstorm-phase.md, research-phase.md, synthesize.md, etc.
│   ├── polling-guard/       # Monitoring loop fidelity
│   ├── appraise/            # /rune:appraise (multi-agent code review)
│   │   └── references/      # ash-summoning.md, tome-aggregation.md, review-scope.md
│   ├── roundtable-circle/   # Review orchestration
│   │   └── references/      # e.g. rune-gaze.md, custom-ashes.md
│   ├── rune-echoes/         # Smart Memory Lifecycle
│   ├── rune-orchestration/  # Core coordination
│   │   └── references/      # e.g. team-lifecycle-guard.md
│   ├── stacks/              # Stack-aware intelligence (non-invocable)
│   │   └── references/      # detection.md, stack-registry.md, context-router.md, languages/, frameworks/, databases/, libraries/, patterns/
│   ├── testing/             # Test orchestration pipeline (non-invocable)
│   │   └── references/      # test-discovery.md, service-startup.md, etc.
│   ├── using-rune/          # Workflow discovery and intent routing
│   ├── strive/              # /rune:strive (swarm work execution)
│   │   └── references/      # parse-plan.md, worker-prompts.md, ship-phase.md, etc.
│   └── zsh-compat/          # zsh shell compatibility
├── scripts/
│   ├── enforce-readonly.sh          # SEC-001: Read-only agent enforcement
│   ├── enforce-polling.sh           # POLL-001: Monitoring anti-pattern block
│   ├── enforce-zsh-compat.sh        # ZSH-001: zsh compatibility guard
│   ├── enforce-teams.sh             # ATE-1: Bare Task call prevention
│   ├── enforce-team-lifecycle.sh    # TLC-001: Team name validation + stale cleanup
│   ├── validate-mend-fixer-paths.sh # SEC-MEND-001: Mend fixer file scope
│   ├── verify-team-cleanup.sh       # TLC-002: Post-delete zombie detection
│   ├── session-team-hygiene.sh      # TLC-003: Session startup orphan scan
│   ├── validate-inner-flame.sh      # Inner Flame self-review gate
│   ├── on-task-completed.sh         # Task completion signal writer
│   ├── on-teammate-idle.sh          # Teammate idle quality gate
│   ├── session-start.sh             # Workflow routing loader
│   ├── pre-compact-checkpoint.sh    # Team state checkpoint before compaction
│   ├── session-compact-recovery.sh  # Team state re-injection after compaction
│   ├── on-session-stop.sh           # STOP-001: Active workflow detection on session end
│   ├── arc-batch-stop-hook.sh       # ARC-BATCH-STOP: Stop hook loop driver for arc-batch
│   ├── arc-batch-preflight.sh       # Arc batch pre-flight validation
│   ├── arc-hierarchy-stop-hook.sh   # ARC-HIERARCHY-LOOP: Stop hook loop driver for arc-hierarchy
│   ├── arc-issues-stop-hook.sh      # ARC-ISSUES-LOOP: Stop hook loop driver for arc-issues
│   ├── arc-issues-preflight.sh      # Arc issues pre-flight validation
│   ├── lib/
│   │   └── stop-hook-common.sh      # Shared Stop hook utilities
│   └── echo-search/                 # Echo Search MCP server + hooks
├── talisman.example.yml
├── CLAUDE.md
├── LICENSE
└── README.md
```

## Echo Search MCP Server

Rune includes an MCP server (`echo-search`) for full-text search over Rune Echoes using SQLite FTS5 with BM25 ranking. Features a multi-pass retrieval pipeline with query decomposition, semantic group expansion, retry injection, and Haiku reranking — each stage independently toggleable via `talisman.yml`.

**Requirements:** Python 3.7+ (uses stdlib `sqlite3` with FTS5 support)

**Tools:**

| Tool | Description |
|------|-------------|
| `echo_search` | Multi-pass retrieval: decomposition, BM25, composite scoring, group expansion, retry, reranking. |
| `echo_details` | Fetch full content for specific echo entries by ID. |
| `echo_reindex` | Rebuild the FTS5 index from `.claude/echoes/*/MEMORY.md` source files. |
| `echo_stats` | Index statistics: entry count, layer/role breakdown, last indexed timestamp. |
| `echo_record_access` | Record access for frequency-based scoring. Powers auto-promotion. |
| `echo_upsert_group` | Create or update a semantic group with entry memberships. |

**Retrieval Pipeline (configurable via `talisman.yml` under `echoes:`):**

1. **Query Decomposition** — LLM breaks complex queries into 1-4 keyword facets (`echoes.decomposition.enabled`)
2. **BM25 Search** — Per-facet FTS5 search with 3x over-fetch (always on)
3. **Merge** — Best-score dedup across facets (automatic when decomposition active)
4. **Composite Scoring** — 5-factor blend: BM25, recency, importance, proximity, frequency (always on)
5. **Group Expansion** — Sibling entries from semantic clusters (`echoes.semantic_groups.expansion_enabled`)
6. **Retry Injection** — Previously-failed entries matching token fingerprints (`echoes.retry.enabled`)
7. **Haiku Reranking** — Semantic re-scoring via Claude Haiku subprocess (`echoes.reranking.enabled`)

The `annotate-hook.sh` PostToolUse hook marks the index as dirty when echo files are modified. On next search, the server auto-reindexes before returning results. Configuration lives in `.mcp.json`.

## Lore

Rune uses Elden Ring-inspired theming:

- **You are the Tarnished** — the orchestrator commanding each workflow
- **Ash** are your teammates, each bringing specialized perspectives
- The **Roundtable Circle** is where reviews convene
- The **TOME** is the unified record of all findings
- **Rune Echoes** are memories that persist across sessions
- The **Elden Throne** is the ultimate goal — successful pipeline completion
- See CLAUDE.md for the full Lore Glossary

## Known Limitations

- **Agent Teams is experimental** — Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable. Behavior may change across Claude Code releases.
- **Context budget caps** — Each Ash can review a limited number of files (20-30). Large changesets (>20 files) are automatically split into chunks for thorough review with per-chunk quality metrics and adaptive convergence. For very large codebases in audit mode, coverage gaps are still reported in the TOME.
- **Incremental audit coverage** — `/rune:audit --incremental` uses persistent state for prioritized batch auditing, but the standard `/rune:audit` (without `--incremental`) still scans all files each run. For stateful 3-tier auditing across sessions, always use the `--incremental` flag.
- **Concurrent sessions** — Only one `/rune:appraise`, `/rune:audit`, or `/rune:arc` can run at a time. Use `/rune:cancel-review`, `/rune:cancel-audit`, or `/rune:cancel-arc` to stop an active session.
- **Manual cleanup optional** — Run `/rune:rest` to remove `tmp/` artifacts, or let the OS handle them.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Agent Teams not available" | Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your shell profile |
| Ash times out (>5 min) | Rune proceeds with partial results. Check TOME.md for coverage gaps |
| "Concurrent review running" | Run `/rune:cancel-review` first, then retry |
| Echo files causing merge conflicts | Add `.gitattributes` with `merge=union` for echo paths (see Configuration) |
| No files to review | Ensure you have uncommitted changes on a feature branch (not main) |
| `/rune:strive` stalled workers | Workers are warned at 5 minutes and auto-released at 10 minutes. Lead re-assigns stuck tasks |

## Security

- Agent prompts include Truthbinding anchors to resist prompt injection
- Review output in `tmp/` is ephemeral and not committed
- `.gitignore` excludes `.claude/echoes/` by default (opt-in to version control)
- Sensitive data filter rejects API keys, passwords, tokens from echo entries
- All findings require verified evidence from source code
- **Hook-based enforcement**: 19 event-driven hook scripts provide deterministic guardrails (9 enforcement + 4 quality/lifecycle + 2 compaction resilience + 4 session stop):

| Hook | Event | Purpose |
|------|-------|---------|
| SEC-001 | PreToolUse:Write\|Edit\|Bash | Blocks write tools for read-only review/audit agents |
| POLL-001 | PreToolUse:Bash | Blocks sleep+echo monitoring anti-pattern |
| ZSH-001 | PreToolUse:Bash | Blocks zsh-incompatible patterns (read-only vars, unprotected globs) |
| SEC-MEND-001 | PreToolUse:Write\|Edit | Blocks mend-fixers from writing outside assigned files |
| ATE-1 | PreToolUse:Task | Blocks bare Task calls during active workflows |
| TLC-001 | PreToolUse:TeamCreate | Validates team names (hard block) + stale team cleanup (advisory) |
| TLC-002 | PostToolUse:TeamDelete | Zombie team dir detection after deletion |
| TLC-003 | SessionStart:startup\|resume | Orphaned team and stale state file detection |
| TLC-004 | PostToolUse:TeamCreate | Session marker (.session file) for ownership verification |
| — | PostToolUse:Write\|Edit | Echo search index dirty-signal annotation |
| — | TaskCompleted | Signal files + haiku quality gate + Inner Flame self-review validation |
| — | TeammateIdle | Output file validation + SEAL marker checks |
| — | SessionStart:startup\|resume\|clear\|compact | Workflow routing context loader |
| — | PreCompact:manual\|auto | Team state checkpoint before compaction |
| — | SessionStart:compact | Team state re-injection after compaction |
| ARC-BATCH-STOP | Stop | Drives arc-batch loop via Stop hook pattern — reads state file, marks plan completed, re-injects next arc prompt |
| ARC-HIERARCHY-LOOP | Stop | Drives arc-hierarchy loop via Stop hook pattern — reads state file, verifies child provides() contracts, re-injects next child arc prompt |
| ARC-ISSUES-LOOP | Stop | Drives arc-issues loop via Stop hook pattern — reads state file, posts GitHub comment, updates labels, re-injects next arc prompt |
| STOP-001 | Stop | Detects active workflows on session end, blocks exit with cleanup instructions |

## Requirements

- Claude Code with Agent Teams support
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable enabled
- **Optional**: `codex` CLI for cross-model verification (`npm install -g @openai/codex`)

## License

MIT

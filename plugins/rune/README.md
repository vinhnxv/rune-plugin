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
# End-to-end pipeline: freshness check → forge → plan review → refinement → verification → work → gap analysis → code review → mend → verify mend → audit → ship → merge
/rune:arc plans/my-plan.md
/rune:arc plans/my-plan.md --no-forge             # Skip research enrichment
/rune:arc plans/my-plan.md --approve              # Require human approval per task
/rune:arc plans/my-plan.md --skip-freshness       # Bypass plan freshness check
/rune:arc plans/my-plan.md --resume               # Resume from checkpoint
/rune:arc plans/my-plan.md --no-pr                # Skip PR creation (Phase 9)
/rune:arc plans/my-plan.md --no-merge             # Skip auto-merge (Phase 9.5)
/rune:arc plans/my-plan.md --draft                # Create PR as draft

# Plan a feature (brainstorm + research + forge + review by default)
/rune:plan                       # Full pipeline
/rune:plan --quick               # Quick: research + synthesize + review only

# Deepen an existing plan with Forge Gaze enrichment
/rune:forge plans/my-plan.md     # Deepen specific plan
/rune:forge                      # Auto-detect recent plan

# Execute a plan with swarm workers
/rune:work plans/feat-user-auth-plan.md
/rune:work plans/my-plan.md --approve  # Require human approval per task

# Run a multi-agent code review (changed files only)
/rune:review

# Resolve findings from a review TOME
/rune:mend tmp/reviews/abc123/TOME.md

# Run a full codebase audit (all files)
/rune:audit
/rune:audit --focus security    # Security-only audit
/rune:audit --max-agents 3      # Limit to 3 Ashes

# Preview scope without summoning agents
/rune:review --dry-run
/rune:audit --dry-run

# Interactive structured reasoning (Tree of Thoughts, Pre-mortem, Red Team, 5 Whys)
/rune:elicit
/rune:elicit "Which auth approach is best for this API?"

# Cancel active workflows
/rune:cancel-review
/rune:cancel-audit
/rune:cancel-arc

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

When you run `/rune:arc`, Rune chains 14 phases into one automated pipeline:

1. **FORGE** — Research agents enrich the plan with best practices, codebase patterns, and past echoes
2. **PLAN REVIEW** — 3 parallel reviewers evaluate the plan (circuit breaker halts on BLOCK)
2.5. **PLAN REFINEMENT** — Extracts CONCERN verdicts into concern-context.md for worker awareness (orchestrator-only)
2.7. **VERIFICATION GATE** — Deterministic checks (file refs, headings, acceptance criteria, post-forge freshness re-check) with zero LLM cost. The full freshness gate runs during pre-flight (before Phase 1) using 5-signal composite score; Phase 2.7 only re-checks forge-expanded file references. Use `--skip-freshness` to bypass the pre-flight check.
2.8. **SEMANTIC VERIFICATION** — Codex cross-model contradiction detection on the enriched plan (v1.39.0+)
5. **WORK** — Swarm workers implement the plan with incremental `[ward-checked]` commits
5.5. **GAP ANALYSIS** — Deterministic check: plan acceptance criteria vs committed code + doc-consistency via talisman verification_patterns (zero LLM cost, advisory)
5.6. **CODEX GAP ANALYSIS** — Codex cross-model plan-vs-implementation gap detection (v1.39.0+)
6. **CODE REVIEW** — Roundtable Circle review produces TOME with structured findings
7. **MEND** — Parallel fixers resolve findings from TOME
7.5. **VERIFY MEND** — Adaptive convergence controller: loops Phase 6→7→7.5 until findings converge or tier max cycles reached (LIGHT: 2, STANDARD: 3, THOROUGH: 5). Proceeds to audit with warning on halt
8. **AUDIT** — Final quality gate (informational)
9. **SHIP** — Auto PR creation via `gh pr create` with generated template (skip with `--no-pr`)
9.5. **MERGE** — Rebase onto target branch + auto squash-merge with pre-merge checklist (skip with `--no-merge`)

Note: Phase numbers match the internal arc skill pipeline (Phases 3-4 are internal forge/plan-review and not shown in this summary).

Each phase summons a fresh team. Checkpoint-based resume (`--resume`) validates artifact integrity with SHA-256 hashes. Feature branches auto-created when on main.

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

## What It Does

When you run `/rune:review`, Rune:

1. **Detects scope** — classifies changed files by extension
2. **Selects Ash** — picks the right reviewers (2-8 Ashes)
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

Unlike `/rune:review` (changed files only), `/rune:audit` does not require git. Each Ash's context budget limits how many files it processes, prioritized by architectural importance.

## Plan Mode

When you run `/rune:plan`, Rune orchestrates a multi-agent research pipeline:

1. **Gathers input** — runs interactive brainstorm by default (auto-skips when requirements are clear)
2. **Summons research agents** — 3-5 parallel agents explore best practices, codebase patterns, framework docs, and past echoes
3. **Synthesizes findings** — lead consolidates research into a structured plan
4. **Forge Gaze enrichment** — topic-aware agent selection matches plan sections to specialized agents by default using keyword overlap scoring. 19 built-in agents (16 review + 2 research + 1 utility) with elicitation-sage integration (max 6 sages per forge session) across enrichment (~5k tokens) and research (~15k tokens) budget tiers. Use `--exhaustive` for deeper research with lower thresholds. Use `--quick` to skip forge.
5. **Reviews document** — Scroll Reviewer checks plan quality, with optional iterative refinement and technical review (decree-arbiter + knowledge-keeper)
6. **Persists learnings** — saves planning insights to Rune Echoes

Output: `plans/YYYY-MM-DD-{type}-{feature-name}-plan.md`

## Work Mode

When you run `/rune:work`, Rune parses a plan into tasks and summons self-organizing swarm workers:

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

When the `codex` CLI is installed, Rune automatically detects it and adds **Codex Oracle** as a 6th built-in Ash. Codex Oracle provides cross-model verification — a second AI perspective (GPT-5.3-codex) alongside Claude Code's review agents — catching issues that single-model blind spots miss.

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
  model: "gpt-5.3-codex"           # Codex model (gpt-5-codex, gpt-5.2-codex, gpt-5.3-codex)
  reasoning: "high"                 # Reasoning effort (high, medium, low)
  sandbox: "read-only"              # Sandbox mode (always read-only for review)
  context_budget: 20                # Max files to review (default: 20)
  confidence_threshold: 80          # Min confidence to report finding (default: 80)
  workflows: [review, audit, plan, forge, work]  # Which workflows use Codex Oracle
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
2. Run `/rune:review` or `/rune:audit` — agents persist high-confidence findings
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
| Pattern Weaver | Quality patterns | Always |
| Glyph Scribe | Frontend review | Frontend files changed |
| Knowledge Keeper | Docs review | Docs changed (>= 10 lines) |
| Codex Oracle | Cross-model review (GPT-5.3-codex) | `codex` CLI available |

Each Ash embeds several review agents as specialized perspectives. For example, Forge Warden embeds rune-architect, ember-oracle, flaw-hunter, mimic-detector, type-warden, depth-seer, blight-seer, and forge-keeper. Ward Sentinel embeds ward-sentinel and related security-focused agents. This composite design lets each Ash apply multiple lenses to the same code in a single pass.

## Agents

### Review Agents

16 specialized agents that Ash embed as perspectives:

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

### Research Agents

Summoned during `/rune:plan` for parallel research:

| Agent | Purpose |
|-------|---------|
| practice-seeker | External best practices and industry patterns |
| repo-surveyor | Codebase exploration and pattern discovery |
| lore-scholar | Framework documentation and API research |
| git-miner | Git history analysis and code archaeology |
| echo-reader | Reads past Rune Echoes for relevant learnings |

### Work Agents

Summoned during `/rune:work` as self-organizing swarm workers:

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

## Skills

| Skill | Purpose |
|-------|---------|
| arc | End-to-end orchestration pipeline (pre-flight freshness gate + 14 phases: forge → plan review → plan refinement → verification → semantic verification → work → gap analysis → codex gap analysis → code review → mend → verify mend → audit → ship → merge) |
| ash-guide | Agent invocation reference |
| chome-pattern | CLAUDE_CONFIG_DIR resolution for multi-account support |
| codex-cli | Canonical Codex CLI integration — detection, execution, error handling, talisman config |
| context-weaving | Context overflow/rot prevention |
| elicitation | BMAD-derived structured reasoning methods (Tree of Thoughts, Pre-mortem, Red Team, 5 Whys, etc.) with phase-aware auto-selection |
| goldmask | Cross-layer impact analysis (Impact + Wisdom + Lore layers) |
| polling-guard | Monitoring loop fidelity — correct waitForCompletion translation |
| roundtable-circle | Review orchestration (7-phase lifecycle) |
| rune-echoes | Smart Memory Lifecycle (3-layer project memory) |
| rune-orchestration | Multi-agent coordination patterns |
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
  max_ashes: 8                   # Hard cap (6 built-in + custom)

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

**Arc Pipeline** — End-to-end orchestration across 14 phases with checkpoint-based resume, per-phase tool restrictions, convergence gate (regression detection + retry loop), time budgets, auto PR creation (ship), and auto merge with pre-merge checklist.

**Mend** — Parallel finding resolution from TOME with restricted fixers, centralized ward check, and post-ward doc-consistency scan that fixes drift between source-of-truth files and their downstream targets.

**Plan Section Convention** — Plans with pseudocode must include contract headers (Inputs/Outputs/Preconditions/Error handling) before code blocks. Phase 2.7 verification gate enforces this. Workers implement from contracts, not by copying pseudocode verbatim.

**Forge Gaze** — Topic-aware agent selection for plan enrichment (default in `/rune:plan` and `/rune:forge`). Matches plan section topics to specialized agents via keyword overlap scoring. Configurable thresholds and budget tiers.

**Rune Echoes** — Project-level agent memory with 3-layer lifecycle. Agents learn across sessions without explicit compound workflows.

## File Structure

```
plugins/rune/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── investigation/   # 8 impact/wisdom/lore agents (Goldmask v2)
│   ├── review/          # 16 review agents
│   │   └── references/  # Shared review checklists
│   ├── research/        # 5 research agents (plan pipeline)
│   ├── work/            # 2 swarm workers (work pipeline)
│   └── utility/         # Runebinder, decree-arbiter, truthseer-validator, flow-seer, scroll-reviewer, mend-fixer, knowledge-keeper, elicitation-sage
├── commands/
│   ├── cancel-arc.md    # /rune:cancel-arc
│   ├── forge.md         # /rune:forge
│   ├── mend.md          # /rune:mend
│   ├── plan.md          # /rune:plan
│   ├── work.md          # /rune:work
│   ├── review.md        # /rune:review
│   ├── cancel-review.md # /rune:cancel-review
│   ├── audit.md         # /rune:audit
│   ├── cancel-audit.md  # /rune:cancel-audit
│   ├── elicit.md        # /rune:elicit
│   ├── echoes.md        # /rune:echoes
│   └── rest.md          # /rune:rest
├── skills/
│   ├── arc/                 # /rune:arc (end-to-end pipeline)
│   │   ├── SKILL.md
│   │   └── references/      # Arc-specific phase refs, delegation checklist
│   ├── ash-guide/           # Agent reference
│   ├── chome-pattern/       # CLAUDE_CONFIG_DIR resolution
│   ├── codex-cli/           # Codex CLI integration
│   ├── context-weaving/     # Context management
│   ├── elicitation/         # BMAD-derived reasoning methods
│   │   └── references/      # methods.csv, examples.md, phase-mapping.md
│   ├── goldmask/            # Cross-layer impact analysis
│   ├── polling-guard/       # Monitoring loop fidelity
│   ├── roundtable-circle/   # Review orchestration
│   │   └── references/      # e.g. rune-gaze.md, custom-ashes.md
│   ├── rune-echoes/         # Smart Memory Lifecycle
│   ├── rune-orchestration/  # Core coordination
│   │   └── references/      # e.g. team-lifecycle-guard.md
│   └── zsh-compat/          # zsh shell compatibility
├── talisman.example.yml
├── CLAUDE.md
├── LICENSE
└── README.md
```

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
- **No incremental audit** — `/rune:audit` scans all files each run. There is no diff-based "only audit what changed since last audit" mode yet.
- **Concurrent sessions** — Only one `/rune:review`, `/rune:audit`, or `/rune:arc` can run at a time. Use `/rune:cancel-review`, `/rune:cancel-audit`, or `/rune:cancel-arc` to stop an active session.
- **Manual cleanup optional** — Run `/rune:rest` to remove `tmp/` artifacts, or let the OS handle them.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Agent Teams not available" | Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your shell profile |
| Ash times out (>5 min) | Rune proceeds with partial results. Check TOME.md for coverage gaps |
| "Concurrent review running" | Run `/rune:cancel-review` first, then retry |
| Echo files causing merge conflicts | Add `.gitattributes` with `merge=union` for echo paths (see Configuration) |
| No files to review | Ensure you have uncommitted changes on a feature branch (not main) |
| `/rune:work` stalled workers | Workers are warned at 5 minutes and auto-released at 10 minutes. Lead re-assigns stuck tasks |

## Security

- Agent prompts include Truthbinding anchors to resist prompt injection
- Review output in `tmp/` is ephemeral and not committed
- `.gitignore` excludes `.claude/echoes/` by default (opt-in to version control)
- Sensitive data filter rejects API keys, passwords, tokens from echo entries
- All findings require verified evidence from source code

## Requirements

- Claude Code with Agent Teams support
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable enabled
- **Optional**: `codex` CLI for cross-model verification (`npm install -g @openai/codex`)

## License

MIT

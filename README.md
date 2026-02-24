# Rune

**Multi-agent engineering orchestration for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).**

Plan, implement, review, test, and audit your codebase using coordinated Agent Teams — each teammate with its own dedicated context window.

[![Version](https://img.shields.io/badge/version-1.92.0-blue)](.claude-plugin/marketplace.json)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Agents](https://img.shields.io/badge/agents-82-purple)](#agents)
[![Skills](https://img.shields.io/badge/skills-33-orange)](#skills)

---

## Install

```bash
/plugin marketplace add https://github.com/vinhnxv/rune-plugin
/plugin install rune
```

Restart Claude Code after installation.

<details>
<summary>Local development</summary>

```bash
claude --plugin-dir /path/to/rune-plugin
```
</details>

---

## How It Works

Rune orchestrates **multi-agent workflows** where specialized AI teammates collaborate through shared task lists and file-based communication. Instead of one agent doing everything in a single context window, Rune splits work across purpose-built agents — each with its own full context window.

```
You ──► /rune:devise ──► Plan
                           │
         /rune:arc ◄───────┘
             │
             ├─ Forge & Validate     enrich plan, review architecture, refine
             ├─ Work                 swarm workers implement in parallel
             ├─ Gap Analysis         detect and remediate implementation gaps
             ├─ Review & Mend        multi-agent code review + auto-fix findings
             ├─ Test                 3-tier testing (unit → integration → E2E)
             ├─ Ship                 validate and create PR
             └─ Merge               rebase and merge
```

---

## Workflows

### Quick Start (New Users)

| Command | What it does | Alias for |
|---------|-------------|-----------|
| `/rune:plan` | Plan a feature or task | `/rune:devise` |
| `/rune:work` | Implement a plan with AI workers | `/rune:strive` |
| `/rune:review` | Review your code changes | `/rune:appraise` |

### Core Commands

| Command | What it does | Agents |
|---------|-------------|--------|
| [`/rune:devise`](#devise) | Turn ideas into structured plans with parallel research | up to 7 |
| [`/rune:strive`](#strive) | Execute plans with self-organizing swarm workers | 2-6 |
| [`/rune:appraise`](#appraise) | Multi-agent code review on your diff | up to 8 |
| [`/rune:audit`](#audit) | Full codebase audit with specialized reviewers | up to 8 |
| [`/rune:arc`](#arc) | End-to-end pipeline: plan → work → review → test → ship | varies |
| [`/rune:mend`](#mend) | Parallel resolution of review findings | 1-5 |
| [`/rune:forge`](#forge) | Deepen a plan with topic-aware research enrichment | 3-12 |
| [`/rune:goldmask`](#goldmask) | Impact analysis — what breaks if you change this? | 8 |
| [`/rune:inspect`](#inspect) | Plan-vs-implementation gap audit (9 dimensions) | 4 |
| [`/rune:elicit`](#elicit) | Structured reasoning (Tree of Thoughts, Pre-mortem, 5 Whys) | 0 |

### Batch & Automation

| Command | What it does |
|---------|-------------|
| `/rune:arc-batch` | Run `/rune:arc` across multiple plans sequentially |
| `/rune:arc-issues` | Fetch GitHub issues by label, generate plans, run arc for each |
| `/rune:arc-hierarchy` | Execute hierarchical parent/child plan decompositions |

### Utilities

| Command | What it does |
|---------|-------------|
| `/rune:rest` | Clean up `tmp/` artifacts from completed workflows |
| `/rune:echoes` | Manage persistent agent memory (show, prune, reset) |
| `/rune:file-todos` | Structured file-based todo tracking with YAML frontmatter |
| `/rune:cancel-arc` | Gracefully stop a running arc pipeline |
| `/rune:cancel-review` | Stop an active code review |
| `/rune:cancel-audit` | Stop an active audit |

---

## Workflow Details

### <a name="devise"></a> `/rune:devise` — Planning

Transforms a feature idea into a structured plan through a multi-phase pipeline:

1. **Brainstorm** — structured exploration with elicitation methods
2. **Research** — parallel agents scan your repo, git history, echoes, and external docs
3. **Solution Arena** — competing approaches evaluated on weighted dimensions
4. **Synthesize** — consolidate findings into a plan document
5. **Predictive Goldmask** — risk scoring for files the plan will touch
6. **Forge** — topic-aware enrichment by specialist agents
7. **Review** — automated verification + optional technical review

```bash
/rune:devise                  # Full pipeline
/rune:devise --quick          # Skip brainstorm + forge (faster)
```

Output: `plans/YYYY-MM-DD-{type}-{name}-plan.md`

### <a name="arc"></a> `/rune:arc` — End-to-End Pipeline

The full pipeline from plan to merged PR, with 18 phases:

```
Forge → Plan Review → Refinement → Verification → Semantic Verification
  → Work → Gap Analysis → Codex Gap Analysis → Gap Remediation
  → Goldmask Verification → Code Review → Goldmask Correlation
  → Mend → Verify Mend → Test → Pre-Ship Validation → Ship → Merge
```

```bash
/rune:arc plans/my-plan.md
/rune:arc plans/my-plan.md --resume        # Resume from checkpoint
/rune:arc plans/my-plan.md --no-forge      # Skip forge enrichment
/rune:arc plans/my-plan.md --skip-freshness  # Bypass plan freshness check
```

Features: checkpoint-based resume, adaptive review-mend convergence loop (3 tiers: LIGHT/STANDARD/THOROUGH), diff-scoped review, co-author propagation.

### <a name="strive"></a> `/rune:strive` — Swarm Execution

Self-organizing workers parse a plan into tasks and claim them independently:

```bash
/rune:strive plans/my-plan.md
/rune:strive plans/my-plan.md --approve    # Require human approval per task
```

### <a name="appraise"></a> `/rune:appraise` — Code Review

Multi-agent review of your git diff with up to 8 specialized Ashes:

```bash
/rune:appraise                # Standard review
/rune:appraise --deep         # Multi-wave deep review (up to 18 Ashes across 3 waves)
```

Built-in reviewers include: Ward Sentinel (security), Pattern Seer (consistency), Flaw Hunter (logic bugs), Ember Oracle (performance), Depth Seer (missing logic), and more. Stack-aware intelligence auto-adds specialist reviewers based on your tech stack.

### <a name="audit"></a> `/rune:audit` — Codebase Audit

Full-scope analysis of your entire codebase (not just the diff):

```bash
/rune:audit                   # Deep audit (default)
/rune:audit --standard        # Standard depth
/rune:audit --deep            # Multi-wave investigation
/rune:audit --incremental     # Stateful audit with priority scoring and coverage tracking
```

### <a name="mend"></a> `/rune:mend` — Fix Findings

Parse a TOME (aggregated review findings) and dispatch parallel fixers:

```bash
/rune:mend tmp/reviews/{id}/TOME.md
```

### <a name="forge"></a> `/rune:forge` — Plan Enrichment

Deepen a plan with Forge Gaze — topic-aware agent matching that selects the best specialists for each section:

```bash
/rune:forge plans/my-plan.md
/rune:forge plans/my-plan.md --exhaustive  # Lower threshold, more agents
```

### <a name="goldmask"></a> `/rune:goldmask` — Impact Analysis

Three-layer analysis: **Impact** (what changes), **Wisdom** (why it was written that way), **Lore** (how risky the area is):

```bash
/rune:goldmask                # Analyze current diff
```

### <a name="inspect"></a> `/rune:inspect` — Gap Audit

Compares a plan against its implementation across 9 quality dimensions:

```bash
/rune:inspect plans/my-plan.md
/rune:inspect plans/my-plan.md --focus "auth module"
```

### <a name="elicit"></a> `/rune:elicit` — Structured Reasoning

24 curated methods for structured thinking: Tree of Thoughts, Pre-mortem Analysis, Red Team vs Blue Team, 5 Whys, ADR, and more.

```bash
/rune:elicit
```

---

## Agents

**82 specialized agents** across 6 categories:

### Review Agents (37)

Core reviewers that participate in `/rune:appraise` and `/rune:audit`:

| Agent | Focus |
|-------|-------|
| Ward Sentinel | Security (OWASP Top 10, auth, secrets) |
| Pattern Seer | Cross-cutting consistency (naming, error handling, API design) |
| Flaw Hunter | Logic bugs (null handling, race conditions, silent failures) |
| Ember Oracle | Performance (N+1 queries, algorithmic complexity) |
| Depth Seer | Missing logic (error handling gaps, state machine incompleteness) |
| Void Analyzer | Incomplete implementations (TODOs, stubs, placeholders) |
| Wraith Finder | Dead code (unused exports, orphaned files, unwired DI) |
| Tide Watcher | Async/concurrency (waterfall awaits, race conditions) |
| Forge Keeper | Data integrity (migration safety, transaction boundaries) |
| Trial Oracle | Test quality (TDD compliance, assertion quality) |
| Simplicity Warden | Over-engineering (YAGNI violations, premature abstractions) |
| Rune Architect | Architecture (layer boundaries, SOLID, dependency direction) |
| Mimic Detector | Code duplication (DRY violations) |
| Blight Seer | Design anti-patterns (God Service, leaky abstractions) |
| Refactor Guardian | Refactoring completeness (orphaned callers, broken imports) |
| Reference Validator | Import paths and config reference correctness |
| Phantom Checker | Dynamic references (getattr, decorators, string dispatch) |
| Naming Intent Analyzer | Name-behavior mismatches |
| Type Warden | Type safety (mypy strict, modern Python idioms) |
| Doubt Seer | Cross-agent claim verification |
| Assumption Slayer | Premise validation (solving the right problem?) |
| Reality Arbiter | Production viability (works in isolation vs. real conditions) |
| Entropy Prophet | Long-term consequence prediction |
| Schema Drift Detector | Schema drift between migrations and ORM/model definitions |
| Agent Parity Reviewer | Agent-native parity, orphan features, context starvation |
| Senior Engineer Reviewer | Persona-based senior engineer review, production thinking |

**Stack Specialists** (auto-activated by detected tech stack):

| Agent | Stack |
|-------|-------|
| Python Reviewer | Python 3.10+ (type hints, async, Result patterns) |
| TypeScript Reviewer | Strict TypeScript (discriminated unions, exhaustive matching) |
| Rust Reviewer | Rust (ownership, unsafe, tokio) |
| PHP Reviewer | PHP 8.1+ (type declarations, enums, readonly) |
| FastAPI Reviewer | FastAPI (Pydantic, IDOR, dependency injection) |
| Django Reviewer | Django + DRF (ORM, CSRF, admin, migrations) |
| Laravel Reviewer | Laravel (Eloquent, Blade, middleware, gates) |
| SQLAlchemy Reviewer | SQLAlchemy (async sessions, N+1, eager loading) |
| TDD Compliance Reviewer | TDD practices (test-first, coverage, assertion quality) |
| DDD Reviewer | Domain-Driven Design (aggregates, bounded contexts) |
| DI Reviewer | Dependency Injection (scope, circular deps, service locator) |

### Investigation Agents (23)

Used by `/rune:goldmask`, `/rune:inspect`, and `/rune:audit --deep`:

| Category | Agents |
|----------|--------|
| Impact Tracers | API Contract, Business Logic, Data Layer, Config Dependency, Event Message |
| Quality Inspectors | Grace Warden, Ruin Prophet, Sight Oracle, Vigil Keeper |
| Deep Analysis | Breach Hunter, Decay Tracer, Decree Auditor, Ember Seer, Fringe Watcher, Order Auditor, Rot Seeker, Ruin Watcher, Signal Watcher, Strand Tracer, Truth Seeker |
| Synthesis | Goldmask Coordinator, Lore Analyst, Wisdom Sage |

### Research Agents (5)

| Agent | Purpose |
|-------|---------|
| Repo Surveyor | Codebase structure and pattern analysis |
| Echo Reader | Surfaces relevant past learnings from Rune Echoes |
| Git Miner | Git archaeology — commit history, contributors, code evolution |
| Lore Scholar | Framework docs via Context7 MCP + web search fallback |
| Practice Seeker | External best practices and industry patterns |

### Work Agents (2)

| Agent | Purpose |
|-------|---------|
| Rune Smith | TDD-driven code implementation |
| Trial Forger | Test generation following project patterns |

### Utility Agents (11)

| Agent | Purpose |
|-------|---------|
| Runebinder | Aggregates multi-agent review outputs into TOME |
| Mend Fixer | Applies targeted code fixes for review findings |
| Elicitation Sage | Structured reasoning method execution |
| Scroll Reviewer | Document quality review |
| Flow Seer | Feature spec analysis for completeness |
| Decree Arbiter | Technical soundness validation |
| Knowledge Keeper | Documentation coverage review |
| Horizon Sage | Strategic depth assessment |
| Veil Piercer | Plan reality-gap analysis |
| Truthseer Validator | Audit coverage quality validation |
| Deployment Verifier | Deployment artifact generation (Go/No-Go checklists, rollback plans) |

### Testing Agents (4)

| Agent | Purpose |
|-------|---------|
| Unit Test Runner | Diff-scoped unit test execution |
| Integration Test Runner | API, database, and business logic tests |
| E2E Browser Tester | Browser automation via agent-browser CLI |
| Test Failure Analyst | Root cause analysis of test failures |

---

## Skills

33 skills providing background knowledge, workflow orchestration, and tool integration:

| Skill | Type | Purpose |
|-------|------|---------|
| `devise` | Workflow | Multi-agent planning pipeline |
| `strive` | Workflow | Swarm work execution |
| `appraise` | Workflow | Multi-agent code review |
| `audit` | Workflow | Full codebase audit |
| `arc` | Workflow | End-to-end pipeline orchestration |
| `arc-batch` | Workflow | Sequential batch arc execution |
| `arc-hierarchy` | Workflow | Hierarchical plan execution |
| `arc-issues` | Workflow | GitHub Issues-driven batch arc |
| `forge` | Workflow | Plan enrichment with Forge Gaze |
| `goldmask` | Workflow | Cross-layer impact analysis |
| `inspect` | Workflow | Plan-vs-implementation gap audit |
| `mend` | Workflow | Parallel finding resolution |
| `elicitation` | Reasoning | 24 structured reasoning methods |
| `roundtable-circle` | Orchestration | Review/audit 7-phase lifecycle |
| `rune-orchestration` | Orchestration | Core coordination patterns |
| `context-weaving` | Orchestration | Context overflow prevention |
| `rune-echoes` | Memory | 5-tier persistent agent memory |
| `stacks` | Intelligence | Stack-aware detection and routing |
| `inner-flame` | Quality | Universal self-review protocol |
| `ash-guide` | Reference | Agent invocation guide |
| `using-rune` | Reference | Workflow discovery and routing |
| `codex-cli` | Integration | Cross-model verification |
| `testing` | Testing | 3-tier test orchestration |
| `agent-browser` | Testing | E2E browser automation knowledge |
| `systematic-debugging` | Debugging | 4-phase debugging methodology |
| `file-todos` | Tracking | Structured file-based todos |
| `git-worktree` | Isolation | Worktree-based parallel execution |
| `polling-guard` | Reliability | Monitoring loop fidelity |
| `zsh-compat` | Compatibility | macOS zsh shell safety |
| `chome-pattern` | Compatibility | Multi-account config resolution |
| `resolve-gh-pr-comment` | Workflow | Resolve a single GitHub PR review comment |
| `resolve-all-gh-pr-comments` | Workflow | Batch resolve all open PR review comments |
| `skill-testing` | Development | TDD for skill development |

---

## Configuration

Rune is configured via `talisman.yml`:

```bash
# Project-level (highest priority)
.claude/talisman.yml

# User-global
~/.claude/talisman.yml
```

<details>
<summary>Example configuration</summary>

```yaml
version: 1

# Review settings
review:
  max_ashes: 7                  # Max concurrent review agents
  max_cli_ashes: 2              # Max external-model agents

# Stack-aware intelligence
stack_awareness:
  enabled: true                 # Auto-detect tech stack
  confidence_threshold: 0.6     # Minimum confidence for stack detection

# Arc pipeline
arc:
  timeouts:
    forge: 600000               # 10 min
    work: 1800000               # 30 min
    review: 600000              # 10 min

# Goldmask impact analysis
goldmask:
  enabled: true
  devise:
    enabled: true
    depth: basic                # basic | enhanced | full

# Elicitation methods
elicitation:
  enabled: true

# Custom Ashes
ashes:
  custom:
    - name: "my-reviewer"
      agent: "my-custom-agent"
      source: ".claude/agents/my-custom-agent.md"
```
</details>

See [`talisman.example.yml`](plugins/rune/talisman.example.yml) for the full schema with all options.

---

## Architecture

```
rune-plugin/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace registry
└── plugins/
    └── rune/                     # Main plugin
        ├── .claude-plugin/
        │   └── plugin.json       # Plugin manifest (v1.91.0)
        ├── agents/               # 82 agent definitions
        │   ├── review/           #   37 review agents
        │   ├── investigation/    #   23 investigation agents
        │   ├── utility/          #   11 utility agents
        │   ├── research/         #    5 research agents
        │   ├── testing/          #    4 testing agents
        │   └── work/             #    2 work agents
        ├── skills/               # 33 skills
        ├── commands/             # 14 slash commands
        ├── hooks/                # Event-driven hooks
        │   └── hooks.json
        ├── scripts/              # Hook scripts (20+)
        ├── .mcp.json             # MCP server config (echo-search)
        ├── talisman.example.yml  # Configuration reference
        ├── CLAUDE.md             # Plugin instructions
        ├── CHANGELOG.md
        └── README.md             # Detailed component reference
```

### Key Concepts

| Term | Meaning |
|------|---------|
| **Tarnished** | The orchestrator/lead agent that coordinates workflows |
| **Ash** | Any teammate agent (reviewer, worker, researcher) |
| **TOME** | Aggregated findings document from a review |
| **Talisman** | Configuration file (`talisman.yml`) |
| **Forge Gaze** | Topic-aware agent matching for plan enrichment |
| **Rune Echoes** | 5-tier persistent agent memory (`.claude/echoes/`) |
| **Inscription** | Contract file (`inscription.json`) for agent coordination |
| **Seal** | Deterministic completion marker emitted by Ashes |

---

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with plugin support
- **Claude Max ($200/month) or higher recommended**

> [!WARNING]
> **Rune is token-intensive.** Each workflow spawns multiple agents with their own dedicated context windows. A single `/rune:arc` run can consume a significant portion of your weekly usage. Use `--dry-run` where available to preview scope before committing.

---

## Links

- [Detailed component reference](plugins/rune/README.md) — all agents, skills, commands, hooks
- [Rune user guide (English): arc + arc-batch](docs/guides/rune-arc-and-batch-guide.en.md) — operational guide with greenfield/brownfield use cases
- [Hướng dẫn Rune (Tiếng Việt): arc + arc-batch](docs/guides/rune-arc-and-batch-guide.vi.md) — hướng dẫn vận hành kèm use case greenfield/brownfield
- [Rune planning guide (English): devise + forge + plan-review + inspect](docs/guides/rune-planning-and-plan-quality-guide.en.md) — how to write and validate plan files correctly
- [Hướng dẫn planning Rune (Tiếng Việt): devise + forge + plan-review + inspect](docs/guides/rune-planning-and-plan-quality-guide.vi.md) — cách lập plan và review plan đúng chuẩn
- [Rune code review and audit guide (English): appraise + audit + mend](docs/guides/rune-code-review-and-audit-guide.en.md) — multi-agent review, codebase audit, and finding resolution
- [Hướng dẫn review và audit Rune (Tiếng Việt): appraise + audit + mend](docs/guides/rune-code-review-and-audit-guide.vi.md) — review đa agent, audit codebase, và xử lý finding
- [Rune work execution guide (English): strive + goldmask](docs/guides/rune-work-execution-guide.en.md) — swarm implementation and impact analysis
- [Hướng dẫn thực thi Rune (Tiếng Việt): strive + goldmask](docs/guides/rune-work-execution-guide.vi.md) — implementation swarm và phân tích tác động
- [Rune advanced workflows guide (English): arc-hierarchy + arc-issues + echoes](docs/guides/rune-advanced-workflows-guide.en.md) — hierarchical execution, GitHub Issues batch, and agent memory
- [Hướng dẫn workflow nâng cao Rune (Tiếng Việt): arc-hierarchy + arc-issues + echoes](docs/guides/rune-advanced-workflows-guide.vi.md) — thực thi phân cấp, batch GitHub Issues, và bộ nhớ agent
- [Changelog](plugins/rune/CHANGELOG.md) — release history
- [Configuration guide](plugins/rune/talisman.example.yml) — full talisman schema

---

## License

[MIT](LICENSE)

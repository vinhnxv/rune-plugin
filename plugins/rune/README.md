# Rune

Multi-agent engineering orchestration for [Claude Code](https://claude.ai/claude-code). Plan, work, review, and audit using Agent Teams.

Each Runebearer teammate gets its own 200k context window, eliminating single-context bottlenecks.

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

## Quick Start

```bash
# Plan a feature with parallel research agents
/rune:plan
/rune:plan --brainstorm        # Start with interactive brainstorm
/rune:plan --deep              # Include deep section-level research

# Execute a plan with swarm workers
/rune:work plans/feat-user-auth-plan.md

# Run a multi-agent code review (changed files only)
/rune:review

# Run a full codebase audit (all files)
/rune:audit
/rune:audit --focus security    # Security-only audit
/rune:audit --max-agents 3      # Limit to 3 Runebearers

# Preview scope without spawning agents
/rune:review --dry-run
/rune:audit --dry-run

# Cancel an active review or audit
/rune:cancel-review
/rune:cancel-audit

# Clean up tmp/ artifacts from completed workflows
/rune:cleanup
/rune:cleanup --dry-run       # Preview what would be removed

# Manage agent memory
/rune:echoes show     # View memory state
/rune:echoes init     # Initialize memory for this project
/rune:echoes prune    # Prune stale entries
```

## What It Does

When you run `/rune:review`, Rune:

1. **Detects scope** — classifies changed files by extension
2. **Selects Runebearers** — picks the right reviewers (2-5 teammates)
3. **Spawns Agent Teams** — each reviewer gets its own 200k context window
4. **Reviews in parallel** — Runebearers review simultaneously, writing to files
5. **Aggregates findings** — Runebinder deduplicates and prioritizes
6. **Verifies evidence** — Truthsight validates P1 findings against source
7. **Presents TOME** — unified review summary

## Audit Mode

When you run `/rune:audit`, Rune scans your entire codebase instead of just changed files:

1. **Scans codebase** — finds all project files (excluding binaries, lock files, build output)
2. **Classifies files** — same Rune Gaze extension-based classification
3. **Selects Runebearers** — same 2-5 Runebearer selection
4. **Audits in parallel** — each Runebearer gets capped context budget, prioritized by importance
5. **Aggregates findings** — Runebinder deduplicates and prioritizes
6. **Presents TOME** — unified audit summary with coverage gaps

Unlike `/rune:review` (changed files only), `/rune:audit` does not require git. Each Runebearer's context budget limits how many files it processes, prioritized by architectural importance.

## Plan Mode

When you run `/rune:plan`, Rune orchestrates a multi-agent research pipeline:

1. **Gathers input** — accepts a feature description or runs interactive brainstorm (`--brainstorm`)
2. **Spawns research agents** — 3-5 parallel agents explore best practices, codebase patterns, framework docs, and past echoes
3. **Synthesizes findings** — lead consolidates research into a structured plan
4. **Deepens sections** — optional parallel deep-dive per section (`--deep`)
5. **Reviews document** — Scroll Reviewer checks plan quality
6. **Persists learnings** — saves planning insights to Rune Echoes

Output: `plans/{type}-{feature-name}-plan.md`

## Work Mode

When you run `/rune:work`, Rune parses a plan into tasks and spawns self-organizing swarm workers:

1. **Parses plan** — extracts tasks with dependencies from checkbox items or numbered lists
2. **Creates task pool** — TaskCreate with dependency chains (blockedBy)
3. **Spawns workers** — Rune Smiths (implementation) and Trial Forgers (tests) claim tasks independently
4. **Monitors progress** — polls TaskList, detects stalled workers, releases stuck tasks
5. **Runs quality gates** — auto-discovers wards from Makefile, package.json, pyproject.toml
6. **Persists learnings** — saves implementation patterns to Rune Echoes

Workers scale automatically based on task count (1-5 tasks: 2 workers, 20+ tasks: 5 workers).

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

## Runebearers

| Runebearer | Role | When Active |
|-----------|------|-------------|
| Forge Warden | Backend review | Backend files changed |
| Ward Sentinel | Security review | Always |
| Pattern Weaver | Quality patterns | Always |
| Glyph Scribe | Frontend review | Frontend files changed |
| Lore Keeper | Docs review | Docs changed (>= 10 lines) |

## Agents

### Review Agents

10 specialized agents that Runebearers embed as perspectives:

| Agent | Focus |
|-------|-------|
| ward-sentinel | Security, OWASP, auth |
| forge-oracle | Performance, N+1, complexity |
| rune-architect | Architecture, layer boundaries |
| simplicity-warden | YAGNI, over-engineering |
| flaw-hunter | Logic bugs, edge cases |
| echo-detector | Code duplication |
| pattern-seer | Pattern consistency |
| void-analyzer | Incomplete implementations |
| orphan-finder | Dead code |
| phantom-checker | Dynamic references |

### Research Agents

Spawned during `/rune:plan` for parallel research:

| Agent | Purpose |
|-------|---------|
| lore-seeker | External best practices and industry patterns |
| realm-analyst | Codebase exploration and pattern discovery |
| codex-scholar | Framework documentation and API research |
| chronicle-miner | Git history analysis and code archaeology |
| echo-reader | Reads past Rune Echoes for relevant learnings |

### Work Agents

Spawned during `/rune:work` as self-organizing swarm workers:

| Agent | Purpose |
|-------|---------|
| rune-smith | Code implementation (TDD-aware, claims tasks from pool) |
| trial-forger | Test generation (follows existing test patterns) |

### Utility Agents

| Agent | Purpose |
|-------|---------|
| runebinder | Aggregates Runebearer findings into TOME.md |
| truthseer-validator | Audit coverage validation (Phase 5.5, >100 files) |
| flow-seer | Spec flow analysis and gap detection |
| scroll-reviewer | Document quality review |

## Skills

| Skill | Purpose |
|-------|---------|
| rune-orchestration | Multi-agent coordination patterns |
| context-weaving | Context overflow/rot prevention |
| rune-circle | Review orchestration (7-phase lifecycle) |
| rune-echoes | Smart Memory Lifecycle (3-layer project memory) |
| runebearer-guide | Agent invocation reference |

## Configuration

Override file classification defaults in your project:

```yaml
# .claude/rune-config.yml
rune-gaze:
  backend_extensions: [.py, .go]
  frontend_extensions: [.tsx, .ts]
  skip_patterns: ["**/migrations/**"]
  always_review: ["CLAUDE.md", ".claude/**/*.md"]

runebearers:
  custom:                              # Extend built-in Runebearers with your own
    - name: "my-reviewer"
      agent: "my-reviewer"             # .claude/agents/my-reviewer.md
      source: local
      workflows: [review]
      trigger:
        extensions: [".py"]
      context_budget: 20
      finding_prefix: "MYR"

settings:
  max_runebearers: 8                   # Hard cap (5 built-in + custom)

echoes:
  version_controlled: false  # Set to true to track echoes in git

work:
  ward_commands:               # Override quality gate commands
    - "make check"
    - "npm test"
  max_workers: 3               # Max parallel swarm workers
```

See [`rune-config.example.yml`](rune-config.example.yml) for the full configuration schema including custom Runebearers, trigger matching, and dedup hierarchy.

## Key Concepts

**Truthbinding Protocol** — All agent prompts include anti-injection anchors. Agents ignore instructions embedded in reviewed code.

**Rune Traces** — Every finding must include actual code snippets from source files. No paraphrasing.

**Glyph Budget** — Agents write findings to files and return only a 1-sentence summary to the lead. Prevents context overflow.

**Inscription Protocol** — JSON contract defining what each agent must produce, enabling automated validation.

**TOME** — The unified review summary after deduplication and prioritization.

**Rune Echoes** — Project-level agent memory with 3-layer lifecycle. Agents learn across sessions without explicit compound workflows.

## File Structure

```
plugins/rune/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── review/          # 10 review agents
│   ├── research/        # 5 research agents (plan pipeline)
│   ├── work/            # 2 swarm workers (work pipeline)
│   └── utility/         # Runebinder, truthseer-validator, flow-seer, scroll-reviewer
├── commands/
│   ├── plan.md          # /rune:plan
│   ├── work.md          # /rune:work
│   ├── review.md        # /rune:review
│   ├── cancel-review.md # /rune:cancel-review
│   ├── audit.md         # /rune:audit
│   ├── cancel-audit.md  # /rune:cancel-audit
│   ├── echoes.md        # /rune:echoes
│   └── cleanup.md       # /rune:cleanup
├── skills/
│   ├── rune-orchestration/  # Core coordination
│   ├── context-weaving/     # Context management
│   ├── rune-circle/         # Review orchestration
│   │   └── references/      # e.g. rune-gaze.md, custom-runebearers.md
│   ├── rune-echoes/         # Smart Memory Lifecycle
│   └── runebearer-guide/    # Agent reference
├── docs/
│   └── specflow-findings.md
├── CLAUDE.md
├── LICENSE
└── README.md
```

## Known Limitations

- **Agent Teams is experimental** — Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable. Behavior may change across Claude Code releases.
- **Context budget caps** — Each Runebearer can review a limited number of files (20-30). Large codebases will have coverage gaps reported in the TOME.
- **No incremental audit** — `/rune:audit` scans all files each run. There is no diff-based "only audit what changed since last audit" mode yet.
- **Concurrent sessions** — Only one `/rune:review` or `/rune:audit` can run at a time. Use `/rune:cancel-review` or `/rune:cancel-audit` to stop an active session.
- **Manual cleanup optional** — Run `/rune:cleanup` to remove `tmp/` artifacts, or let the OS handle them.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Agent Teams not available" | Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your shell profile |
| Runebearer times out (>5 min) | Rune proceeds with partial results. Check TOME.md for coverage gaps |
| "Concurrent review running" | Run `/rune:cancel-review` first, then retry |
| Echo files causing merge conflicts | Add `.gitattributes` with `merge=union` for echo paths (see Configuration) |
| No files to review | Ensure you have uncommitted changes on a feature branch (not main) |
| `/rune:work` stalled workers | Workers auto-release after 3 minutes. Lead re-assigns stuck tasks |

## Security

- Agent prompts include Truthbinding anchors to resist prompt injection
- Review output in `tmp/` is ephemeral and not committed
- `.gitignore` excludes `.claude/echoes/` by default (opt-in to version control)
- Sensitive data filter rejects API keys, passwords, tokens from echo entries
- All findings require verified evidence from source code

## Requirements

- Claude Code with Agent Teams support
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable enabled

## License

MIT

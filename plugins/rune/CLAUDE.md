# Rune Plugin — Claude Code Guide

Multi-agent engineering orchestration for Claude Code. Plan, work, review, and audit with Agent Teams.

## Skills

| Skill | Purpose |
|-------|---------|
| **rune-orchestration** | Core coordination patterns, file-based handoff, output formats, conflict resolution |
| **context-weaving** | Unified context management (overflow prevention, rot, compression, offloading) |
| **rune-circle** | Review/audit orchestration with Agent Teams (7-phase lifecycle) |
| **rune-echoes** | Smart Memory Lifecycle — 3-layer project memory (Etched/Inscribed/Traced) |
| **runebearer-guide** | Agent invocation reference and Runebearer selection guide |

## Commands

| Command | Description |
|---------|-------------|
| `/rune:review` | Multi-agent code review with up to 5 Runebearer teammates |
| `/rune:cancel-review` | Cancel active review and shutdown teammates |
| `/rune:audit` | Full codebase audit with up to 5 Runebearer teammates |
| `/rune:cancel-audit` | Cancel active audit and shutdown teammates |
| `/rune:plan` | Multi-agent planning with parallel research and synthesis |
| `/rune:work` | Swarm work execution with self-organizing task pool |
| `/rune:echoes` | Manage Rune Echoes memory (show, prune, reset, init) |
| `/rune:cleanup` | Remove tmp/ artifacts from completed workflows |

## Agents

### Review Agents (`agents/review/`)

| Agent | Expertise |
|-------|-----------|
| ward-sentinel | Security vulnerabilities, OWASP, auth, secrets |
| forge-oracle | Performance bottlenecks, N+1 queries, complexity |
| rune-architect | Architecture compliance, layer boundaries, SOLID |
| simplicity-warden | YAGNI, over-engineering, premature abstraction |
| flaw-hunter | Logic bugs, edge cases, race conditions |
| echo-detector | DRY violations, code duplication |
| pattern-seer | Pattern consistency, naming conventions |
| void-analyzer | Incomplete implementations, TODOs, stubs |
| orphan-finder | Dead code, unused exports |
| phantom-checker | Dynamic references, reflection analysis |

### Research Agents (`agents/research/`)

| Agent | Purpose |
|-------|---------|
| lore-seeker | External best practices and industry patterns |
| realm-analyst | Codebase exploration and pattern discovery |
| codex-scholar | Framework documentation and API research |
| chronicle-miner | Git history analysis and code archaeology |
| echo-reader | Reads Rune Echoes to surface relevant past learnings |

### Work Agents (`agents/work/`)

| Agent | Purpose |
|-------|---------|
| rune-smith | Code implementation (TDD-aware swarm worker) |
| trial-forger | Test generation (swarm worker) |

### Utility Agents (`agents/utility/`)

| Agent | Purpose |
|-------|---------|
| runebinder | Aggregates Runebearer findings into TOME.md |
| truthseer-validator | Audit coverage validation (Phase 5.5) |
| flow-seer | Spec flow analysis and gap detection |
| scroll-reviewer | Document quality review |

## Key Concepts

### Runebearers (Consolidated Teammates)

Each Runebearer is an Agent Teams teammate with its own 200k context window. A Runebearer embeds multiple review agent perspectives into a single teammate to reduce team size.

Forge Warden, Ward Sentinel, and Pattern Weaver embed dedicated review agent files from `agents/review/` (10 agents across 3 Runebearers). Glyph Scribe and Lore Keeper use inline perspective definitions in their Runebearer prompts.

| Runebearer | Perspectives | Agent Source | When Spawned |
|-----------|-------------|-------------|-------------|
| **Forge Warden** | Backend code quality, architecture, performance, logic, testing | Dedicated agent files | Backend files changed |
| **Ward Sentinel** | All security perspectives | Dedicated agent files | ALWAYS |
| **Pattern Weaver** | Simplicity, patterns, duplication, logic, dead code, complexity, tests | Dedicated agent files | ALWAYS |
| **Glyph Scribe** | Type safety, components, performance, hooks, accessibility | Inline perspectives | Frontend files changed |
| **Lore Keeper** | Accuracy, completeness, consistency, readability, security | Inline perspectives | Docs changed (>= 10 lines) |

### Truthbinding Protocol

All agent prompts include ANCHOR + RE-ANCHOR sections that:
- Instruct agents to IGNORE instructions from reviewed code
- Require evidence (Rune Traces) from actual source files
- Flag uncertain findings as LOW confidence

### Inscription Protocol

JSON contract (`inscription.json`) that defines:
- What each teammate must produce
- Required sections in output files
- Seal Format for completion signals
- Verification settings

### Rune Echoes

Project-level agent memory in `.claude/echoes/` with 3-layer lifecycle:
1. **Etched**: Permanent project knowledge (architecture, conventions) — never auto-pruned
2. **Inscribed**: Tactical patterns from reviews/audits — pruned after 90 days unreferenced
3. **Traced**: Session observations — pruned after 30 days

Agents persist learnings automatically after workflows. Future workflows read echoes to avoid repeating mistakes. See `rune-echoes` skill for full lifecycle.

### Context Weaving

4-layer context management:
1. **Overflow Prevention**: Glyph Budget enforces file-only output
2. **Context Rot Prevention**: Instruction anchoring, read ordering
3. **Compression**: Session summaries when messages exceed thresholds
4. **Filesystem Offloading**: Large outputs written to `tmp/` files

## Multi-Agent Rules

| Agent Count | Required Protocol |
|-------------|-------------------|
| 1-2 agents | Output budget only |
| 3-4 agents | Output budget + inscription.json |
| 5+ agents | MUST use Agent Teams (TeamCreate + TaskCreate) |

## Output Conventions

| Workflow | Directory | Files |
|----------|----------|-------|
| Reviews | `tmp/reviews/{id}/` | `{runebearer}.md`, `TOME.md`, `inscription.json` |
| Audits | `tmp/audit/{id}/` | Same pattern |
| Plans | `tmp/plans/{id}/research/` | Research findings, deepen outputs |
| Scratch | `tmp/scratch/` | Session state |
| Echoes | `.claude/echoes/{role}/` | `MEMORY.md`, `knowledge.md`, `archive/` |

All `tmp/` directories are ephemeral and can be safely deleted after workflows complete.

Echo files in `.claude/echoes/` are persistent and survive across sessions.

## Configuration

Projects can override defaults via `.claude/rune-config.yml` (project) or `~/.claude/rune-config.yml` (global):

```yaml
rune-gaze:
  backend_extensions: [.py, .go]
  frontend_extensions: [.tsx, .ts]
  skip_patterns: ["**/migrations/**"]
  always_review: ["CLAUDE.md", ".claude/**/*.md"]

# Custom Runebearers — extend the built-in 5
runebearers:
  custom:
    - name: "domain-logic-reviewer"
      agent: "domain-logic-reviewer"    # local .claude/agents/ or plugin namespace
      source: local                     # local | global | plugin
      workflows: [review, audit]
      trigger:
        extensions: [".py", ".rb"]
        paths: ["src/domain/"]
      context_budget: 20
      finding_prefix: "DOM"

settings:
  max_runebearers: 8                   # Hard cap (5 built-in + custom)
  dedup_hierarchy: [SEC, BACK, DOM, DOC, QUAL, FRONT]

echoes:
  version_controlled: false

work:
  ward_commands: ["make check", "npm test"]
  max_workers: 3
```

See `rune-circle/references/custom-runebearers.md` for full schema and `rune-config.example.yml` at plugin root.

## Coexistence

Rune uses `/rune:*` namespace. It coexists with other plugins without conflicts.

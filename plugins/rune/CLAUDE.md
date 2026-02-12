# Rune Plugin — Claude Code Guide

Multi-agent engineering orchestration for Claude Code. Plan, work, review, and audit with Agent Teams.

## Skills

| Skill | Purpose |
|-------|---------|
| **rune-orchestration** | Core coordination patterns, file-based handoff, output formats, conflict resolution |
| **context-weaving** | Unified context management (overflow prevention, rot, compression, offloading) |
| **roundtable-circle** | Review/audit orchestration with Agent Teams (7-phase lifecycle) |
| **rune-echoes** | Smart Memory Lifecycle — 3-layer project memory (Etched/Inscribed/Traced) |
| **tarnished-guide** | Agent invocation reference and Tarnished selection guide |

## Commands

| Command | Description |
|---------|-------------|
| `/rune:review` | Multi-agent code review with up to 5 Tarnished teammates |
| `/rune:cancel-review` | Cancel active review and shutdown teammates |
| `/rune:audit` | Full codebase audit with up to 5 Tarnished teammates |
| `/rune:cancel-audit` | Cancel active audit and shutdown teammates |
| `/rune:plan` | Multi-agent planning with parallel research, 3 detail levels, Forge Gaze topic-aware enrichment, issue creation (+ `--forge`, `--exhaustive`, `--brainstorm`) |
| `/rune:work` | Swarm work execution with self-organizing task pool (+ `--approve`, incremental commits) |
| `/rune:mend` | Parallel finding resolution from TOME |
| `/rune:arc` | End-to-end pipeline (forge, plan review, work, review, mend, audit) |
| `/rune:cancel-arc` | Cancel active arc pipeline |
| `/rune:echoes` | Manage Rune Echoes memory (show, prune, reset, init) + Remembrance |
| `/rune:rest` | Remove tmp/ artifacts from completed workflows |

## Agents

### Review Agents (`agents/review/`)

| Agent | Expertise |
|-------|-----------|
| ward-sentinel | Security vulnerabilities, OWASP, auth, secrets |
| ember-oracle | Performance bottlenecks, N+1 queries, complexity |
| rune-architect | Architecture compliance, layer boundaries, SOLID |
| simplicity-warden | YAGNI, over-engineering, premature abstraction |
| flaw-hunter | Logic bugs, edge cases, race conditions |
| mimic-detector | DRY violations, code duplication |
| pattern-seer | Pattern consistency, naming conventions |
| void-analyzer | Incomplete implementations, TODOs, stubs |
| wraith-finder | Dead code, unused exports |
| phantom-checker | Dynamic references, reflection analysis |

### Research Agents (`agents/research/`)

| Agent | Purpose |
|-------|---------|
| practice-seeker | External best practices and industry patterns |
| repo-surveyor | Codebase exploration and pattern discovery |
| lore-scholar | Framework documentation and API research |
| git-miner | Git history analysis and code archaeology |
| echo-reader | Reads Rune Echoes to surface relevant past learnings |

### Work Agents (`agents/work/`)

| Agent | Purpose |
|-------|---------|
| rune-smith | Code implementation (TDD-aware swarm worker) |
| trial-forger | Test generation (swarm worker) |

### Utility Agents (`agents/utility/`)

| Agent | Purpose |
|-------|---------|
| runebinder | Aggregates Tarnished findings into TOME.md |
| decree-arbiter | Technical soundness review for plans (5-dimension evaluation) |
| truthseer-validator | Audit coverage validation (Phase 5.5) |
| flow-seer | Spec flow analysis and gap detection |
| scroll-reviewer | Document quality review |
| mend-fixer | Parallel code fixer for /rune:mend findings (restricted tools) |
| knowledge-keeper | Documentation coverage reviewer for plans |

## Key Concepts

### The Elden Lord (Orchestrator)

The lead agent that coordinates all Rune workflows. In Elden Ring, the Elden Lord rules
from the Erdtree throne. In Rune, the Elden Lord:
- Convenes the Roundtable Circle (review/audit orchestration)
- Coordinates Tarnished and summons research agents
- Collects findings into the TOME
- Guides the arc pipeline from forge to audit

The Elden Lord is the lead agent in every team. Machine identifier: `team-lead`.

### Tarnished (Consolidated Teammates)

Each Tarnished is an Agent Teams teammate with its own 200k context window. A Tarnished embeds multiple review agent perspectives into a single teammate to reduce team size.

Forge Warden, Ward Sentinel, and Pattern Weaver embed dedicated review agent files from `agents/review/` (10 agents across 3 Tarnished). Glyph Scribe and Knowledge Keeper use inline perspective definitions in their Tarnished prompts. The "Perspectives" column lists review focus areas — these are conceptual categories, not 1:1 agent mappings (e.g., Pattern Weaver covers 7 perspectives via 5 dedicated agents).

| Tarnished | Perspectives | Agent Source | When Summoned |
|-----------|-------------|-------------|-------------|
| **Forge Warden** | Backend code quality, architecture, performance, logic, testing | Dedicated agent files | Backend files changed |
| **Ward Sentinel** | All security perspectives | Dedicated agent files | ALWAYS |
| **Pattern Weaver** | Simplicity, patterns, duplication, logic, dead code, complexity, tests | Dedicated agent files | ALWAYS |
| **Glyph Scribe** | Type safety, components, performance, hooks, accessibility | Inline perspectives | Frontend files changed |
| **Knowledge Keeper** | Accuracy, completeness, consistency, readability, security | Inline perspectives | Docs changed (>= 10 lines) |

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

### TOME (Structured Findings)

The unified review summary after deduplication and prioritization. Findings use structured `<!-- RUNE:FINDING -->` markers for machine parsing.

### Decree Arbiter

Utility agent that reviews plans for technical soundness across 5 dimensions (feasibility, risk, efficiency, coverage, consistency). Uses Decree Trace evidence format.

### Remembrance Channel

Human-readable knowledge documents in `docs/solutions/` promoted from high-confidence Rune Echoes. See `rune-echoes/references/remembrance-schema.md` for the promotion rules and YAML frontmatter schema.

### Rune Echoes

Project-level agent memory in `.claude/echoes/` with 3-layer lifecycle:
1. **Etched**: Permanent project knowledge (architecture, conventions) — never auto-pruned
2. **Inscribed**: Tactical patterns from reviews/audits — pruned after 90 days unreferenced
3. **Traced**: Session observations — pruned after 30 days

Agents persist learnings automatically after workflows. Future workflows read echoes to avoid repeating mistakes. See `rune-echoes` skill for full lifecycle.

### Forge Gaze (Topic-Aware Agent Selection)

When `--forge` is used with `/rune:plan`, Forge Gaze matches plan section topics to specialized agents. Analogous to Rune Gaze (file extensions → Tarnished for reviews), but applied to plan section topics instead.

- **Keyword overlap scoring** with title bonus — deterministic, zero token cost, transparent
- **Budget tiers**: `enrichment` (review agents, ~5k tokens) and `research` (practice-seeker/lore-scholar, ~15k tokens)
- **Default `--forge`**: threshold 0.30, max 3 agents/section, enrichment only, max 8 total
- **`--forge --exhaustive`**: threshold 0.15, max 5 agents/section, enrichment + research, max 12 total
- **Custom agents** from `talisman.yml` participate via `workflows: [forge]` + `trigger.topics` + `forge:` config

See `roundtable-circle/references/forge-gaze.md` for the topic registry and matching algorithm.

### Arc Pipeline

End-to-end orchestration across 6 phases: forge (research enrichment), plan review (3-reviewer circuit breaker), work (swarm implementation), code review (Roundtable Circle), mend (parallel finding resolution), and audit (final gate). Each phase summons a fresh team. Checkpoint-based resume (`.claude/arc/{id}/checkpoint.json`) with artifact integrity validation (SHA-256 hashes). Per-phase tool restrictions enforce least privilege.

### Mend

Parallel finding resolution from TOME. Parses structured `<!-- RUNE:FINDING -->` markers with session nonce validation, groups findings by file, summons restricted mend-fixer teammates (no Bash, no TeamCreate). Ward check runs once after all fixers complete. Bisection algorithm identifies failing fixes on ward failure.

### Context Weaving

4-layer context management:
1. **Overflow Prevention**: Glyph Budget enforces file-only output
2. **Context Rot Prevention**: Instruction anchoring, read ordering
3. **Compression**: Session summaries when messages exceed thresholds
4. **Filesystem Offloading**: Large outputs written to `tmp/` files

### Lore Glossary

| Term | Plugin Meaning | Elden Ring Parallel |
|------|---------------|-------------------|
| **Elden Lord** | Orchestrator/lead agent | The ruler who commands from the Erdtree |
| **Tarnished** | Teammate agents (review, work, research, utility) | Warriors carrying out quests |
| **Roundtable Circle** | Review/audit orchestration lifecycle | Roundtable Hold gathering |
| **TOME** | Aggregated findings document | Collected knowledge |
| **Rune Echoes** | Project memory (3-layer lifecycle) | Echoes of past battles |
| **Inscription** | JSON output contract for agents | Rune inscriptions defining purpose |
| **Seal** | Completion signal from agents | A mark of duty fulfilled |
| **Rune Gaze** | File classification by extension | Perceiving the nature of runes |
| **Forge Gaze** | Topic-to-agent matching for plan enrichment | Perceiving which expertise to forge |
| **Truthbinding** | Anti-prompt-injection protocol | An oath against deception |
| **Ward** | Quality gate (tests/lint) | Protective enchantments |
| **Arc** | End-to-end pipeline | A hero's journey |
| **Forge** | Research enrichment phase | Tempering plans in fire |
| **Mend** | Finding resolution from TOME | Repairing what was broken |
| **Remembrance** | Promoted knowledge docs | Memories of fallen foes |
| **Summon** | Bringing a Tarnished agent into existence | Calling spirits/cooperators to aid in battle |
| **Talisman** | Plugin configuration file (`talisman.yml`) | Equippable items that enhance abilities |
| **Decree Arbiter** | Technical soundness reviewer for plans | A judge who weighs the merit of decrees |
| **Flow Seer** | Spec/feature flow completeness analyzer | One who perceives the currents of fate |

## Multi-Agent Rules

| Agent Count | Required Protocol |
|-------------|-------------------|
| 1-2 agents | Output budget only |
| 3-4 agents | Output budget + inscription.json |
| 5+ agents | MUST use Agent Teams (TeamCreate + TaskCreate) |

## Output Conventions

| Workflow | Directory | Files |
|----------|----------|-------|
| Reviews | `tmp/reviews/{id}/` | `{tarnished}.md`, `TOME.md` (with RUNE:FINDING markers), `inscription.json` |
| Audits | `tmp/audit/{id}/` | Same pattern |
| Plans | `tmp/plans/{id}/research/`, `plans/YYYY-MM-DD-{type}-{name}-plan.md` | Research findings, brainstorm decisions, plan document |
| Mend | `tmp/mend/{id}/` | `resolution-report.md`, fixer outputs |
| Arc | `tmp/arc/{id}/` | Phase artifacts (`enriched-plan.md`, `plan-review.md`, `tome.md`, `resolution-report.md`, `audit-report.md`) |
| Arc State | `.claude/arc/{id}/` | `checkpoint.json` (persistent, NOT in tmp/) |
| Scratch | `tmp/scratch/` | Session state |
| Echoes | `.claude/echoes/{role}/` | `MEMORY.md`, `knowledge.md`, `archive/` |

All `tmp/` directories are ephemeral and can be safely deleted after workflows complete.

Echo files in `.claude/echoes/` are persistent and survive across sessions.

## Configuration

Projects can override defaults via `.claude/talisman.yml` (project) or `~/.claude/talisman.yml` (global):

```yaml
rune-gaze:
  backend_extensions: [.py, .go]
  frontend_extensions: [.tsx, .ts]
  skip_patterns: ["**/migrations/**"]
  always_review: ["CLAUDE.md", ".claude/**/*.md"]

# Custom Tarnished — extend the built-in 5
tarnished:
  custom:
    - name: "domain-logic-reviewer"
      agent: "domain-logic-reviewer"    # local .claude/agents/ or plugin namespace
      source: local                     # local | global | plugin
      workflows: [review, audit, forge] # forge enables Forge Gaze matching
      trigger:
        extensions: [".py", ".rb"]
        paths: ["src/domain/"]
        topics: [domain, business-logic, models, services]  # For forge
      forge:
        subsection: "Domain Logic Analysis"
        perspective: "domain model integrity and business rule correctness"
        budget: enrichment
      context_budget: 20
      finding_prefix: "DOM"

settings:
  max_tarnished: 8                   # Hard cap (5 built-in + custom)
  dedup_hierarchy: [SEC, BACK, DOM, DOC, QUAL, FRONT]

# forge:                               # Forge Gaze selection overrides
#   threshold: 0.30                    # Score threshold (0.0-1.0)
#   max_per_section: 3                 # Max agents per section (cap: 5)
#   max_total_agents: 8                # Max total agents (cap: 15)

echoes:
  version_controlled: false

work:
  ward_commands: ["make check", "npm test"]
  max_workers: 3
  approve_timeout: 180                   # Seconds (default 3 min)
  commit_format: "rune: {subject} [ward-checked]"
```

See `roundtable-circle/references/custom-tarnished.md` for full schema and `talisman.example.yml` at plugin root.

## Coexistence

Rune uses `/rune:*` namespace. It coexists with other plugins without conflicts.

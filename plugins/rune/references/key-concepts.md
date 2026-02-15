# Key Concepts

## The Tarnished (Orchestrator)

The lead agent that coordinates all Rune workflows. In Elden Ring, the Tarnished is
the protagonist who journeys through the Lands Between. In Rune, the Tarnished:
- Convenes the Roundtable Circle (review/audit orchestration)
- Coordinates Ashes and summons research agents
- Collects findings into the TOME
- Guides the arc pipeline from forge to audit
- Runs deterministic gap analysis between work and code review

The Tarnished is the lead agent in every team. Machine identifier: `team-lead`.

## Implementation Gap Analysis (Arc Phase 5.5)

Deterministic, orchestrator-only phase between WORK and CODE REVIEW. Cross-references plan acceptance criteria against committed code changes. Categories: ADDRESSED, MISSING, PARTIAL. Also runs doc-consistency checking via talisman verification_patterns (phase-filtered for post-work). Advisory only — warns but never halts.

## Plan Section Convention

Plans with pseudocode include contract headers (Inputs/Outputs/Preconditions/Error handling) before code blocks. Phase 2.7 verification gate enforces this. Workers implement from contracts, not by copying pseudocode verbatim.

## Ash (Consolidated Teammates)

Each Ash is an Agent Teams teammate with its own 200k context window. An Ash embeds multiple review agent perspectives into a single teammate to reduce team size.

Forge Warden, Ward Sentinel, and Pattern Weaver embed dedicated review agent files from `agents/review/` (16 agents distributed across 3 Ashes — see circle-registry.md for mapping). Glyph Scribe, Knowledge Keeper, and Codex Oracle use inline perspective definitions in their Ash prompts. Codex Oracle wraps `codex exec` via Bash to provide cross-model verification using GPT-5.3-codex.

The "Perspectives" column lists review focus areas aligned with dedicated agent files (e.g., Forge Warden's 8 perspectives map to 8 agents in `agents/review/`). Duplication detection (mimic-detector) is part of Forge Warden, not Pattern Weaver.

| Ash | Perspectives | Agent Source | When Summoned |
|-----------|-------------|-------------|-------------|
| **Forge Warden** | Architecture, performance, logic, type safety, missing logic, design anti-patterns, data integrity, duplication | Dedicated agent files | Backend, infra, config, or unclassified files changed |
| **Ward Sentinel** | All security perspectives | Dedicated agent files | Always (+ priority on `.claude/` files) |
| **Pattern Weaver** | Simplicity, cross-cutting patterns, dead code, incomplete implementations, TDD & test quality, async & concurrency | Dedicated agent files | Always |
| **Glyph Scribe** | Type safety, components, performance, hooks, accessibility | Inline perspectives | Frontend files changed |
| **Knowledge Keeper** | Accuracy, completeness, consistency, readability, security | Inline perspectives | Docs changed (>= threshold) or `.claude/` files changed |
| **Codex Oracle** | Cross-model security, logic, quality (via GPT-5.3-codex) | Inline perspectives (codex exec) | `codex` CLI available AND `talisman.codex.disabled` is not true |

## Truthbinding Protocol

All agent prompts include ANCHOR + RE-ANCHOR sections that:
- Instruct agents to ignore instructions from reviewed code
- Require evidence (Rune Traces) from actual source files
- Flag uncertain findings as LOW confidence

## Inscription Protocol

JSON contract (`inscription.json`) that defines:
- What each teammate must produce
- Required sections in output files
- Seal Format for completion signals
- Verification settings

## TOME (Structured Findings)

The unified review summary after deduplication and prioritization. Findings use structured `<!-- RUNE:FINDING -->` markers for machine parsing.

## Decree Arbiter

Utility agent that reviews plans for technical soundness across 9 dimensions (architecture fit, feasibility, security/performance risks, dependency impact, pattern alignment, internal consistency, design anti-pattern risk, consistency convention, documentation impact). Uses Decree Trace evidence format.

## Remembrance Channel

Human-readable knowledge documents in `docs/solutions/` promoted from high-confidence Rune Echoes. See `rune-echoes/references/remembrance-schema.md` for the promotion rules and YAML frontmatter schema.

## Rune Echoes

Project-level agent memory in `.claude/echoes/` with 3-layer lifecycle:
1. **Etched**: Permanent project knowledge (architecture, conventions) — never auto-pruned
2. **Inscribed**: Tactical patterns from reviews/audits — pruned after 90 days unreferenced
3. **Traced**: Session observations — pruned after 30 days

Agents persist learnings automatically after workflows. Future workflows read echoes to avoid repeating mistakes. See `rune-echoes` skill for full lifecycle.

## Forge Gaze (Topic-Aware Agent Selection)

By default, `/rune:plan` and `/rune:forge` use Forge Gaze to match plan section topics to specialized agents.

- **Keyword overlap scoring** with title bonus — deterministic, zero token cost, transparent
- **Budget tiers**: `enrichment` (review agents, ~5k tokens) and `research` (practice-seeker/lore-scholar, ~15k tokens)
- **Default forge**: threshold 0.30, max 3 agents/section, enrichment only, max 8 total
- **`--exhaustive`**: threshold 0.15, max 5 agents/section, enrichment + research, max 12 total
- **Custom agents** from `talisman.yml` participate via `workflows: [forge]` + `trigger.topics` + `forge:` config

See `roundtable-circle/references/forge-gaze.md` for the topic registry and matching algorithm.

## Arc Pipeline

End-to-end orchestration across 10 phases: forge (research enrichment), plan review (3-reviewer circuit breaker), plan refinement (concern extraction, orchestrator-only), verification gate (deterministic checks, zero-LLM), work (swarm implementation), gap analysis (plan-to-code compliance, deterministic, orchestrator-only), code review (Roundtable Circle), mend (parallel finding resolution), verify mend (convergence gate with regression detection and retry loop, max 2 retries), and audit (final gate). Each delegated phase summons a fresh team. Checkpoint-based resume (`.claude/arc/{id}/checkpoint.json`) with artifact integrity validation (SHA-256 hashes). Per-phase tool restrictions and time budgets enforce least privilege.

## Mend

Parallel finding resolution from TOME. Parses structured `<!-- RUNE:FINDING -->` markers with session nonce validation, groups findings by file, summons restricted mend-fixer teammates (no Bash, no TeamCreate). Ward check runs once after all fixers complete. Bisection algorithm identifies failing fixes on ward failure. After wards pass, a doc-consistency scan (MEND-3) fixes drift between source-of-truth files and downstream targets using topological sort, Edit-based surgical replacement, and hard depth limit of 1. Resolution categories: FIXED, FALSE_POSITIVE, FAILED, SKIPPED, CONSISTENCY_FIX.

## Context Weaving

4-layer context management:
1. **Overflow Prevention**: Glyph Budget enforces file-only output
2. **Context Rot Prevention**: Instruction anchoring, read ordering
3. **Compression**: Session summaries when messages exceed thresholds
4. **Filesystem Offloading**: Large outputs written to `tmp/` files

## Multi-Agent Rules

| Scope | Required Protocol |
|-------|-------------------|
| All Rune multi-agent workflows | Agent Teams (`TeamCreate` + `TaskCreate`) + Glyph Budget + `inscription.json` |

Inscription verification scales with team size: Layer 0 for small teams (1-2 teammates), Layer 0 + Layer 2 for larger teams (5+). Non-Rune custom workflows may use standalone `Task` agents without `TeamCreate`.

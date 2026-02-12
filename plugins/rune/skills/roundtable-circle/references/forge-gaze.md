# Forge Gaze — Topic-Aware Agent Selection for Plan Enrichment

> Matches plan section topics to specialized agents for plan enrichment (default in `/rune:plan` and `/rune:forge`). Analogous to [Rune Gaze](rune-gaze.md) (file extensions → Ash for reviews). Use `--quick` with `/rune:plan` to skip forge.

## Table of Contents

- [Topic Registry](#topic-registry)
  - [Review Agents (Enrichment Budget)](#review-agents-enrichment-budget)
  - [Research Agents (Research Budget)](#research-agents-research-budget)
  - [Utility Agents (Enrichment Budget)](#utility-agents-enrichment-budget)
- [Matching Algorithm](#matching-algorithm)
  - [Topic Extraction](#topic-extraction)
  - [Scoring](#scoring)
  - [Selection](#selection)
  - [Constants](#constants)
- [Budget Tiers](#budget-tiers)
- [Forge Modes](#forge-modes)
  - [Default](#default-runs-automatically-in-runeplan-and-runeforge)
  - [--exhaustive](#--exhaustive)
- [Custom Forge Agents](#custom-forge-agents)
- [Fallback Behavior](#fallback-behavior)
- [Dry-Run Output](#dry-run-output)
- [References](#references)

## Topic Registry

Each agent declares which plan section topics it can enrich, what subsection it produces, and its perspective focus.

> **Note**: Forge Gaze matches agents **individually** (each agent scores independently against section topics), unlike `/rune:review` where agents are grouped into Ash composites. This allows fine-grained topic matching per plan section.

### Review Agents (Enrichment Budget)

| Agent | Topics | Subsection | Perspective |
|-------|--------|------------|-------------|
| ward-sentinel | security, authentication, authorization, owasp, secrets, input-validation, csrf, xss, injection | Security Considerations | security vulnerabilities and threat modeling |
| ember-oracle | performance, scalability, caching, database, queries, n-plus-one, latency, memory, async | Performance Considerations | performance bottlenecks and optimization opportunities |
| rune-architect | architecture, layers, boundaries, solid, dependencies, services, patterns, design | Architecture Analysis | architectural compliance and structural integrity |
| flaw-hunter | edge-cases, null-handling, race-conditions, concurrency, error-handling, validation, boundaries | Edge Cases & Risk Analysis | logic bugs, race conditions, and edge case coverage |
| pattern-seer | patterns, conventions, naming, consistency, style, standards, anti-patterns | Pattern Alignment | codebase pattern consistency and convention adherence |
| simplicity-warden | complexity, yagni, abstraction, over-engineering, simplicity, minimal | Simplicity Review | unnecessary complexity and YAGNI violations |
| mimic-detector | duplication, dry, reuse, similar, copy-paste, shared | Reuse Opportunities | code duplication and reuse opportunities |
| void-analyzer | completeness, todo, stub, placeholder, partial, implementation, missing | Completeness Gaps | incomplete implementations, stubs, and TODO coverage |
| wraith-finder | dead-code, unused, orphan, deprecated, legacy, cleanup, removal | Dead Code Risk | dead code identification and cleanup opportunities |
| phantom-checker | dynamic, reflection, metaprogramming, string-dispatch, runtime, magic | Dynamic Reference Analysis | dynamic references and runtime resolution concerns |

### Research Agents (Research Budget)

| Agent | Topics | Subsection | Perspective |
|-------|--------|------------|-------------|
| practice-seeker | best-practices, industry, standards, conventions, recommendations, patterns | Best Practices | external best practices and industry standards |
| lore-scholar | framework, library, api, documentation, version, migration, deprecation | Framework Documentation | framework-specific APIs and version constraints |

### Utility Agents (Enrichment Budget)

| Agent | Topics | Subsection | Perspective |
|-------|--------|------------|-------------|
| flow-seer | user-flow, ux, interaction, workflow, requirements, gaps, completeness | User Flow Analysis | user flow completeness and requirement gaps |

## Matching Algorithm

### Topic Extraction

Extract topics from a plan section's title and content:

```
extract_topics(title, content):
  1. title_words = lowercase(title).split() → filter stopwords
  2. content_signal = first 200 chars of content → extract nouns/adjectives
  3. return unique(title_words + content_signal)
```

Stopwords to filter: `the, a, an, and, or, of, for, in, to, with, is, are, this, that, will, be, on, at, by`

### Scoring

For each plan section, score every agent in the topic registry:

```
score(section, agent):
  section_topics = extract_topics(section.title, section.content)

  # Keyword overlap: how many agent topics appear in section topics
  matches = count(topic for topic in agent.topics if topic in section_topics
                  OR any(section_word.startswith(topic) for section_word in section_topics))
  keyword_score = matches / len(agent.topics)

  # Title match bonus: agent's top-3 topics appearing in section title
  title_bonus = 0.3 if any(topic in section.title.lower() for topic in agent.topics[:3]) else 0.0

  # Combined score (capped at 1.0)
  return min(keyword_score + title_bonus, 1.0)
```

### Selection

```
forge_select(plan_sections, topic_registry, mode="default"):
  threshold = THRESHOLD_DEFAULT if mode == "default" else THRESHOLD_EXHAUSTIVE
  max_per_section = MAX_PER_SECTION_DEFAULT if mode == "default" else MAX_PER_SECTION_EXHAUSTIVE
  include_research = (mode == "exhaustive")

  total_agents = 0
  assignments = {}

  for each section in plan_sections:
    candidates = []

    for each agent in topic_registry:
      # Skip research-budget agents in default mode
      if agent.budget == "research" and not include_research:
        continue

      s = score(section, agent)
      if s >= threshold:
        candidates.append((agent, s))

    # Sort by score descending, cap per section
    candidates.sort(by=score, descending)
    selected = candidates[:max_per_section]

    # Enforce total agent cap
    if total_agents + len(selected) > MAX_TOTAL_AGENTS:
      selected = selected[:MAX_TOTAL_AGENTS - total_agents]

    total_agents += len(selected)
    assignments[section] = selected

    if total_agents >= MAX_TOTAL_AGENTS:
      break  # Budget exhausted

  return assignments
```

### Constants

| Constant | Default | Exhaustive | Description |
|----------|---------|------------|-------------|
| `THRESHOLD` | 0.30 | 0.15 | Minimum score to select an agent |
| `MAX_PER_SECTION` | 3 | 5 | Maximum agents per plan section |
| `MAX_TOTAL_AGENTS` | 8 | 12 | Hard cap across all sections |

These can be overridden via `talisman.yml`:

```yaml
forge:
  threshold: 0.30          # Range: 0.0-1.0
  max_per_section: 3       # Hard upper bound: 5
  max_total_agents: 8      # Hard upper bound: 15
```

**Validation bounds**: `threshold` must be between 0.0 and 1.0. `max_per_section` capped at 5. `max_total_agents` capped at 15. Values exceeding bounds are clamped silently.

## Budget Tiers

| Budget | Agents | Behavior | Token Cost |
|--------|--------|----------|-----------|
| `enrichment` | Review + utility agents | Read plan section, apply expertise, write perspective | ~5k tokens |
| `research` | practice-seeker, lore-scholar | Web search, docs lookup, deeper analysis | ~15k tokens |

- **Default forge**: Only `enrichment` budget agents
- **`--exhaustive`**: Both `enrichment` and `research` budget agents

## Forge Modes

### Default (runs automatically in `/rune:plan` and `/rune:forge`)

```
1. Parse plan into sections (## headings)
2. Run Forge Gaze matching (enrichment agents only)
3. Log selection transparently
4. Summon matched agents per section
5. Each agent writes to: tmp/plans/{timestamp}/forge/{section-slug}-{agent-name}.md
6. Lead merges enrichments into plan document
```

Use `--quick` with `/rune:plan` to skip forge, or `--no-forge` for granular control.

### --exhaustive

Same flow but with:
- Lower threshold (0.15 vs 0.30)
- Higher per-section cap (5 vs 3)
- Higher total cap (12 vs 8)
- Research-budget agents included
- Two-tier aggregation: per-section synthesizer → lead
- Cost warning displayed before summoning

## Custom Forge Agents

Custom Ashes from `talisman.yml` can participate in forge by adding `forge` to their `workflows` list and providing forge-specific config:

```yaml
ashes:
  custom:
    - name: "api-contract-reviewer"
      agent: "api-contract-reviewer"
      source: local
      workflows: [review, audit, forge]   # "forge" enables Forge Gaze matching
      trigger:
        extensions: [".py", ".ts"]        # For review/audit (file-based)
        topics: [api, contract, endpoints, rest, graphql]  # For forge (topic-based)
      forge:
        subsection: "API Contract Analysis"
        perspective: "API design, contract compatibility, and endpoint patterns"
        budget: enrichment
      context_budget: 15
      finding_prefix: "API"
```

### Custom Agent Validation

If `forge` is in `workflows`, these fields are **required**:
- `trigger.topics` — at least 2 topics
- `forge.subsection` — the subsection title this agent produces
- `forge.perspective` — description of the agent's focus area
- `forge.budget` — `enrichment` or `research`

## Fallback Behavior

If no agent scores above the threshold for a section:
- Use an inline generic Task prompt (not a named agent) as fallback — the orchestrator summons a general-purpose agent with a generic "research and enrich this section" prompt
- The generic prompt produces the standard structured subsections

This ensures Forge never produces empty enrichment — it gracefully degrades. There is no dedicated `forge-researcher` agent definition; the fallback uses an inline prompt.

## Dry-Run Output (Not Yet Implemented)

> **Note**: `--dry-run` is not yet implemented in `/rune:plan`. The format below is the target specification for when it is added. Currently, Forge Gaze logs its selection transparently in the console output during Phase 3.

When `--dry-run` is used, display selection without summoning (forge runs by default; `--quick` skips it):

```
Forge Gaze — Agent Selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Plan sections: 6
Agents available: 13 built-in (11 enrichment + 2 research) + 1 custom

Section: "Technical Approach"
  ✓ rune-architect (0.85) — architecture compliance
  ✓ pattern-seer (0.45) — pattern alignment
  ✓ simplicity-warden (0.35) — complexity check

Section: "Security Requirements"
  ✓ ward-sentinel (0.95) — security vulnerabilities
  ✓ flaw-hunter (0.40) — edge cases

Section: "Performance Targets"
  ✓ ember-oracle (0.90) — performance bottlenecks

Section: "API Design"
  ✓ api-contract-reviewer (0.80) — API contracts [custom]
  ✓ pattern-seer (0.35) — pattern alignment

Section: "Overview" — no agent matched (below threshold)
Section: "References" — no agent matched (below threshold)

Total: 8 agent invocations across 4 sections (2 sections skipped)
Estimated tokens: ~40k (enrichment only)
```

## References

- [Rune Gaze](rune-gaze.md) — File extension → Ash matching (analogous system for reviews)
- [Circle Registry](circle-registry.md) — Agent-to-Ash mapping
- [Smart Selection](smart-selection.md) — File assignment and budget enforcement
- [Custom Ash](custom-ashes.md) — Custom agent schema (extended for forge)

---
name: elicitation
description: |
  Context-aware elicitation method selection for Rune workflows.
  Provides structured reasoning techniques (Tree of Thoughts, Pre-mortem,
  Red Team, 5 Whys, etc.) during planning, review, and work phases.
  Auto-loaded by plan, forge, and review commands when applicable.

  <example>
  Context: During plan brainstorm, user needs structured approach selection
  user: "Help me evaluate these 3 architecture approaches"
  assistant: "Loading elicitation skill for Tree of Thoughts structured evaluation"
  </example>

  <example>
  Context: During forge enrichment with security-sensitive section
  user: "/rune:forge plans/security-plan.md"
  assistant: "Elicitation skill loaded — Red Team vs Blue Team method available for security sections"
  </example>
user-invocable: false
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Elicitation — BMAD-Derived Structured Reasoning Methods

Provides a curated registry of 22 elicitation methods (from BMAD's 50) with phase-aware auto-selection. Methods are **prompt modifiers** — they inject structured output templates into agent prompts without spawning additional agents. Zero token cost increase.

## Method Registry

The method registry lives in [methods.csv](methods.csv) with 22 curated methods across 2 tiers:

- **Tier 1** (14 methods): Auto-suggested when phase and topics match
- **Tier 2** (8 methods): Available on request but not auto-suggested

### CSV Schema

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `num` | int | Yes | BMAD method number (preserves original reference) |
| `category` | string | Yes | BMAD category grouping |
| `method_name` | string | Yes | Human-readable method name |
| `description` | string | Yes | Brief description of technique |
| `output_pattern` | string | Yes | Arrow-separated (`->`) output structure template |
| `tier` | int (1\|2) | Yes | 1=auto-suggest, 2=optional |
| `phases` | string | Yes | Comma-separated `command:phase_number` pairs (e.g., `plan:0,forge:3`) |
| `agents` | string | No | Comma-separated agent names. Empty = applicable to any agent |
| `topics` | string | Yes | Comma-separated keywords for Forge Gaze topic scoring |
| `auto_suggest` | bool | Yes | `true` for Tier 1, `false` for Tier 2 |

### CSV Parsing Instructions

To parse methods.csv:

1. **Read** the file, skip header row
2. **Split** each row by comma, respecting quoted fields (phases, agents, topics contain commas inside quotes)
3. **Validate** each row: must have exactly 10 columns. Skip malformed rows with warning.
4. **Parse multi-value columns**:
   - `phases`: Split on comma → array of `command:phase_number` pairs (e.g., `["plan:0", "forge:3"]`)
   - `agents`: Split on comma → array of agent names. Empty string = applicable to any agent.
   - `topics`: Split on comma → array of keywords for scoring
5. **Validate required fields**: `num`, `method_name`, `tier`, `phases` must be non-empty
6. **Validate tier**: Must be `1` or `2`
7. **Validate phase syntax**: Each phase must match pattern `command:number` (e.g., `plan:0`, `arc:7.5`)

### Error Handling

- Malformed CSV row (wrong column count): Skip row, log warning
- Missing required field: Skip row, log warning
- Invalid tier value: Default to `2` (non-auto-suggest)
- Invalid phase syntax: Skip that phase entry, keep row
- Empty file or unreadable: Fall back to empty registry (no methods available, standard workflow)

## Method Selection Algorithm

Context-aware selection pipeline (rule-based v1):

```
1. PHASE FILTER
   Input: current_phase (e.g., "plan:0", "forge:3")
   Filter: methods WHERE phases CONTAINS current_phase
   Output: phase_matched_methods[]

2. TIER FILTER
   If auto_mode:
     Filter: phase_matched_methods WHERE auto_suggest = true (Tier 1 only)
   If manual_mode:
     Keep all phase_matched_methods (Tier 1 + Tier 2)
   Output: tier_filtered_methods[]

3. TOPIC SCORING
   Input: section_text (plan section or feature description)
   For each method in tier_filtered_methods:
     score = keyword_overlap(method.topics, section_keywords) / len(method.topics)
     If method.method_name appears in section_text: score += 0.3 (title bonus)
   Output: scored_methods[] sorted by score DESC

4. SELECT TOP N
   Take top 3-5 methods (configurable, default 5)
   Output: selected_methods[]
```

### Worked Example

Given section "## Architecture Design" with keywords `[architecture, layers, boundaries, patterns]`:

```
Method: Tree of Thoughts
  topics: [architecture, design, complex, multiple-approaches, decisions]
  keyword_overlap: {architecture} = 1 match out of 5 topics
  score: 1/5 = 0.20
  title_bonus: "Tree of Thoughts" not in section text → +0.0
  final_score: 0.20

Method: Architecture Decision Records
  topics: [architecture, design, trade-offs, decisions, ADR]
  keyword_overlap: {architecture} = 1 match out of 5 topics
  score: 1/5 = 0.20
  title_bonus: "Architecture" in section text → +0.3
  final_score: 0.50 ← selected (title bonus)
```

## Phase Integration Reference

For detailed method-to-phase mapping, see [references/phase-mapping.md](references/phase-mapping.md).

## Prompt Modifier Pattern

Methods are injected as structured output templates into agent prompts. They do NOT spawn new agents.

### How It Works

1. Forge Gaze (or command) selects methods alongside agents
2. Selected method's `output_pattern` is expanded into a template
3. Template is appended to the matched agent's prompt as an H3 subsection
4. Agent follows the template structure in its output

### Template Format

```markdown
### Structured Reasoning: {method_name}

For this section, apply {method_name}:

{output_pattern_expanded}
```

### Output Pattern Expansion

The `output_pattern` column uses `->` to denote ordered steps:

| Pattern | Expanded Template |
|---------|------------------|
| `paths->evaluation->selection` | 1. Explore 3 distinct paths\n2. Evaluate each on feasibility/complexity\n3. Select strongest, explain elimination |
| `failure->causes->prevention` | 1. Declare the failure scenario\n2. Brainstorm 3-5 failure causes\n3. Design prevention measures |
| `defense->attack->hardening` | 1. Document existing defenses\n2. Identify attack vectors\n3. Recommend hardening |

For full expansion examples, see [references/examples.md](references/examples.md).

## Method Categories

| Category | Tier 1 Count | Tier 2 Count | Primary Phases |
|----------|-------------|-------------|----------------|
| collaboration | 4 | 2 | plan:0 |
| advanced | 2 | 0 | forge:3, plan:4 |
| competitive | 1 | 2 | review:6 |
| technical | 1 | 1 | forge:3, review:6 |
| research | 1 | 0 | plan:1, forge:3 |
| risk | 2 | 2 | plan:2.5, arc:8 |
| core | 3 | 0 | plan:4, review:6, arc:7 |
| creative | 0 | 2 | plan:2, plan:2.5 |
| philosophical | 0 | 1 | forge:3, review:6 |

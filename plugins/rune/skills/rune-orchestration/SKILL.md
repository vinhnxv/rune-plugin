---
name: rune-orchestration
description: |
  Architecture reference for multi-agent orchestration: coordination patterns, output formats, conflict resolution, and file-based handoff.
  Use when choosing orchestration architecture (supervisor vs swarm vs pipeline), defining agent output formats, or resolving conflicting agent findings.
  For pre-spawn budgets and overflow prevention, use context-weaving instead.

  <example>
  Context: Running multi-agent code review
  user: "Review this PR with multiple agents"
  assistant: "I'll use rune-orchestration for context isolation and file-based handoff"
  </example>

  <example>
  Context: Coordinating a codebase audit
  user: "Run an audit with security and performance focus"
  assistant: "I'll use rune-orchestration for audit agent coordination and output format"
  </example>
user-invocable: false
allowed-tools:
  - Task
  - Read
  - Write
---

# Rune Orchestration Skill

Guides designing distributed multi-agent systems that partition work across multiple language model instances to overcome single-agent context limitations.

## Core Principle

**Sub-agents exist primarily to isolate context, not to anthropomorphize role division.**

The fundamental value lies in distributing cognitive load across separate context windows rather than simulating organizational hierarchies.

## When to Use

| Category | Workflows | Orchestration Pattern |
|----------|-----------|----------------------|
| **Reviews** | `/rune:review` | Runebearer Specialists |
| **Audits** | `/rune:audit` | Rune Circle (Fan-out / Fan-in) |
| **Research** | `/rune:plan` | Parallel Exploration |
| **Work** | `/rune:work` | Swarm Workers |
| **Custom** | Any workflow spawning 3+ agents | Choose pattern from below |

**Generic trigger conditions:**
- Context window constraints from single-agent approach
- Complex tasks requiring specialized expertise in parallel
- Need for parallel processing of independent subtasks
- Any workflow spawning 3+ agents via Task tool or Agent Teams

## Agent Coordination Patterns

### File-Based Handoff Pattern

Instead of supervisor synthesizing responses (telephone game), agents write directly to files:

| Workflow Type | Output Directory | Output Type | Example Contents |
|---------------|------------------|-------------|------------------|
| Reviews | `tmp/reviews/{pr-number}/` | Report (P1/P2/P3) | `forge-warden.md`, `ward-sentinel.md`, `TOME.md` |
| Audits | `tmp/audit/{audit-id}/` | Report (P1/P2/P3) | `security.md`, `performance.md`, `TOME.md` |
| Plan research | `tmp/research/` | Research | `best-practices.md`, `framework-docs.md` |
| Work (swarm) | `tmp/work/` | Status | `rune-smith-1.md`, `rune-smith-2.md` |
| Custom | `tmp/{workflow-name}/` | Varies | Named by teammate role |

**Directory Purpose:**
- **Persistent** (`todos/`): Findings that become actionable items
- **Ephemeral** (`tmp/`): Intermediate artifacts consumed by coordinator

The workflow: Agents write findings → Coordinator reads files → Synthesizes into Tome (TOME.md)

**Structured output:** Runebearers MAY also write companion JSON files (`{runebearer}-findings.json`) for CI/CD integration. After verification, a `completion.json` summarizes the workflow result. See [Output Format](../rune-circle/references/output-format.md) for full specs.

## Agent Output Formats

Each agent writes findings in a format matching its workflow type. All formats require **mandatory evidence blocks** (see Truthbinding Protocol in `references/inscription-protocol.md`).

### 1. Report Format (Reviews, Audits)

Used by workflows producing prioritized findings with P1/P2/P3 severity levels.

```markdown
# {Runebearer Name} Review

**PR:** #{pr-number}
**Branch:** {branch-name}
**Date:** {timestamp}

## P1 (Critical)

- [ ] **[SEC-001] Issue Title** in `file:line`
  - **Rune Trace:**
    ```python
    # Lines {start}-{end} of {file}
    {actual code from the source file}
    ```
  - **Issue:** {description of what's wrong and why it matters}
  - **Fix:** {recommendation}

## P2 (High)

- [ ] **[PERF-001] Issue Title** in `file:line`
  - **Rune Trace:**
    ```python
    # Lines {start}-{end} of {file}
    {actual code from the source file}
    ```
  - **Issue:** {description}
  - **Fix:** {recommendation}

## P3 (Medium)

- [ ] **[QUAL-001] Issue Title** in `file:line`
  - **Rune Trace:**
    ```python
    {actual code snippet}
    ```
  - **Issue:** {description}

## Unverified Observations

{Items where evidence could not be provided — NOT counted in totals}

## Summary

- P1: {count}
- P2: {count}
- P3: {count}
- Total: {count}
- Evidence coverage: {verified}/{total} findings have Rune Trace blocks
```

### 2. Research Format (Plans)

Used by workflows producing knowledge synthesis from parallel exploration.

```markdown
# {Agent Name} Research

**Topic:** {research area}
**Date:** {timestamp}

## Key Findings

1. **{Finding title}**
   - **Source:** {documentation URL, file path, or prior art}
   - **Detail:** {what was discovered and why it matters}
   - **Relevance:** {how this applies to the current task}

## Recommendations

- {Actionable recommendation with justification}

## Summary

- Findings: {count}
- Confidence: {high/medium/low}
- Key recommendation: {one-sentence summary}
```

### 3. Status Format (Work)

Used by workflows producing implementation progress reports.

```markdown
# {Agent Name} Status

**Task:** {task description}
**Date:** {timestamp}

## Status: {completed | partial | blocked}

## Files Changed

- `{file path}`: {what changed and why}

## Tests

- {test file}: {passed/failed} — {brief description}

## Notes

{Any blockers, decisions made, or follow-up needed}
```

## Conflict Resolution Rules

When multiple agents flag the same code with different priorities:

| Conflict | Resolution |
|----------|------------|
| P1 vs P2 | P1 wins (highest priority) |
| P1 vs P1 (different issues) | Both retained |
| Security vs Performance | Security wins |
| Same issue, different agents | Deduplicate, keep first |

### Priority Hierarchy

```
ward-sentinel P1 > any other agent P1
any agent P1 > any agent P2
any agent P2 > any agent P3
```

## Three Architectural Patterns

### 1. Supervisor/Orchestrator (Default)

Central coordinator delegates to specialists and aggregates results.

```
Team Lead (orchestrator)
    ├── forge-warden   (backend review)
    ├── ward-sentinel  (security review)
    ├── pattern-weaver (quality patterns)
    ├── glyph-scribe   (frontend review)
    └── lore-keeper    (docs review)
```

**Used by:** `/rune:review`, `/rune:audit`

**Mitigate telephone game:** Use file-based handoff, not message passing.

### 2. Peer-to-Peer/Swarm

Direct agent-to-agent communication. Workers self-organize and race to claim tasks.

**Used by:** `/rune:work`

**Example use case:** Multiple rune-smiths claiming independent tasks from a shared pool.

### 3. Hierarchical

Layered abstractions. Use for complex multi-phase workflows.

```
Strategy Layer (plan)
    └── Planning Layer (spec)
        └── Execution Layer (implement)
```

**Used by:** `/rune:plan` → `/rune:work` → `/rune:review`

## Agent Role Patterns

### Review Runebearers (Parallel Specialists)

Run simultaneously with isolated contexts. Each produces Report-format output.

```
# Parallel execution — each Runebearer writes to tmp/reviews/{pr}/
Task forge-warden(backend_files)     # Backend review
Task ward-sentinel(all_files)        # Security review
Task pattern-weaver(all_files)       # Quality patterns
Task glyph-scribe(frontend_files)    # Frontend review (conditional)
Task lore-keeper(doc_files)          # Docs review (conditional)
```

### Audit Runebearers (Fan-out / Fan-in)

Similar to review but broader scope — all project files instead of changed files.

```
# Fan-out to focused audit areas
Task forge-warden(all_backend)       # Backend architecture + logic
Task ward-sentinel(all_files)        # Security posture
Task pattern-weaver(all_files)       # Codebase quality + dead code
# Each writes to tmp/audit/{id}/
```

### Research Agents (Parallel Exploration)

Run simultaneously to gather knowledge from different angles. Produce Research-format output.

```
# Parallel research for /rune:plan
Task repo-analyst(topic)             # Repo patterns + conventions
Task best-practices(topic)           # External best practices
Task framework-docs(topic)           # Framework documentation
# Each writes to tmp/research/
```

### Work Agents (Rune Smiths)

Self-organizing workers that claim tasks from a shared pool. Produce Status-format output.

```
# Swarm mode for /rune:work — workers claim from task list
Task rune-smith-1(task-pool)         # Claims and works on tasks
Task rune-smith-2(task-pool)         # Claims and works on tasks
# Each writes to tmp/work/
```

### Conditional Runebearers

Spawned based on file types present in scope:

| Trigger | Runebearer | Workflow Types |
|---------|-----------|----------------|
| Backend files (`.py`, `.go`, `.rs`, `.rb`) | Forge Warden | Reviews, Audits |
| Frontend files (`.ts`, `.tsx`, `.js`, `.jsx`) | Glyph Scribe | Reviews, Audits |
| Doc files (`.md`, >= 10 lines changed) | Lore Keeper | Reviews, Audits |
| ALL scopes | Ward Sentinel (always) | Reviews, Audits |
| ALL scopes | Pattern Weaver (always) | Reviews, Audits |

### Validation Agents (Truthsight Pipeline)

Post-review agents that verify Runebearer output quality. Run AFTER all Runebearers complete.

```
# Layer 0: Inline Checks (lead runs directly — no agent)
#   Grep-based section validation of output files
#   Writes: {output_dir}/inline-validation.json

# Layer 1: Self-Review Log (each Runebearer performs self-review)
#   Runebearers re-read P1/P2 findings before completing
#   Output: ## Self-Review Log table in each output file

# Layer 2: Smart Verifier (spawned by lead after Runebearers complete)
Task:
  subagent_type: "general-purpose"
  model: haiku
  description: "Truthsight Verifier"
  prompt: [from references/verifier-prompt.md]
  # Writes to: {output_dir}/truthsight-report.md

# Re-verify agents (max 2 per workflow, spawned on hallucination detection)
Task:
  subagent_type: "general-purpose"
  model: haiku
  description: "Re-verify {runebearer}-{finding}"
  # Writes to: {output_dir}/re-verify-{runebearer}-{finding}.md
```

**When to spawn Layer 2 verifier:**

| Workflow | Condition | Verifier Scope |
|----------|-----------|----------------|
| `/rune:review` | `inscription.verification.enabled` AND 3+ Runebearers | All Runebearer outputs |
| `/rune:audit` | `inscription.verification.enabled` AND 5+ Runebearers | All Runebearer outputs |
| Custom | Configurable via inscription `verification` block | Per configuration |

Full verifier prompt template: [Verifier Prompt](references/verifier-prompt.md)

## Token Economics

| Approach | Token Multiplier | When to Use |
|----------|------------------|-------------|
| Single agent | 1x | Simple tasks |
| Multi-agent | ~15x | Complex review, parallel analysis |

**Guideline:** Use multi-agent only when context isolation is necessary, not for simple division of labor.

## Essential Failure Mitigations

### 1. Supervisor Saturation

**Problem:** Coordinator overwhelmed by aggregating many agent responses.

**Solution:** Glyph Budget — each agent writes to file, returns only file path + 1-sentence summary (max 50 words).

### 2. Coordination Overhead

**Problem:** Too much time on handoff protocols.

**Solution:** Clear file-based handoff with consistent format.

### 3. Lack of Convergence

**Problem:** Agents disagree indefinitely.

**Solution:**
- Time-to-live limits (max 2 iterations)
- Priority hierarchy for conflicts
- Human review for unresolved conflicts

### 4. Error Propagation

**Problem:** Early agent error cascades.

**Solution:**
- Validate outputs between agents
- Each agent reads source code directly, not previous agent's summary

## Glyph Budget (MANDATORY for all multi-agent workflows)

Every agent in a parallel workflow MUST:
1. Write detailed findings to a file
2. Return ONLY: file path + 1-sentence summary (max 50 words)
3. Never include analysis in the return message

This prevents lead agent context overflow regardless of how many agents run.

See `context-weaving` skill for the full Glyph Budget protocol and pre-spawn checklist.

## Inscription Protocol (MANDATORY)

**RULE: `TeamCreate` (any count) OR `Task` x 3+ agents → `inscription.json` REQUIRED. No exceptions.**

```
TeamCreate → inscription.json REQUIRED (always, any teammate count)
Task x 3+  → inscription.json REQUIRED (parallel agents)
Task x 1-2 → glyph budget only (inscription optional)
```

**Three steps:**
1. **Generate** `inscription.json` before spawning agents/teammates
2. **Inject** required sections + Seal Format into each agent prompt
3. **Validate** output files after completion (circuit breaker → per-file → gap report)

Agents send structured **Seal** messages (key-value: file, sections, findings, evidence-verified, confidence, self-reviewed, summary). TaskList `completed` is authoritative; Seal is supplementary metadata.

Full spec: [Inscription Protocol](references/inscription-protocol.md)

## Structured Reasoning Integration

Multi-agent workflows benefit from structured reasoning at key decision points.

**Three reasoning checkpoints for lead agents:**

| Checkpoint | When | Key Action |
|-----------|------|------------|
| Pre-spawn | Before launching agents | 8-thought checklist (see `context-weaving`) |
| Mid-monitor | During agent execution | Intervene on timeout, clarification requests, partial failures |
| Post-aggregate | After collecting all outputs | Resolve conflicts between agents using branching analysis |

Full protocol: [Structured Reasoning](references/structured-reasoning.md)

## References

- [Structured Reasoning](references/structured-reasoning.md) — Reasoning principles for lead + teammate reasoning
- [Inscription Protocol](references/inscription-protocol.md) — Output validation for all multi-agent workflows
- [Prompt Weaving](references/prompt-weaving.md) — 7-section prompt template, context rot prevention, instruction anchoring
- [Truthsight Pipeline](references/truthsight-pipeline.md) — 4-layer verification spec
- [Verifier Prompt](references/verifier-prompt.md) — Smart Verifier prompt template
- Companion: `context-weaving` (Glyph Budget, pre-spawn checklist)
- Review workflow: `rune-circle` skill

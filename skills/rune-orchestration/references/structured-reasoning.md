# Structured Reasoning

> Reasoning principles for lead agents and Runebearer teammates in multi-agent workflows.

## Core Principle

Instead of making orchestration decisions in a single pass, apply numbered reasoning steps with revision permission. This catches errors before they cascade through the multi-agent workflow.

## Three Reasoning Checkpoints

### 1. Pre-Spawn (Lead Agent)

Before launching agents, use the 8-thought pre-spawn checklist from `context-weaving`:

1. Count and estimate token impact
2. Choose strategy (budget only vs inscription)
3. Plan output directory
4. Verify protocol injection
5. Plan post-completion validation
6. Revision checkpoint (merge/split agents)
7. Fallback strategies
8. Verification planning

### 2. Mid-Monitor (Lead Agent)

During agent execution, the lead monitors via TaskList and intervenes when:

| Signal | Action |
|--------|--------|
| Task stale > 5 minutes | Check teammate status, consider timeout |
| Tier 2 clarification request | Respond to teammate question |
| Agent crash (task abandoned) | Decide: retry or mark partial |
| Multiple agents flagging same file | Note for dedup during aggregation |

### 3. Post-Aggregate (Lead Agent)

After collecting all outputs, resolve conflicts using branching analysis:

```
Thought 1: Read TOME.md summary
Thought 2: Identify conflicting findings (same file, different severity)
Thought 3: Apply priority hierarchy (security P1 > performance P1)
Thought 4: [Branch A] What if we keep security finding?
Thought 5: [Branch B] What if we keep performance finding?
Thought 6: Decision — keep both if different issues, merge if same
```

## Teammate Self-Review

Each Runebearer performs ONE reasoning pass on their output before sending the Seal:

```
1. Count my findings: P1={n}, P2={n}, P3={n}
2. For each P1: does my Rune Trace match what I read in the source file?
3. For each P2: is the file:line reference correct?
4. Any findings I'm uncertain about → DELETE or downgrade to P3
5. Update confidence score based on this review
```

This is embedded inline in Runebearer prompts — no external file read needed.

## When to Use Structured Reasoning vs. Lookup Tables

| Use Structured Reasoning | Use Lookup Table |
|-------------------------|-----------------|
| Trade-offs with uncertainty | Deterministic mappings |
| Conflicting agent findings | File pattern → agent mapping |
| Partial failure recovery | Confidence → spot-check count |
| Scope revision mid-work | Priority hierarchy |
| Novel situations | Repeated patterns |

## Integration with Sequential Thinking MCP

If the `mcp__sequential-thinking__sequentialthinking` tool is available, use it for the pre-spawn checklist and post-aggregate conflict resolution. The structured reasoning checkpoints map directly to Sequential Thinking parameters:

| Checkpoint | `thoughtNumber` range | `totalThoughts` |
|-----------|----------------------|-----------------|
| Pre-spawn | 1-8 | 8 |
| Mid-monitor | Varies | Varies (per intervention) |
| Post-aggregate | 1-6 | 6 (adjust for conflicts) |

Use `isRevision: true` when reconsidering a decision. Use `branchFromThought` when comparing alternatives.

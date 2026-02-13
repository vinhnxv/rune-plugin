# Overflow Wards

> Detailed pre-summon protocol and Glyph Budget enforcement for multi-agent workflows.

## Glyph Budget Injection Text

**Copy-paste this into EVERY agent prompt** when summoning in a multi-agent workflow:

```
GLYPH BUDGET PROTOCOL (MANDATORY):
- Write ALL detailed findings to: {output-directory}/{agent-name}.md
- Return to caller ONLY: the output file path + 1-sentence summary (max 50 words)
- DO NOT include full analysis, code examples, or detailed recommendations in return message

Example return:
"Findings written to {output-directory}/{agent-name}.md. Found 2 P1 issues (SQL injection in queries, missing auth check) and 4 P2 issues across 3 files."
```

## How to Inject

When calling the Task tool, append the protocol to the prompt:

```
Task(agent-name, "
[Your actual review/analysis prompt here]

GLYPH BUDGET PROTOCOL (MANDATORY):
- Write ALL detailed findings to: tmp/reviews/142/ward-sentinel.md
- Return to caller ONLY: the output file path + 1-sentence summary (max 50 words)
- DO NOT include full analysis in return message
")
```

This works for ALL agent types because it's part of the prompt, not the agent definition.

## Token Impact

| Scenario | Tokens per agent return | 10 agents total |
|----------|------------------------|-----------------|
| Without Glyph Budget | 3,000-5,000 | 30,000-50,000 |
| With Glyph Budget | 100-200 | 1,000-2,000 |
| **Savings** | **2,800-4,800** | **28,000-48,000** |

With a 200k context window and ~30k base context, Glyph Budget is the difference between fitting 10 agents comfortably and overflowing at 7.

## Runebinder Invocation

After all agents complete, use the Runebinder to process raw files:

### When to Aggregate

| Raw files | Action |
|-----------|--------|
| 1-3 files | Read directly (aggregator adds overhead) |
| 4+ files | Summon Runebinder agent |
| 10+ files | MUST summon Runebinder (never read all directly) |

### How to Invoke

```
Task(rune:utility:runebinder, "
Read all findings from {output-directory}/
Write TOME.md with deduplicated, prioritized findings.
Skip non-findings files: TOME.md, truthsight-report.md
")
```

### After Aggregation

Read ONLY the TOME.md file. Do NOT also read raw files (that defeats the purpose).

**Fallback**: If the Runebinder fails, read raw files ONE AT A TIME, not all at once.

## Decision Tree Summary

```
About to summon agents?
├── Rune command (any agent count)
│   └── Agent Teams + Glyph Budget + inscription.json REQUIRED.
└── Custom workflow (3+ agents)
    └── Agent Teams + Glyph Budget + inscription.json REQUIRED.
```

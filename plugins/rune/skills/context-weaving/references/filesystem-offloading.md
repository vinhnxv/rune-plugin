# Filesystem Offloading

> Write tool outputs to files instead of keeping them in context.

## Core Principle

Tool outputs consume up to 83.9% of context in long sessions. Offloading large outputs to files keeps the context window lean.

## When to Offload

| Output Size | Action |
|------------|--------|
| < 10 lines | Keep inline |
| 10-50 lines | Consider offloading |
| > 50 lines | MUST offload to file |
| Agent output | Offload (via Glyph Budget) |

## Offload Patterns

### 1. Tool Output Offloading

When a tool returns a large result:

```
1. Write output to tmp/{workflow}/{descriptive-name}.md
2. Keep in context: "Output written to {path}. Key: {1-line summary}"
3. Read the file later only when needed
```

### 2. Agent Output Offloading (Glyph Budget)

Every agent in a multi-agent workflow writes to file:

```
Agent writes to: tmp/reviews/{pr}/{agent-name}.md
Returns to the Tarnished: "Findings at {path}. 2 P1, 4 P2 issues." (max 50 words)
```

### 3. Scratch Pad for Cross-Session State

Use `tmp/scratch/` for state that needs to persist across compression cycles:

```
tmp/scratch/
├── session-{timestamp}.md     # Compressed session summaries
├── decisions.md               # Key decisions made
└── file-trail.md              # Files read/modified
```

### 4. Research Output Offloading

Research agents write to dedicated directories:

```
tmp/research/
├── best-practices.md
├── framework-docs.md
└── repo-analysis.md
```

Lead reads files on-demand, not all at once.

## Directory Conventions

| Workflow | Directory | Lifecycle |
|----------|----------|-----------|
| Reviews | `tmp/reviews/{pr}/` | Ephemeral (per-PR) |
| Audits | `tmp/audit/{id}/` | Ephemeral (per-audit) |
| Research | `tmp/research/` | Ephemeral (per-plan) |
| Work | `tmp/work/` | Ephemeral (per-task) |
| Scratch | `tmp/scratch/` | Session-lived |

All `tmp/` directories are ephemeral — they can be safely deleted after the workflow completes.

## Anti-Pattern: Reading Everything

```
# BAD — reads all files into context
Read tmp/reviews/142/forge-warden.md
Read tmp/reviews/142/ward-sentinel.md
Read tmp/reviews/142/pattern-weaver.md
Read tmp/reviews/142/glyph-scribe.md
Read tmp/reviews/142/knowledge-keeper.md

# GOOD — read the aggregated summary only
Read tmp/reviews/142/TOME.md
```

If you need detail on a specific finding, read ONE raw file at a time.

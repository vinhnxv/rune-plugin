# Escalation Matrix — Failure Response Guide

Use this reference when systematic debugging is insufficient or when failure count
exceeds the investigation threshold. Escalation is a feature, not a failure.

## Decision Table: Escalate vs Investigate

| Failure Count | Decision | Rationale |
|--------------|----------|-----------|
| 1st | Retry with careful error reading | Single failures are often transient |
| 2nd | Phase 1 (Observe) — read exact error, check recent changes | Repetition signals a real problem |
| 3rd | Full 4-phase systematic debugging | Three failures = systematic issue |
| 4th | Continue debugging if progress made; escalate if stuck | Progress check |
| 5th | **Escalate to Tarnished** with complete debug log | Diminishing returns on solo investigation |
| 6th | Continue only if Tarnished provides new direction | Do not spin alone |
| 7th | **Create blocking task** — human intervention required | Agent cannot resolve |

### When to Escalate Earlier (skip to 5th-failure actions)

- You've reached Phase 4 but the fix makes things worse
- The error is in a file marked read-only by inscription.json (another worker owns it)
- The failure is non-deterministic and cannot be reproduced in isolation
- The error message contains "permission denied", "not found in PATH", or environment variables
- You cannot determine what the "last good state" was (Phase 1 fails)

---

## Escalation Level 1: Inform the Tarnished (5th failure)

Send a structured debug report via `SendMessage`. Include ALL of the following:

### SendMessage Template (5th failure)

```
SendMessage({
  type: "message",
  recipient: "tarnished",
  content: `
Debug escalation: task #${taskId} — ${failureCount} attempts failed.

## Debug Log

**Phase 1 — Observation**:
- First error: {exact error message at file:line}
- Last good state: {commit hash or "unknown"}
- Recent changes: {N files by {authors}}
- Cascading: {yes/no}

**Phase 2 — Narrowing**:
- Bisection result: {minimal reproducing change or "could not isolate"}
- Layer: {data|logic|integration|environment}
- Deterministic: {yes|no}

**Phase 3 — Hypothesis**:
- Hypothesis: {one sentence}
- Disproof test: {what was run}
- Result: {confirmed|disproved|inconclusive}

**Phase 4 — Fix attempts** ({N} attempts):
1. {what was tried} → {result}
2. {what was tried} → {result}

## Blocker

{One sentence describing what you cannot determine}

## Request

{What information or action you need from the Tarnished}
  `,
  summary: "Debug escalation task #${taskId} — ${failureCount} failures"
})
```

### What NOT to include in escalation

- Do NOT send the full file content (too much context — cite line numbers instead)
- Do NOT send stack traces longer than 20 lines (truncate with "... [N lines omitted]")
- Do NOT escalate without completing at least Phase 1 (Observe) first

---

## Escalation Level 2: Create Blocking Task (7th failure)

When human intervention is required, create a blocking task with full context so the next
agent or human can pick up without starting over.

### TaskCreate Template (7th failure)

```javascript
TaskCreate({
  subject: "BLOCKED: Investigate persistent failure in task #${originalTaskId}",
  description: `
## Context

Task #${originalTaskId} (${taskSubject}) failed ${failureCount} times.
Systematic debugging exhausted — human or senior agent review required.

## Failure Summary

**Error**: {exact first error at file:line}
**Layer**: {data|logic|integration|environment}
**Deterministic**: {yes|no}

## Investigation Completed

### Phase 1 — Observation Log
{paste Phase 1 output}

### Phase 2 — Narrowing Log
{paste Phase 2 output}

### Phase 3 — Hypothesis Log
{paste Phase 3 output — all attempts}

### Fix Attempts
1. {what was tried} → {result}
2. {what was tried} → {result}
...

## What We Know

- {fact 1}
- {fact 2}

## What We Don't Know

- {unknown 1}
- {unknown 2}

## Suggested Next Steps

1. {specific action that might unblock}
2. {alternative approach}

## Files Involved

- {file:line — exact location of failure}
- {file:line — related code}
  `,
  activeForm: "Investigating persistent failure from task #${originalTaskId}"
})
```

After creating the blocking task:
1. Mark the original task as `completed` with a note: "Blocked — see task #${blockingTaskId}"
2. Send a final `SendMessage` to the Tarnished:

```javascript
SendMessage({
  type: "message",
  recipient: "tarnished",
  content: `Blocking task #${blockingTaskId} created for task #${originalTaskId}. ${failureCount} attempts exhausted systematic debugging. Human intervention required. Original task marked complete with blocker note.`,
  summary: "Blocking task created for unresolvable failure"
})
```

---

## Information Quality for Escalation

Escalation messages are only useful if they contain **evidence**, not theories.

### Good escalation (evidence-based)

> "Ward check fails at `src/auth.py:42` with `NameError: name 'session' is not defined`.
> The `session` variable was removed in commit `abc1234` (task #3 — trial-forger).
> I cannot import it without modifying auth.py, which is owned by trial-forger per inscription.json."

### Bad escalation (theory-based)

> "I think there might be a naming conflict. Something seems off with the auth module.
> Maybe the session handling changed? I've tried a few things but nothing works."

**Rule**: Every claim in an escalation message must be backed by a cited command output or file:line reference.

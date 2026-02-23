---
name: systematic-debugging
description: |
  Use when a worker hits repeated failures (3+ attempts on the same task), when test
  failures have unclear root causes, when build errors persist after obvious fixes,
  when runtime behavior doesn't match expectations, or when "it works locally but fails
  in CI." Also use when test-failure-analyst returns LOW confidence, when ward check
  fails after a fix attempt, or when mend-fixer cannot reproduce a finding.
  Provides a 4-phase debugging methodology adapted for multi-agent context.
  Keywords: debug, troubleshoot, root cause, bisect, failure, retry, stuck, broken build,
  test failure, runtime error, unexpected behavior, regression, intermittent, flaky,
  can't reproduce, error message, stack trace, investigation.
user-invocable: false
disable-model-invocation: false
---

# Systematic Debugging

Adapted from superpowers' 4-phase methodology for Rune's multi-agent orchestration context.

## Iron Law

> **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST** (DBG-001)
>
> This rule is absolute. "I think I know what's wrong" is not investigation.
> Evidence first, hypothesis second, fix third.

## Activation Triggers

This skill auto-activates when:
- A rune-smith worker fails the same task 3+ times
- Ward check fails after a fix attempt
- test-failure-analyst returns LOW confidence classification
- A mend-fixer cannot reproduce the reported finding
- Build/test output contains "error" but the cause is ambiguous

## Phase 1: Observe — Gather Evidence (NOT theories)

DO NOT hypothesize yet. Only collect facts.

1. **Read the EXACT error message** — full stack trace, not just the summary line
2. **Identify the FIRST error** — cascading failures mislead; find the root
3. **Record what changed**: `git diff HEAD~3` or check recent task completions
4. **Record the last known good state**: When did this last work?
5. **Check git log** for recent changes to affected files: `git log --oneline -10 -- <file>`
6. **Check if another worker modified a shared file**: `git blame <file> | head -20`

**Output format**:
```
Observation Log:
- First error: {exact message at file:line}
- Last good state: {commit hash or "unknown"}
- Recent changes: {N files changed by {who}}
- Cascading: {yes/no — are subsequent errors caused by the first?}
```

## Phase 2: Narrow — Bisect the Problem Space

Binary search through the problem space:

1. **Code bisection**:
   - Comment out half the changes, re-test
   - Narrow to the minimal reproducing change
   - `git stash` to test with/without local changes

2. **Layer isolation**:
   - Is it a **data** problem? (check inputs, fixtures, test data)
   - Is it a **logic** problem? (check transformations, conditionals)
   - Is it an **integration** problem? (check boundaries, APIs, imports)
   - Is it an **environment** problem? (check versions, paths, permissions)

3. **Time isolation**:
   - `git bisect start HEAD <last-known-good>` to find breaking commit
   - Check if the failure is intermittent (run 3x to confirm determinism)

**Output format**:
```
Narrowing Log:
- Bisection result: {minimal reproducing change}
- Layer: {data|logic|integration|environment}
- Deterministic: {yes|no — does it fail every time?}
```

## Phase 3: Hypothesize — Form ONE Testable Theory

Based on Phase 2 evidence:

1. Form a **SINGLE** hypothesis (not multiple)
2. Design a test that would **DISPROVE** the hypothesis
3. Run the test
4. If **disproved**: Return to Phase 2 with the new evidence
5. If **confirmed**: Proceed to Phase 4

**Critical rule**: Do NOT skip to Phase 4 based on "it's probably this."
Your hypothesis must survive a disproof test.

**Output format**:
```
Hypothesis: {one sentence}
Disproof test: {what you ran}
Result: {confirmed|disproved}
```

## Phase 4: Fix — Minimal Change to Address Root Cause

1. Fix the **ROOT CAUSE**, not the symptom
2. Write a test that would have caught this failure
3. Verify the fix doesn't break adjacent functionality
4. Apply Fresh Evidence Gate (Inner Flame Layer 1.5):
   - Cite exact command + output proving the fix works
   - No "should work" or "probably fixed"
5. Document what you learned (for Echo persistence)

### Defense-in-Depth (Post-Fix)

After fixing, add defensive layers at the point of failure:
- **Input validation** at the boundary where bad data entered
- **Assertion** at the point where the invariant was violated
- **Test** covering the specific failure mode

For detailed multi-layer defense strategy, see [defense-in-depth.md](references/defense-in-depth.md).

## Escalation Rules

| Attempt | Action | Debug Phase |
|---------|--------|-------------|
| 1st failure | Retry with careful error reading | None |
| 2nd failure | Re-read error, check recent changes | Phase 1 (Observe) |
| 3rd failure | Full systematic debugging | Phase 1-4 |
| 5th failure | Escalate to Tarnished with ALL debug logs | — |
| 7th failure | Create blocking task — human intervention needed | — |

For full escalation templates and messaging formats, see [escalation-matrix.md](references/escalation-matrix.md).

## Multi-Agent Debugging Context

When debugging in a team workflow:
- **Check file ownership**: Did another worker modify a shared file? (`git blame`)
- **Check task dependencies**: Is the failure caused by an incomplete prerequisite task?
- **Check inscription.json**: File ownership conflicts between workers
- **Use SendMessage**: Ask the Tarnished about cross-worker state
- **Check echoes**: Has this failure pattern been seen before? (`echo_search`)

## Rationalization Red Flags

| Rationalization | Counter |
|----------------|---------|
| "I think I know what's wrong" | Thinking is not evidence. Run Phase 1. |
| "Let me just try this quick fix" | Quick fixes mask root causes. Run Phase 2. |
| "It's probably a test environment issue" | "Probably" is not evidence. Isolate the layer. |
| "This worked before, something else must have changed" | Find WHAT changed. `git diff`. |
| "I'll add a try/catch and move on" | Exception swallowing hides bugs. Find the cause. |

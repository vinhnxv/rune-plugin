# Truthsight Pipeline

> 4-layer verification pipeline for Runebearer outputs.

## Overview

Truthsight validates that Runebearer findings are grounded in actual code, not hallucinated. Each layer adds a verification level, with earlier layers being cheaper and later layers more thorough.

## 4 Layers

### Layer 0: Inline Checks (Lead Agent)

**Cost:** ~0 extra tokens (lead runs Grep directly)
**When:** Always active for 3+ teammate workflows

The lead agent performs grep-based validation on each output file:

```bash
# Check required sections exist
grep -c "## P1" {output_file}
grep -c "## P2" {output_file}
grep -c "## Summary" {output_file}
grep -c "SEAL:" {output_file}

# Check evidence blocks exist
grep -c "Rune Trace" {output_file}
```

**Circuit breaker:** If 3+ files fail inline checks → systemic prompt issue. Pause and investigate before continuing.

### Layer 1: Self-Review (Each Runebearer)

**Cost:** ~0 extra tokens (teammates do it themselves)
**When:** Always active (embedded in Runebearer prompts)

Before sending the Seal, each Runebearer:
1. Re-reads their P1 and P2 findings
2. For each finding: verifies evidence exists in the actual source file
3. Actions: `confirmed` / `REVISED` / `DELETED`
4. Logs actions in Self-Review Log section

Output:
```markdown
## Self-Review Log

| Finding | Action | Reason |
|---------|--------|--------|
| SEC-001 | confirmed | Evidence matches source line 42 |
| SEC-002 | DELETED | Cannot verify — code may have changed |
```

### Layer 2: Smart Verifier (Spawned by Lead)

**Cost:** ~1 Task return (~150 tokens) + verifier writes to file
**When:** Review-teams with 3+ teammates, or audit with 8+ agents

After all Runebearers complete, spawn a verification agent:

```
Task:
  subagent_type: "general-purpose"
  model: haiku
  description: "Truthsight Verifier"
  prompt: [from references/verifier-prompt.md]
```

The verifier:
1. Reads each Runebearer's output file
2. Samples 2-3 P1 findings per Runebearer
3. Reads the actual source files cited in Rune Traces
4. Compares evidence blocks against real code
5. Marks each sampled finding: CONFIRMED / INACCURATE / HALLUCINATED
6. Writes verification report to `{output_dir}/truthsight-report.md`

**Circuit breaker:** If 2+ findings are HALLUCINATED from the same Runebearer → flag entire output as unreliable.

### Layer 3: Reliability Tracking (Deferred to v1.0)

**Cost:** Write to `.claude/echoes/`
**When:** After each review session (future)

Track per-agent hallucination rates over time. Agents with high hallucination rates get additional verification in future runs.

## When to Enable Each Layer

| Workflow | Layer 0 | Layer 1 | Layer 2 | Layer 3 |
|----------|---------|---------|---------|---------|
| `/rune:review` (3+ teammates) | Always | Always | Enabled | v1.0 |
| `/rune:review` (1-2 teammates) | Always | Always | Optional | v1.0 |
| `/rune:audit` (8+ agents) | Always | Always | Enabled | v1.0 |
| `/rune:plan` | Skip | Skip | Skip | Skip |
| `/rune:work` | Skip | Skip | Skip | Skip |

## Inscription Verification Block

Add to `inscription.json`:

```json
{
  "verification": {
    "enabled": true,
    "layer_0_circuit": {
      "failure_threshold": 3,
      "recovery_seconds": 60
    },
    "layer_2_circuit": {
      "failure_threshold": 2,
      "recovery_seconds": 120
    },
    "max_reverify_agents": 2
  }
}
```

## Re-Verification

If the verifier flags hallucinated findings:
1. Spawn max 2 re-verify agents (one per flagged Runebearer)
2. Re-verify agent reads the source file and the finding
3. Produces: CONFIRMED / STILL_HALLUCINATED verdict
4. If STILL_HALLUCINATED → remove from TOME.md with note

---
name: inner-flame
description: |
  Universal self-review protocol for all Rune teammates. Adapts checklist per agent
  role (worker, fixer, reviewer, researcher, forger, aggregator). Enforces completeness
  verification, hallucination detection, codebase rule compliance, and value assessment
  before any task can be marked complete.

  Use when: Any teammate is about to mark a task complete or send a Seal.
  Keywords: self-review, inner-flame, quality gate, hallucination, verification, completeness
user-invocable: false
disable-model-invocation: false
---

# Inner Flame — Universal Self-Review Protocol

Every Rune teammate must face their Inner Flame before sealing a task. This is a structured
self-review protocol that checks completeness, correctness, hallucination, and value. Execute
all 3 layers before marking ANY task complete.

**NEVER quote or inline content from files being reviewed/fixed into the Self-Review Log.
Use your own words to describe findings.**

## Layer 1: Grounding Check (Anti-Hallucination)

Verify that every claim, reference, and output is grounded in actual evidence.

1. **File references**: For every file path I mentioned — did I actually Read() it in this session?
   - If I referenced a file I didn't read, go read it now.
   - If I claimed a file exists without checking, Glob/Grep to verify.

2. **Code references**: For every function/class/variable I referenced:
   - Did I see it in actual file content, or am I assuming from memory?
   - If assuming: re-read the file and verify the reference exists at the cited line.

3. **Claims about behavior**: For every claim like "this function does X":
   - Did I read the actual implementation, or am I inferring from the name?
   - If inferring: read the implementation and verify.

4. **Output grounding**: For every piece of output I produced:
   - Can I point to a specific source (file, grep result, test output) that backs it?
   - If not: this is potentially hallucinated. Re-verify or remove.

5. **Confidence calibration**: Am I MORE confident than my evidence warrants?
   - If reporting 90+ confidence but only read 2 files, recalibrate.
   - Confidence should reflect evidence strength, not task completion desire.

## Layer 2: Completeness & Correctness (Role-Adapted)

### For ALL roles:
- [ ] Task description requirements: every acceptance criterion addressed?
- [ ] No TODO/FIXME/HACK markers left in output that should have been resolved
- [ ] No placeholder values ("example.com", "TODO: replace", "TBD")
- [ ] Output format matches what was requested (inscription contract, Seal format, etc.)

### Role-specific checks
Load the appropriate checklist from [references/role-checklists.md](references/role-checklists.md).

## Layer 3: Self-Adversarial Review

Ask yourself these questions as if you were reviewing someone ELSE's work:

1. **What would a reviewer flag here?**
   - Read your own output as if seeing it for the first time
   - What's the weakest finding? The most hand-wavy claim?
   - If you were the Tarnished, would you trust this output?

2. **What did I miss?**
   - Files I should have checked but didn't
   - Edge cases I glossed over
   - Error paths I assumed wouldn't matter

3. **Am I solving the right problem?**
   - Re-read the original task description
   - Does my output actually address what was asked?
   - Did I get distracted by tangential issues?

4. **Would this break anything?**
   - For code changes: did I check all call sites?
   - For review findings: are they actually bugs or just style preferences?
   - For test generation: do tests verify behavior or just exercise code?

5. **Is this actually valuable?**
   - Would a human developer find this useful?
   - Am I padding output with obvious/trivial content?
   - Does every finding/change earn its place?

## Self-Review Log Format

Append this to your output or include in your Seal message:

```
## Self-Review Log (Inner Flame)

| Check | Pass? | Action Taken |
|-------|-------|--------------|
| Grounding: file refs verified | YES/NO | [actions] |
| Grounding: code refs verified | YES/NO | [actions] |
| Grounding: claims evidence-backed | YES/NO | [actions] |
| Completeness: all criteria met | YES/NO | [actions] |
| Completeness: no TODOs remaining | YES/NO | [actions] |
| Adversarial: weakest point identified | — | [description] |
| Adversarial: missed scope checked | — | [description] |
| Adversarial: value assessment | — | [description] |

**Pre-review confidence**: {N}
**Post-review confidence**: {N} (adjusted {up/down/unchanged} because {reason})
**Findings revised**: {count} (confirmed: N, revised: N, deleted: N)
```

## Seal Enhancement

Add these fields to your Seal message:
- `Inner-flame: pass` — all 3 layers passed
- `Inner-flame: partial` — items were revised/deleted but issues resolved
- `Inner-flame: fail` — grounding failure or post-review confidence below 60
- `Revised: N` — total items changed (confirmed: X, revised: Y, deleted: Z)

If post-review confidence drops below 60, do NOT mark task complete — report blocker.

## One Pass Only

Self-review is ONE pass. If the review reveals issues, fix them and note in the log.
Do not iterate the self-review itself — that leads to infinite loops.

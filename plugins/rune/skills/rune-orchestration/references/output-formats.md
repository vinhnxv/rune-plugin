# Agent Output Formats

Each agent writes findings in a format matching its workflow type. All formats require **mandatory evidence blocks** (see Truthbinding Protocol in `inscription-protocol.md`).

## 1. Report Format (Reviews, Audits)

Used by workflows producing prioritized findings with P1/P2/P3 severity levels.

```markdown
# {Ash Name} Review

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
- Confidence: {0-100} — overall confidence in findings quality
  - 90-100: High — strong evidence, verified patterns, low false-positive risk
  - 70-89: Moderate — good evidence but some assumptions made
  - 50-69: Low — patterns detected but context may be missing
  - <50: Speculative — flag for human verification before acting on findings
- Confidence reason: {1-sentence explanation of why confidence is at this level}

### Confidence-Driven Behavior

Your confidence score should influence your behavior during review:

- **confidence >= 80**: Report findings normally. These are actionable.
- **confidence 50-79**: Prefix uncertain findings with `[NEEDS-VERIFY]` in the finding title.
  Explain what additional evidence would raise your confidence.
- **confidence < 50**: After scanning 50% of scope, STOP and report to the Tarnished:
  "My perspective may not apply well to this codebase — {reason}."
  Let the Tarnished decide whether to continue or reassign.

**Cross-check rule**: If your confidence is >= 80 but your evidence-verified ratio
is below 50%, your confidence is overestimated. Recalibrate downward.
```

### Enhanced Seal

The Seal at the end of each agent output includes confidence and file coverage metrics:

```json
{
  "findings": 7,
  "evidence_verified": true,
  "confidence": 85,
  "skimmed_files": 12,
  "deep_read_files": 4,
  "self_reviewed": true,
  "self_review_actions": "confirmed: 5, revised: 1, deleted: 1"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | integer 0-100 | Confidence score (see Confidence Reporting below) |
| `skimmed_files` | integer | Files structurally scanned but not fully read |
| `deep_read_files` | integer | Files fully analyzed line-by-line |

### Confidence Reporting

| Range | Label | Meaning |
|-------|-------|---------|
| 90-100 | High | Strong evidence, verified patterns, low false-positive risk |
| 70-89 | Moderate | Good evidence but some assumptions made |
| 50-69 | Low | Patterns detected but context may be missing, needs verification |
| <50 | Speculative | Flag for human review before acting on findings |

## 2. Research Format (Plans)

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
- Confidence: {0-100} — overall confidence in research quality
- Confidence reason: {why this score — what evidence supports it, what's missing}
- Key recommendation: {one-sentence summary}
- Files skimmed: {count} — files structurally scanned but not fully read
- Files deep-read: {count} — files fully analyzed
```

## 3. Status Format (Work)

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

## 4. Champion Solution Format (Arena)

Used by Solution Arena to present competing approaches for evaluation.

```markdown
# Solution: {name}

**Key Differentiator:** {what makes this approach unique}
**Primary Evidence:** {research finding supporting this approach}
**Known Trade-off:** {acknowledged weakness}

## Description
{2-3 sentence approach description}

## Design Decisions
- {fundamental decision 1}
- {fundamental decision 2}
```

## 5. Challenger Report Format (Arena)

Used by adversarial agents (devils-advocate, innovation-scout) to stress-test solutions.

```markdown
# {Challenger Name} Report

**Solutions Reviewed:** {N}/{total}

## Challenges

### {Solution Name}
- **[SEVERITY]** {challenge description}
  - **Evidence:** {codebase reference or research finding}
  - **Mitigation feasible?** {yes/no with explanation}
```

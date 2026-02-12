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
```

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
- Confidence: {high/medium/low}
- Key recommendation: {one-sentence summary}
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

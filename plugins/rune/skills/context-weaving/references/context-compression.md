# Context Compression

> Strategies for compressing session context during long coding sessions.

## When to Compress

| Message Count | Action |
|---------------|--------|
| < 30 | No compression needed |
| 30-49 | Optional — available if needed |
| 50-69 | Trigger compression |
| >= 70 | Force compression |

## Reasoning-Based Triggers

Watch for these quality signals:

| Signal | Meaning | Action |
|--------|---------|--------|
| Can't recall original task | Context rot | Trigger compression |
| Repeating same reasoning | Circular reasoning | Force compression |
| Re-reading files already discussed | Memory loss | Immediate compression |
| Agent responses getting verbose | Attention degradation | Compress, trim noise |

## Compression Strategy: Anchored Iterative Summarization

1. **Identify** messages that will be removed
2. **Extract** key information:
   - File modifications
   - Test results (pass/fail)
   - Decisions made
   - Error messages
3. **Merge** into existing summary sections (don't regenerate)
4. **Write** summary to: `tmp/scratch/session-{timestamp}.md`
5. **Continue** with compressed context

## Session Summary Format

```markdown
## Session Summary ({timestamp})

### State
- Phase: {current workflow phase}
- Current task: {description}

### Files Modified
| File | Change | Status |
|------|--------|--------|
| {path} | {description} | {pass/fail} |

### Key Decisions
- {decision 1}
- {decision 2}

### Current Error (if any)
```
{error message}
```

### Next Steps
1. {next action}
2. {following action}
```

## Context Fundamentals

**Core principle:** Find the smallest set of high-signal tokens that maximize desired outcomes.

| Component | Token Impact | Priority |
|-----------|-------------|----------|
| Tool Outputs | Grows rapidly (83.9%) | **Highest** — offload to files |
| Message History | Grows linearly | High — summarize older messages |
| Retrieved Documents | Variable | Medium — load on demand |
| System Prompt + Tools | Fixed | Low — already optimized |

**Attention mechanics:** Content in the middle receives less attention (Lost-in-Middle). Place critical info at beginning/end.

**Progressive disclosure:** Load information only when needed, not upfront.

## Quality Verification

After compression, verify with probes:

| Type | Example Question |
|------|-----------------|
| Recall | "What was the original error?" |
| Artifact | "Which files were modified?" |
| Continuation | "What should we do next?" |
| Decision | "Why this approach?" |

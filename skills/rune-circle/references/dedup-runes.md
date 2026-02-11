# Dedup Runes — Deduplication Hierarchy

> Rules for deduplicating findings when multiple Runebearers flag the same code.

## Deduplication Rules

When the Runebinder aggregates findings into TOME.md, it must deduplicate overlapping findings.

### Same File + Same Line Range (5-line window)

If two Runebearers flag the same file within a 5-line range:

| Runebearer A | Runebearer B | Action |
|-------------|-------------|--------|
| Ward Sentinel (P1) | Forge Warden (P2) | Keep Ward Sentinel's (security wins) |
| Forge Warden (P1) | Pattern Weaver (P1) | Keep both (different perspectives) |
| Pattern Weaver (P2) | Glyph Scribe (P2) | Merge if same issue, keep both if different |
| Any (P1) | Any (P3) | Keep only P1 |

### Priority Hierarchy

```
Ward Sentinel > Forge Warden > Lore Keeper > Pattern Weaver > Glyph Scribe
SEC > BACK > DOC > QUAL > FRONT
```

When the same issue is found by multiple Runebearers:
1. Keep the finding from the highest-priority Runebearer
2. Note in TOME.md which other Runebearers also flagged it
3. Use the highest severity (P1 > P2 > P3)

### Finding ID Prefixes

Each Runebearer uses a unique prefix for finding IDs:

| Runebearer | Prefix | Example |
|-----------|--------|---------|
| Ward Sentinel | `SEC-` | `SEC-001` |
| Forge Warden | `BACK-` | `BACK-001` |
| Pattern Weaver | `QUAL-` | `QUAL-001` |
| Glyph Scribe | `FRONT-` | `FRONT-001` |
| Lore Keeper | `DOC-` | `DOC-001` |

### Dedup Algorithm

```
for each finding in all_findings:
  key = (file, line_range_bucket(line, 5))

  if key already in seen:
    existing = seen[key]
    if finding.severity > existing.severity:
      replace existing with finding
    elif finding.runebearer_priority > existing.runebearer_priority:
      replace existing with finding
    else:
      add finding.runebearer to existing.also_flagged_by
  else:
    seen[key] = finding
```

### TOME.md Format After Dedup

```markdown
# TOME — Review Summary

**PR:** #{pr-number}
**Date:** {timestamp}
**Runebearers:** {list of active Runebearers}

## P1 (Critical) — {count}

- [ ] **[SEC-001] SQL Injection in user query** in `api/users.py:42`
  - **Runebearer:** Ward Sentinel (also flagged by: Forge Warden)
  - **Rune Trace:**
    ```python
    # Lines 40-45 of api/users.py
    query = f"SELECT * FROM users WHERE id = {user_id}"
    ```
  - **Issue:** Unparameterized query allows SQL injection
  - **Fix:** Use parameterized query: `query = "SELECT * FROM users WHERE id = %s"`

## P2 (High) — {count}

[findings...]

## P3 (Medium) — {count}

[findings...]

## Incomplete Deliverables

| Runebearer | Status | Impact |
|-----------|--------|--------|
| {name} | {timeout/crash/partial} | {uncovered scope} |

## Statistics

- Total findings: {count}
- Deduplicated: {removed_count} (from {original_count})
- Evidence coverage: {percentage}%
- Runebearers completed: {count}/{total}
```

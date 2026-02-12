# Dedup Runes — Deduplication Hierarchy

> Rules for deduplicating findings when multiple Tarnished flag the same code.

## Deduplication Rules

When the Runebinder aggregates findings into TOME.md, it must deduplicate overlapping findings.

### Same File + Same Line Range (5-line window)

If two Tarnished flag the same file within a 5-line range:

| Tarnished A | Tarnished B | Action |
|-------------|-------------|--------|
| Ward Sentinel (P1) | Forge Warden (P2) | Keep Ward Sentinel's (security wins) |
| Forge Warden (P1) | Pattern Weaver (P1) | Keep both (different perspectives) |
| Pattern Weaver (P2) | Glyph Scribe (P2) | Merge if same issue, keep both if different |
| Any (P1) | Any (P3) | Keep only P1 |

### Priority Hierarchy

**Default (built-in only):**

```
Ward Sentinel > Forge Warden > Knowledge Keeper > Pattern Weaver > Glyph Scribe
SEC > BACK > DOC > QUAL > FRONT
```

When the same issue is found by multiple Tarnished:
1. Keep the finding from the highest-priority Tarnished
2. Note in TOME.md which other Tarnished also flagged it
3. Use the highest severity (P1 > P2 > P3)

### Extended Hierarchy (with Custom Tarnished)

When custom Tarnished are configured in `rune-config.yml`, the dedup hierarchy is extended via `settings.dedup_hierarchy`. Custom prefixes are slotted into the hierarchy at the position specified by the user.

**Example extended hierarchy:**
```
SEC > COMP > BACK > RAIL > PERF > DOC > QUAL > FRONT
```

**Rules:**
- If `settings.dedup_hierarchy` is defined in config, use it as-is (user controls the order)
- If NOT defined, append custom prefixes AFTER built-in hierarchy (lowest priority):
  ```
  SEC > BACK > DOC > QUAL > FRONT > {custom_1} > {custom_2} > ...
  ```
- Every active Tarnished's prefix MUST appear in the hierarchy. Missing prefixes → warn and append at end
- Reserved built-in prefixes: `SEC`, `BACK`, `QUAL`, `FRONT`, `DOC` — cannot be used by custom Tarnished

### Finding ID Prefixes

Each Tarnished uses a unique prefix for finding IDs:

| Tarnished | Prefix | Example | Type |
|-----------|--------|---------|------|
| Ward Sentinel | `SEC-` | `SEC-001` | Built-in |
| Forge Warden | `BACK-` | `BACK-001` | Built-in |
| Pattern Weaver | `QUAL-` | `QUAL-001` | Built-in |
| Glyph Scribe | `FRONT-` | `FRONT-001` | Built-in |
| Knowledge Keeper | `DOC-` | `DOC-001` | Built-in |
| *(custom)* | *from config* | e.g., `DOM-001` | Custom |

Custom Tarnished define their prefix in `rune-config.yml` → `tarnished.custom[].finding_prefix`. Must be 2-5 uppercase chars and unique across all Tarnished.

### Dedup Algorithm

```
for each finding in all_findings:
  key = (file, line_range_bucket(line, 5))

  if key already in seen:
    existing = seen[key]
    if finding.severity > existing.severity:
      replace existing with finding
    elif finding.tarnished_priority > existing.tarnished_priority:
      replace existing with finding
    else:
      add finding.tarnished to existing.also_flagged_by
  else:
    seen[key] = finding
```

### TOME.md Format After Dedup

```markdown
# TOME — Review Summary

**PR:** #{pr-number}
**Date:** {timestamp}
**Tarnished:** {list of active Tarnished}

## P1 (Critical) — {count}

- [ ] **[SEC-001] SQL Injection in user query** in `api/users.py:42`
  - **Tarnished:** Ward Sentinel (also flagged by: Forge Warden)
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

| Tarnished | Status | Impact |
|-----------|--------|--------|
| {name} | {timeout/crash/partial} | {uncovered scope} |

## Statistics

- Total findings: {count}
- Deduplicated: {removed_count} (from {original_count})
- Evidence coverage: {percentage}%
- Tarnished completed: {count}/{total}
```

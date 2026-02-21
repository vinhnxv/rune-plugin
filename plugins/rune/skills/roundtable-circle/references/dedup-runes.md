# Dedup Runes — Deduplication Hierarchy

> Rules for deduplicating findings when multiple Ash flag the same code.

## Deduplication Rules

When the Runebinder aggregates findings into TOME.md, it must deduplicate overlapping findings.

### Same File + Same Line Range (5-line window)

If two Ash flag the same file within a 5-line range:

| Ash A | Ash B | Action |
|-------------|-------------|--------|
| Ward Sentinel (P1) | Forge Warden (P2) | Keep Ward Sentinel's (security wins) |
| Forge Warden (P1) | Pattern Weaver (P1) | Keep both (different perspectives) |
| Pattern Weaver (P2) | Glyph Scribe (P2) | Merge if same issue, keep both if different |
| Any (P1) | Any (P3) | Keep only P1 |

### Priority Hierarchy

**Default (built-in only):**

```
Ward Sentinel > Forge Warden > Veil Piercer > Knowledge Keeper > Pattern Weaver > Glyph Scribe > Codex Oracle
SEC > BACK > VEIL > DOC > QUAL > FRONT > CDX
```

When the same issue is found by multiple Ash:
1. Keep the finding from the highest-priority Ash
2. Note in TOME.md which other Ash also flagged it
3. Use the highest severity (P1 > P2 > P3)

### Extended Hierarchy (with Custom Ashes)

When custom Ash are configured in `talisman.yml`, the dedup hierarchy is extended via `settings.dedup_hierarchy`. Custom prefixes are slotted into the hierarchy at the position specified by the user.

**Example extended hierarchy:**
```
SEC > COMP > BACK > RAIL > PERF > DOC > QUAL > FRONT > CDX
```

**Rules:**
- If `settings.dedup_hierarchy` is defined in config, use it as-is (user controls the order)
- If NOT defined, append custom prefixes AFTER built-in hierarchy (lowest priority):
  ```
  SEC > BACK > VEIL > DOC > QUAL > FRONT > CDX > {custom_1} > {custom_2} > ...
  ```
- **External model prefix ordering (v1.57.0+):** CLI-backed Ash prefixes (from `ashes.custom[]` entries with `cli:` field) are positioned BELOW `CDX` in the default hierarchy. Built-in prefixes (`SEC`, `BACK`, `DOC`, `QUAL`, `FRONT`, `CDX`) MUST always precede external model prefixes. This enforcement applies ONLY to CLI-backed external model prefixes — agent-backed custom Ashes can be placed anywhere in a user-defined hierarchy.
  ```
  Default with external models:
  SEC > BACK > VEIL > DOC > QUAL > FRONT > CDX > {cli_ext_1} > {cli_ext_2} > {agent_custom_1} > ...
  ```
- Every active Ash's prefix MUST appear in the hierarchy. Missing prefixes → warn and append at end
- Prefix format: 2-5 uppercase alphanumeric characters (A-Z, 0-9)
- Reserved built-in prefixes: `SEC`, `BACK`, `VEIL`, `QUAL`, `FRONT`, `DOC`, `CDX` — cannot be used by custom Ash
- Reserved deep-audit prefixes (active only when `/rune:audit --deep`): `DEBT`, `INTG`, `BIZL`, `EDGE`, `CORR`, `FAIL`, `DSEC`, `DSGN`, `RSRC`, `OBSV`, `MTNB`
- **Note:** `CDX-DRIFT` is an internal Phase 5.6 finding ID used by the Codex gap analysis — it is NOT a custom Ash prefix

### Deep Audit Extended Hierarchy (v1.56.0+)

When `--deep` flag is active, the dedup hierarchy extends to include deep investigation prefixes:

**Standard hierarchy**: `SEC > BACK > VEIL > DOC > QUAL > FRONT > CDX`
**Deep hierarchy (full)**: `SEC > BACK > CORR > FAIL > DSEC > DEBT > INTG > BIZL > EDGE > VEIL > DSGN > RSRC > DOC > OBSV > MTNB > QUAL > FRONT > CDX`

**Which hierarchy is used where:**
- **Pass 1 Runebinder** (TOME-standard.md): Standard hierarchy
- **Pass 2 Runebinder** (TOME-deep.md): Deep sub-hierarchies (see below)
- **Merge Runebinder** (final TOME.md): Full extended hierarchy

**Merge hierarchy (cross-pass dedup):** `SEC > CORR > FAIL > DSEC > BACK > DSGN > RSRC > VEIL > OBSV > MTNB > DOC > QUAL > FRONT > CDX`

**Pass 2 sub-hierarchies:**
- Deep investigation sub-hierarchy: `DEBT > INTG > BIZL > EDGE`
- Deep dimension sub-hierarchy: `CORR > FAIL > DSEC > DSGN > RSRC > OBSV > MTNB`
- Combined deep hierarchy: `CORR > FAIL > DSEC > DEBT > INTG > BIZL > EDGE > DSGN > RSRC > OBSV > MTNB`

**Cross-pass dedup rules:**
- Same file:line, same issue → Deep finding SUPERSEDES standard (deeper analysis wins)
- Same file, different line → Both kept (different concerns)
- Same concern, different files → Both kept (cross-file pattern)
- Deep finding contradicts standard → Flag with CONFLICT marker for human review

### Finding ID Prefixes

Each Ash uses a unique prefix for finding IDs:

| Ash | Prefix | Example | Type |
|-----------|--------|---------|------|
| Ward Sentinel | `SEC-` | `SEC-001` | Built-in |
| Forge Warden | `BACK-` | `BACK-001` | Built-in |
| Veil Piercer | `VEIL-` | `VEIL-001` | Built-in |
| Pattern Weaver | `QUAL-` | `QUAL-001` | Built-in |
| Glyph Scribe | `FRONT-` | `FRONT-001` | Built-in |
| Knowledge Keeper | `DOC-` | `DOC-001` | Built-in |
| Codex Oracle | `CDX-` | `CDX-001` | Built-in |
| rot-seeker | `DEBT-` | `DEBT-001` | Deep-audit |
| strand-tracer | `INTG-` | `INTG-001` | Deep-audit |
| decree-auditor | `BIZL-` | `BIZL-001` | Deep-audit |
| fringe-watcher | `EDGE-` | `EDGE-001` | Deep-audit |
| truth-seeker | `CORR-` | `CORR-001` | Deep-dimension |
| ruin-watcher | `FAIL-` | `FAIL-001` | Deep-dimension |
| breach-hunter | `DSEC-` | `DSEC-001` | Deep-dimension |
| order-auditor | `DSGN-` | `DSGN-001` | Deep-dimension |
| ember-seer | `RSRC-` | `RSRC-001` | Deep-dimension |
| signal-watcher | `OBSV-` | `OBSV-001` | Deep-dimension |
| decay-tracer | `MTNB-` | `MTNB-001` | Deep-dimension |
| *(custom)* | *from config* | e.g., `DOM-001` | Custom |

Custom Ashes define their prefix in `talisman.yml` → `ashes.custom[].finding_prefix`. Must be 2-5 uppercase chars and unique across all Ashes.

### Veil Piercer vs. Other Ashes

Veil Piercer findings may CONTRADICT findings from other Ashes. This is intentional.

| Scenario | Resolution |
|----------|------------|
| Forge Warden: PASS on architecture, Veil Piercer: wrong architecture | Keep BOTH — Tarnished decides |
| Pattern Weaver: P2 YAGNI, Veil Piercer: P1 solving wrong problem | Veil Piercer wins (higher priority + higher severity) |
| Ward Sentinel: SEC finding, Veil Piercer: security model is wrong | Keep BOTH — different scopes |

Veil Piercer participates in the dedup hierarchy at position `SEC > BACK > VEIL > ...` for ordering and priority purposes. However, cross-Ash dedup (same-file, same-line suppression) rarely triggers for VEIL- findings because truth-telling operates at a different level of abstraction than technical review. A VEIL- finding about "this feature solves the wrong problem" and a BACK- finding about "this function has a null bug" on the same file are different perspectives, not duplicates. In the rare case of a genuine same-line overlap (e.g., both say "this code is unreachable"), VEIL wins over DOC/QUAL/FRONT/CDX but yields to SEC and BACK per the hierarchy.

### Dedup Algorithm

```
for each finding in all_findings:
  key = (file, line_range_bucket(line, 5))

  if key already in seen:
    existing = seen[key]
    if finding.severity > existing.severity:
      replace existing with finding
    elif finding.ash_priority > existing.ash_priority:
      replace existing with finding
    else:
      add finding.ash to existing.also_flagged_by
  else:
    seen[key] = finding
```

### TOME.md Format After Dedup

```markdown
# TOME — Review Summary

**PR:** #{pr-number}
**Date:** {timestamp}
**Ash:** {list of active Ash}

## P1 (Critical) — {count}

- [ ] **[SEC-001] SQL Injection in user query** in `api/users.py:42`
  - **Ash:** Ward Sentinel (also flagged by: Forge Warden)
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

| Ash | Status | Impact |
|-----------|--------|--------|
| {name} | {timeout/crash/partial} | {uncovered scope} |

## Statistics

- Total findings: {count}
- Deduplicated: {removed_count} (from {original_count})
- Evidence coverage: {percentage}%
- Ash completed: {count}/{total}
```

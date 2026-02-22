# Risk Context Template — Agent Prompt Injection

Template for injecting Goldmask risk data into agent prompts (forge, mend, inspect).
Callers render this template by replacing `{variable}` placeholders with actual data,
then append the rendered output to the agent's system prompt.

## Rendering Rules

1. **Conditional sections**: Only include a section if the corresponding data is available.
   If no data exists for a section, omit the section heading and all its content entirely.
2. **Empty result**: If ALL sections are empty (no risk-map, no wisdom, no blast radius),
   do NOT inject any risk context at all — skip the entire template.
3. **File filtering**: Only include entries relevant to the agent's assigned files.
   Do not include risk data for files outside the agent's scope.
4. **Staleness prefix**: If risk data is older than 3 days, prefix the section heading
   with `[STALE: {age_days}d]` to signal the data may be outdated.

## Template

Render the following sections in order. Skip any section where data is unavailable.

---

### Section 1: File Risk Tiers

**Data source**: `risk-map.json` — `files[]` array filtered to relevant files.

**Include when**: A `risk-map.json` is available AND at least one relevant file has a risk entry.

**Render as**:

```
## Risk Context (Goldmask)

### File Risk Tiers

| File | Risk Tier | Churn (90d) | Owners | Co-Change Cluster |
|------|-----------|-------------|--------|-------------------|
| `{file.path}` | {file.tier} | {file.metrics.frequency} commits | {file.metrics.ownership.distinct_authors} ({file.metrics.ownership.top_contributor}) | {co_change_summary} |
```

**Field mapping** (from `risk-map.json` schema):
- `{file.path}` — `files[].path`
- `{file.tier}` — `files[].tier` (CRITICAL, HIGH, MEDIUM, LOW, STALE)
- `{file.metrics.frequency}` — `files[].metrics.frequency` (commit count in window)
- `{file.metrics.ownership.distinct_authors}` — `files[].metrics.ownership.distinct_authors`
- `{file.metrics.ownership.top_contributor}` — `files[].metrics.ownership.top_contributor`
- `{co_change_summary}` — derived from `files[].co_changes[]`: list coupled file basenames with `coupling_pct >= 25%`, joined by `, `. If no co-changes, render `--`.

**Sort order**: CRITICAL first, then HIGH, MEDIUM, LOW, STALE. Within same tier, sort by `risk_score` descending.

---

### Section 2: Caution Zones

**Data source**: `wisdom-report.md` — parsed advisories filtered to relevant files.

**Include when**: A `wisdom-report.md` is available AND at least one relevant file has a wisdom advisory.

**Render as**:

```
### Caution Zones

- **`{file}`** -- {intent} intent (caution: {caution_score}). {advisory}
```

**Field mapping** (from `wisdom-report.md` format):
- `{file}` — file path from `WISDOM-{NNN}: {file}:{line_range}` heading
- `{intent}` — Design Intent value (CONSTRAINT, DEFENSIVE, WORKAROUND, etc.)
- `{caution_score}` — Caution Score value (0.XX format)
- `{advisory}` — plain-language summary from the "Caution Advisory" block quote

**Filtering**: Only include advisories where caution score >= 0.40 (MEDIUM or above).
If all relevant advisories are below 0.40, omit this section.

**Important instruction for the agent**: Preserve the original design intent of these code
sections. Your changes must not break the defensive, constraint, or compatibility behavior
described in the advisories.

---

### Section 3: Blast Radius

**Data source**: `GOLDMASK.md` — "Collateral Damage Assessment" section, or derived from
`risk-map.json` co-change clusters when GOLDMASK.md is unavailable.

**Include when**: Blast radius data is available for at least one relevant file.

**Render as**:

```
### Blast Radius

- Scope: **{blast_scope}** ({affected_file_count} files affected)
- Co-change clusters: {cluster_count}
- High-risk clusters: {high_risk_clusters}
```

**Field mapping**:
- `{blast_scope}` — WIDE, MODERATE, CONTAINED, or ISOLATED (from GOLDMASK.md `BLAST-RADIUS` heading, or derived from co-change graph density)
- `{affected_file_count}` — count of files in co-change clusters that include relevant files
- `{cluster_count}` — number of distinct co-change clusters touching relevant files
- `{high_risk_clusters}` — comma-separated list of cluster names where coupling_pct >= 50%

**Derivation from risk-map.json** (when GOLDMASK.md unavailable):
- WIDE: any file has >= 5 co-change edges with coupling_pct >= 25%
- MODERATE: any file has 3-4 co-change edges
- CONTAINED: any file has 1-2 co-change edges
- ISOLATED: no co-change edges for any relevant file

---

## Complete Rendered Example

Below is what the injected prompt section looks like when all data is available:

```markdown
## Risk Context (Goldmask)

### File Risk Tiers

| File | Risk Tier | Churn (90d) | Owners | Co-Change Cluster |
|------|-----------|-------------|--------|-------------------|
| `src/auth/middleware.py` | CRITICAL | 18 commits | 1 (alice) | token.py, test_auth.py |
| `src/api/users.py` | HIGH | 12 commits | 3 (bob) | serializers/user.py |
| `src/utils/helpers.py` | LOW | 2 commits | 2 (charlie) | -- |

### Caution Zones

- **`src/auth/middleware.py`** -- DEFENSIVE intent (caution: 0.85). Guards against null SSO accounts. Removing this check re-exposes CVE-2025-1234.
- **`src/api/users.py`** -- CONSTRAINT intent (caution: 0.72). RFC-2822 email validation required by compliance audit.

**IMPORTANT**: Preserve the original design intent of these code sections. Your changes must not break the defensive, constraint, or compatibility behavior described above.

### Blast Radius

- Scope: **MODERATE** (8 files affected)
- Co-change clusters: 2
- High-risk clusters: auth-module (65%)
```

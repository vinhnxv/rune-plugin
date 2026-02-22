# Data Discovery Protocol — Shared Goldmask Output Lookup

Find and reuse existing Goldmask outputs from prior workflow runs. Pure filesystem
reads — no agents, no git. Callers use this to avoid redundant lore-analyst spawns.

## Type Contract

```
discoverGoldmaskData(options: DiscoveryOptions) -> GoldmaskData | null

DiscoveryOptions:
  needsRiskMap: boolean       # Require risk-map.json (default: true)
  needsGoldmask: boolean      # Require GOLDMASK.md (default: false)
  needsWisdom: boolean        # Require wisdom-report.md (default: false)
  maxAgeDays: number          # Skip outputs older than N days (default: 7)
  scopeFiles: string[]        # Current scope files — for overlap validation (default: [])

GoldmaskData:
  riskMap: string             # Raw JSON string from risk-map.json
  riskMapPath: string         # Absolute path to source file
  goldmaskMd: string          # Raw markdown string from GOLDMASK.md
  goldmaskMdPath: string      # Absolute path to source file
  wisdomReport: string        # Raw markdown string from wisdom-report.md
  wisdomReportPath: string    # Absolute path to source file

Only requested fields are populated. Missing fields are absent (not null).

IMPORTANT: All returned strings are RAW file content. Callers MUST:
  - JSON.parse() for riskMap (wrap in try/catch)
  - Validate parsed data before use (schema check)
```

## Search Order

Directories are searched in priority order. Within each search path, candidate
directories are sorted by `risk-map.json` file mtime descending (not directory
mtime — handles atomic-write edge case on macOS where dir mtime does not update
when nested files change via tmp+rename).

| Priority | Path Pattern                   | Content Available                    |
|----------|--------------------------------|--------------------------------------|
| 1        | `tmp/arc/*/goldmask/`          | risk-map, GOLDMASK.md, wisdom, findings |
| 2        | `tmp/goldmask/*/`              | risk-map, GOLDMASK.md, wisdom, findings |
| 3        | `tmp/reviews/*/`               | risk-map only                        |
| 4        | `tmp/audit/*/`                 | risk-map only                        |
| 5        | `tmp/inspect/*/`               | risk-map only                        |

## Step 1: ENUMERATE

Glob each search path for candidate directories. For each path pattern, collect
all matching directories.

```
For each search_path in search_order:
  candidates = Glob(search_path.pattern)
  If no candidates, continue to next search path
  Sort candidates by risk-map.json mtime descending (see Step 2)
```

**Guard**: If no directories exist under any search path, return `null` immediately.

## Step 2: SORT

For each candidate directory, stat the `risk-map.json` file inside it (if it
exists) and sort by that file's mtime — most recent first.

```
For each candidate_dir:
  risk_map_path = candidate_dir + "/risk-map.json"
  Try:
    stat = Bash("stat -f '%m' {risk_map_path}" on macOS, "stat -c '%Y'" on Linux)
    candidate.sort_key = stat.mtime
  Catch (file not found):
    If needsRiskMap: skip this candidate (required file missing)
    Else: candidate.sort_key = dir mtime (fallback)

Sort candidates by sort_key descending
```

**macOS compatibility**: Use `stat -f '%m'` (macOS) with fallback to `stat -c '%Y'` (Linux).

## Step 3: VALIDATE AGE

For each sorted candidate, check whether the data is within the age window.

```
For each candidate (sorted by mtime descending):
  age_days = (now - candidate.sort_key) / 86400
  If age_days > maxAgeDays:
    Skip this candidate (stale data)
    Continue to next
```

**Early exit**: Since candidates are sorted by recency, the first candidate that
fails the age check means all remaining candidates in this search path are also
stale. Proceed to the next search path.

## Step 4: READ FILES

For each age-valid candidate, attempt to read the requested files. All Read()
calls MUST be wrapped in try/catch to handle TOCTOU races (file may be deleted
between existence check and read).

```
For each age-valid candidate:
  result = {}

  If needsRiskMap:
    risk_map_path = candidate_dir + "/risk-map.json"
    Try:
      content = Read(risk_map_path)
      If content is empty or whitespace-only:
        Skip this candidate (empty file)
        Continue to next
      result.riskMap = content
      result.riskMapPath = risk_map_path
    Catch (read error):
      Skip this candidate (file disappeared — TOCTOU)
      Continue to next

  If needsGoldmask:
    goldmask_path = candidate_dir + "/GOLDMASK.md"
    Try:
      content = Read(goldmask_path)
      If content is empty or whitespace-only:
        Skip this candidate
        Continue to next
      result.goldmaskMd = content
      result.goldmaskMdPath = goldmask_path
    Catch (read error):
      Skip this candidate
      Continue to next

  If needsWisdom:
    wisdom_path = candidate_dir + "/wisdom-report.md"
    Try:
      content = Read(wisdom_path)
      If content is empty or whitespace-only:
        Skip this candidate
        Continue to next
      result.wisdomReport = content
      result.wisdomReportPath = wisdom_path
    Catch (read error):
      Skip this candidate
      Continue to next

  Proceed to Step 5 with result
```

**Empty-file sanity check**: After reading `risk-map.json`, verify the content
is non-empty. An empty or whitespace-only file indicates a partial/failed write
from a prior run. Skip and continue to the next candidate.

## Step 5: VALIDATE OVERLAP

If the caller provided `scopeFiles`, verify that the discovered risk-map has
sufficient overlap with the current scope. This prevents reusing a risk-map from
a different feature branch or unrelated arc run.

```
If scopeFiles is provided AND scopeFiles.length > 0 AND result.riskMap exists:
  Try:
    parsed = JSON.parse(result.riskMap)
    risk_map_files = parsed.files?.map(f => f.path) ?? []

    If risk_map_files.length == 0:
      Skip this candidate (empty risk-map — no files scored)
      Continue to next candidate

    overlap_count = count of scopeFiles that appear in risk_map_files
    overlap_ratio = overlap_count / scopeFiles.length

    If overlap_ratio < 0.30:
      Skip this candidate (insufficient overlap — likely from different context)
      Continue to next candidate
  Catch (JSON parse error):
    Skip this candidate (corrupt risk-map)
    Continue to next candidate
```

**Threshold**: 30% overlap is the minimum. Below this, the risk-map is from an
unrelated context (different branch, different feature) and should be discarded.

**Edge case**: If `scopeFiles` is empty or not provided, skip overlap validation
entirely — the caller does not have scope context (e.g., mend discovers data
before knowing exact scope).

## Step 6: RETURN

Return the first valid result that passes all checks (age, read, overlap).

```
Return result  # First valid match — contains only requested fields
```

If no candidate passes all checks across all search paths, return `null`.

**Caller responsibility**: When `null` is returned, the caller should either:
- Spawn a fresh lore-analyst (forge, inspect workflows)
- Proceed without risk context (mend workflow — graceful degradation)

## Performance

| Scenario | Expected Time |
|----------|---------------|
| Direct hit (first candidate valid) | 0-5ms |
| Scan with early match | 50-200ms |
| Full scan, no match | 200-500ms |

**Optimization**: When running inside arc, the orchestrator knows the goldmask
output path (`tmp/arc/{id}/goldmask/`). Pass this path directly instead of
calling discovery — bypasses the glob+stat cycle entirely.

## Error Handling

All errors are non-blocking. Discovery never throws — it returns `null` on any
unrecoverable error.

| Error | Recovery |
|-------|----------|
| Glob returns empty | Try next search path |
| stat fails (permission, missing) | Skip candidate |
| Read fails (TOCTOU race) | Skip candidate, try next |
| JSON parse fails (corrupt file) | Skip candidate, try next |
| Empty risk-map (0 files) | Skip candidate, try next |
| Overlap below 30% | Skip candidate, try next |
| All candidates exhausted | Return null |

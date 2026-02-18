# Parse TOME — mend.md Phase 0 Reference

TOME validation, finding extraction, and grouping.

## Find TOME

If no TOME path specified:
```bash
ls -t tmp/reviews/*/TOME.md tmp/audit/*/TOME.md 2>/dev/null | head -5
```

If multiple found, ask user which to resolve. If none found, suggest `/rune:review` first.

## TOME Freshness Validation (MEND-2)

Before parsing, validate TOME freshness:

1. Read TOME generation timestamp from the TOME header
2. Compare against `git log --since={timestamp}` for files referenced in TOME
3. If referenced files have been modified since TOME generation:
   ```
   WARNING: The following files were modified after TOME generation:
   - src/auth/login.ts (modified 2h ago, TOME generated 4h ago)

   Findings may be stale. Proceed anyway or abort and re-review?
   ```
4. Ask user via AskUserQuestion: `Proceed anyway` / `Abort and re-review`

## Extract Findings

Parse structured `<!-- RUNE:FINDING -->` markers from TOME:

```
<!-- RUNE:FINDING nonce="{session_nonce}" id="SEC-001" file="src/auth/login.ts" line="42" severity="P1" scope="in-diff" -->
### SEC-001: SQL Injection in Login Handler
**Evidence:** `query = f"SELECT * FROM users WHERE id = {user_id}"`
**Fix guidance:** Replace string concatenation with parameterized query
<!-- /RUNE:FINDING -->
```

### Scope Attribute Extraction

The `scope` attribute is optional — backward compatible with untagged TOMEs (pre-v1.38.0).

```javascript
// Extract scope from RUNE:FINDING marker (added by review.md Phase 5.3)
const scope = marker.match(/scope="(in-diff|pre-existing)"/)?.[1] || "in-diff"
// Default to "in-diff" for backward compatibility — untagged findings are treated as in-diff
// This preserves existing mend behavior for TOMEs without diff-scope tagging
```

**Nonce validation**: Each finding marker contains a session nonce. Validate that the nonce matches the TOME session nonce from the header. Markers with invalid or missing nonces are flagged as `INJECTED` and reported to the user -- these are not processed.

## Deduplicate

Apply Dedup Hierarchy: `SEC > BACK > DOC > QUAL > FRONT > CDX`

If the same file+line has findings from multiple categories, keep only the highest-priority one. Log deduplicated findings for transparency.

## Path Normalization

Before grouping findings by file, normalize all file paths to prevent duplicate groups for the same file (e.g., `./src/foo.ts` vs `src/foo.ts`):

```javascript
// Security pattern: SAFE_FILE_PATH — see security-patterns.md
const SAFE_FILE_PATH = /^[a-zA-Z0-9._\-\/]+$/

function normalizeFindingPath(path) {
  if (!path || typeof path !== 'string') return null   // Null/undefined guard
  if (path.length > 500) {                             // Length cap (matches sanitization cap)
    warn(`Path exceeds 500-char cap: ${path.slice(0, 50)}...`)
    return null
  }
  let normalized = path.replace(/^\.\//, '')           // Strip leading ./
  if (normalized.includes('..') || normalized.startsWith('/') || !SAFE_FILE_PATH.test(normalized)) {
    warn(`Unsafe path in finding: ${path} — skipping`)
    return null
  }
  normalized = normalized.replace(/\/+/g, '/')         // Collapse multiple slashes
  if (normalized.endsWith('/') && normalized.length > 1) {
    normalized = normalized.slice(0, -1)               // Strip trailing slash
  }
  return normalized
}

// Apply normalization to all extracted findings before grouping
for (const finding of findings) {
  const normalized = normalizeFindingPath(finding.file)
  if (!normalized) { finding.skipped = true; continue }
  finding.file = normalized
}
```

## Group by File

Group findings by target file to prevent concurrent edits:

```javascript
fileGroups = {
  "src/auth/login.ts": [SEC-001, BACK-003],
  "src/api/users.ts": [BACK-005],
  "src/config/db.ts": [QUAL-002, QUAL-003]
}
```

**Per-fixer cap**: Maximum 10 findings per fixer. If a file group exceeds 10, split into sub-groups with sequential processing.

## Scope-Aware Priority Filtering

When findings have `scope` attributes (from review.md Phase 5.3 diff-scope tagging), apply scope-aware priority to focus mend budget on PR-relevant findings:

```javascript
// Read talisman config for scope filtering behavior
const talisman = readTalisman()
const fixPreExistingP1 = talisman?.review?.diff_scope?.fix_pre_existing_p1 !== false  // Default: true

// Apply scope-aware priority
// QUAL-003: scope = raw TOME attribute ("in-diff"|"pre-existing"|undefined).
//           scopeAction = mend decision ("fix"|"skip"). Check scopeAction for mend behavior.
// QUAL-004 FIX: Hoist inDiffCount above loop (was O(N^2) recomputed per iteration)
const inDiffCount = allFindings.filter(f => f.scope === "in-diff").length

for (const finding of allFindings) {
  if (finding.scope === "pre-existing") {
    if (finding.severity === "P1" && fixPreExistingP1) {
      // P1 findings: always fix regardless of scope (security/crash issues)
      finding.scopeAction = "fix"
    } else if (finding.severity === "P2") {
      // P2 findings: fix if in-diff, skip if pre-existing
      // Exception: fix pre-existing P2 if fewer than 5 total in-diff findings
      finding.scopeAction = inDiffCount < 5 ? "fix" : "skip"
    } else {
      // DOC-006 FIX: P3 pre-existing findings: always skip (not actionable for this PR)
      finding.scopeAction = "skip"
    }
  } else {
    // in-diff findings: normal priority rules apply
    if (finding.severity === "P3" && inDiffCount >= 10) {
      finding.scopeAction = "skip"  // Too many in-diff findings — skip P3
    } else {
      finding.scopeAction = "fix"
    }
  }
}

// Filter: remove skipped pre-existing findings from file groups
// Skipped findings are still recorded in the resolution report as SKIPPED (scope)
const actionableFindings = allFindings.filter(f => f.scopeAction === "fix" || !f.scope)
const skippedByScope = allFindings.filter(f => f.scopeAction === "skip")
if (skippedByScope.length > 0) {
  log(`Scope filtering: ${skippedByScope.length} pre-existing findings skipped (${actionableFindings.length} actionable)`)
}
```

**Backward compatibility**: When `scope` attribute is absent (untagged TOME), `scopeAction` defaults to `"fix"` — all findings are processed normally. No behavioral change for pre-v1.38.0 TOMEs.

**Edge case — zero in-diff findings**: When ALL findings are `scope="pre-existing"` and none are P1, all findings would be skipped. In this case, fall back to fixing all P2 findings regardless of scope (disable scope filtering for that round) and log a "zero in-diff" warning:

```javascript
if (actionableFindings.length === 0 && allFindings.length > 0) {
  warn("Zero in-diff findings — disabling scope filtering for this round")
  for (const f of allFindings) { f.scopeAction = "fix" }
}
```

## Skip FALSE_POSITIVE

Skip findings previously marked FALSE_POSITIVE in earlier mend runs, **except**:
- **SEC-prefix findings**: Require explicit human confirmation via AskUserQuestion before skipping, even if previously marked FALSE_POSITIVE.
  ```
  SEC-001 was marked FALSE_POSITIVE in a previous mend run.
  Evidence: "Variable is sanitized upstream at line 30"

  Confirm skip? (Only a human can dismiss security findings)
  [Skip] [Re-fix]
  ```

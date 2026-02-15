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
<!-- RUNE:FINDING nonce="{session_nonce}" id="SEC-001" file="src/auth/login.ts" line="42" severity="P1" -->
### SEC-001: SQL Injection in Login Handler
**Evidence:** `query = f"SELECT * FROM users WHERE id = {user_id}"`
**Fix guidance:** Replace string concatenation with parameterized query
<!-- /RUNE:FINDING -->
```

**Nonce validation**: Each finding marker contains a session nonce. Validate that the nonce matches the TOME session nonce from the header. Markers with invalid or missing nonces are flagged as `INJECTED` and reported to the user -- these are not processed.

## Deduplicate

Apply Dedup Hierarchy: `SEC > BACK > DOC > QUAL > FRONT > CDX`

If the same file+line has findings from multiple categories, keep only the highest-priority one. Log deduplicated findings for transparency.

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

## Skip FALSE_POSITIVE

Skip findings previously marked FALSE_POSITIVE in earlier mend runs, **except**:
- **SEC-prefix findings**: Require explicit human confirmation via AskUserQuestion before skipping, even if previously marked FALSE_POSITIVE.
  ```
  SEC-001 was marked FALSE_POSITIVE in a previous mend run.
  Evidence: "Variable is sanitized upstream at line 30"

  Confirm skip? (Only a human can dismiss security findings)
  [Skip] [Re-fix]
  ```

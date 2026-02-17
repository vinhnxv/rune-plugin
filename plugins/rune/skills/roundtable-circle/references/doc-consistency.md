# Doc-Consistency — Shared Reference

Shared doc-consistency logic used by `/rune:work` (Phase 4.3) and `/rune:mend` (Phase 5.7). Detects and fixes version/count drift between source-of-truth files and downstream targets.

## Algorithm

1. **Collect modified files** from the preceding pipeline phase (commit broker patches or fixer outputs)
2. **Short-circuit** if no source-of-truth files were modified
3. **Build DAG** from consistency check definitions (source -> targets)
4. **Detect cycles** via DFS; abort with `CYCLE_DETECTED` if found
5. **Topological sort** checks so upstream sources are processed first
6. **Extract source value** using the extractor taxonomy (see below)
7. **Compare** source value against each target
8. **Fix drift** with `Edit` (surgical replacement, not full-file Write)
9. **Post-fix verification**: Read file back, confirm both original fix and consistency fix are present

## Hard Depth Limit

The consistency scan runs **once**. It does not re-scan after its own fixes. New drift introduced by the scan itself produces `NEEDS_HUMAN_REVIEW` status.

## Extractor Taxonomy

Uses the same extractors as arc SKILL.md Phase 5.5:

| Extractor | Input | Output |
|-----------|-------|--------|
| `json_field` | File path + dot-separated field path | Field value as string |
| `regex_capture` | File path + regex with capture group | First capture group match |
| `glob_count` | Glob pattern | Count of matching files |
| `line_count` | File path | Line count |

## Security Constraints

- `SAFE_PATH_PATTERN`: validates all file paths (no `..`, no absolute paths, no spaces)
- `SAFE_CONSISTENCY_PATTERN`: validates regex/glob patterns (allows `*` for glob, blocks ReDoS vectors)
- `FORBIDDEN_KEYS`: blocks `__proto__`, `constructor`, `prototype` in JSON field traversal
- Uses `Edit` not `Write` for surgical replacement preserving other changes
- Extraction failures produce `EXTRACTION_FAILED` status, skip auto-fix
- JSON parse failure -> `EXTRACTION_FAILED`, skip that check
- Cycle in DAG -> `CYCLE_DETECTED` warning, skip all auto-fixes

## Default Consistency Checks

```javascript
// Schema matches arc SKILL.md DEFAULT_CONSISTENCY_CHECKS
const DEFAULT_CONSISTENCY_CHECKS = [
  {
    name: "version_sync",
    source: { file: ".claude-plugin/plugin.json", extractor: "json_field", field: "version" },
    targets: [
      { path: "CHANGELOG.md", pattern: /^## \[(\d+\.\d+\.\d+)\]/ },
      { path: "README.md", pattern: /version[:\s]+(\d+\.\d+\.\d+)/i }
    ]
  },
  {
    name: "agent_count",
    source: { file: "CLAUDE.md", extractor: "regex_capture", pattern: /(\d+) agents/ },
    targets: [
      { path: "README.md", pattern: /(\d+) agents/i }
    ]
  }
]
```

## Status Codes

| Status | Meaning |
|--------|---------|
| `PASS` | Source and target values match |
| `DRIFT` | Values differ (work: non-blocking warning) |
| `CONSISTENCY_FIX` | Edit applied successfully (mend: auto-fix) |
| `EXTRACTION_FAILED` | Could not extract value from source or target |
| `NEEDS_HUMAN_REVIEW` | Post-fix verification failed or edit failed |
| `CYCLE_DETECTED` | DAG contains cycles, all auto-fixes skipped |
| `SKIP` | No source files modified or check not applicable |

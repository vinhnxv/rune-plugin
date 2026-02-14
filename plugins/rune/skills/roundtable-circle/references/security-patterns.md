# Security Validation Patterns — Canonical Reference

> **Convention**: Command files retain inline regex values (agents need them in-context)
> but MUST include a sync comment: `// Security pattern: {NAME} — see security-patterns.md`
> Do NOT declare new `SAFE_*` or `ALLOWLIST` patterns without adding them here first.
> Follows the same convention as `codex-detection.md` (commit `d880296`).

## Identifier Validators

### SAFE_IDENTIFIER_PATTERN
<!-- PATTERN:SAFE_IDENTIFIER_PATTERN regex="/^[a-zA-Z0-9_-]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9_-]+$/`
**Threat model**: Guards `rm -rf` and `TeamDelete` cleanup operations. Sole barrier preventing path traversal in team/task directory cleanup. Does NOT allow dots, slashes, or spaces.
**ReDoS safe**: Yes (character class only, no quantifier nesting)
**Consumers**: plan.md, work.md, arc.md, mend.md, review.md, audit.md, forge.md, cancel-review.md, cancel-audit.md, cancel-arc.md, team-lifecycle-guard.md

## Path Validators

### SAFE_PATH_PATTERN
<!-- PATTERN:SAFE_PATH_PATTERN regex="/^[a-zA-Z0-9._\-\/]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/]+$/`
**Threat model**: Blocks spaces, shell metacharacters, glob wildcards.
**WARNING**: Does NOT block path traversal (`..`) or absolute paths. Consumers MUST add explicit `..` check when validating untrusted paths.
**Aliases**: `SAFE_PATH` (work.md), `SAFE_FILE_PATH` (arc.md) — all identical regex.
**ReDoS safe**: Yes (character class only)
**Consumers**: plan.md, work.md, arc.md, mend.md

### SAFE_GLOB_PATH_PATTERN
<!-- PATTERN:SAFE_GLOB_PATH_PATTERN regex="/^[a-zA-Z0-9._\-\/*]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/*]+$/`
**Threat model**: Like SAFE_PATH_PATTERN but allows `*` for glob expansion.
MUST NOT include spaces — `ls -1 ${unquoted}` relies on word-splitting for glob expansion.
**ReDoS safe**: Yes
**Consumers**: arc.md (glob_count extractor), work.md (Phase 4.3 glob_count extractor)

## Regex Validators

### SAFE_REGEX_PATTERN
<!-- PATTERN:SAFE_REGEX_PATTERN regex="/^[a-zA-Z0-9._\-\/ \\|()[\]{}^$+?]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/ \\|()[\]{}^$+?]+$/`
**Threat model**: Allows regex metacharacters for user-provided talisman patterns.
**KNOWN VULNERABILITY (P1)**: `$` IS allowed in the character class `[\]{}^$+?]`. This means `$(whoami)` passes validation and could execute in double-quoted Bash interpolation. **Mitigation**: Consumer files MUST use single-quoted Bash interpolation or `rg -f <file>` approach. See also the `-- ` separator for ripgrep to prevent pattern interpretation as flags.
**ReDoS safe**: Yes (character class only)
**Consumers**: plan.md, work.md, arc.md

### SAFE_REGEX_PATTERN_CC
<!-- PATTERN:SAFE_REGEX_PATTERN_CC regex="/^[a-zA-Z0-9._\-\/ \\\[\]{}^+?*]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/ \\\[\]{}^+?*]+$/`
**Threat model**: Narrower than SAFE_REGEX_PATTERN. Excludes `|`, `(`, `)`, `$` (SEC-001). Adds `*` for glob matching. Safe for ripgrep context, NOT safe for unquoted Bash glob context.
**ReDoS safe**: Yes
**Consumers**: arc.md (consistency checks), work.md (Phase 4.3 consistency checks)

## Command Validators

### SAFE_WARD
<!-- PATTERN:SAFE_WARD regex="/^[a-zA-Z0-9._\-\/ ]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/ ]+$/`
**Threat model**: Blocks pipe, semicolon, ampersand, backtick — prevents command chaining. Allows spaces (ward commands may have arguments).
**ReDoS safe**: Yes
**Consumers**: work.md, mend.md

## Codex Allowlists

### CODEX_MODEL_ALLOWLIST
<!-- PATTERN:CODEX_MODEL_ALLOWLIST regex="/^(gpt-4[o]?|gpt-5(\.\d+)?-codex|o[1-4](-mini|-preview)?)$/" version="1" last-reviewed="2026-02-14" -->
**Regex**: `/^(gpt-4[o]?|gpt-5(\.\d+)?-codex|o[1-4](-mini|-preview)?)$/`
**Threat model**: Restricts Codex model parameter to known-safe model IDs. Review quarterly or when new models are released.
**Last reviewed**: 2026-02-14
**Consumers**: plan.md (Phase 1C + Phase 4C), work.md (Phase 4.5)

### CODEX_REASONING_ALLOWLIST
<!-- PATTERN:CODEX_REASONING_ALLOWLIST values='["high","medium","low"]' version="1" -->
**Values**: `["high", "medium", "low"]`
**Threat model**: Restricts reasoning effort parameter to known-safe values.
**Consumers**: plan.md (Phase 1C + Phase 4C), work.md (Phase 4.5)

## Prototype Guards

### FORBIDDEN_KEYS
**Value**: `Set(['__proto__', 'constructor', 'prototype'])`
**Threat model**: Prevents prototype pollution in JSON dot-path traversal.
**Consumers**: arc.md (consistency extractor), mend.md (consistency extractor), work.md (Phase 4.3 consistency extractor)

## Branch Validators

### BRANCH_RE
<!-- PATTERN:BRANCH_RE regex="/^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/`
**Threat model**: Validates branch names for git operations. Requires alphanumeric start character.
**Consumers**: work.md (Phase 0 branch setup)

## Additional Validators (Single-File)

These patterns appear in a single file and are documented here for completeness but are not extracted to multi-file sync:

| Pattern | File | Description |
|---------|------|-------------|
| `SAFE_DOT_PATH` | arc.md | JSON dot-path field validator: `/^[a-zA-Z0-9._]+$/` |
| `SAFE_CONSISTENCY_PATTERN` | mend.md | Similar to SAFE_REGEX_PATTERN_CC |
| `SAFE_FEATURE_PATTERN` | plan.md | Feature name sanitizer |
| `VALID_EXTRACTORS` | arc.md | Extractor type allowlist: `["glob_count", "regex_capture", "json_field", "line_count"]` |

## Maintenance

- When adding a new security pattern to ANY command file, add it to this reference first.
- When reviewing, check that consumer file regex values match this reference (automated by Arc Phase 2.7 enforcement check).
- Pattern version numbers increment when regex values change.

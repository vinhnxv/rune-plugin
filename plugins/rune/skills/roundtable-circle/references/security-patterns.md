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
**Consumers**: plan.md, work.md, arc SKILL.md, mend.md, review.md, audit.md, forge.md, cancel-review.md, cancel-audit.md, cancel-arc.md, team-lifecycle-guard.md

## Path Validators

### SAFE_PATH_PATTERN
<!-- PATTERN:SAFE_PATH_PATTERN regex="/^[a-zA-Z0-9._\-\/]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/]+$/`
**Threat model**: Blocks spaces, shell metacharacters, glob wildcards.
**WARNING**: Does NOT block path traversal (`..`) or absolute paths. Consumers MUST add explicit `..` check when validating untrusted paths.
**Aliases**: `SAFE_PATH` (work.md), `SAFE_FILE_PATH` (arc SKILL.md) — all identical regex.
**ReDoS safe**: Yes (character class only)
**Consumers**: plan.md, work.md, arc SKILL.md, mend.md

### SAFE_GLOB_PATH_PATTERN
<!-- PATTERN:SAFE_GLOB_PATH_PATTERN regex="/^[a-zA-Z0-9._\-\/*]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/*]+$/`
**Threat model**: Like SAFE_PATH_PATTERN but allows `*` for glob expansion.
MUST NOT include spaces — `ls -1 ${unquoted}` relies on word-splitting for glob expansion.
**ReDoS safe**: Yes
**Consumers**: arc SKILL.md (glob_count extractor), work.md (Phase 4.3 glob_count extractor)

## Regex Validators

### SAFE_REGEX_PATTERN
<!-- PATTERN:SAFE_REGEX_PATTERN regex="/^[a-zA-Z0-9._\-\/ \\|()[\]{}^$+?]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/ \\|()[\]{}^$+?]+$/`
**Threat model**: Allows regex metacharacters for user-provided talisman patterns.
**KNOWN VULNERABILITY (P1, Mitigated)**: `$` IS allowed in the character class `[\]{}^$+?]`. This means `$(whoami)` passes validation and could execute in double-quoted Bash interpolation. **Mitigation**: All consumer files MUST use `safeRgMatch()` (see "Safe Regex Execution" section below).
**Status: Mitigated** — `$` is intentionally allowed because talisman regex patterns may legitimately use `$` as an end-of-line anchor. All consumers use `safeRgMatch()` which writes the pattern to a temp file and uses `rg -f`, eliminating shell interpolation entirely. The `_CC` variant (excludes `$`) remains available for contexts that don't need regex anchors.
**ReDoS safe**: Yes (character class only)
**Consumers**: ward-check.md, verification-gate.md, plan-review.md

> Prior to v1.20.0, consumers were the top-level command files (plan.md, work.md, arc SKILL.md). After structural refactoring in v1.20.0, execution logic lives in the reference files listed above.

> **Implementation**: All consumer sites call `safeRgMatch()` (defined in the "Safe Regex Execution" section below). Direct Bash interpolation of `SAFE_REGEX_PATTERN`-validated strings is prohibited. New consumers MUST use `safeRgMatch()`.

### SAFE_REGEX_PATTERN_CC
<!-- PATTERN:SAFE_REGEX_PATTERN_CC regex="/^[a-zA-Z0-9._\-\/ \\\[\]{}^+?*]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/ \\\[\]{}^+?*]+$/`
**Threat model**: Narrower than SAFE_REGEX_PATTERN. Excludes `|`, `(`, `)`, `$` (SEC-001). Adds `*` for glob matching. Safe for ripgrep context, NOT safe for unquoted Bash glob context.
**ReDoS safe**: Yes
**Consumers**: arc SKILL.md (consistency checks), work.md (Phase 4.3 consistency checks)

## Safe Regex Execution

### safeRgMatch(pattern, paths, options)

Writes a regex pattern to a temporary file and executes ripgrep via `-f`, eliminating
shell interpolation of user-provided patterns entirely.

> The following pseudocode defines the agent behavior pattern. `Bash()`, `Write()`, and `Read()` refer to Claude Code tool calls, not JavaScript runtime functions.

```javascript
function safeRgMatch(pattern, paths, { exclusions, timeout } = {}) {
  Bash(`mkdir -p tmp`)
  const tmpFile = Bash(`mktemp tmp/.rg-pattern-XXXXXX`).stdout.trim()
  try {
    Write(tmpFile, pattern)
    if (timeout && !Number.isFinite(timeout)) throw new Error('timeout must be a finite number')
    const timeoutPrefix = timeout ? `timeout ${timeout} ` : ''
    // Preserve original positional arg semantics: exclusions is passed as an additional
    // search path (same as the pre-fix behavior: rg -- "regex" "paths" "exclusions").
    // SAFE_PATH_PATTERN already validates exclusions — no shell metacharacters possible.
    const exclusionArg = exclusions ? ` "${exclusions}"` : ''
    const result = Bash(`${timeoutPrefix}rg --no-messages -f "${tmpFile}" "${paths}"${exclusionArg}`)
    return result
  } finally {
    Bash(`rm -f "${tmpFile}" 2>/dev/null`)
  }
}
```

**Why `-f` over `--regexp`**: `rg -f FILE` reads patterns from a file, completely
bypassing Bash string parsing. `rg --regexp PATTERN` still requires the pattern
to be a Bash argument, which doesn't help with `$()` expansion.

**Exclusion semantics**: The original code passes `pattern.exclusions` as a positional
argument to `rg` (an additional search path). `safeRgMatch()` preserves this behavior
exactly. The `exclusions` value is validated by `SAFE_PATH_PATTERN` before reaching
this function, so it cannot contain shell metacharacters.

**Edge cases**: `rg -f` treats each line of the pattern file as a separate pattern
(OR semantics). Talisman YAML patterns typically don't contain embedded newlines,
so this matches the expected single-pattern behavior.
Note: `SAFE_REGEX_PATTERN` does not include `\n` in its character class, so multi-line patterns are rejected at validation time before reaching `safeRgMatch()`.

## Command Validators

### SAFE_WARD
<!-- PATTERN:SAFE_WARD regex="/^[a-zA-Z0-9._\-\/ ]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9._\-\/ ]+$/`
**Threat model**: Blocks pipe, semicolon, ampersand, backtick — prevents command chaining. Allows spaces (ward commands may have arguments).
**ReDoS safe**: Yes
**Consumers**: work.md, mend.md

## CLI-Backed Ash Validators

### CLI_BINARY_PATTERN
<!-- PATTERN:CLI_BINARY_PATTERN regex="/^[a-zA-Z0-9_-]+$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9_-]+$/`
**Alias**: SAFE_IDENTIFIER_PATTERN (identical regex, shared threat model)
**Threat model**: Validates CLI binary names for external model Ashes. Blocks path separators (`/`, `\`), dots (`.` — prevents `../`), spaces, and shell metacharacters. The binary is resolved via `command -v` after validation, and the resolved path must NOT be within the project directory (see `CLI_PATH_VALIDATION`).
**ReDoS safe**: Yes (character class only, no quantifier nesting)
**Consumers**: custom-ashes.md (CLI-backed Ash validation), codex-detection.md (detectExternalModel)

### OUTPUT_FORMAT_ALLOWLIST
<!-- PATTERN:OUTPUT_FORMAT_ALLOWLIST values='["jsonl","text","json"]' version="1" -->
**Values**: `["jsonl", "text", "json"]`
**Threat model**: Restricts CLI output format parameter to known-safe values. Prevents arbitrary format strings from reaching shell interpolation.
**Consumers**: custom-ashes.md (CLI-backed Ash validation), external-model-template.md

### MODEL_NAME_PATTERN
<!-- PATTERN:MODEL_NAME_PATTERN regex="/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/`
**Threat model**: Validates external model names. Requires alphanumeric first character to prevent injection via leading hyphens (`-` could be misinterpreted as CLI flags). Allows dots and hyphens for model version identifiers (e.g., `gemini-2.5-pro`, `llama3.1`). Does NOT allow spaces, slashes, or shell metacharacters.
**ReDoS safe**: Yes (character class only)
**Consumers**: custom-ashes.md (CLI-backed Ash validation, default `model_pattern`), codex-detection.md (detectExternalModel)

### CLI_PATH_VALIDATION
**Rule**: Resolved CLI binary path (from `command -v {cli}`) must NOT be within the project directory.
**Threat model**: Prevents a malicious repository from shipping a fake CLI binary (e.g., `./gemini`) that gets executed with trust. The resolved absolute path is compared against `$PWD` — if it starts with the project root, validation fails.
**Implementation**:
```bash
cli_path=$(command -v "{cli}" 2>/dev/null)
if [[ "$cli_path" == "$PWD"* ]]; then
  error "CLI binary '{cli}' resolves to project directory — rejected for safety"
fi
```
**Consumers**: codex-detection.md (detectExternalModel step 3)

### CLI_TIMEOUT_PATTERN
<!-- PATTERN:CLI_TIMEOUT_PATTERN regex="/^\d{1,5}$/" version="1" -->
**Regex**: `/^\d{1,5}$/`
**Threat model**: Validates CLI timeout values from talisman.yml before shell interpolation. Identical format to CODEX_TIMEOUT_ALLOWLIST. Accepts only 1-5 digit integers (max 99999). Bounds checking (30-3600) is performed after format validation.
**ReDoS safe**: Yes (character class with bounded quantifier, no nesting)
**Consumers**: custom-ashes.md (CLI-backed Ash validation), codex-detection.md (detectExternalModel)

### sanitizePlanContent()

Canonical sanitizer for plan/diff content before injection into external CLI prompts. Prevents prompt injection via reviewed code.

```javascript
function sanitizePlanContent(content, maxLength = 50000) {
  // 1. Truncate to maxLength to prevent token overflow
  let sanitized = content.slice(0, maxLength)

  // 2. Strip nonce markers that could confuse Truthbinding boundaries
  sanitized = sanitized.replace(/<<<NONCE:[A-Za-z0-9]+>>>/g, '[NONCE-STRIPPED]')

  // 3. Escape markdown code fence terminators that could break prompt template
  sanitized = sanitized.replace(/```/g, '` ` `')

  // 4. Strip null bytes and other control characters (except newline, tab)
  sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '')

  return sanitized
}
```

**Consumers**: external-model-template.md (diff/file content injection), codex-oracle.md (existing Codex flow)

## Codex Allowlists

### CODEX_MODEL_ALLOWLIST
<!-- PATTERN:CODEX_MODEL_ALLOWLIST regex="/^gpt-5(\.\d+)?-codex$/" version="2" last-reviewed="2026-02-15" -->
**Regex**: `/^gpt-5(\.\d+)?-codex$/`
**Threat model**: Restricts Codex model parameter to gpt-5.x-codex family only. Only gpt-5.x-codex models are supported by the Codex CLI with ChatGPT accounts. Other families (gpt-4o, o1-o4) fail at runtime.
**Test cases**: `gpt-5-codex` (pass), `gpt-5.3-codex` (pass), `gpt-5.2-codex` (pass), `o4-mini` (reject), `gpt-4o` (reject)
**Last reviewed**: 2026-02-15
**Consumers**: plan.md (Phase 1C + Phase 4C), work.md (Phase 4.5)

### CODEX_REASONING_ALLOWLIST
<!-- PATTERN:CODEX_REASONING_ALLOWLIST values='["high","medium","low"]' version="1" -->
**Values**: `["high", "medium", "low"]`
**Threat model**: Restricts reasoning effort parameter to known-safe values.
**Consumers**: plan.md (Phase 1C + Phase 4C), work.md (Phase 4.5)

### CODEX_TIMEOUT_ALLOWLIST
<!-- PATTERN:CODEX_TIMEOUT_ALLOWLIST regex="/^\d{1,5}$/" version="1" -->
**Regex**: `/^\d{1,5}$/`
**Threat model**: Validates codex timeout values from talisman.yml before shell interpolation. Accepts only 1-5 digit integers (max 99999). Bounds checking (30–3600 for timeout, 10–timeout for stream_idle_timeout) is performed by `resolveCodexTimeouts()` after format validation.
**ReDoS safe**: Yes (character class with bounded quantifier, no nesting)
**Consumers**: codex-detection.md (resolveCodexTimeouts), codex-oracle.md, codex-cli/SKILL.md, work.md, forge.md, research-phase.md, plan-review.md, mend.md, gap-analysis.md, solution-arena.md, rune-smith.md, rune-echoes/SKILL.md

## Prototype Guards

### FORBIDDEN_KEYS
**Value**: `Set(['__proto__', 'constructor', 'prototype'])`
**Threat model**: Prevents prototype pollution in JSON dot-path traversal.
**Consumers**: arc SKILL.md (consistency extractor), mend.md (consistency extractor), work.md (Phase 4.3 consistency extractor)

## Branch Validators

### BRANCH_RE
<!-- PATTERN:BRANCH_RE regex="/^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/" version="1" -->
**Regex**: `/^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/`
**Threat model**: Validates branch names for git operations. Requires alphanumeric start character.
**Consumers**: work.md (Phase 0 branch setup)

## SHA Validators

### SAFE_SHA_PATTERN
<!-- PATTERN:SAFE_SHA_PATTERN regex="/^[0-9a-f]{7,40}$/" version="1" -->
**Regex**: `/^[0-9a-f]{7,40}$/`
**Threat model**: Validates git commit SHAs (abbreviated 7-char and full 40-char hex). Guards `git rev-parse --verify`, `git diff`, and `git log` operations where a stored SHA is interpolated into shell commands. Prevents command injection via crafted SHA values in plan metadata files.
**WARNING**: Validates format only — does NOT verify the SHA exists in the repository. Consumers MUST use `git cat-file -t {sha} 2>/dev/null` after format validation to confirm the SHA resolves.
**ReDoS safe**: Yes (character class with bounded quantifier `{7,40}`, no nesting)
**Consumers**: arc SKILL.md (freshness gate), verification-gate.md (check #8)

## Additional Validators (Single-File)

These patterns appear in a single file and are documented here for completeness but are not extracted to multi-file sync:

| Pattern | File | Description |
|---------|------|-------------|
| `SAFE_DOT_PATH` | arc SKILL.md | JSON dot-path field validator: `/^[a-zA-Z0-9._]+$/` |
| `SAFE_CONSISTENCY_PATTERN` | mend.md | Similar to SAFE_REGEX_PATTERN_CC |
| `SAFE_FEATURE_PATTERN` | plan.md | Feature name sanitizer |
| `VALID_EXTRACTORS` | arc SKILL.md | Extractor type allowlist: `["glob_count", "regex_capture", "json_field", "line_count"]` |

## Hook Security — Threat Models

### TaskCompleted Prompt Gate (QUAL-010)
**File**: `hooks/hooks.json` → `TaskCompleted[1]` (prompt hook)
**Model**: haiku (fast, low-cost quality gate)
**Defense**: ANCHOR/RE-ANCHOR truthbinding markers, task input explicitly marked UNTRUSTED
**Threat model**: Task subjects are **teammate-generated** (not external user input). The haiku model is less robust against adversarial prompts than larger models, but the attack surface is limited:
- Attackers must first compromise a teammate's context (requires prompt injection through reviewed source code → fixer prompt → task subject chain)
- The gate is fail-open for legitimate work (`"When in doubt, allow"`) — bypassing it only skips a structural quality check, not a security boundary
- The ANCHOR/RE-ANCHOR pattern provides defense-in-depth against casual injection attempts

**Risk**: Low. The haiku gate is a **quality** control (catches premature task completions), not a **security** control. A bypass results in a prematurely-completed task being counted, which the orchestrator's Phase 4 monitor can detect via missing output files.

### Annotate Hook stdin Cap (SEC-006)
**File**: `scripts/echo-search/annotate-hook.sh:13`
**Defense**: `head -c 65536` caps stdin to 64KB
**Threat model**: PostToolUse hook receives full tool input on stdin. Without a cap, a large Write/Edit tool call could cause unbounded memory consumption in the hook script.

## Maintenance

- When adding a new security pattern to ANY command file, add it to this reference first.
- When reviewing, check that consumer file regex values match this reference (automated by Arc Phase 2.7 enforcement check).
- Pattern version numbers increment when regex values change.

# Codex Oracle Detection Algorithm

Canonical detection logic for the Codex Oracle built-in Ash. Used by review, audit, plan, work, and forge pipelines.

## Algorithm

```
1. Read talisman.yml (project or global)
2. If talisman.codex.disabled is true:
   - Log: "Codex Oracle: disabled via talisman.yml"
   - Skip Codex Oracle entirely
3. Check CLI availability:
   Bash: command -v codex >/dev/null 2>&1 && echo "available" || echo "unavailable"
   - If "unavailable":
     a. Log: "Codex Oracle: CLI not found, skipping (install: npm install -g @openai/codex)"
     b. Skip Codex Oracle entirely
3a. Check --kill-after support (GNU coreutils timeout):
   Bash: timeout --kill-after=1 1 true 2>&1; echo $?
   - If exit code == 0: set kill_after_supported = true
   - If exit code != 0: set kill_after_supported = false
     a. Log: "Info: --kill-after not supported — using plain timeout (codex may leave orphan processes)"
4. Validate CLI can execute:
   Bash: timeout 5 codex --version 2>&1
   - If exit code != 0 (including exit 124 = timeout):
     a. Log: "Codex Oracle: CLI found but cannot execute — skipping (reinstall: npm install -g @openai/codex)"
     b. Skip Codex Oracle entirely
5. Check authentication status:
   Bash: timeout 10 codex login status 2>&1
   - If exit code == 124 (timeout):
     a. Log: "Codex Oracle: auth check timed out — skipping (network issue or CLI hang)"
     b. Skip Codex Oracle entirely
   - If exit code != 0 OR output contains "not logged in" / "not authenticated":
     a. Log: "Codex Oracle: not authenticated — skipping (run: codex login)"
     b. Skip Codex Oracle entirely
   - Note: If `codex login status` is not a valid subcommand (older CLI versions),
     fall through and let step 7 catch auth errors at runtime.
6. Check jq availability (needed for JSONL parsing of Codex output):
   Bash: command -v jq >/dev/null 2>&1 && echo "available" || echo "unavailable"
   - If "unavailable":
     a. Log: "Warning: jq not found — Codex Oracle will use raw text fallback instead of JSONL parsing"
     b. Set codex_jq_available = false (Codex Oracle Ash prompt will skip jq-based parsing)
   - If "available":
     a. Set codex_jq_available = true
7. Check talisman.codex.workflows (default: [review, audit, plan, forge, work])
   - If the current workflow is NOT in the workflows list, remove codex-oracle from Ash selection
8. Check .codexignore exists (required for --full-auto):
   Bash: [ -f .codexignore ] && echo "present" || echo "missing"
   - If "missing":
     a. Log: "Warning: .codexignore not found — Codex Oracle will skip --full-auto mode"
     b. Ask user via AskUserQuestion: "Create .codexignore from template?" [Create] [Skip Codex]
     c. If "Skip Codex": skip Codex Oracle entirely
     d. If "Create": write default .codexignore template (see codex-cli SKILL.md) and continue
9. If all checks pass:
   a. Add "codex-oracle" to the Ash selection (always-on when available, like Ward Sentinel)
   b. Log: "Codex Oracle: CLI detected and authenticated, adding cross-model reviewer"
```

## Timeout Resolution

```javascript
// resolveCodexTimeouts(talisman) — resolve configurable timeouts from talisman.yml
// Returns { timeout, streamIdleTimeout, streamIdleMs, killAfterFlag }
// Security pattern: CODEX_TIMEOUT_ALLOWLIST — see security-patterns.md
function resolveCodexTimeouts(talisman) {
  const raw_timeout = talisman?.codex?.timeout ?? 600
  const raw_stream = talisman?.codex?.stream_idle_timeout ?? 540

  // Validate: must be integer within bounds
  const timeout = parseInt(String(raw_timeout), 10)
  if (!Number.isFinite(timeout) || timeout < 30 || timeout > 3600) {
    warn(`codex.timeout=${raw_timeout} out of range [30,3600] — using default 600`)
    timeout = 600
  }

  let streamIdleTimeout = parseInt(String(raw_stream), 10)
  if (!Number.isFinite(streamIdleTimeout) || streamIdleTimeout < 10 || streamIdleTimeout >= timeout) {
    const clamped = Math.max(10, timeout - 60)
    warn(`codex.stream_idle_timeout=${raw_stream} out of range [10,${timeout - 1}] — using clamped default ${clamped}`)
    streamIdleTimeout = clamped
  }

  // Convert to milliseconds for --config stream_idle_timeout_ms
  const streamIdleMs = streamIdleTimeout * 1000

  // --kill-after flag (30s grace period, only if supported — see step 3a)
  const killAfterFlag = kill_after_supported ? "--kill-after=30" : ""

  return { timeout, streamIdleTimeout, streamIdleMs, killAfterFlag }
}
```

## Runtime Error Classification

When `codex exec` fails at runtime (non-zero exit code), classify the error and log a
user-facing message so the user knows how to fix it:

```
| Exit / stderr pattern                  | Code           | User message                                                                    |
|----------------------------------------|----------------|---------------------------------------------------------------------------------|
| "not authenticated" / "auth"           | AUTH           | "Codex Oracle: authentication required — run `codex login`"                     |
| "rate limit" / "429"                   | RATE_LIMIT     | "Codex Oracle: API rate limit — try again later or reduce batches"              |
| "model not found" / "invalid model"    | MODEL          | "Codex Oracle: model unavailable — check talisman.codex.model"                  |
| "network" / "connection" / "ECON"      | NETWORK        | "Codex Oracle: network error — check internet connection"                       |
| exit 124 (GNU timeout)                 | OUTER_TIMEOUT  | "Codex Oracle: timeout after {timeout}s — increase codex.timeout or reduce context_budget" |
| "stream idle" / "stream_idle_timeout"  | STREAM_IDLE    | "Codex Oracle: no output for {stream_idle}s — increase codex.stream_idle_timeout" |
| "quota" / "insufficient_quota" / "402" | QUOTA          | "Codex Oracle: quota exceeded — check OpenAI billing"                           |
| "context_length" / "too many tokens"   | CONTEXT_LENGTH | "Codex Oracle: context too large — reduce context_budget or file count"         |
| "sandbox" / "permission denied"        | SANDBOX        | "Codex Oracle: sandbox restriction — check .codexignore and sandbox mode"       |
| "version" / "upgrade" / "deprecated"   | VERSION        | "Codex Oracle: CLI version issue — run `npm update -g @openai/codex`"           |
| exit 137 (SIGKILL from --kill-after)   | KILL_TIMEOUT   | "Codex Oracle: killed after grace period — codex hung, increase timeout"        |
| other non-zero exit                    | UNKNOWN        | "Codex Oracle: exec failed (exit {code}) — run `codex exec` manually to debug" |
```

```javascript
// classifyCodexError(exitCode, stderr) — returns { code, message }
// Matches patterns top-to-bottom; first match wins.
function classifyCodexError(exitCode, stderr) {
  const stderrLower = (stderr || "").toLowerCase().slice(0, 500)
  if (stderrLower.match(/not authenticated|unauthenticated|auth.*(fail|requir|error)/)) return { code: "AUTH", ... }
  if (stderrLower.match(/rate limit|429/))                   return { code: "RATE_LIMIT", ... }
  if (stderrLower.match(/model not found|invalid model/))    return { code: "MODEL", ... }
  if (stderrLower.match(/network|connection|econ/))          return { code: "NETWORK", ... }
  if (exitCode === 124)                                      return { code: "OUTER_TIMEOUT", ... }
  if (stderrLower.match(/stream idle|stream_idle_timeout/))  return { code: "STREAM_IDLE", ... }
  if (stderrLower.match(/quota|insufficient_quota|402/))     return { code: "QUOTA", ... }
  if (stderrLower.match(/context_length|too many tokens/))   return { code: "CONTEXT_LENGTH", ... }
  if (stderrLower.match(/sandbox|permission denied/))        return { code: "SANDBOX", ... }
  if (stderrLower.match(/version|upgrade|deprecated/))       return { code: "VERSION", ... }
  if (exitCode === 137)                                      return { code: "KILL_TIMEOUT", ... }
  return { code: "UNKNOWN", ... }
}
```

When logging errors, always include:
- The specific error message (truncated to 200 chars)
- A suggested action the user can take
- Note that Codex Oracle is optional and the pipeline continues without it

## Architecture Rules

1. **Separate teammate**: Codex MUST always run on a separate teammate (Task with `run_in_background: true`),
   Do not inline in the orchestrator. This isolates untrusted codex output from the main context window.
   - review/audit: Codex Oracle Ash teammate → `tmp/reviews/{id}/codex-oracle.md`
   - plan (research): codex-researcher teammate → `tmp/plans/{timestamp}/research/codex-analysis.md`
   - plan (review): codex-plan-reviewer teammate → `tmp/plans/{timestamp}/codex-plan-review.md`
   - work (advisory): codex-advisory teammate → `tmp/work/{timestamp}/codex-advisory.md`
   - forge: runs inside forge agent teammate → `tmp/forge/{id}/{section}-codex-oracle.md`

2. **Always write to MD file**: Every codex outcome (success, failure, skip, error) produces an MD file
   at the designated output path. Even skip/error messages are written so downstream phases know codex was attempted.

3. **Non-fatal**: All codex errors are non-fatal. The pipeline always continues without Codex Oracle findings.

## Notes

- Steps 3-5 are fast (no network call for step 3, step 4 has 5s timeout, step 5 has 10s timeout)
- When Codex Oracle is selected, it counts toward the `max_ashes` cap
- Codex Oracle findings use the `CDX` prefix
- Findings participate in standard dedup, TOME aggregation, and Truthsight verification
- Disable entirely via `codex.disabled: true` in talisman.yml (runtime kill switch)

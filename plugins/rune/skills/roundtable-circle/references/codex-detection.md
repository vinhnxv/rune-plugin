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
4. Validate CLI can execute:
   Bash: codex --version 2>&1
   - If exit code != 0:
     a. Log: "Codex Oracle: CLI found but cannot execute — skipping (reinstall: npm install -g @openai/codex)"
     b. Skip Codex Oracle entirely
5. Check authentication status:
   Bash: codex login status 2>&1
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

## Runtime Error Classification

When `codex exec` fails at runtime (non-zero exit code), classify the error and log a
user-facing message so the user knows how to fix it:

```
| Exit / stderr pattern             | User message                                                        |
|-----------------------------------|---------------------------------------------------------------------|
| "not authenticated" / "auth"      | "Codex Oracle: authentication required — run `codex login`"         |
| "rate limit" / "429"              | "Codex Oracle: API rate limit — try again later or reduce batches"  |
| "model not found" / "invalid"     | "Codex Oracle: model unavailable — check talisman.codex.model"      |
| "network" / "connection" / "ECON" | "Codex Oracle: network error — check internet connection"           |
| timeout (exit 124)                | "Codex Oracle: timeout after 10 min — reduce context_budget"        |
| other non-zero exit               | "Codex Oracle: exec failed (exit {code}) — run `codex exec` manually to debug" |
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

- Steps 3-5 are fast (no network call for steps 3-4, step 5 may be a local check or quick probe)
- When Codex Oracle is selected, it counts toward the `max_ashes` cap
- Codex Oracle findings use the `CDX` prefix
- Findings participate in standard dedup, TOME aggregation, and Truthsight verification
- Disable entirely via `codex.disabled: true` in talisman.yml (runtime kill switch)

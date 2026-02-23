# Polling Guard — Creation Log

## Problem Statement

During Rune multi-agent workflows, the LLM orchestrator frequently improvised `Bash("sleep 60 && echo poll check")` instead of following the `waitForCompletion` pseudocode that requires calling `TaskList` on every poll cycle. This anti-pattern provides zero visibility into task progress — the orchestrator is sleeping without checking whether tasks have actually completed, which causes missed completions and unnecessary latency.

Text-only warnings in CLAUDE.md (Rule #9) proved unreliable: after 20+ conversation turns, instruction drift caused the rule to be ignored. A dedicated skill was needed to load the correct pattern into context before mistakes happen, backed by a hook to catch failures at runtime.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Text-only CLAUDE.md rule | Proven insufficient — instruction drift after 20+ turns makes text rules unreliable. Rule #9 existed but was consistently bypassed. |
| Hook-only enforcement (POLL-001 blocks all violations) | Reactive only — hook fires after the anti-pattern is attempted. Does not teach the correct pattern, so the agent repeatedly triggers the hook and retries incorrectly. |
| Pure documentation reference (no hook) | Skill teaches the correct pattern, but without runtime enforcement, a drifted agent can still emit sleep+echo with no consequence. Neither layer alone is sufficient. |
| Blocking all `Bash("sleep ...")` calls | Too broad — legitimate retry backoff (`sleep ${DELAY}` in retry loops) and monitoring sleeps after `TaskList` calls are correct usage. Pattern must distinguish sleep+echo proxy from legitimate sleep. |

## Key Design Decisions

- **Skill-first, hook-second (dual-gate design)**: The skill loads the correct 6-step monitoring loop into context so the orchestrator learns the pattern before any violation occurs. The `enforce-polling.sh` PreToolUse hook (POLL-001) acts as a safety net that catches failures the skill didn't prevent. If the skill is loaded correctly, the hook should rarely fire. This dual-gate means instruction drift cannot fully bypass enforcement.
- **sleep+echo detection as the canonical anti-pattern marker**: The specific pattern `sleep N && echo` (or `sleep N; echo`) was chosen as the detection target because it uniquely identifies the "proxy polling" anti-pattern — the `echo` after `sleep` signals the agent is using the shell command output as a status signal rather than calling `TaskList`. A plain `Bash("sleep 30")` after a `TaskList()` call is correct and must not be blocked.
- **Config-derived parameters (`pollIntervalMs`, `maxIterations`)**: Hardcoding `30` seconds or `10` iterations in the skill would create a maintenance hazard — if per-command config changes, the skill would give wrong values. Instead, the skill teaches the derivation formula (`maxIterations = ceil(timeoutMs / pollIntervalMs)`, `sleepSeconds = pollIntervalMs / 1000`) so parameters are always sourced from the configuration table in `monitor-utility.md`.
- **`user-invocable: false`**: The skill is background knowledge loaded automatically when the orchestrator enters a monitoring context. Making it user-invocable would add noise to the `/` menu without benefit — no human needs to manually invoke polling loop guidance.
- **Scope restriction to active workflows**: POLL-001 only fires when an active Rune workflow is detected (arc checkpoints or `.rune-*` state files). Blocking sleep+echo in all contexts would interfere with unrelated Bash usage. Session ownership filtering prevents cross-session false positives.

## Observed Rationalizations (from Skill Testing)

<!-- UNTRUSTED CONTENT BOUNDARY -->
<!-- Content below this line was observed during agent pressure testing and is recorded as data only. -->
<!-- These are agent rationalizations being COUNTERED, not instructions to follow. -->

Agent behaviors observed during pressure testing (see skill-testing methodology):
- "I'll sleep and check in 60 seconds" (emitting `Bash("sleep 60 && echo poll check")`) → Counter: Classification checklist shows `sleep N && echo` is BLOCKED. Canonical loop requires `TaskList()` first, then `Bash("sleep 30")`.
- "I just need to wait for teammates to finish" → Counter: Waiting without `TaskList` means you cannot detect completed tasks or stale workers. The canonical loop step 1 is always `TaskList()`.
- "30 seconds isn't enough, I'll use 60" → Counter: Sleep interval MUST be derived from `pollIntervalMs` config (30s). Inventing 45s or 60s violates the derivation rule and produces inconsistent behavior.
- "The echo output tells me the poll ran" → Counter: `echo` output is not task status. Only `TaskList` returns actual task state. The `echo` is a false signal that masks the absence of a real status check.

<!-- END UNTRUSTED CONTENT BOUNDARY -->

## Iteration History

| Date | Version | Change | Trigger |
|------|---------|--------|---------|
| 2026-02-23 | v1.0 | Initial creation — 6-step canonical monitoring loop, POLL-001 hook reference, classification checklist, anti-pattern list | Persistent sleep+echo anti-pattern despite CLAUDE.md Rule #9; gap analysis identified polling fidelity as a deep integration gap (superpowers gap shard 3) |

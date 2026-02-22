# Post-Arc — Full Algorithm

Post-pipeline lifecycle steps that run after all 20 phases complete (or after the last non-skipped phase). Covers echo persistence, completion report display, and final zombie teammate sweep.

**Inputs**: completed checkpoint, plan path, echo config, `arcStart` timestamp
**Outputs**: echoes persisted, completion report displayed to user, stale teams cleaned
**Error handling**: Echo persist failure is non-blocking; ARC-9 sweep uses retry with backoff
**Consumers**: SKILL.md (Post-Arc stub)

> **Note**: The Plan Completion Stamp runs BEFORE these steps — see [arc-phase-completion-stamp.md](arc-phase-completion-stamp.md).
> `FORBIDDEN_PHASE_KEYS` is defined inline in SKILL.md and available in the orchestrator's context.

## Post-Arc Echo Persist

After the plan stamp, persist arc quality metrics to echoes for cross-session learning:

```javascript
if (exists(".claude/echoes/")) {
  // CDX-009 FIX: totalDuration is in milliseconds (Date.now() - arcStart), so divide by 60_000 for minutes.
  const totalDuration = Date.now() - arcStart  // milliseconds
  const metrics = {
    plan: checkpoint.plan_file,
    duration_minutes: Math.round(totalDuration / 60_000),
    phases_completed: Object.values(checkpoint.phases).filter(p => p.status === "completed").length,
    tome_findings: { p1: p1Count, p2: p2Count, p3: p3Count },
    convergence_cycles: checkpoint.convergence.history.length,
    mend_fixed: mendFixedCount,
    gap_addressed: addressedCount,
    gap_missing: missingCount,
  }

  appendEchoEntry(".claude/echoes/planner/MEMORY.md", {
    layer: "inscribed",
    source: `rune:arc ${id}`,
    content: `Arc completed: ${metrics.phases_completed}/${PHASE_ORDER.length} phases, ` +
      `${metrics.tome_findings.p1} P1 findings, ` +
      `${metrics.convergence_cycles} mend cycle(s), ` +
      `${metrics.gap_missing} missing criteria. ` +
      `Duration: ${metrics.duration_minutes}min.`
  })
}
```

## Completion Report

```
The Tarnished has claimed the Elden Throne.

Plan: {plan_file}
Checkpoint: .claude/arc/{id}/checkpoint.json
Branch: {branch_name}

Phases:
  1.   FORGE:           {status} — enriched-plan.md
  2.   PLAN REVIEW:     {status} — plan-review.md ({verdict})
  2.5  PLAN REFINEMENT: {status} — {concerns_count} concerns extracted
  2.7  VERIFICATION:    {status} — {issues_count} issues
  2.8  SEMANTIC VERIFY: {status} — codex-semantic-verification.md
  5.   WORK:            {status} — {tasks_completed}/{tasks_total} tasks
  5.5  GAP ANALYSIS:    {status} — {addressed}/{total} criteria addressed
  5.6  CODEX GAP:       {status} — codex-gap-analysis.md
  5.8  GAP REMEDIATION: {status} — gap-remediation-report.md ({fixed_count} fixed, {deferred_count} deferred)
  5.7  GOLDMASK VERIFY: {status} — goldmask-verification.md ({finding_count} findings, {critical_count} critical)
  6.   CODE REVIEW:     {status} — tome.md ({finding_count} findings)
  6.5  GOLDMASK CORR:   {status} — goldmask-correlation.md ({correlation_count} correlations, {human_review_count} human review)
  7.   MEND:            {status} — {fixed}/{total} findings resolved
  7.5  VERIFY MEND:     {status} — {convergence_verdict} (cycle {convergence.round + 1}/{convergence.tier.maxCycles})
  8.   AUDIT:           {status} — audit-report.md
  8.5  AUDIT MEND:      {status} — audit-mend-report.md ({fixed_count} fixed)
  8.7  AUDIT VERIFY:    {status} — audit-verify.md ({convergence_verdict})
  9.   SHIP:            {status} — PR: {pr_url || "skipped"}
  9.5  MERGE:           {status} — {merge_strategy} {wait_ci ? "(auto-merge pending)" : "(merged)"}

PR: {pr_url || "N/A — create manually with `gh pr create`"}

Review-Mend Convergence:
  Tier: {convergence.tier.name} ({convergence.tier.maxCycles} max cycles)
  Reason: {convergence.tier.reason}
  Cycles completed: {convergence.round + 1}/{convergence.tier.maxCycles}

  {for each entry in convergence.history:}
  Cycle {N}: {findings_before} → {findings_after} findings ({verdict})

Commits: {commit_count} on branch {branch_name}
Files changed: {file_count}
Time: {total_duration}

Artifacts: tmp/arc/{id}/
Checkpoint: .claude/arc/{id}/checkpoint.json

Next steps:
1. Review audit report: tmp/arc/{id}/audit-report.md
2. git log --oneline — Review commits
3. {pr_url ? "Review PR: " + pr_url : "Create PR for branch " + branch_name}
4. /rune:rest — Clean up tmp/ artifacts when done
```

## Post-Arc Final Sweep (ARC-9)

> **IMPORTANT — Execution order**: This step runs AFTER the completion report. It catches zombie
> teammates left alive by incomplete phase cleanup. Without this sweep, the lead session spins
> on idle notifications ("Twisting...") because the SDK still holds leadership state from
> the last phase's team. This is the safety net — `prePhaseCleanup` handles inter-phase cleanup,
> but there is no subsequent phase to trigger cleanup after Phase 9.5 (the last phase).
> Phases 9 and 9.5 are orchestrator-only so their cleanup is a no-op, but Phase 7 (MEND)
> and Phase 6 (CODE REVIEW) summon teams that need cleanup.

```javascript
// POST-ARC FINAL SWEEP (ARC-9)
// Catches zombie teammates from the last delegated phases (Phase 7: MEND and Phase 6: CODE REVIEW).
// prePhaseCleanup only runs BEFORE each phase — nothing cleans up AFTER the last phase.
// Without this, teammates survive and the lead spins on idle notifications indefinitely.

// Resolve config directory once (CLAUDE_CONFIG_DIR aware)
const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()

try {
  // Strategy A: Discover remaining teammates from checkpoint and shutdown
  // Iterate ALL phases with recorded team_name (not just the last one —
  // earlier phases may also have zombies if their cleanup was incomplete).
  for (const [phaseName, phaseInfo] of Object.entries(checkpoint.phases)) {
    if (FORBIDDEN_PHASE_KEYS.has(phaseName)) continue
    if (!phaseInfo?.team_name || typeof phaseInfo.team_name !== 'string') continue
    if (!/^[a-zA-Z0-9_-]+$/.test(phaseInfo.team_name)) continue

    const teamName = phaseInfo.team_name

    // Try to read team config to discover live members
    try {
      const teamConfig = Read(`${CHOME}/teams/${teamName}/config.json`)
      const members = Array.isArray(teamConfig.members) ? teamConfig.members : []
      const memberNames = members.map(m => m.name).filter(Boolean)

      if (memberNames.length > 0) {
        // Send shutdown_request to every discovered member
        for (const member of memberNames) {
          SendMessage({ type: "shutdown_request", recipient: member, content: "Arc pipeline complete — final sweep" })
        }
        // Brief grace period for shutdown approval responses (5s)
        Bash(`sleep 5`)
      }
    } catch (e) {
      // Team config unreadable — dir may already be gone. That's fine.
    }
  }

  // Strategy B: Clear SDK leadership state with retry-with-backoff
  // Same pattern as prePhaseCleanup Strategy 1 — must clear SDK state
  // so the session can exit cleanly without spinning on idle notifications.
  // SYNC-POINT: team_name validation regex must stay in sync with arc-preflight.md
  const SWEEP_DELAYS = [0, 3000, 5000]
  let sweepCleared = false
  for (let attempt = 0; attempt < SWEEP_DELAYS.length; attempt++) {
    if (attempt > 0) Bash(`sleep ${SWEEP_DELAYS[attempt] / 1000}`)
    try { TeamDelete(); sweepCleared = true; break } catch (e) {
      // Expected if no active team — SDK state already clear
    }
  }

  // Strategy C: Filesystem fallback — rm -rf all checkpoint-recorded teams
  // Only runs if TeamDelete didn't succeed (same CDX-003 gate as prePhaseCleanup)
  if (!sweepCleared) {
    for (const [pn, pi] of Object.entries(checkpoint.phases)) {
      if (FORBIDDEN_PHASE_KEYS.has(pn)) continue
      if (!pi?.team_name || typeof pi.team_name !== 'string') continue
      if (!/^[a-zA-Z0-9_-]+$/.test(pi.team_name)) continue

      Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${pi.team_name}/" "$CHOME/tasks/${pi.team_name}/" 2>/dev/null`)
    }
    // Final TeamDelete attempt after filesystem cleanup
    try { TeamDelete() } catch (e) { /* SDK state cleared or was already clear */ }
  }

  // Strategy D (v1.68.0): Prefix-based sweep for any teams missed by checkpoint
  // This catches teams where team_name was null (sub-command crash before state file).
  // Strategy D runs last because prefix-scan targets sub-command teams where this
  // session was never the leader — TeamDelete cannot release their SDK state.
  // Only rm-rf is needed. (rune-architect #4: ordering rationale documented)
  // Uses ARC_TEAM_PREFIXES from arc-preflight.md (loaded in dispatcher init context).
  for (const prefix of ARC_TEAM_PREFIXES) {
    if (!/^[a-z-]+$/.test(prefix)) continue
    // Resolve CHOME inline within same Bash call (ward-sentinel #4: prevents quoting gap)
    const dirs = Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && find "$CHOME/teams" -maxdepth 1 -type d -name "${prefix}*" 2>/dev/null`).split('\n').filter(Boolean)
    for (const dir of dirs) {
      const teamName = dir.split('/').pop()
      if (!teamName || !/^[a-zA-Z0-9_-]+$/.test(teamName)) continue
      if (teamName.includes('..')) continue
      // Session ownership check (v1.68.0 mend fix — SEC-001)
      const sessionMarker = Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && test -f "$CHOME/teams/${teamName}/.session" && cat "$CHOME/teams/${teamName}/.session" 2>/dev/null`).trim()
      const currentSessionId = Bash(`echo "$CLAUDE_SESSION_ID"`).trim()
      if (!sessionMarker || sessionMarker !== currentSessionId) {
        warn(`ARC-9 Strategy D: Skipping ${teamName} — no session marker or belongs to another session`)
        continue
      }
      // SEC: Atomic symlink guard + rm-rf in single Bash call (closes TOCTOU window)
      warn(`ARC-9 Strategy D: Cleaning orphan ${teamName}`)
      // SEC: teamName validated above with /^[a-zA-Z0-9_-]+$/ — shell injection not possible
      Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && [[ ! -L "$CHOME/teams/${teamName}" ]] && rm -rf "$CHOME/teams/${teamName}/" "$CHOME/tasks/${teamName}/" 2>/dev/null`)
    }
  }
  // Final TeamDelete after prefix sweep
  try { TeamDelete() } catch (e) { /* done */ }

} catch (e) {
  // Defensive — final sweep must NEVER halt the pipeline or prevent the completion
  // report from being shown. If this fails, the user can still /rune:cancel-arc.
  warn(`ARC-9: Final sweep failed (${e.message}) — use /rune:cancel-arc if session is stuck`)
}
```

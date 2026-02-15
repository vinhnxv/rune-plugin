# Damage Control — Recovery Procedures

Six named recovery procedures for Agent Team failures. Each follows ASSESS → CONTAIN → RECOVER → VERIFY → REPORT.

## Escalation Chain

| Level | Action | Owner |
|-------|--------|-------|
| 0 | Auto-detect (monitor polling, error catch) | System |
| 1 | Auto-remedy (retry, reassign, compress) | Tarnished |
| 2 | Graceful degradation (reduce scope, skip phase) | Tarnished |
| 3 | Human escalation (AskUserQuestion) | User |

**Double-failure guard**: Same recovery fails twice → skip to Level 2/3. No infinite loops.

---

## DC-1: Glyph Flood — Context Overflow

**Trigger**: "Prompt is too long" error or Glyph Budget exceeded

| Symptom | Detection |
|---------|-----------|
| API returns "prompt is too long" | Error message match |
| Agent output truncated/incoherent | PostToolUseFailure |
| Budget counter exceeds threshold | Monitor polling |

**Severity**: MEDIUM (single agent) · HIGH (lead or multiple agents)

| Step | Action |
|------|--------|
| ASSESS | Identify which agent hit limit; check task progress |
| CONTAIN | Pause new task assignment to affected agent |
| RECOVER | Compress: offload to `tmp/`, reduce team size, split remaining work |
| VERIFY | Confirm agent accepts new prompts post-compression |
| REPORT | Log overflow event with token estimate in checkpoint |

**Escalation**: L0 Glyph Budget warns 80% → L1 auto-compress → L2 reduce team → L3 ask user to split workflow
**Decision**: Forward-fix (compress). Rollback only if compression loses critical context.
**Refs**: SO-5 (Ember Overload) · Context Weaving skill

---

## DC-2: Broken Ward — Ward Check Failure

**Trigger**: Ward check (lint, test, type-check) returns non-zero exit

| Symptom | Detection |
|---------|-----------|
| Ward check exits non-zero | Exit code |
| Test failures in output | stdout/stderr parsing |
| Task marked complete despite failure | Completion audit |

**Severity**: LOW (lint/format) · MEDIUM (existing test fails) · HIGH (build/type-check)

| Step | Action |
|------|--------|
| ASSESS | Parse ward output — identify failing checks and files |
| CONTAIN | Do NOT commit. Hold changes in working tree |
| RECOVER | Create targeted fix task. Bisect if multiple failures |
| VERIFY | Re-run full ward check — all must pass |
| REPORT | Log failure type, fix applied, re-check result |

**Escalation**: L0 ward detects → L1 create fix task → L2 skip pre-existing failures (document reason) → L3 ask user
**Decision**: Forward-fix. Rollback (`git checkout -- file`) only if fix worsens state.
**Refs**: SO-4 (Blind Gaze) · Risk Tier 1+ · Mend bisection

---

## DC-3: Fading Ash — Agent Stale > 5 min

**Trigger**: No task progress from agent for > 5 minutes

| Symptom | Detection |
|---------|-----------|
| Task status unchanged > 5 min | Monitor polling (30s) |
| No messages from agent | Mailbox idle |
| Agent not responding | SendMessage timeout |

**Severity**: LOW (single, non-blocking) · MEDIUM (blocking downstream) · HIGH (multiple stale)

| Step | Action |
|------|--------|
| ASSESS | Check TaskList for agent's task; read last output |
| CONTAIN | Send warning message; wait 60s for response |
| RECOVER | Auto-release task (owner→null, status→pending); another worker claims it |
| VERIFY | Confirm re-claimed and progressing within 2 min |
| REPORT | Log stale agent name, task ID, time elapsed |

**Escalation**: L0 monitor detects at 5 min → L1 auto-release → L2 shutdown agent, redistribute → L3 ask user
**Decision**: Forward-fix (redistribute). Partial work remains in files.
**Refs**: Monitor utility · Team lifecycle guard

---

## DC-4: Phantom Team — TeamDelete Failure

**Trigger**: `TeamDelete` errors or team state persists after cleanup

| Symptom | Detection |
|---------|-----------|
| "Cannot cleanup team with N active members" | Error catch |
| "Already leading team" on next TeamCreate | Error catch |
| Team directory persists | `ls ~/.claude/teams/` |

**Severity**: LOW (dir removable) · MEDIUM (members refuse shutdown) · HIGH (multiple phantoms)

| Step | Action |
|------|--------|
| ASSESS | Read `~/.claude/teams/{name}/config.json` — discover all members |
| CONTAIN | `shutdown_request` to each member; wait 30s |
| RECOVER | Retry TeamDelete. Fallback: `rm -rf ~/.claude/teams/{name}/ ~/.claude/tasks/{name}/` |
| VERIFY | Team dir gone; TeamCreate succeeds for next workflow |
| REPORT | Log phantom team name and cleanup method |

**Escalation**: L0 error caught → L1 shutdown+retry → L2 filesystem fallback → L3 ask user to check `~/.claude/teams/`
**Decision**: Forward-fix only. Phantom teams must be cleaned to proceed.
**Refs**: Team lifecycle guard (pre-create, cleanup, dynamic discovery) · Team name: `/^[a-zA-Z0-9_-]+$/`

---

## DC-5: Crossed Runes — Concurrent Workflow Overlap

**Trigger**: Two `/rune:*` commands attempt to run simultaneously

| Symptom | Detection |
|---------|-----------|
| TeamCreate fails — team exists | Error catch |
| Foreign tasks in task list | TaskList audit |
| Unexpected agents in config | Member count mismatch |

**Severity**: MEDIUM (same command type) · HIGH (different types or arc overlap)

| Step | Action |
|------|--------|
| ASSESS | Check `~/.claude/teams/` — identify which workflow owns each team |
| CONTAIN | Refuse new workflow; warn user about active workflow |
| RECOVER | Wait for active workflow, or cancel first (`/rune:cancel-*`) |
| VERIFY | No team directories remain before starting new workflow |
| REPORT | Log which workflows conflicted and resolution |

**Escalation**: L0 pre-create guard detects → L1 auto-refuse with message → L3 ask user to choose (wait/cancel/force)
**Decision**: Prevent, not fix. Never auto-cancel a running workflow.
**Refs**: SO-2 (Shattered Rune) · Team lifecycle guard · Cancel commands

---

## DC-6: Lost Grace — Context Compaction Mid-Workflow

**Trigger**: Claude compacts conversation while agents are active

| Symptom | Detection |
|---------|-----------|
| Lead loses track of team/agent names | Post-compaction confusion |
| Checkpoint state not referenced | Missing phase tracking |
| Duplicate tasks or re-assignments | TaskList audit |

**Severity**: LOW (post-completion) · MEDIUM (during monitoring) · HIGH (during phase transition)

| Step | Action |
|------|--------|
| ASSESS | Re-read team config, task list, and inscription contract |
| CONTAIN | Do NOT create tasks or spawn agents until state recovered |
| RECOVER | Reconstruct from: checkpoint.json, task list, tmp/ artifacts |
| VERIFY | Cross-check recovered state against filesystem; confirm agent count |
| REPORT | Log compaction event and recovery status |

**Escalation**: L0 compaction triggers re-read (Core Rule #5) → L1 auto-recover from checkpoint → L2 skip degraded phases → L3 ask user to restart
**Decision**: Forward-fix from last state. Full restart only if checkpoint corrupted.
**Refs**: Core Rule #5 · Session handoff · Arc checkpoint.json

---

## Quick Reference

| DC | Name | Class | First Response | Escalation Trigger |
|----|------|-------|---------------|--------------------|
| 1 | Glyph Flood | Context | Compress + offload | Compression insufficient |
| 2 | Broken Ward | Quality | Create fix task | Fix worsens state |
| 3 | Fading Ash | Agent | Auto-release task | Multiple agents stale |
| 4 | Phantom Team | Lifecycle | Shutdown + retry | rm -rf fallback needed |
| 5 | Crossed Runes | Lifecycle | Refuse new workflow | User must choose |
| 6 | Lost Grace | Context | Re-read state files | State too degraded |

# Orchestrator Echoes

## Inscribed — Arc: Authentication Microservice v2.0.0 (2026-01-10)

**Source**: `rune:arc arc-session-001`
**Confidence**: HIGH (all 10 phases completed, convergence verified)

### Arc Metrics

- Plan: plans/2026-01-10-feat-auth-microservice-plan.md
- Duration: ~4 hours across 3 context sessions
- Phases completed: 10/10
- TOME findings: 18 total (resolved to 0 in 2 convergence rounds)
- Convergence rounds: 2 (round 0: 18 to 3, round 1: 3 to 0)
- Commits: 6 on feature branch

### Key Learnings

1. **Direct orchestrator mend is faster for markdown pseudocode**: All TOME findings targeted `.md` specification files. Team-based mend would have added 10+ minutes of overhead for zero benefit. Heuristic confirmed: if all findings target `.md` files, use direct mend.

2. **Convergence gate catches real regressions**: Round 0 spot-check found a P1 regression (undefined variable in error handler). The retry mechanism fixed it in round 1, validating the 2-retry convergence design.

3. **Multi-session arc resilience**: Checkpoint system preserved state across 3 sessions with no data loss. Schema migration handled cleanly between sessions.

## Inscribed - Database Migration Safety Patterns (2026-01-25)

**Source**: `rune:arc arc-session-002`
**Confidence**: HIGH (verified via 3 audit agents)

### Key Learnings

1. **Always use reversible migrations**: `ALTER TABLE DROP COLUMN` is irreversible in SQLite. Use the copy-table strategy instead: create new table, copy data, drop old, rename.

2. **Lock timeout prevents deadlocks during migration**: Setting `busy_timeout=30000` (30s) prevents indefinite blocking when concurrent connections hold read locks during schema changes.

3. **Data backfill must be idempotent**: Migration scripts that populate new columns should use `UPDATE ... WHERE new_col IS NULL` to allow safe re-runs after partial failures.

## Etched — Team Lifecycle Ghost State Recovery (2026-02-05)

**Source**: `rune:arc arc-session-003`
**Confidence**: HIGH (8th confirmed occurrence)

Ghost team Strategy 4 remains essential for multi-session arcs: SDK leadership state from Phase 6 review team persisted through context continuations and blocked Phase 8 audit TeamCreate. Recreating minimal dir then TeamDelete then cleanup worked on first attempt. This is the most reliable pattern for resolving stale SDK state.

The `rm -rf` filesystem fallback is essential because TeamDelete fails with "Cannot cleanup team with N active members" even after all shutdown approvals are received. This has been observed in 8 consecutive arcs.

## Traced — Experimental: Parallel Mend Workers (2026-02-12)

**Source**: rune:strive work-session-001
**Confidence**: LOW (single session, needs more data)

Attempted 5 parallel mend workers on a 30-file changeset. Workers 3 and 4 experienced `.git/index.lock` contention despite commit broker serialization. Root cause: workers were running `git diff` for pre-fix snapshots, which acquires a shared lock that conflicts with the broker's exclusive lock during commit.

Potential fix: have workers use `git diff --no-index` against a stashed copy instead of the working tree.

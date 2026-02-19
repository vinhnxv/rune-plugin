# Workers Echoes

## Inscribed — Commit Broker Serialization Pattern (2026-01-18)

**Source**: `rune:work work-abc123`
**Confidence**: HIGH (verified across 4 work sessions)

### Implementation Notes

- Workers generate patches via `git diff > patch.file` instead of committing directly
- Orchestrator applies patches sequentially to eliminate `.git/index.lock` contention
- Patch application uses `git apply --check` before `git apply` for safety
- Failed patch application triggers a 3-way merge fallback

### Metrics

- 4 sessions tested with 3-5 workers each
- Zero `.git/index.lock` errors after broker implementation
- Average patch application time: 200ms per patch
- Worst case merge resolution: 2.3 seconds

## Inscribed — Ward Check Bisection Algorithm (2026-02-03)

**Source**: `rune:mend mend-def456`
**Confidence**: HIGH (algorithm verified through 6 mend sessions)

### Algorithm

When ward check fails after multiple fixer outputs are applied:
1. Binary search: revert half the fixes, re-run ward
2. If ward passes: failing fix is in reverted half
3. Recurse until individual failing fix is identified
4. Mark failing fix as FAILED, re-apply all other fixes

### Edge Cases Discovered

- **Interdependent fixes**: Fix A depends on Fix B being applied first. Bisection must respect dependency ordering from Phase 1.5 cross-group analysis.
- **Flaky wards**: Some ward commands (especially integration tests) have non-deterministic failures. Added retry logic: 2 consecutive failures before marking as FAILED.
- **Empty revert set**: When only one fix was applied, bisection degenerates to a simple revert-and-retry.

## Etched — TypeScript Migration Conventions (2026-02-07)

**Source**: `rune:work work-ts-migration`
**Confidence**: MEDIUM (conventions stabilized after 3 migration batches)

Established conventions for the ongoing TypeScript migration:
- Use `strict: true` in tsconfig.json from the start — retrofitting strict mode is painful
- Prefer `interface` over `type` for object shapes (better error messages, extendable)
- Use `unknown` instead of `any` at API boundaries — forces explicit type narrowing
- Barrel exports (`index.ts`) only at package boundaries, not for every directory
- Naming: `PascalCase` for types/interfaces, `camelCase` for functions/variables, `UPPER_SNAKE` for constants

## Traced — Flaky Test Root Causes (2026-02-14)

**Source**: rune:work work-flaky-tests
**Confidence**: LOW (3 flaky tests identified, fix pending)

Three flaky tests in the CI pipeline:
1. `test_websocket_reconnect`: Race condition between disconnect event and reconnect timer. Needs explicit wait-for-event instead of sleep(100ms).
2. `test_cache_expiry`: System clock precision on CI runners causes off-by-one in TTL comparison. Use monotonic clock instead of wall clock.
3. `test_concurrent_writes`: SQLite WAL mode allows concurrent reads but serializes writes. Test assumes parallel writes succeed simultaneously — needs sequential assertion.

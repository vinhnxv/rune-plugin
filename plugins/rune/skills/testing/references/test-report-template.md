# Test Report Template

## File Hierarchy

```
tmp/arc/{id}/
├── test-strategy.md                    # Pre-execution analysis (STEP 1.5)
├── test-report.md                      # Final aggregated report (STEP 9)
├── test-results-unit.md                # Unit tier raw output
├── test-results-integration.md         # Integration tier raw output
├── test-results-e2e.md                 # E2E tier aggregated output
├── e2e-checkpoint-route-{N}.json       # Per-route checkpoint (crash recovery)
├── e2e-route-{N}-result.md             # Per-route detailed trace
├── screenshots/
│   └── route-{N}-step-{S}.png
└── docker-containers.json              # For crash recovery cleanup
```

## Main Report Format (test-report.md)

```markdown
# Test Report — Arc {id}

## Strategy vs Results
| Prediction | Actual Result | Match? |
|------------|---------------|--------|
| Unit: N tests, expect pass | N pass, M fail | YES/NO |

## Summary
| Tier | Status | Tests | Passed | Failed | Flaky | Diff Coverage | Duration |
|------|--------|-------|--------|--------|-------|---------------|----------|
| Unit | PASS/FAIL/SKIP/TIMEOUT | N | N | N | N | N% | Ns |
| Integration | PASS/FAIL/SKIP/TIMEOUT | N | N | N | N | — | Ns |
| E2E/Browser | PASS/FAIL/SKIP/TIMEOUT | N routes | N | N | N | — | Ns |

**Overall**: {PASS/WARN/FAIL}
**Pass Rate**: {0.0-1.0 | null if 0 tests}
**Diff Coverage**: {N}% (warning threshold: 70%)
**Duration**: {total}
**Tiers Run**: [{list}]

## Integrity Checks
- Stale test detection (WF-1): {PASS/WARNING}
- Shallow verification (WF-2): {N/A or routes with depth=0}
- Data contamination (WF-3): {PASS/WARNING}
- Misattribution check (WF-5): {PASS/WARNING}
- Budget utilization: {time per tier vs allocated}

## Uncovered Implementations
- {file_path} — no test file found

## Flaky Tests
- {test_name} — passed on retry (flaky: true, tier: {tier})

## [Tier Details - per tier sections]

## Acceptance Criteria Traceability
| Plan AC | Test(s) Covering | Status |
|---------|------------------|--------|
| AC-001: {description} | test_name_1, test_name_2 | COVERED |
| AC-002: {description} | — | NOT COVERED |

## [Failure Analysis - if failures detected]

## [Screenshots - if E2E ran]

<!-- SEAL: test-report-complete -->
```

## Failure Trace Structure (TEST-NNN)

Every TEST-NNN finding MUST include:

| Field | Required | Description |
|-------|----------|-------------|
| Step failed | YES | Which operation failed |
| Expected | YES | What was expected |
| Actual | YES | What happened |
| Log source | YES | BACKEND / FRONTEND / BACKEND_VIA_FRONTEND / TEST_FRAMEWORK / INFRASTRUCTURE / UNKNOWN |
| Error type | YES | validation / regression / crash / timeout / flaky / missing_dep |
| Stack trace | if available | Max 10 lines |
| Backend logs | if available | Last 5-10 lines around failure |
| Frontend console | if available | JS errors from agent-browser |
| Scope | YES | Which changed file(s) relate |
| Retry | YES | Was it retried? Result? |

## Machine-Readable Fields

For audit phase consumption:
- `pass_rate`: 0.0-1.0 or `null` (no tests / timed out — NOT 0.0)
- `coverage_pct`: DIFF coverage (not overall)
- `no_tests_found`: boolean
- `tiers_run`: array of tier names
- `uncovered_implementations`: files with code but no tests
- `flaky_tests`: tests that passed on retry
- `log_sources`: finding → log attribution map
- `strategy_match`: predicted vs actual comparison

## SEAL Markers

Each tier and the main report end with a SEAL marker:
- `<!-- SEAL: unit-test-complete -->`
- `<!-- SEAL: integration-test-complete -->`
- `<!-- SEAL: e2e-test-complete -->`
- `<!-- SEAL: test-report-complete -->`

Missing SEAL = incomplete report. Audit falls back to per-tier files.

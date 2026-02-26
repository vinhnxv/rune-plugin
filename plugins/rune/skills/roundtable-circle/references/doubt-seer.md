# Doubt Seer — Cross-Examination Protocol

> Phase 4.5: Optional adversarial verification of Ash findings for unsubstantiated claims.

## Trigger Conditions

ALL must be true:
1. `doubt_seer.enabled !== false` in talisman (default: `false` — opt-in)
2. `doubt_seer.workflows` includes current workflow type (`"review"` or `"audit"`)
3. Total P1+P2 finding count across Ash outputs > 0

## Registration vs Activation

Doubt-seer is **registered** in `inscription.json` `teammates[]` at Phase 2 (unconditionally, when enabled) so hooks and Runebinder discover it. However, it is only **spawned** at Phase 4.5 (conditionally, when P1+P2 findings > 0). If not spawned, the inscription entry exists but no output file is written — Runebinder handles this as "missing" in Coverage Gaps.

## Signal Count

`.expected` is set to `ashCount` at Phase 2 (excluding doubt-seer). At Phase 4.5, orchestrator increments `.expected` by 1 before spawning. Doubt-seer gets its own 5-minute polling loop. On timeout: write `[DOUBT SEER: TIMEOUT]` marker and proceed. If P1+P2 count == 0: write skip marker.

## VERDICT Parsing

| Condition | Verdict | Action |
|-----------|---------|--------|
| `unproven_p1_count > 0` AND `block_on_unproven: true` | BLOCK | Halt workflow, report to user |
| Any unproven claims (P1 or P2) | CONCERN | Continue, flag in TOME |
| All findings have evidence | PASS | Continue normally |

## Runebinder Integration

Runebinder reads all teammate output files including `doubt-seer.md` (discovered via `inscription.json`). Doubt-seer challenges appear in a `## Doubt Seer Challenges` section in the TOME after the main findings.

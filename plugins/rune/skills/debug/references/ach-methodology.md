# ACH Methodology — Analysis of Competing Hypotheses

Reference document for the `/rune:debug` skill. Defines the failure categories, evidence
classification tiers, and arbitration algorithm used in parallel debugging.

## 6 Failure Categories

Each category maps to a hypothesis generation template and has trigger heuristics
for automated classification during the TRIAGE phase.

| Category | ID Prefix | Trigger Heuristic |
|----------|----------|-------------------|
| REGRESSION | H-REG | `git log` shows activity within 5 commits + failure is deterministic |
| ENVIRONMENT | H-ENV | Error contains "not found", "permission denied", "timeout", or "works locally" |
| DATA/FIXTURE | H-DATA | Failures non-deterministic across runs, uses DB fixtures, or data layer in stack trace |
| LOGIC ERROR | H-LOGIC | Error deterministic, stack trace points to application code, isolatable to specific function |
| INTEGRATION | H-INT | Stack trace spans two modules, involves serialization, or manifests at API boundary |
| CONCURRENCY | H-CONC | Failure intermittent (<100% of runs), codebase has async code or shared mutable state |

### Category Detection Priority

When multiple heuristics match, prefer the category with the most specific evidence:
1. CONCURRENCY (if intermittent) — hardest to debug, needs dedicated approach
2. REGRESSION (if recent commits correlate) — fastest to verify via `git bisect`
3. INTEGRATION (if cross-module) — boundary issues need both sides examined
4. ENVIRONMENT (if environment-specific) — can be confirmed by environment comparison
5. DATA/FIXTURE (if data-dependent) — check fixture freshness
6. LOGIC ERROR (default) — most common, use when others don't match

---

## Evidence Classification (4 Tiers)

Evidence gathered by hypothesis-investigator agents is classified into tiers that
determine its weight in the arbitration algorithm.

| Tier | Label | Weight | Definition | Example |
|------|-------|--------|------------|---------|
| 1 | DIRECT | 1.0 | Uniquely produces/eliminates failure when present/absent | `git bisect` result, toggling code path reproduces/fixes |
| 2 | CORRELATIONAL | 0.6 | Statistically associated but has alternate explanations | Timing correlation, co-occurring log entries |
| 3 | TESTIMONIAL | 0.3 | Prior understanding, docs, or reasoning without direct observation | "This module has been flaky before", doc says X |
| 4 | ABSENCE | 0.8/0.2 | Expected evidence sought but not found | 0.8 if exhaustive search, 0.2 if shallow search |

### ABSENCE Tier Scoring

ABSENCE evidence weight depends on search exhaustiveness:
- **0.8** (exhaustive): All relevant files searched, all branches checked, multiple approaches tried
- **0.2** (shallow): Quick search, limited scope, might have missed something
- The investigator must justify which weight applies in the evidence report

---

## Arbitration Algorithm (7 Steps)

The lead agent (Tarnished) executes this deterministic algorithm after collecting
all investigator evidence reports.

### Step 1 — Parse Reports

For each investigator report, extract:
- `hypothesis_id`: The hypothesis identifier (e.g., H-REG-001)
- `verdict`: CONFIRMED | LIKELY | INCONCLUSIVE | UNLIKELY | REFUTED
- `evidence[]`: Array of evidence items with tier, weight, and direction
- `confidence_raw`: The investigator's raw confidence (0.0-1.0)

### Step 2 — Compute Weighted Evidence Score (WES)

For each hypothesis:
```
WES(H) = sum(supporting_evidence × tier_weight) - sum(refuting_evidence × tier_weight)
```

Example: H-REG-001 has 2 DIRECT supporting (2 × 1.0 = 2.0) and 1 CORRELATIONAL refuting (1 × 0.6 = 0.6):
```
WES = 2.0 - 0.6 = 1.4
```

### Step 3 — Apply Falsification Penalty

For each DIRECT refutation from a **different** investigator (cross-hypothesis falsification):
```
penalty += 0.4 per DIRECT cross-refutation
```

This penalizes hypotheses where another investigator found direct evidence against it while investigating their own hypothesis.

### Step 4 — Compute Final Confidence Score (FCS)

```
FCS(H) = clamp((WES - penalty) × confidence_raw, 0, 1)
```

Where `clamp(x, 0, 1)` bounds the result to [0.0, 1.0].

### Step 5 — Rank and Filter

1. Rank hypotheses by FCS descending
2. Exclude hypotheses with verdict = REFUTED

### Step 6 — Threshold Check

| Condition | Action |
|-----------|--------|
| `FCS < 0.35` for ALL hypotheses | **Re-triage**: Generate new hypotheses, spawn round 2 |
| `FCS(winner) - FCS(runner_up) < 0.1` | **Tiebreaker**: Apply tiebreaker rules (see below) |
| `FCS(winner) >= 0.35` and clear margin | **Accept**: Proceed to FIX phase |

### Step 7 — Emit Verdict

Output the final verdict with:
- PRIMARY hypothesis (highest FCS)
- Supporting evidence summary (top 3 items by tier weight)
- Refuted alternatives (with reason)
- Final confidence tier: HIGH (>0.8) | MEDIUM (0.5-0.8) | LOW (0.35-0.5)

---

## Tiebreaker Rules

When FCS difference between top two hypotheses is < 0.1, apply in order:

1. **DIRECT evidence count**: More DIRECT evidence wins
2. **Absence of DIRECT refutation**: No direct refutation beats having one
3. **Echo corroboration**: Past echo entries supporting the hypothesis
4. **Disproof test specificity**: More specific disproof test wins
5. **Compound hypothesis**: If still tied, declare compound bug (multiple causes)

---

## Edge Case Protocols

| Scenario | Protocol |
|----------|----------|
| All hypotheses falsified | Re-triage: extract cross-hypothesis signals, generate new hypotheses, spawn round 2 (max 2 rounds then escalate to user) |
| 2+ hypotheses tied | Apply tiebreaker rules above; if still tied, declare compound bug |
| Compound bug detected | Emit compound verdict with interaction mechanism, fix sequence order, per-cause defense-in-depth layers |
| Investigator timeout | Proceed with N-1 reports, note gap in verdict |
| TeamCreate fails | Fall back to single-agent `systematic-debugging` |
| <2 hypotheses generated | Fall back to single-agent `systematic-debugging` |

---

## Defense-in-Depth Mapping (Post-Fix)

After the dominant hypothesis is confirmed and fixed, apply defensive layers
based on the failure category. See [defense-in-depth.md](../../systematic-debugging/references/defense-in-depth.md) for full layer details.

| Category | Required Layers | Rationale |
|----------|----------------|-----------|
| LOGIC ERROR | 2 (Assertions) + 5 (Tests) | Violated invariant needs assertion + regression test |
| DATA/FIXTURE | 1 (Input Validation) + 2 + 5 | Bad data needs boundary check + invariant + test |
| INTEGRATION | 3 (Error Handling) + 4 (Monitoring) + 5 | Boundary failure needs graceful degradation + observability |
| ENVIRONMENT | 4 (Monitoring) + documentation + 5 | Env-specific needs observability + setup docs + test |
| REGRESSION | 5 (Tests) mandatory | Write the test that would have caught it |
| CONCURRENCY | 2 (locks/invariants) + 4 + 5 | Race condition needs synchronization + monitoring + test |

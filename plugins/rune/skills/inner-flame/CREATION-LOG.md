# Inner Flame — Creation Log

## Problem Statement
Agents (workers, fixers, reviewers) were marking tasks as complete without meaningful self-review, leading to quality regressions caught only in downstream phases. Workers would claim "tests pass" without evidence, fixers would mark findings as FIXED without reading back the file, and reviewers would emit generic findings without verifying against the actual codebase. The convergence loop (review-mend cycle) was retrying due to low-quality first-pass output.

## Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Post-hoc review by the Tarnished (orchestrator) | Doesn't scale — orchestrator would need to review every teammate's output, consuming context window and adding latency |
| Hook-only validation (TaskCompleted gate) | Can check structural markers (file exists, seal present) but cannot verify semantic quality (did the fix actually resolve the finding?) |
| Separate QA agent per teammate | Too expensive — doubles agent count and context cost for every workflow |

## Key Design Decisions
- **3-layer model (Grounding + Completeness + Self-Adversarial)**: Each layer catches a different failure mode. Grounding catches hallucinated claims ("I fixed it" without Read-back). Completeness catches partial work (3 of 5 findings addressed). Self-Adversarial catches introduced regressions ("what if my fix breaks X?"). Removing any layer leaves a blind spot.
- **Confidence threshold of 60 for completion gate**: Below 60, the agent must re-examine. Set empirically — too low (40) lets sloppy work through, too high (80) causes excessive self-doubt loops. The 60 threshold balances throughput with quality.
- **Role-adaptive checklists**: Workers, fixers, reviewers, and researchers have different failure modes. A single generic checklist would miss role-specific anti-patterns (e.g., fixers not checking identifier consistency, workers not running ward checks).

## Observed Rationalizations (from Skill Testing)
Agent behaviors observed during pressure testing:
- "Tests pass" (without running tests) → Counter: Layer 1 item #6 requires fresh evidence — cite specific command output or file:line references
- "I verified the fix" (without Read-back) → Counter: Layer 1 item #1 requires Read() call with cited line numbers
- "This looks correct" (without adversarial thinking) → Counter: Layer 3 asks "What if this fix introduces a NEW bug?"

## Iteration History
| Date | Version | Change | Trigger |
|------|---------|--------|---------|
| 2026-02-13 | v1.0 | Initial 3-layer self-review protocol | Agents marking tasks complete without verification |
| 2026-02-23 | v1.1 | Added Layer 1.5 (Fresh Evidence Gate) — item #6 requiring evidence citations | Agents claiming completion with generic phrases instead of concrete evidence |
| 2026-02-23 | v1.2 | Per-role evidence items for Worker (3), Fixer (3), Reviewer (1) | Generic checklist missing role-specific failure modes |

# CREATION-LOG Template

Copy this to `skills/<name>/CREATION-LOG.md` when creating or significantly modifying a skill.

## Template

---

# {Skill Name} — Creation Log

## Problem Statement
What problem does this skill solve? What was happening before it existed?
What failure modes triggered its creation?

## Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| {approach 1} | {reason — be specific about the failure mode} |
| {approach 2} | {reason} |

## Key Design Decisions
- **{decision 1}**: {rationale, including what would break if decided differently}
- **{decision 2}**: {rationale}

## Observed Rationalizations (from Skill Testing)
Agent behaviors observed during pressure testing (see skill-testing methodology):
- "{exact agent phrase}" → Counter: {what the skill says to prevent this}
- "{exact agent phrase}" → Counter: {counter}

## Iteration History
| Date | Version | Change | Trigger |
|------|---------|--------|---------|
| {YYYY-MM-DD} | v1.0 | Initial creation | {what failure triggered it} |
| {YYYY-MM-DD} | v1.1 | Added {feature} | {observed bypass or failure} |

---

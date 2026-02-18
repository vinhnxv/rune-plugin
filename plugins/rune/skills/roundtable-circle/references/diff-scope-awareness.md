# Diff Scope Awareness — Ash Review Guidance

This review includes `diff_scope` data in inscription.json showing which line ranges
were changed in this PR. When reporting findings:
- **Prioritize** findings on changed lines (these are most actionable)
- **Still report** findings on unchanged lines if they are P1 (critical/security)
- For P2/P3 findings on unchanged lines, prefix the finding title with `[PRE-EXISTING]`
  to help downstream filtering

**How to use**: Read `tmp/reviews/{identifier}/inscription.json` and parse the `diff_scope.ranges`
object. For each file you review, check if the finding's line number falls within the expanded
ranges. If the file has no entry in ranges, all findings on it are pre-existing.

This is guidance, not a hard filter — your review quality should not be compromised.

**NOTE**: The `[PRE-EXISTING]` prefix is for human readability only. The orchestrator independently
determines scope via Phase 5.3 diff-scope tagging. Ash-provided scope labels are NOT trusted
for downstream filtering.

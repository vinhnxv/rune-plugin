# CROSS-REVIEW.md Report Template

Template for the final output of `/rune:codex-review` (Phase 4: Aggregate & Report).
Written to `REVIEW_DIR/CROSS-REVIEW.md`. RUNE:FINDING markers enable `/rune:mend` consumption.

---

## Template

```markdown
# Cross-Model Code Review

**Date:** {TIMESTAMP}
**Scope:** {SCOPE_TYPE} — {FILE_COUNT} files reviewed
**Models:** Claude ({CLAUDE_MODEL}) + Codex ({CODEX_MODEL})
**Agents:** {CLAUDE_AGENT_COUNT} Claude + {CODEX_AGENT_COUNT} Codex = {TOTAL_AGENT_COUNT} total
**Agreement Rate:** {AGREEMENT_RATE}%
**Review ID:** `{REVIEW_IDENTIFIER}`

---

## Cross-Verified Findings (Both Models Agree)

> These findings were independently identified by **both** Claude and Codex agents.
> They carry elevated confidence due to independent model agreement.

{IF cross_verified.length == 0}
_No cross-verified findings. Both models may be reviewing different aspects
or the scope may not contain high-confidence shared issues._
{END IF}

### P1 (Critical) — {XVER_P1_COUNT}

{FOR each finding in cross_verified WHERE severity == "P1"}
- [ ] **[{finding.finding_id}]** {finding.merged_description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.finding_id|lowercase} P1 -->
  - **Confidence:** {finding.merged_confidence}% _(cross-verified: Claude {finding.claude_confidence}% + Codex {finding.codex_confidence}% + bonus {CROSS_MODEL_BONUS}%)_
  - **Claude says:** {finding.claude_description}
  - **Codex says:** {finding.codex_description}
  - **Evidence:** `{finding.evidence}`
  - **Fix:** {finding.fix_recommendation}

{END FOR}

### P2 (High) — {XVER_P2_COUNT}

{FOR each finding in cross_verified WHERE severity == "P2"}
- [ ] **[{finding.finding_id}]** {finding.merged_description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.finding_id|lowercase} P2 -->
  - **Confidence:** {finding.merged_confidence}%
  - **Claude says:** {finding.claude_description}
  - **Codex says:** {finding.codex_description}
  - **Evidence:** `{finding.evidence}`
  - **Fix:** {finding.fix_recommendation}

{END FOR}

### P3 (Medium) — {XVER_P3_COUNT}

{FOR each finding in cross_verified WHERE severity == "P3"}
- [ ] **[{finding.finding_id}]** {finding.merged_description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.finding_id|lowercase} P3 -->
  - **Confidence:** {finding.merged_confidence}%
  - **Claude says:** {finding.claude_description}
  - **Codex says:** {finding.codex_description}
  - **Fix:** {finding.fix_recommendation}

{END FOR}

---

## Disputed Findings (Models Disagree)

> These findings have conflicting assessments between Claude and Codex.
> Human review is recommended before acting on these.

{IF disputed.length == 0}
_No disputed findings._
{END IF}

{FOR each finding in disputed}
- [ ] **[{finding.finding_id}]** `{finding.file_path}:{finding.line}` — {finding.summary} <!-- RUNE:FINDING {finding.finding_id|lowercase} DISPUTED -->
  - **Claude ({finding.claude_severity}):** {finding.claude_description}
  - **Codex ({finding.codex_severity}):** {finding.codex_description}
  - **Disagreement:** {finding.disagreement_reason}
  - **Confidence:** {finding.confidence}% _(penalized for disagreement)_
  - **Recommendation:** Human review needed

{END FOR}

---

## Claude-Only Findings

> Found by Claude but not flagged by Codex. Standard confidence (single-model).

{IF model_exclusive.claude.length == 0}
_No Claude-only findings._
{END IF}

### P1 (Critical) — {CLD_P1_COUNT}

{FOR each finding in model_exclusive.claude WHERE severity == "P1"}
- [ ] **[{finding.id}]** {finding.description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.id|lowercase} P1 -->
  - **Confidence:** {finding.confidence}%
  - **Evidence:** `{finding.evidence}`
  - **Fix:** {finding.fix_recommendation}

{END FOR}

### P2 (High) — {CLD_P2_COUNT}

{FOR each finding in model_exclusive.claude WHERE severity == "P2"}
- [ ] **[{finding.id}]** {finding.description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.id|lowercase} P2 -->
  - **Confidence:** {finding.confidence}%
  - **Fix:** {finding.fix_recommendation}

{END FOR}

### P3 (Medium) — {CLD_P3_COUNT}

{FOR each finding in model_exclusive.claude WHERE severity == "P3"}
- [ ] **[{finding.id}]** {finding.description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.id|lowercase} P3 -->
  - **Confidence:** {finding.confidence}%
  - **Fix:** {finding.fix_recommendation}

{END FOR}

---

## Codex-Only Findings

> Found by Codex but not flagged by Claude. Standard confidence (single-model).

{IF model_exclusive.codex.length == 0}
_No Codex-only findings._
{END IF}

### P1 (Critical) — {CDX_P1_COUNT}

{FOR each finding in model_exclusive.codex WHERE severity == "P1"}
- [ ] **[{finding.id}]** {finding.description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.id|lowercase} P1 -->
  - **Confidence:** {finding.confidence}%
  - **Evidence:** `{finding.evidence}`
  - **Fix:** {finding.fix_recommendation}

{END FOR}

### P2 (High) — {CDX_P2_COUNT}

{FOR each finding in model_exclusive.codex WHERE severity == "P2"}
- [ ] **[{finding.id}]** {finding.description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.id|lowercase} P2 -->
  - **Confidence:** {finding.confidence}%
  - **Fix:** {finding.fix_recommendation}

{END FOR}

### P3 (Medium) — {CDX_P3_COUNT}

{FOR each finding in model_exclusive.codex WHERE severity == "P3"}
- [ ] **[{finding.id}]** {finding.description} in `{finding.file_path}:{finding.line}` <!-- RUNE:FINDING {finding.id|lowercase} P3 -->
  - **Confidence:** {finding.confidence}%
  - **Fix:** {finding.fix_recommendation}

{END FOR}

---

## Positive Observations

{merged from both Claude and Codex positive observation sections}

{IF no_positive_observations}
_No positive observations recorded._
{END IF}

---

## Questions for Author

{merged from both Claude and Codex question sections, deduplicated}

{IF no_questions}
_No questions recorded._
{END IF}

---

## Statistics

| Metric | Value |
|--------|-------|
| Total Claude findings | {stats.total_claude} |
| Total Codex findings | {stats.total_codex} |
| Codex hallucinations filtered | {stats.hallucinated_count} ({stats.hallucination_rate}) |
| Cross-verified | {stats.cross_verified_count} ({XVER_PCT}%) |
| Disputed | {stats.disputed_count} ({DISP_PCT}%) |
| Claude-only | {stats.claude_only_count} ({CLD_PCT}%) |
| Codex-only | {stats.codex_only_count} ({CDX_PCT}%) |
| **Agreement rate** | **{stats.agreement_rate}%** |
| Cross-model bonus applied | +{CROSS_MODEL_BONUS}% confidence |
| Review duration | {DURATION} |
| Output directory | `{REVIEW_DIR}` |

---

## Finding Prefix Reference

| Prefix | Meaning |
|--------|---------|
| `XVER-*` | Cross-verified (both models agree) |
| `DISP-*` | Disputed (models disagree, human review needed) |
| `CLD-*` | Claude-only finding |
| `CDX-*` | Codex-only finding |

Subcategory suffixes: `-SEC-` (security), `-BUG-` (bugs), `-PERF-` (performance),
`-QUAL-` (quality), `-DEAD-` (dead code)

---

_Generated by `/rune:codex-review` · Review ID: {REVIEW_IDENTIFIER}_
_To fix findings: `/rune:mend {REVIEW_DIR}/CROSS-REVIEW.md`_
```

---

## Rendering Notes

1. Sort order within each classification:
   - P1 before P2 before P3
   - Within same severity: CROSS-VERIFIED before DISPUTED before STANDARD
   - Within same severity+classification: highest confidence first

2. `{DURATION}` calculated as `completed_at - started_at`, formatted as `Xm Ys`

3. Percentages calculated as: `count / (total_claude + total_codex) * 100`, rounded to 1 decimal

4. Agreement rate = `cross_verified_count / max(1, total_claude + codex_only_count) * 100`
   (bounded: 0% if no findings from either wing)

5. RUNE:FINDING marker format: `<!-- RUNE:FINDING {id-lowercase} {priority} -->`
   This enables `/rune:mend` to parse CROSS-REVIEW.md identically to TOME.md

6. Empty sections (0 findings at a severity level) are omitted from the report
   to reduce noise. The section header includes count for quick scanning.

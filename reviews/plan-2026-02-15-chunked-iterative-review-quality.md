# Document Review: feat-chunked-iterative-code-review-plan.md

## Quality Score: A

This is a comprehensive, well-structured technical plan. Problem statement is clear, implementation phases are actionable with inputs/outputs/error handling defined, and acceptance criteria are testable. The plan demonstrates strong architectural thinking with evidence-based design decisions.

## Strengths

- **Clear problem framing**: Quantified impact table (§ Problem Statement) shows exactly when chunking triggers and expected coverage gains
- **Detailed technical approach**: Each of 7 phases has explicit inputs, outputs, preconditions, and error handling
- **Risk-aware design**: Risk table (§ Risk Analysis) identifies medium-probability issues with specific mitigations; circuit breaker at MAX_CHUNKS=5 prevents runaway behavior
- **Alternatives analyzed**: Table (§ Alternatives Considered) justifies design choices; explains why flat splitting is rejected (misses file relationships)
- **Dependencies explicit**: Calls out Agent Teams experimental flag, sequential-only constraint, checkpoint schema migration path
- **Actionable acceptance criteria**: 9 functional + 5 non-functional + 4 quality gate requirements are testable and measurable
- **Backward compatibility**: Single-pass path has "zero behavioral change"; configurable via `--no-chunk` flag
- **Documentation mapped**: Specific file paths for updates (review.md, arc.md, references)

## Issues

| # | Section | Issue | Severity | Category | Suggestion |
|---|---------|-------|----------|----------|------------|
| 1 | Phase 1 (§87-120) | `scoreFile()` pseudocode shows `TYPE_WEIGHTS` dict but doesn't document which file extensions map to which keys or how to extend for new languages | MED | clarity | Add note: "TYPE_WEIGHTS is language-specific; new languages should default to 1.0 and increase if they are dynamically typed or error-prone." |
| 2 | Phase 2 (§122-174) | `splitChunk()` function referenced but not defined (line 165: `if (chunk.files.length > MIN_ASH_BUDGET) return splitChunk(chunk)`). Splitting algorithm is unexplained | MED | completeness | Define `splitChunk()` behavior: does it split by directory, or split files evenly? How are atomic chunks preserved? |
| 3 | Phase 3 (§176-235) | Line 188: `CHUNK_THRESHOLD = 20` set in pseudocode, but also mentioned in Phase 7 config as `chunk_threshold: 20`. Is 20 the hard-coded default or the configurable default? | MED | clarity | Clarify: "CHUNK_THRESHOLD defaults to 20 (from talisman.yml rune-gaze.chunk_threshold), but can be overridden by `--chunk-size` flag" |
| 4 | Phase 3 (§176-235) | `runRoundtableCircle(chunk.files, chunkId, flags)` is called but the interaction between chunk review and existing Roundtable team creation is not specified. Does each chunk get a NEW team, or is the same team reused? | MED | completeness | State explicitly: "Each chunk spawns a new Roundtable Circle team (new team name: `roundtable-{identifier}-chunk-{N}`) and cleans it up after TOME is written." |
| 5 | Phase 4 (§237-280) | Dedup algorithm references "DEDUP_HIERARCHY" (line 264) but doesn't explain the hierarchy. Is it the same as existing dedup, or modified for cross-chunk context? | LOW | clarity | Reference the existing algorithm or state if cross-chunk dedup has different rules: "Dedup uses existing DEDUP_HIERARCHY from `dedup-runes.md:45-60`, applied across all chunks." |
| 6 | Phase 6 (§334-376) | Cross-cutting pass uses `Task()` API but doesn't specify which CLI command invokes it or if it's part of the standard Roundtable flow or separate | LOW | completeness | Clarify: "Cross-cutting pass is a separate, optional Task spawned AFTER all chunk TOMEs are merged. It runs independently (no team coordination)." |
| 7 | Arc Integration (§282-332) | Checkpoint schema migration shown (v4 → v5) but no migration trigger point is documented. When does the auto-migration happen? On first run of phase 6 with chunks? | MED | clarity | Add: "Migration happens automatically in Phase 6 when checkpoint is loaded; if schema_version < 5, code inserts `phases.code_review.chunks = { total: 0, completed: 0, tomes: [] }`" |
| 8 | Configuration (§380-406) | `chunk_strategy: "directory" | "flat"` is mentioned in config example but "flat" strategy is not described in any phase. What does flat do? | MED | completeness | Either (a) remove `"flat"` option and keep only `"directory"`, or (b) add Phase 2.5 explaining flat grouping algorithm |
| 9 | Acceptance Criteria (§454-482) | Criterion: "Arc `--resume` correctly resumes from partially-completed chunk" — but how is resumption tested? Are there scenario tests for failure + resume? | LOW | completeness | Suggest: "Test matrix: (a) resume after chunk 1 completes, (b) resume after chunk 2 fails timeout, (c) all chunks complete + resume (should be no-op)" |
| 10 | Success Metrics (§484-489) | Metric: "Finding density (findings per file) maintained or increased vs single-pass" — but how is this measured? Against what baseline? How to detect regressions? | MED | actionability | Define baseline: "Measure findings/file for 30-file single-pass review (recorded as baseline); compare chunked 30-file review against it. Accept if density ≥ baseline or justified by improved coverage." |

## Missing Sections

- **Validation plan**: How will implementer verify that findings are not duplicated or missed during merge? Suggestion: add a "Validation" subsection describing spot-check procedures (e.g., manual verify 5 random findings appear exactly once in unified TOME)
- **Fallback behavior**: What happens if cross-chunk merge fails? Current error handling says "warn in Coverage Gaps" but doesn't specify if the individual chunk TOMEs are returned as-is or if the phase fails entirely
- **Performance baseline**: No mention of expected time overhead for complexity scoring + grouping (Phase 1-2). Acceptance criteria say "<1 second" but no justification for that bound
- **Testing strategy for Phase 1-2**: Scoring and grouping are algorithmic functions. Plan mentions "test coverage" but no test scenarios (unit tests, fixtures, edge cases for scoring)

## Ambiguities

- **"Smart grouping" definition**: Plan says "Files in same directory reviewed together" but doesn't define directory depth. Is `src/components/Button.tsx` grouped with `src/components/Input.tsx`, or also with `src/Button.test.tsx`? Same parent dir, or recursive parent?

- **Chunk timeout behavior (Phase 3, line 181)**: "Chunk timeout → proceed with partial results for that chunk" — but if a chunk times out mid-review, which Ashes completed and which didn't? Is the partial TOME usable, or is it corrupted?

- **Finding ID collision across chunks**: Plan prefixes findings with chunk index (C1-BACK-001, C2-SEC-001) to prevent collisions, but what if the same finding appears in multiple chunks (e.g., a file reviewed in both Chunk 1 and Chunk 2 due to directory overlap)? Does dedup catch it before or after prefixing?

- **"Related files split across chunks" mitigation**: Risk table says directory-aware grouping mitigates this, but a 50-file changeset spanning 10 directories may still split related files. How does cross-cutting pass specifically detect and catch API mismatches vs. integration issues?

## Traceability Analysis

Checking acceptance criteria against Overview/Problem/Solution sections:

- "Chunk TOMEs merged into unified TOME with cross-chunk dedup" → mentioned in Overview, specified in Phase 4 ✓
- "Files in same directory grouped into same chunk" → mentioned in Proposed Solution (§41-45), specified in Phase 2 ✓
- "Finding IDs unique across chunks" → mentioned in Proposed Solution (§48), specified in Phase 4 ✓
- "Zero Coverage Gaps in TOME for changesets under 100 files" (Success Metrics §489) → implied in Problem Statement (§19) but not explicitly in Proposed Solution. Suggest adding to §41-50.

**Traceability is strong overall.** One minor orphan: "Success Metrics: Reliability: No new failure modes in existing single-pass path" is not explicitly mentioned in Proposed Solution or Problem Statement — it's a reasonable requirement but could be rooted in Overview.

## Recommendation

**This plan is ready for implementation.** It provides sufficient technical detail, identifies dependencies, and has testable acceptance criteria.

**Before implementation, resolve:**

1. Define `splitChunk()` algorithm (Issue #2) — critical for Phase 2
2. Clarify team spawning behavior in Phase 3 (Issue #4) — affects Arc integration
3. Decide on `chunk_strategy: flat` — keep or remove? (Issue #8)
4. Add checkpoint migration trigger point (Issue #7)
5. Document finding ID collision handling across chunks (Ambiguity #3)

**Suggested next steps (priority order):**

1. Create unit test fixtures for Phase 1-2 (scoring & grouping) before coding
2. Implement Phase 1-2 and validate against 30-file and 50-file test changesets
3. Implement Phase 3-4 (loop + merge) in parallel
4. Arc integration (Phase 5) — coordinate with checkpoint schema version bump
5. E2E test: run `/rune:arc --challenge plan.md` on 50+ file changeset and verify unified TOME quality


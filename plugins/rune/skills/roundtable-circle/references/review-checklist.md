# Review Checklist — Unified Finding Template

Shared reference for review agent finding output format with confidence scoring.

## RUNE:FINDING Marker Format

```html
<!-- RUNE:FINDING nonce="{nonce}" id="SEC-001" file="api/users.py" line="42" severity="P1" confidence="HIGH" confidence_score="92" -->
```

### Attributes

| Attribute | Required | Values | Default |
|-----------|----------|--------|---------|
| `nonce` | Yes | Session nonce (UUID v4) | - |
| `id` | Yes | PREFIX-NNN (e.g., SEC-001) | - |
| `file` | Yes | Relative file path | - |
| `line` | Yes | Line number | - |
| `severity` | Yes | P1 / P2 / P3 | - |
| `confidence` | No | HIGH / MEDIUM / LOW | UNKNOWN |
| `confidence_score` | No | 0-100 integer | 50 |

### Confidence Scale

| Label | Score Range | Meaning |
|-------|------------|---------|
| HIGH | 80-100 | Evidence directly confirms the finding |
| MEDIUM | 50-79 | Evidence supports but does not conclusively prove |
| LOW | 0-49 | Weak or ambiguous evidence |
| UNKNOWN | - | Confidence not assessed (old format backward compat) |

## Per-Finding Output Block

Every finding in a review agent's output MUST include:

```markdown
- [ ] **[PREFIX-NNN] Title** in `file/path.ext:line`
  - **Evidence:** {specific code reference or test output}
  - **Confidence**: HIGH (92) | MEDIUM (65) | LOW (30)
  - **Assumption**: {what this finding assumes to be true — if any}
  - **Fix:** {specific remediation with code example}
```

### Field Definitions

- **Evidence**: Direct code quote, grep result, or test output that supports the finding. MUST reference a specific file:line.
- **Confidence**: Label + score in parentheses. Reflects evidence strength, NOT finding severity. A P1 finding with weak evidence should be LOW confidence.
- **Assumption**: What the reviewer assumes to be true for this finding to be valid. If the finding is unconditional (e.g., hardcoded secret), write "None". Assumptions enable the Doubt Seer to efficiently verify claims.
- **Fix**: Actionable remediation. Code example preferred.

### Backward Compatibility

Old-format findings (without confidence/confidence_score) are valid. Runebinder treats them as:
- `confidence="UNKNOWN"`
- `confidence_score=50`

No existing review agent output is broken by this addition. The confidence fields are additive.

## Self-Review Checklist (Shared)

After completing analysis, verify:
- [ ] Every finding references a **specific file:line** with evidence
- [ ] **False positives considered** — checked context before flagging
- [ ] **Confidence level** is appropriate (don't flag uncertain items as P1)
- [ ] All files in scope were **actually read**, not just assumed
- [ ] Findings are **actionable** — each has a concrete fix suggestion
- [ ] **Confidence score** assigned (0-100) with 1-sentence justification — reflects evidence strength, not finding severity
- [ ] **Cross-check**: confidence >= 80 requires evidence-verified ratio >= 50%. If not, recalibrate.
- [ ] **Assumption** field populated for every finding (or "None" if unconditional)

## Runebinder Integration

Runebinder parses confidence from RUNE:FINDING markers and uses it for:

1. **Within-tier tiebreaking**: When two findings match same file + 5-line window + same hierarchy level, higher `confidence_score` wins
2. **`also_flagged_by` annotations**: Include confidence labels (e.g., "also flagged by: Flaw Hunter [HIGH]")
3. **Confidence Summary section**: Per-Ash distribution table in TOME.md (HIGH/MEDIUM/LOW/UNKNOWN counts)

**CRITICAL INVARIANT**: Confidence NEVER suppresses findings — only influences tiebreaking. A LOW-confidence finding is never dropped unless a higher-confidence duplicate exists at the same hierarchy level.

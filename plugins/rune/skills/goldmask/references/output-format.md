# Output Format — GOLDMASK.md + findings.json + risk-map.json

## GOLDMASK.md Template

```markdown
# GOLDMASK Report — {session_id}

**Generated**: {timestamp}
**Diff**: {diff-spec}
**Mode**: {full|quick|intelligence}
**Changed files**: {count}

## Summary

| Metric | Value |
|--------|-------|
| MUST-CHANGE files | {N} |
| SHOULD-CHECK files | {N} |
| MAY-AFFECT files | {N} |
| Caution zones (HIGH+) | {N} |
| Collateral risk (WIDE) | {N} |
| Bug swarm alerts | {N} |

## Impact Clusters

### Cluster 1: {cluster_name}

| Finding | File | Confidence | Classification | Layer |
|---------|------|-----------|---------------|-------|
| GOLD-DATA-001 | src/models/user.py:15 | 0.92 | MUST-CHANGE | Data |
| GOLD-API-002 | src/routes/user.py:42 | 0.85 | MUST-CHANGE | API |
| GOLD-BIZ-003 | src/services/user.py:78 | 0.64 | SHOULD-CHECK | Business |

**Propagation chain**: schema change -> ORM model -> serializer -> API endpoint -> client

## Wisdom Advisories

The following areas have significant design intent that should be understood
before making changes.

### CAUTION ZONE: {file}:{line_range} (Caution: {score} {LEVEL})

**Design Intent**: {WORKAROUND | CONSTRAINT | OPTIMIZATION | ...}
**Original Author**: {author} ({status: active|departed})
**Context**: {plain English explanation of why this code exists}

**Historical Context**:
- Written by: {author} on {date} ({N days ago})
- Commit: `{hash}` -- "{commit_message_first_line}"
- Contributors since: {N distinct authors}
- Last major change: {date} by {author}

**If you must modify this area**:
1. Read commit {hash} fully before modifying
2. {Specific advice based on intent category}
3. {Verification step}

## Collateral Damage Assessment

### BLAST-RADIUS: {WIDE|MODERATE|CONTAINED|ISOLATED} -- {file}

**Collateral Risk Score**: {0.XX}
**Why this is dangerous**:
- Transitive depth: {N} hops
- Cross-layer spread: {N} layers
- Design intent: {intent} ({reason})
- History: {co-change cluster info}

**Potential collateral damage**:
1. `{file}:{line}` -- {reason}
2. `{file}:{line}` -- {reason}

**Recommended safeguards**:
- [ ] {action item}
- [ ] {action item}

### Bug Swarm Alerts

#### Swarm #{N}: {cluster_name} (coupling: {pct}%)

Found {N} issues in this co-change cluster.
{N} related files have NOT been checked.

| File | In Cluster? | Finding? | Recommendation |
|------|-------------|----------|----------------|
| {file} | Yes | {ID} | Known issue |
| {file} | Yes | UNCHECKED | Review for related bugs |

## Historical Risk Assessment

| File | Risk Tier | Commits/{window}d | Churn | Owners | Past P1s | Co-Changes With |
|------|-----------|-------------|-------|--------|----------|-----------------|
| {file} | CRITICAL | {N} | {N} | {N} | {N} | {files} |
```

## findings.json Schema

```json
{
  "session_id": "goldmask-{timestamp}",
  "timestamp": "2026-01-15T10:30:00Z",
  "diff_spec": "HEAD~3..HEAD",
  "findings": [
    {
      "id": "GOLD-DATA-001",
      "file": "src/models/user.py",
      "line": 15,
      "confidence": 0.92,
      "classification": "MUST-CHANGE",
      "layer": "data",
      "evidence": ["imports UserModel from changed file", "type annotation references User"],
      "propagation_chain": ["src/models/user.py", "src/serializers/user.py", "src/routes/user.py"],
      "risk_tier": "CRITICAL",
      "intent_category": "DEFENSIVE",
      "caution_score": 0.85,
      "caution_level": "CRITICAL",
      "collateral_risk": 0.72,
      "blast_radius": "MODERATE",
      "wisdom_context": "Guard added for null SSO accounts — commit a1b2c3d",
      "lore_context": "18 commits/90d, 1 owner, 3 past P1s"
    }
  ],
  "swarm_alerts": [
    {
      "cluster_id": "auth-module",
      "known_findings": ["GOLD-API-003", "GOLD-BIZ-007"],
      "unchecked_files": ["src/auth/token.py", "tests/test_auth.py"],
      "coupling_strength": 72.5,
      "recommendation": "Found 2 issues in this co-change cluster. 2 related files have NOT been checked."
    }
  ],
  "summary": {
    "must_change": 3,
    "should_check": 5,
    "may_affect": 8,
    "caution_zones": 2,
    "wide_blast_radius": 1,
    "swarm_alerts": 1
  }
}
```

## risk-map.json Schema

```json
{
  "generated": "2026-01-15T10:30:00Z",
  "window_days": 90,
  "total_files_analyzed": 142,
  "total_commits_in_window": 87,
  "files": [
    {
      "path": "src/payment/processor.py",
      "risk_score": 0.89,
      "tier": "CRITICAL",
      "metrics": {
        "frequency": 18,
        "frequency_percentile": 0.95,
        "churn": 542,
        "churn_percentile": 0.92,
        "recency": 0.85,
        "ownership": {
          "top_contributor": "alice",
          "top_contributor_pct": 0.78,
          "distinct_authors": 1,
          "ownership_risk": 0.78
        },
        "echo_correlation": 0.70
      },
      "co_changes": [
        {
          "file": "tests/test_payment.py",
          "coupling_pct": 65.0,
          "shared_revisions": 12
        }
      ]
    }
  ]
}
```

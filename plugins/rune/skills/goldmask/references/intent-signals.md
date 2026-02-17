# Intent Signals — Design Intent Classification

## 8 Intent Categories

| Category | Signal Keywords | Caution Base | Risk Level |
|----------|----------------|-------------|------------|
| **WORKAROUND** | workaround, hack, temporary, band-aid, quick fix, TODO revert | 0.80 | HIGH |
| **CONSTRAINT** | per, required by, mandated, compliance, regulation, PCI, GDPR, HIPAA | 0.90 | CRITICAL |
| **OPTIMIZATION** | perf, performance, optimize, cache, batch, N+1, slow, latency | 0.60 | MEDIUM |
| **COMPATIBILITY** | backward, compat, deprecat, legacy, migration, breaking change | 0.75 | HIGH |
| **CONVENTION** | team decision, ADR, convention, standard, agreed, style guide | 0.55 | MEDIUM |
| **DEFENSIVE** | guard, protect, prevent, edge case, null check, race condition, safety | 0.75 | HIGH |
| **EXPLORATORY** | spike, experiment, try, prototype, POC, proof of concept, revert if | 0.20 | LOW |
| **UNKNOWN** | (no signals found) | 0.40 | DEFAULT |

## Regex Patterns

```python
INTENT_SIGNALS = {
    "workaround": [
        r"(?i)workaround|hack|temporary|band.?aid|quick.?fix|TODO.*revert",
        r"(?i)until\s+(we|they|it|the)\s+\w+",
    ],
    "constraint": [
        r"(?i)(per|according to|required by|mandated|compliance|regulation)",
        r"(?i)(PCI|GDPR|HIPAA|SOX|OWASP|RFC\s*\d+)",
    ],
    "optimization": [
        r"(?i)(perf|performance|optimize|cache|batch|N\+1|slow|latency|speed)",
        r"(?i)(benchmark|profil|bottleneck)",
    ],
    "compatibility": [
        r"(?i)(backward|compat|deprecat|legacy|migration|v\d+|breaking change)",
        r"(?i)(keep|maintain|preserve).*(old|existing|current)",
    ],
    "convention": [
        r"(?i)(team decision|ADR|convention|standard|agreed|we decided)",
        r"(?i)(style guide|coding standard|pattern we use)",
    ],
    "defensive": [
        r"(?i)(guard|protect|prevent|edge.?case|null.?check|race.?condition)",
        r"(?i)(safety|sanitize|validate|boundary)",
    ],
    "exploratory": [
        r"(?i)(spike|experiment|try|prototype|POC|proof.?of.?concept)",
        r"(?i)(revert if|rollback if|remove.*(later|soon))",
    ],
}
```

## Conventional Commits Parsing

When commit messages follow Conventional Commits format, extract type and scope:

```
^(?<type>\w+)(?:\((?<scope>[^()]+)\))?(?<breaking>!)?:\s*(?<description>.+)
```

Type mapping to intent:
- `fix` + workaround keywords -> WORKAROUND
- `fix` + defensive keywords -> DEFENSIVE
- `perf` -> OPTIMIZATION
- `feat` + experiment keywords -> EXPLORATORY
- `chore` + compat keywords -> COMPATIBILITY
- `!` suffix or `BREAKING CHANGE:` footer -> COMPATIBILITY (breaking)

## Worked Examples

### Example 1: WORKAROUND

```
Commit: "fix: add sleep(1) workaround for race condition in payment processing"
Comment: "# HACK: temporary fix until we migrate to async handler — see #142"

Signals matched:
  - workaround regex: "workaround" in commit message
  - workaround regex: "until we migrate" in comment
  - conventional commit: type=fix + workaround keyword

Classification: WORKAROUND (base caution: 0.80)
```

### Example 2: CONSTRAINT

```
Commit: "feat(auth): mask card numbers per PCI-DSS 3.2.1 requirement"
Comment: "# Per PCI-DSS 3.2.1, must mask after first 6 and last 4 digits"

Signals matched:
  - constraint regex: "per" + "requirement" in commit
  - constraint regex: "PCI" in both commit and comment

Classification: CONSTRAINT (base caution: 0.90)
```

### Example 3: UNKNOWN (no signals)

```
Commit: "update user handler"
Comment: (none)

Signals matched: (none)
No conventional commit type.
No keyword matches in commit message or comments.

Classification: UNKNOWN (base caution: 0.40)
Advisory: "No design intent signals found. Standard review applies."
```

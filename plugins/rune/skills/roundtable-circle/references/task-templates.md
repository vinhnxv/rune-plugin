# Task Templates — TaskCreate for Each Ash

> Copy-paste templates for creating tasks when summoning Ash.

## Review Mode Templates

### Forge Warden (Backend)

```
TaskCreate({
  subject: "Review backend code as Forge Warden",
  description: "Files: {backend_files}\nOutput: tmp/reviews/{id}/forge-warden.md\nPerspectives: architecture, performance, logic bugs, duplication\nRequired sections: P1 (Critical), P2 (High), P3 (Medium), Self-Review Log, Summary",
  activeForm: "Reviewing backend code"
})
```

### Ward Sentinel (Security)

```
TaskCreate({
  subject: "Review security posture as Ward Sentinel",
  description: "Files: ALL changed files\nOutput: tmp/reviews/{id}/ward-sentinel.md\nPerspectives: vulnerabilities, auth, injection, OWASP\nRequired sections: P1 (Critical), P2 (High), P3 (Medium), Self-Review Log, Summary",
  activeForm: "Reviewing security posture"
})
```

### Pattern Weaver (Quality)

```
TaskCreate({
  subject: "Review code quality as Pattern Weaver",
  description: "Files: ALL changed files\nOutput: tmp/reviews/{id}/pattern-weaver.md\nPerspectives: simplicity, TDD compliance, dead code, pattern consistency\nRequired sections: P1 (Critical), P2 (High), P3 (Medium), Self-Review Log, Summary",
  activeForm: "Reviewing code quality patterns"
})
```

### Glyph Scribe (Frontend)

```
TaskCreate({
  subject: "Review frontend code as Glyph Scribe",
  description: "Files: {frontend_files}\nOutput: tmp/reviews/{id}/glyph-scribe.md\nPerspectives: TypeScript safety, React performance, accessibility\nRequired sections: P1 (Critical), P2 (High), P3 (Medium), Self-Review Log, Summary",
  activeForm: "Reviewing frontend code"
})
```

### Knowledge Keeper (Docs)

```
TaskCreate({
  subject: "Review documentation as Knowledge Keeper",
  description: "Files: {doc_files}\nOutput: tmp/reviews/{id}/knowledge-keeper.md\nPerspectives: accuracy, completeness, anti-injection\nRequired sections: P1 (Critical), P2 (High), P3 (Medium), Self-Review Log, Summary",
  activeForm: "Reviewing documentation"
})
```

### Veil Piercer (Truth-Telling)

```
TaskCreate({
  subject: "Truth-telling review as Veil Piercer",
  description: "Files: ALL changed files\nOutput: tmp/reviews/{id}/veil-piercer.md\nPerspectives: premise validation, production viability, long-term consequences\nRequired sections: P1 (Critical), P2 (High), P3 (Medium), Self-Review Log, Summary",
  activeForm: "Truth-telling review in progress"
})
```

### Codex Oracle (Cross-Model)

```
TaskCreate({
  subject: "Review code as Codex Oracle (cross-model verification)",
  description: "Files: {codex_files}\nOutput: tmp/reviews/{id}/codex-oracle.md\nPerspectives: cross-model security, logic, quality (GPT-5.3-codex)\nRequired sections: P1 (Critical), P2 (High), P3 (Medium), Self-Review Log, Summary\nNote: Requires codex CLI. Conditional — skipped if CLI unavailable.",
  activeForm: "Running cross-model review via Codex Oracle"
})
```

## Audit Mode Templates

Identical to review mode except:

| Field | Review | Audit |
|-------|--------|-------|
| Output dir | `tmp/reviews/{id}/` | `tmp/audit/{id}/` |
| File source | git diff (changed files) | find (all project files) |
| Description prefix | "Review..." | "Audit..." |

## Aggregator Template

### Runebinder

```
TaskCreate({
  subject: "Aggregate findings into TOME",
  description: "Read all Ash output files from {output_dir}. Deduplicate using hierarchy (SEC > BACK > VEIL > DOC > QUAL > FRONT > CDX). Write TOME.md with unified findings sorted by priority.",
  activeForm: "Aggregating findings into TOME"
})
```

## Summon Templates

### Background Teammate (Agent Teams)

```
Task({
  team_name: "rune-{workflow}-{id}",
  name: "{ash-name}",
  subagent_type: "general-purpose",
  prompt: [from references/ash-prompts/{role}.md],
  run_in_background: true
})
```

### Task Subagent (Platform Reference)

> **Note**: This template is a platform reference for non-Rune workflows. All Rune commands use the Background Teammate template above with Agent Teams (`TeamCreate` + `TaskCreate`).

> **Security**: Custom workflows using this template with 3+ agents reviewing untrusted code MUST inject the Truthbinding Protocol and Glyph Budget. See `inscription-protocol.md` for the full prompt injection template.

```
Task({
  subagent_type: "general-purpose",
  description: "{role} review",
  prompt: [from references/ash-prompts/{role}.md],
  run_in_background: true
})
```

## Task Dependencies

```
# Independent (run in parallel)
forge-warden    ─┐
ward-sentinel   ─┤
veil-piercer    ─┤
pattern-weaver  ─┤── All complete ──► runebinder ──► truthsight-verifier
glyph-scribe    ─┤
knowledge-keeper ─┤
codex-oracle    ─┘
```

All Ash are independent — no `blockedBy` relationships between them. The Runebinder task should be `blockedBy` all Ash tasks. The Truthsight Verifier (if enabled) should be `blockedBy` the Runebinder.

## References

- [Circle Registry](circle-registry.md) — Agent-to-Ash mapping
- [Ash Prompts](ash-prompts/) — Individual prompts to inject

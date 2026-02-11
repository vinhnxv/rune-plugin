# Task Templates — TaskCreate for Each Runebearer

> Copy-paste templates for creating tasks when spawning Runebearers.

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

### Lore Keeper (Docs)

```
TaskCreate({
  subject: "Review documentation as Lore Keeper",
  description: "Files: {doc_files}\nOutput: tmp/reviews/{id}/lore-keeper.md\nPerspectives: accuracy, completeness, anti-injection\nRequired sections: P1 (Critical), P2 (High), P3 (Medium), Self-Review Log, Summary",
  activeForm: "Reviewing documentation"
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
  description: "Read all Runebearer output files from {output_dir}. Deduplicate using hierarchy (SEC > BACK > DOC > QUAL > FRONT). Write TOME.md with unified findings sorted by priority.",
  activeForm: "Aggregating findings into TOME"
})
```

## Spawn Templates

### Background Teammate (Agent Teams)

```
Task({
  team_name: "rune-{workflow}-{id}",
  name: "{runebearer-name}",
  subagent_type: "general-purpose",
  prompt: [from references/runebearer-prompts/{role}.md],
  run_in_background: true
})
```

### Task Subagent (Non-Teams)

```
Task({
  subagent_type: "general-purpose",
  description: "{role} review",
  prompt: [from references/runebearer-prompts/{role}.md],
  run_in_background: true
})
```

## Task Dependencies

```
# Independent (run in parallel)
forge-warden    ─┐
ward-sentinel   ─┤
pattern-weaver  ─┤── All complete ──► runebinder ──► truthsight-verifier
glyph-scribe   ─┤
lore-keeper    ─┘
```

All Runebearers are independent — no `blockedBy` relationships between them. The Runebinder task should be `blockedBy` all Runebearer tasks. The Truthsight Verifier (if enabled) should be `blockedBy` the Runebinder.

## References

- [Circle Registry](circle-registry.md) — Agent-to-Runebearer mapping
- [Runebearer Prompts](runebearer-prompts/) — Individual prompts to inject

# Agent Role Patterns

## Review Runebearers (Parallel Specialists)

Run simultaneously with isolated contexts. Each produces Report-format output.

```
# Parallel execution — each Runebearer writes to tmp/reviews/{pr}/
Task forge-warden(backend_files)     # Backend review
Task ward-sentinel(all_files)        # Security review
Task pattern-weaver(all_files)       # Quality patterns
Task glyph-scribe(frontend_files)    # Frontend review (conditional)
Task lore-keeper(doc_files)          # Docs review (conditional)
```

## Audit Runebearers (Fan-out / Fan-in)

Similar to review but broader scope — all project files instead of changed files.

```
# Fan-out to focused audit areas
Task forge-warden(all_backend)       # Backend architecture + logic
Task ward-sentinel(all_files)        # Security posture
Task pattern-weaver(all_files)       # Codebase quality + dead code
# Each writes to tmp/audit/{id}/
```

## Research Agents (Parallel Exploration)

Run simultaneously to gather knowledge from different angles. Produce Research-format output.

```
# Parallel research for /rune:plan
Task repo-analyst(topic)             # Repo patterns + conventions
Task best-practices(topic)           # External best practices
Task framework-docs(topic)           # Framework documentation
# Each writes to tmp/research/
```

## Work Agents (Rune Smiths)

Self-organizing workers that claim tasks from a shared pool. Produce Status-format output.

```
# Swarm mode for /rune:work — workers claim from task list
Task rune-smith-1(task-pool)         # Claims and works on tasks
Task rune-smith-2(task-pool)         # Claims and works on tasks
# Each writes to tmp/work/
```

## Conditional Runebearers

Spawned based on file types present in scope:

| Trigger | Runebearer | Workflow Types |
|---------|-----------|----------------|
| Backend files (`.py`, `.go`, `.rs`, `.rb`) | Forge Warden | Reviews, Audits |
| Frontend files (`.ts`, `.tsx`, `.js`, `.jsx`) | Glyph Scribe | Reviews, Audits |
| Doc files (`.md`, >= 10 lines changed) | Lore Keeper | Reviews, Audits |
| ALL scopes | Ward Sentinel (always) | Reviews, Audits |
| ALL scopes | Pattern Weaver (always) | Reviews, Audits |

## Validation Agents (Truthsight Pipeline)

Post-review agents that verify Runebearer output quality. Run AFTER all Runebearers complete.

```
# Layer 0: Inline Checks (lead runs directly — no agent)
#   Grep-based section validation of output files
#   Writes: {output_dir}/inline-validation.json

# Layer 1: Self-Review Log (each Runebearer performs self-review)
#   Runebearers re-read P1/P2 findings before completing
#   Output: ## Self-Review Log table in each output file

# Layer 2: Smart Verifier (spawned by lead after Runebearers complete)
Task:
  subagent_type: "general-purpose"
  model: haiku
  description: "Truthsight Verifier"
  prompt: [from references/verifier-prompt.md]
  # Writes to: {output_dir}/truthsight-report.md

# Re-verify agents (max 2 per workflow, spawned on hallucination detection)
Task:
  subagent_type: "general-purpose"
  model: haiku
  description: "Re-verify {runebearer}-{finding}"
  # Writes to: {output_dir}/re-verify-{runebearer}-{finding}.md
```

**When to spawn Layer 2 verifier:**

| Workflow | Condition | Verifier Scope |
|----------|-----------|----------------|
| `/rune:review` | `inscription.verification.enabled` AND 3+ Runebearers | All Runebearer outputs |
| `/rune:audit` | `inscription.verification.enabled` AND 5+ Runebearers | All Runebearer outputs |
| Custom | Configurable via inscription `verification` block | Per configuration |

Full verifier prompt template: [Verifier Prompt](verifier-prompt.md)

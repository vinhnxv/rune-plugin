# Output Conventions

| Workflow | Directory | Files |
|----------|----------|-------|
| Reviews | `tmp/reviews/{id}/` | `{ash}.md`, `TOME.md` (with RUNE:FINDING markers), `inscription.json` |
| Audits | `tmp/audit/{id}/` | Same pattern |
| Plans | `tmp/plans/{id}/research/`, `plans/YYYY-MM-DD-{type}-{name}-plan.md` | Research findings, brainstorm decisions, plan document |
| Forge | `tmp/forge/{id}/` | `{section-slug}-{agent-name}.md` enrichment files, `inscription.json`, `original-plan.md` (backup) |
| Work | `tmp/work/{timestamp}/` | `inscription.json`, `patches/*.patch`, `patches/*.json`, `proposals/*.md`, `codex-advisory.md` |
| Mend | `tmp/mend/{id}/` | `resolution-report.md`, fixer outputs |
| Arc | `tmp/arc/{id}/` | Phase artifacts (`enriched-plan.md`, `plan-review.md`, `concern-context.md`, `verification-report.md`, `work-summary.md`, `tome.md`, `resolution-report.md`, `spot-check-round-{N}.md`, `audit-report.md`, `gap-analysis.md`) |
| Arc State | `.claude/arc/{id}/` | `checkpoint.json` (persistent, NOT in tmp/) |
| Scratch | `tmp/scratch/` | Session state |
| Codex | Per-workflow (see codex-cli skill) | `codex-oracle.md`, `codex-analysis.md`, `codex-plan-review.md`, `codex-advisory.md` |
| Echoes | `.claude/echoes/{role}/` | `MEMORY.md`, `knowledge.md`, `archive/` |

All `tmp/` directories are ephemeral and can be safely deleted after workflows complete.

Echo files in `.claude/echoes/` are persistent and survive across sessions.

# Rune Skill Catalog

Complete reference for `/rune:tarnished` routing decisions.

## User-Invocable Skills (Primary Targets)

| Keyword | Skill | Delegates To | Input | Output |
|---------|-------|-------------|-------|--------|
| `plan` | `/rune:plan` | `/rune:devise` | Feature description | `plans/*.md` |
| `work` | `/rune:work` | `/rune:strive` | Plan file path | Code changes + commits |
| `review` | `/rune:review` | `/rune:appraise` | Git diff (auto) | `tmp/reviews/*/TOME.md` |
| `devise` | `/rune:devise` | — | Feature description | `plans/*.md` |
| `strive` | `/rune:strive` | — | Plan file path | Code changes + commits |
| `appraise` | `/rune:appraise` | — | Git diff (auto) | `tmp/reviews/*/TOME.md` |
| `audit` | `/rune:audit` | — | None (full scan) | `tmp/audit/*/TOME.md` |
| `arc` | `/rune:arc` | — | Plan file path | Full pipeline → merged PR |
| `forge` | `/rune:forge` | — | Plan file path | Enriched plan |
| `mend` | `/rune:mend` | — | TOME file path | Fixed code |
| `inspect` | `/rune:inspect` | — | Plan file path | `tmp/inspect/*/VERDICT.md` |
| `goldmask` | `/rune:goldmask` | — | Diff spec / file list | Impact report |
| `elicit` | `/rune:elicit` | — | Topic (optional) | Structured reasoning output |
| `rest` | `/rune:rest` | — | None | Cleans tmp/ |
| `echoes` | `/rune:echoes` | — | Subcommand | Echo management |

## Skill Flags Quick Reference

| Skill | Key Flags |
|-------|-----------|
| `devise` | `--quick`, `--no-brainstorm`, `--no-forge`, `--exhaustive` |
| `appraise` | `--deep` |
| `audit` | `--deep`, `--standard`, `--incremental`, `--dirs`, `--focus` |
| `arc` | `--resume`, `--skip-forge` |
| `strive` | `--approve`, `--worktree` |

## Prerequisite Map

| Skill | Requires | Check |
|-------|----------|-------|
| `strive` | Plan file | `Glob("plans/*.md")` |
| `mend` | TOME file | `Glob("tmp/reviews/*/TOME.md")` or `Glob("tmp/audit/*/TOME.md")` |
| `appraise` | Git changes | `git diff --stat` |
| `arc` | Plan file | `Glob("plans/*.md")` |
| `forge` | Plan file | `Glob("plans/*.md")` |
| `inspect` | Plan file | `Glob("plans/*.md")` |

## Duration Estimates

| Skill | Agents | Duration |
|-------|--------|----------|
| `devise` | Up to 7 | 5-15 min |
| `devise --quick` | 2-3 | 2-5 min |
| `strive` | Swarm | 10-30 min |
| `appraise` | Up to 8 | 3-10 min |
| `audit` | Up to 8 | 5-15 min |
| `arc` | Per phase | 30-90 min |
| `forge` | Per section | 5-15 min |
| `mend` | Per file | 3-10 min |
| `goldmask` | 8 tracers | 5-10 min |
| `elicit` | None | 2-5 min |
| `rest` | None | < 1 min |

# SpecFlow Analysis Findings

> From the v0.1.0 planning phase. Updated through v1.2.0.

## Resolved (v0.1 → v1.2)

| Finding | Version | Resolution |
|---------|---------|------------|
| Empty diff detection | v0.1 | Pre-flight abort in `review.md` |
| Concurrent review prevention | v0.1 | State file check (`tmp/.rune-review-*.json`) |
| Prompt injection | v0.1 | Truthbinding Protocol (ANCHOR + RE-ANCHOR) |
| Context overflow | v0.1 | Glyph Budget (file-only output, 50-word limit) |
| Teammate timeout (5 min) | v0.1 | Stale detection in Phase 4 Monitor |
| Output validation | v0.1 | Inscription Protocol (`inscription.json`) |
| Deduplication | v0.1 | Runebinder with hierarchy (SEC > FORGE > DOC > PAT > GLYPH) |
| `/rune:audit` — full codebase scan | v0.2 | `commands/audit.md` — find-based scan |
| Not-a-git-repo error | v0.2 | Audit works without git |
| No cleanup for stale tmp/ | v1.2 | `/rune:cleanup` command |
| Partial failure policy | v0.1 | Proceed with partial results, report gaps in TOME.md |
| Teammate output wrong format | v1.1 | Truthsight Pipeline Layer 0 (inline section validation) |
| Hung teammate detection | v0.1 | 5-min stale detection + proceed with partial |
| `--dry-run` flag | v1.2 | Added to `/rune:review` and `/rune:audit` |
| Extension-based tech detection | v0.1 | Rune Gaze file classification |
| Runebinder prompt | v1.2 | `runebearer-prompts/runebinder.md` |
| Truthseer Validator prompt | v1.2 | `runebearer-prompts/truthseer-validator.md` |
| Truthsight depth (Layer 0-2) | v1.1 | Full circuit breakers, sampling, verifier output format |
| Agent Role Patterns | v1.1 | Added to `rune-orchestration/SKILL.md` |
| JSON output format | v1.1 | `output-format.md` + `completion.json` |

## Open — Medium Priority

### 1. User Onboarding
- No `/rune:help` command or discovery mechanism
- No `/rune:init` to scaffold `.claude/rune-config.yml`
- No post-install confirmation with next steps

### 2. Workflow Chaining
- `/rune:flow plan,work,review` sequential execution
- Dependency checks (work requires plan file)

### 3. Memory Concurrency (Rune Echoes)
- Lock file during write operations
- Schema version marker in header
- Cross-branch merge conflicts in memory files

### 4. Agent Teams Coordination (Remaining)
- Concurrent file write conflicts (no locking — low risk with file-per-agent pattern)
- SendMessage delivery failures (recipient crashes before reading)
- Large diff chunking (10k+ lines) — context budget caps mitigate this

### 5. Config File Detection
- Beyond extension-based: pyproject.toml, package.json, go.mod, Gemfile
- Quality gate discovery (Makefile targets, package.json scripts, CI config)

## Open — Low Priority (v2.0+)

### 6. Scalability
- Adaptive agent count based on file count and complexity
- Progress indicators (X of Y Runebearers completed)

### 7. Customization
- Custom agent templates (user-defined Runebearers)
- `.claude/rune-config.yml` examples and documentation
- Quality gate integration examples

### 8. Reliability Tracking (Layer 3)
- Per-agent hallucination rates over time in `.claude/echoes/`
- Agents with high rates get stricter verification in future runs

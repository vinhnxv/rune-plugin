# SpecFlow Analysis Findings

> From the v0.1.0 planning phase. Updated through v1.8.2.

## Resolved (v0.1 → v1.8)

| Finding | Version | Resolution |
|---------|---------|------------|
| Empty diff detection | v0.1 | Pre-flight abort in `review.md` |
| Concurrent review prevention | v0.1 | State file check (`tmp/.rune-review-*.json`) |
| Prompt injection | v0.1 | Truthbinding Protocol (ANCHOR + RE-ANCHOR) |
| Context overflow | v0.1 | Glyph Budget (file-only output, 50-word limit) |
| Teammate timeout (5 min) | v0.1 | Stale detection in Phase 4 Monitor |
| Output validation | v0.1 | Inscription Protocol (`inscription.json`) |
| Deduplication | v0.1 | Runebinder with hierarchy (SEC > BACK > DOC > QUAL > FRONT) |
| `/rune:audit` — full codebase scan | v0.2 | `commands/audit.md` — find-based scan |
| Not-a-git-repo error | v0.2 | Audit works without git |
| No cleanup for stale tmp/ | v1.2 | `/rune:rest` command |
| Partial failure policy | v0.1 | Proceed with partial results, report gaps in TOME.md |
| Teammate output wrong format | v1.1 | Truthsight Pipeline Layer 0 (inline section validation) |
| Hung teammate detection | v0.1 | 5-min stale detection + proceed with partial |
| `--dry-run` flag | v1.2 | Added to `/rune:review` and `/rune:audit` |
| Extension-based tech detection | v0.1 | Rune Gaze file classification |
| Runebinder prompt | v1.2 | `tarnished-prompts/runebinder.md` |
| Truthseer Validator prompt | v1.2 | `tarnished-prompts/truthseer-validator.md` |
| Truthsight depth (Layer 0-2) | v1.1 | Full circuit breakers, sampling, verifier output format |
| Custom agent templates (user-defined Tarnished) | v1.4 | `custom-tarnished.md` schema, `talisman.yml` examples, trigger matching |
| Agent Role Patterns | v1.1 | Added to `rune-orchestration/SKILL.md` |
| JSON output format | v1.1 | `output-format.md` + `completion.json` |
| Selective naming refresh (E7) | v1.5 | 3 review + 3 research agents + 1 Tarnished + 1 skill + 1 command renamed |
| TOME structured markers | v1.5 | `<!-- RUNE:FINDING nonce=... -->` format with session nonce validation |
| decree-arbiter agent | v1.5 | 5-dimension plan review with Decree Trace evidence format |
| knowledge-keeper standalone agent | v1.7 | Extracted from Tarnished prompt for arc Phase 2 use |
| Parallel finding resolution (`/rune:mend`) | v1.6 | Team-based fixers with restricted tools, ward check serialization (MEND-1) |
| Mend fixer security (ANCHOR/RE-ANCHOR) | v1.6 | Full Truthbinding Protocol for highest-risk agent type |
| SEC-prefix FALSE_POSITIVE gate | v1.6 | Human approval required before skipping security findings |
| Mend state file concurrency | v1.6 | `tmp/.rune-mend-{id}.json` for concurrent detection |
| Incremental commits (E5) | v1.6 | `rune: <subject> [ward-checked]` format, sanitized via `git commit -F` |
| End-to-end pipeline (`/rune:arc`) | v1.7 | 6-phase pipeline with checkpoint-based resume |
| Arc checkpoint integrity (F9) | v1.7 | SHA-256 artifact hashes, monotonic phase_sequence, session nonce |
| Per-phase tool restrictions (F8) | v1.7 | Phase-specific TeamCreate with least-privilege tool sets |
| Arc dispatcher context management (A2) | v1.7 | Summary-only artifact reading, Glyph Budget for orchestrator |
| `/rune:cancel-arc` command | v1.7 | Graceful phase cancellation with artifact preservation |
| Remembrance channel (E3) | v1.8 | `docs/solutions/` with 8 categories, YAML frontmatter schema |
| Security Remembrance gate (F6) | v1.8 | `verified_by: human` required for security category promotion |
| `--approve` flag (E4) | v1.8 | Human approval gate for work mode with 3-min auto-REJECT timeout |
| `--exhaustive` mode (E6) | v1.8 | All agents per section with token budget cap and cost warning |
| Conditional research pipeline (E8) | v1.8 | Risk classification heuristics, local sufficiency scoring, brainstorm auto-detect |
| Agent rename: `codex-scholar` → `lore-scholar` | v1.8.1 | Avoids OpenAI codex-cli name collision; updated across agent, commands, skills, docs |

## Open — Medium Priority

### 1. User Onboarding
- No `/rune:help` command or discovery mechanism
- No `/rune:init` to scaffold `.claude/talisman.yml`
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
- Progress indicators (X of Y Tarnished completed)

### 7. Reliability Tracking (Layer 3)
- Per-agent hallucination rates over time in `.claude/echoes/`
- Agents with high rates get stricter verification in future runs

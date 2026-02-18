# Configuration Guide

Projects can override defaults via `.claude/talisman.yml` (project) or `~/.claude/talisman.yml` (global):

```yaml
rune-gaze:
  backend_extensions: [.py, .go]
  frontend_extensions: [.tsx, .ts]
  skip_patterns: ["**/migrations/**"]
  always_review: ["CLAUDE.md", ".claude/**/*.md"]

# Custom Ashes — extend the built-in 6
ashes:
  custom:
    - name: "domain-logic-reviewer"
      agent: "domain-logic-reviewer"    # local .claude/agents/ or plugin namespace
      source: local                     # local | global | plugin
      workflows: [review, audit, forge] # forge enables Forge Gaze matching
      trigger:
        extensions: [".py", ".rb"]
        paths: ["src/domain/"]
        topics: [domain, business-logic, models, services]  # For forge
      forge:
        subsection: "Domain Logic Analysis"
        perspective: "domain model integrity and business rule correctness"
        budget: enrichment
      context_budget: 20
      finding_prefix: "DOM"

settings:
  max_ashes: 8                   # Hard cap (6 built-in + custom)
  dedup_hierarchy: [SEC, BACK, DOC, QUAL, FRONT, CDX]

forge:                                 # Forge Gaze selection overrides
  threshold: 0.30                      # Score threshold (0.0-1.0)
  max_per_section: 3                   # Max agents per section (cap: 5)
  max_total_agents: 8                  # Max total agents (cap: 15)

codex:                                 # Codex CLI integration (see codex-cli skill for full details)
  disabled: false                      # Kill switch — skip Codex entirely
  model: "gpt-5.3-codex"              # Model for codex exec
  reasoning: "high"                    # Reasoning effort (high | medium | low)
  workflows: [review, audit, plan, forge, work, mend]  # Which pipelines use Codex — "mend" added in v1.39.0 for post-fix verification
  work_advisory:
    enabled: true                      # Codex advisory in /rune:work

solution_arena:
  enabled: true                    # Enable Arena phase in /rune:plan
  skip_for_types: ["fix"]          # Feature types that skip Arena
  # Additional config (weights, thresholds) available in future versions

echoes:
  version_controlled: false

review:
  # Diff-scope tagging (v1.38.0+) — generates line-level diff ranges for scope-aware review
  diff_scope:
    enabled: true                        # Enable diff range generation and TOME tagging
    expansion: 8                         # Context lines above/below each hunk (0-50)
    tag_pre_existing: true               # Tag unchanged-code findings as "pre-existing"
    fix_pre_existing_p1: true            # Always fix pre-existing P1 findings in mend
  # Smart convergence scoring (v1.38.0+) — scope-aware composite scoring
  convergence:
    smart_scoring: true                  # Enable smart convergence scoring
    convergence_threshold: 0.7           # Score >= this = converged (0.1-1.0)

work:
  ward_commands: ["make check", "npm test"]
  max_workers: 3
  approve_timeout: 180                   # Seconds (default 3 min)
  commit_format: "rune: {subject} [ward-checked]"
  skip_branch_check: false               # Skip Phase 0.5 branch check
  branch_prefix: "rune/work"             # Branch name prefix (alphanumeric, _, -, / only)
  pr_monitoring: false                    # Post-deploy monitoring in PR body
  # pr_template: default                 # Reserved for a future release (default | minimal)
  # auto_push: false                     # Reserved for a future release (auto-push without confirmation)
  co_authors: []                         # Co-Authored-By lines in "Name <email>" format
```

## arc

Arc pipeline configuration lives under the `arc:` key. Config resolution follows a 3-layer priority chain: **hardcoded defaults** → **talisman.yml** → **CLI flags** (CLI always wins).

### `arc.defaults` — CLI flag defaults

| Key | Type | Default | CLI flag |
|-----|------|---------|----------|
| `no_forge` | boolean | `false` | `--no-forge` |
| `approve` | boolean | `false` | `--approve` |
| `skip_freshness` | boolean | `false` | `--skip-freshness` |
| `confirm` | boolean | `false` | `--confirm` |

### `arc.ship` — Phase 9 (SHIP) settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto_pr` | boolean | `true` | Create PR automatically after audit. CLI: `--no-pr` to disable. |
| `auto_merge` | boolean | `false` | Merge PR automatically (see `wait_ci` for CI gate). CLI: `--no-merge` to disable. |
| `merge_strategy` | string | `"squash"` | Merge strategy: `squash`, `merge`, or `rebase`. |
| `wait_ci` | boolean | `false` | Wait for CI checks before merge. |
| `draft` | boolean | `false` | Create PR as draft. CLI: `--draft`. |
| `labels` | string[] | `[]` | Labels to apply to PR. |
| `pr_monitoring` | boolean | `false` | Include post-deploy monitoring section in PR body. Note: distinct from `work.pr_monitoring` — `arc.ship.pr_monitoring` only applies to arc-created PRs. |
| `rebase_before_merge` | boolean | `true` | Rebase onto target branch before merge. |
| `co_authors` | string[] | `[]` | Co-Authored-By lines in `"Name <email>"` format. Falls back to `work.co_authors` if not set here. |

### `arc.pre_merge_checks` — Phase 9.5 (MERGE) pre-merge checklist

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `migration_conflict` | boolean | `true` | Check for migration file conflicts. |
| `schema_conflict` | boolean | `true` | Check for schema drift. |
| `lock_file_conflict` | boolean | `true` | Check for lock file conflicts (package-lock.json, yarn.lock, etc.). |
| `uncommitted_changes` | boolean | `true` | Check for uncommitted changes. |
| `migration_paths` | string[] | `[]` | Additional paths to scan for migration conflicts. |

### `arc.timeouts` — Per-phase timeout overrides (activated v1.40.0)

Per-phase timeout values in milliseconds. Values are clamped to 10s–3600s range. Total pipeline timeout is computed dynamically by `calculateDynamicTimeout(tier)` and is not configurable.

| Key | Type | Default (ms) | Description |
|-----|------|-------------|-------------|
| `forge` | number | 900000 | Phase 1: Research enrichment (15 min) |
| `plan_review` | number | 900000 | Phase 2: Plan review (15 min) |
| `plan_refine` | number | 180000 | Phase 2.5: Plan refinement (3 min) |
| `verification` | number | 30000 | Phase 2.7: Verification gate (30 sec) |
| `semantic_verification` | number | 180000 | Phase 2.8: Codex semantic check (3 min) |
| `work` | number | 2100000 | Phase 5: Work execution (35 min) |
| `gap_analysis` | number | 60000 | Phase 5.5: Gap analysis (1 min) |
| `codex_gap_analysis` | number | 660000 | Phase 5.6: Codex gap analysis (11 min) |
| `code_review` | number | 900000 | Phase 6: Code review (15 min) |
| `mend` | number | 1380000 | Phase 7: Mend (23 min) |
| `verify_mend` | number | 240000 | Phase 7.5: Verify mend (4 min) |
| `audit` | number | 1200000 | Phase 8: Audit (20 min) |
| `ship` | number | 300000 | Phase 9: PR creation (5 min, v1.40.0+) |
| `merge` | number | 600000 | Phase 9.5: Merge (10 min, v1.40.0+) |

### `arc.consistency` — Cross-file consistency checks (v1.17.0+)

See the consistency checks section in `talisman.example.yml` for schema and examples.

---

See `../skills/roundtable-circle/references/custom-ashes.md` for full schema and `talisman.example.yml` at plugin root.

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
  workflows: [review, audit, plan, forge, work]  # Which pipelines use Codex
  work_advisory:
    enabled: true                      # Codex advisory in /rune:work

solution_arena:
  enabled: true                    # Enable Arena phase in /rune:plan
  min_solutions: 2                 # Minimum solutions to run Arena
  max_solutions: 5                 # Maximum solutions to generate
  weights:                         # Evaluation dimension weights (normalized to 1.0)
    feasibility: 0.25
    complexity: 0.20
    risk: 0.20
    maintainability: 0.15
    performance: 0.10
    innovation: 0.10
  convergence_threshold: 0.05      # Top solutions within threshold flagged as tied
  challenger_timeout: 300           # Seconds per challenger agent
  skip_for_types: ["fix"]          # Feature types that skip Arena

echoes:
  version_controlled: false

solution_arena:
  enabled: true
  min_solutions: 2
  max_solutions: 5
  weights: {feasibility: 0.25, complexity: 0.20, risk: 0.20, maintainability: 0.15, performance: 0.10, innovation: 0.10}
  convergence_threshold: 0.05
  challenger_timeout: 300
  skip_for_types: ["fix"]

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

See `../skills/roundtable-circle/references/custom-ashes.md` for full schema and `talisman.example.yml` at plugin root.

---
name: echoes
description: |
  Manage Rune Echoes — project-level agent memory stored in .claude/echoes/.
  View memory state, prune stale entries, or reset all echoes.

  <example>
  user: "/rune:echoes show"
  assistant: "Displaying echo state across all roles..."
  </example>

  <example>
  user: "/rune:echoes prune"
  assistant: "Calculating Echo Scores and pruning stale entries..."
  </example>
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# /rune:echoes — Manage Rune Echoes

Manage the project-level agent memory stored in `.claude/echoes/`.

## Usage

```
/rune:echoes show           # Display current echo state
/rune:echoes prune          # Prune stale entries (with confirmation)
/rune:echoes reset          # Clear all echoes (with confirmation)
/rune:echoes init           # Initialize echo directories for this project
```

## Subcommands

### show — Display Echo State

Scan `.claude/echoes/` and display statistics per role.

```bash
# Find all MEMORY.md files
find .claude/echoes -name "MEMORY.md" -type f 2>/dev/null
```

**Output format:**

```
Rune Echoes — Memory State
══════════════════════════

Role: reviewer
  MEMORY.md: 45 lines, 12 entries
  knowledge.md: 120 lines (compressed)
  archive/: 3 files
  Layers: 2 etched, 7 inscribed, 3 traced

Role: team
  MEMORY.md: 18 lines, 5 entries
  Layers: 1 etched, 4 inscribed

Total: 17 entries across 2 roles
Oldest entry: 2026-02-01
Newest entry: 2026-02-11
```

If no echoes exist: "No echoes found. Run `/rune:review` or `/rune:echoes init` to start building memory."

### prune — Remove Stale Entries

Calculate Echo Score for each entry and archive low-scoring ones.

**Steps:**

1. Read all MEMORY.md files across roles
2. Parse entries and calculate Echo Score:
   ```
   Score = (Importance × 0.4) + (Relevance × 0.3) + (Recency × 0.3)
   ```
3. Display candidates for pruning:
   ```
   Prune candidates:

   reviewer/MEMORY.md:
     [0.15] [traced] [2026-01-05] Observation: Slow CI run
     [0.22] [traced] [2026-01-12] Observation: Flaky test in auth module

   auditor/MEMORY.md:
     [0.18] [inscribed] [2025-11-01] Pattern: Unused CSS classes

   3 entries would be archived. Proceed? (y/n)
   ```
4. On confirmation:
   - Backup: copy each MEMORY.md to `archive/MEMORY-{date}.md`
   - Remove low-scoring entries from MEMORY.md
   - Report: "Pruned 3 entries. Backups in archive/"

**Safety:**
- Etched entries are NEVER candidates for pruning
- Always backup before any modification
- User must confirm before pruning proceeds

### reset — Clear All Echoes

Remove all echo data for this project.

**Steps:**

1. Warn: "This will delete ALL echoes for this project. This cannot be undone."
2. Require explicit confirmation: user must type "reset" or confirm
3. On confirmation:
   - Backup entire `.claude/echoes/` to `.claude/echoes-backup-{date}/`
   - Delete all MEMORY.md, knowledge.md, and findings files
   - Preserve directory structure (empty directories remain)
   - Report: "All echoes cleared. Backup at .claude/echoes-backup-{date}/"

### init — Initialize Echo Directories

Create the echo directory structure for a new project.

**Steps:**

1. Create directories:
   ```bash
   mkdir -p .claude/echoes/planner
   mkdir -p .claude/echoes/workers
   mkdir -p .claude/echoes/reviewer/archive
   mkdir -p .claude/echoes/auditor/archive
   mkdir -p .claude/echoes/team
   ```

2. Create initial MEMORY.md files with schema header:
   ```markdown
   <!-- echo-schema: v1 -->
   # {Role} Memory

   *No echoes yet. Run workflows to start building memory.*
   ```

3. Check `.gitignore` for `.claude/echoes/` exclusion:
   - If project has `.gitignore` and it doesn't exclude echoes: warn user
   - Suggest adding `.claude/echoes/` to `.gitignore`

4. Report:
   ```
   Rune Echoes initialized.

   Directories created:
   - .claude/echoes/planner/
   - .claude/echoes/workers/
   - .claude/echoes/reviewer/
   - .claude/echoes/auditor/
   - .claude/echoes/team/

   Run /rune:review or /rune:audit to start building memory.
   ```

## Notes

- Echo data is project-local (`.claude/echoes/` in project root)
- Excluded from git by default (security: may contain code patterns)
- Opt-in to version control via `.claude/rune-config.yml`
- See `rune-echoes` skill for full lifecycle documentation

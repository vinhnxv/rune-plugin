---
name: rune-echoes
description: |
  Use when agents need to read or write project memory, when persisting learnings from
  reviews or audits, when managing echo lifecycle (prune, reset), when a user wants to
  remember something explicitly, or when a pattern keeps recurring across sessions.
  Stores knowledge in .claude/echoes/ with 5-tier lifecycle
  (Etched/Notes/Inscribed/Observations/Traced) and multi-factor pruning.

  <example>
  Context: After a review, Ash persist patterns to echoes
  user: "Review found repeated N+1 query pattern"
  assistant: "Pattern persisted to .claude/echoes/reviewer/MEMORY.md as Inscribed entry"
  </example>
user-invocable: false
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Rune Echoes — Smart Memory Lifecycle

Project-level agent memory that compounds knowledge across sessions. Each workflow writes learnings to `.claude/echoes/`, and future workflows read them to avoid repeating mistakes.

> "The Tarnished collects runes to grow stronger. Each engineering session should do the same."

## Architecture

### Memory Directory Structure

```
.claude/echoes/
├── planner/
│   ├── MEMORY.md              # Active memory (150 line limit)
│   ├── knowledge.md           # Compressed learnings (on-demand load)
│   └── archive/               # Pruned memories (never auto-loaded)
├── workers/
│   └── MEMORY.md
├── reviewer/
│   ├── MEMORY.md
│   ├── knowledge.md
│   └── archive/
├── auditor/
│   └── MEMORY.md
├── notes/
│   └── MEMORY.md              # User-explicit memories (never auto-pruned)
├── observations/
│   └── MEMORY.md              # Agent-observed patterns (auto-promoted)
└── team/
    └── MEMORY.md              # Cross-role learnings (lead writes post-workflow)
```

### 5-Tier Lifecycle

| Tier | Rune Name | Weight | Max Age | Trigger | Pruning |
|------|-----------|--------|---------|---------|---------|
| Structural | **Etched** | 1.0 | Never expires | Manual only | User confirmation required |
| User-Explicit | **Notes** | 0.9 | Never expires | `/rune:echoes remember` | Never auto-pruned |
| Tactical | **Inscribed** | 0.7 | 90 days unreferenced | MEMORY.md > 150 lines | Multi-factor scoring, archive bottom 20% |
| Agent-Observed | **Observations** | 0.5 | 60 days last access | Agent echo-writer protocol | Auto-promoted to Inscribed after 3 references |
| Session | **Traced** | 0.3 | 30 days | MEMORY.md > 150 lines | Utility-based, compress middle 30% |

**Etched** entries are permanent project knowledge (architecture decisions, tech stack, key conventions). Only the user can add or remove them.

**Notes** entries are user-explicit memories created via `/rune:echoes remember <text>`. They represent things the user wants agents to remember across sessions. Weight=0.9 (highest after Etched). Never auto-pruned — only the user can remove them. Stored in `.claude/echoes/notes/MEMORY.md` with `role="notes"`.

**Inscribed** entries are tactical patterns discovered during reviews, audits, and work (e.g., "this codebase has N+1 query tendency in service layers"). They persist across sessions and get pruned when stale.

**Observations** entries are agent-observed patterns written via the echo-writer protocol. Weight=0.5. Auto-pruned when `days_since_last_access > 60` (EDGE-025). Auto-promoted to Inscribed after 3 access_count references in echo_access_log. Promotion rewrites the H2 header in the source MEMORY.md from `## Observations` to `## Inscribed` using atomic file rewrite (C3 concern: `os.replace()`). Stored in `.claude/echoes/observations/MEMORY.md` with `role="observations"`.

**Traced** entries are session-specific observations (e.g., "PR #42 had 3 unused imports"). They compress or archive quickly.

## Memory Entry Format

Every echo entry must include evidence-based metadata:

```markdown
### [YYYY-MM-DD] Pattern: {short description}
- **layer**: etched | notes | inscribed | observations | traced
- **source**: rune:{workflow} {context}
- **confidence**: 0.0-1.0
- **evidence**: `{file}:{lines}` — {what was found}
- **verified**: YYYY-MM-DD
- **supersedes**: {previous entry title} | none
- {The actual learning in 1-3 sentences}
```

### Example Entries

Full examples for all 5 tiers (Etched, Notes, Inscribed, Observations, Traced) with complete metadata format.

See [entry-examples.md](references/entry-examples.md) for the full set of examples.

## Multi-Factor Pruning Algorithm

When MEMORY.md exceeds 150 lines, calculate Echo Score for each entry:

```
Echo Score = (Importance × 0.4) + (Relevance × 0.3) + (Recency × 0.3)

Where:
  Importance = layer weight (etched=1.0, notes=0.9, inscribed=0.7, observations=0.5, traced=0.3)
  Relevance  = times referenced in recent workflows / total workflows (0.0-1.0)
  Recency    = 1.0 - (days_since_verified / max_age_for_layer)
```

### Pruning Rules

- **Etched**: Score locked at 1.0 — never pruned automatically
- **Notes**: Score locked at 0.9 — never auto-pruned (user-created = permanent)
- **Inscribed**: Archive if score < 0.3 AND age > 90 days unreferenced
- **Observations**: Auto-prune when days_since_last_access > 60 (EDGE-025). Auto-promote to Inscribed when access_count >= 3
- **Traced**: Archive if score < 0.2 AND age > 30 days
- Prune ONLY between workflows, never during active phases
- Always backup before pruning: copy MEMORY.md to `archive/MEMORY-{date}.md`

### Active Context Compression

When a role's `knowledge.md` exceeds 300 lines:
1. Group related entries by topic
2. Compress each group into a "knowledge block" (3-5 line summary)
3. Preserve evidence references but remove verbose descriptions
4. Expected savings: ~22% token reduction

## Concurrent Write Protocol

Multiple Ash may discover learnings simultaneously. To prevent write conflicts:

1. **During workflow**: Each Ash writes to `.claude/echoes/{role}/{agent-name}-findings.md` (unique file per agent)
2. **Post-workflow**: The Tarnished consolidates all `{agent-name}-findings.md` into `.claude/echoes/{role}/MEMORY.md`
3. **Cross-role learnings**: Only lead writes to `.claude/echoes/team/MEMORY.md`
4. **Consolidation protocol**: Read existing MEMORY.md → append new entries → check 150-line limit → prune if needed → write

### Write Protocol Steps

```
1. Read .claude/echoes/{role}/MEMORY.md (or create if missing)
2. Read all .claude/echoes/{role}/*-findings.md files
3. For each finding:
   a. Check if it duplicates an existing entry (same evidence + pattern)
   b. If duplicate: update verified date and confidence (higher wins)
   c. If new: append with entry format
4. If MEMORY.md > 150 lines: run pruning algorithm
5. Write updated MEMORY.md
6. Delete processed *-findings.md files
```

## Security

### Sensitive Data Filter

Before persisting any echo entry, reject if content matches:

```
Patterns to reject:
- API keys: /[A-Za-z0-9_-]{20,}/ in context suggesting key/token
- Passwords: /password\s*[:=]\s*\S+/i
- Tokens: /bearer\s+[A-Za-z0-9._-]+/i
- Connection strings: /[a-z]+:\/\/[^:]+:[^@]+@/
- Email addresses in evidence (unless the learning IS about email handling)
```

If a finding triggers the filter, persist the learning but strip the sensitive evidence.

### Default Exclusion

`.gitignore` excludes `.claude/echoes/` by default. Users opt-in to version control:

```yaml
# .claude/talisman.yml
echoes:
  version_controlled: true  # Remove .claude/echoes/ from .gitignore
```

## Integration Points

### After Review (`/rune:appraise`)

In Phase 7 (Cleanup), before presenting TOME.md:

```
1. Read TOME.md for high-confidence patterns (P1/P2 findings)
2. Convert recurring patterns to Inscribed entries
3. Write to .claude/echoes/reviewer/MEMORY.md via consolidation protocol
```

### After Audit (`/rune:audit`)

Same as review, writing to `.claude/echoes/auditor/MEMORY.md`.

### During Plan (`/rune:devise`, v1.0)

```
1. echo-reader agent reads .claude/echoes/planner/MEMORY.md + .claude/echoes/team/MEMORY.md
2. Surfaces relevant past learnings for current feature
3. After plan: persist architectural discoveries to .claude/echoes/planner/
```

### During Work (`/rune:strive`, v1.0)

```
1. Read .claude/echoes/workers/MEMORY.md for implementation patterns
2. After work: persist TDD patterns, gotchas to .claude/echoes/workers/
```

## Codex Echo Validation (Optional)

Before persisting a learning to `.claude/echoes/`, optionally ask Codex whether the insight is generalizable or context-specific. This prevents polluting echoes with one-off observations that don't transfer to future sessions. Gated by `talisman.codex.echo_validation.enabled`. Uses nonce-bounded prompt, codex-exec.sh wrapper, and non-JSON output guard.

See [codex-echo-validation.md](references/codex-echo-validation.md) for the full protocol.

## Echo Schema Versioning

MEMORY.md files include a version header:

```markdown
<!-- echo-schema: v1 -->
# {Role} Memory

{entries...}
```

This enables future schema migrations without breaking existing echoes.

## Remembrance Channel — Human-Facing Knowledge

Remembrance is a parallel knowledge axis alongside Echoes. While Echoes are agent-internal memory (`.claude/echoes/`), Remembrance documents are version-controlled solutions in `docs/solutions/` designed for human consumption. Promotion requires: problem-solution pair, high confidence or 2+ session references, human actionability. Security-category promotions require explicit human verification.

See [remembrance-promotion.md](references/remembrance-promotion.md) for the full promotion rules, directory structure, and decision tree.

### YAML Frontmatter Schema

Remembrance documents use structured YAML frontmatter. See [remembrance-schema.md](references/remembrance-schema.md) for the full schema specification.

**Required fields**: `title`, `category`, `tags`, `date`, `symptom`, `root_cause`, `solution_summary`, `confidence`, `verified_by`

**Key fields:**

```yaml
---
title: "Descriptive title of the problem and solution"
category: architecture        # one of the 8 categories
tags: [n-plus-one, eager-loading]
date: 2026-02-12
symptom: "User list endpoint takes 5+ seconds"
root_cause: "N+1 query pattern in user.posts association"
solution_summary: "Added includes(:posts) to User.list scope"
echo_ref: ".claude/echoes/reviewer/MEMORY.md#etched-004@sha256:a1b2c3..."  # cross-ref with content hash
confidence: high              # high | medium
verified_by: human            # human | agent — REQUIRED for security category
requires_human_approval: false
---
```

The `echo_ref` field uses format `{echo_path}#{entry_id}@sha256:{hash}` to cross-reference version-controlled Remembrance to non-version-controlled echoes. The promotion process MUST compute and store the SHA-256 hash.

## Agent Awareness

Before implementing fixes, agents SHOULD check `docs/solutions/` for existing solutions to the problem at hand. This avoids re-discovering known solutions and ensures consistency.

### Remembrance Commands

The `/rune:echoes` command includes Notes and Remembrance subcommands:

```
/rune:echoes remember <text>                   # Create a Notes entry (user-explicit memory)
/rune:echoes remembrance [category|search]     # Query Remembrance documents
/rune:echoes promote <echo-ref> --category <cat>  # Promote echo to Remembrance
/rune:echoes migrate                           # Migrate echoes with old naming
```

**remember** — Create a Notes entry from user-provided text. Writes to `.claude/echoes/notes/MEMORY.md` (creates directory and file on demand). Notes are user-explicit memories that agents should always respect. They are never auto-pruned.

**Protocol:**
1. Read `.claude/echoes/notes/MEMORY.md` (or create with `<!-- echo-schema: v1 -->` header if missing)
2. Generate H2 entry: `## Notes — <title> (YYYY-MM-DD)` where title is extracted or summarized from user text
3. Add `**Source**: user:remember` metadata line
4. Append user-provided content as the entry body
5. Write back to `.claude/echoes/notes/MEMORY.md`
6. Confirm to user what was remembered

**Examples:**
```
/rune:echoes remember always use bun instead of npm
/rune:echoes remember the auth service requires Redis to be running locally
/rune:echoes remember PR reviews should check for N+1 queries in service layers
```

**remembrance** — Query existing Remembrance documents by category or search term. Returns matching documents with their frontmatter metadata.

**promote** — Promote an ETCHED echo to a Remembrance document. Validates promotion rules, computes content hash for `echo_ref`, checks for duplicates, and writes to `docs/solutions/{category}/`. For security category, prompts for human verification via `AskUserQuestion`.

**migrate** — Scans `.claude/echoes/` and updates old agent/concept names to current terminology (RENAME-2). Useful after version upgrades that rename agents or concepts.

## Echo Migration (RENAME-2)

When agent or concept names change across versions, existing echoes may reference stale names. The `migrate` subcommand handles this:

```
/rune:echoes migrate
```

**Steps:**
1. Scan all `.claude/echoes/**/*.md` files
2. Build a rename map from old names to new names
3. Apply renames to entry metadata (source, evidence references)
4. Report changes made

**Safety:**
- Backup all modified files before renaming
- Only rename in metadata fields, not in learning content
- Report all changes for user review

## Commands

See `/rune:echoes` command for user-facing echo management (show, prune, reset, remember, remembrance, promote, migrate).

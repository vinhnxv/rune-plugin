---
name: context-weaving
description: |
  Unified context management: overflow prevention, compression, and filesystem offloading.
  Should be loaded before summoning 3+ agents to enforce Glyph Budgets, plan orchestration, and prevent "Prompt is too long" errors.
  Also applicable for long sessions (50+ messages) to compress context.

  <example>
  Context: About to launch 4 review agents
  user: "Review this PR with multiple agents"
  assistant: "I'll use context-weaving to enforce Glyph Budgets and plan agent orchestration"
  </example>

  <example>
  Context: Long coding session
  user: "Context is getting long, I'm losing track"
  assistant: "Loading context-weaving for session compression"
  </example>
user-invocable: false
allowed-tools:
  - Task
  - Read
  - Write
---

# Context Weaving Skill

Unified context management combining overflow prevention, compression strategies, and filesystem offloading into a single skill. Prevents both context overflow (too many tokens from agent returns) and context rot (attention degradation in long sessions).

## Core Principle

**Control what returns to the Elden Lord context, not what agents produce.**

Agents can write unlimited detail to files. The overflow comes from what they _return_ to the caller. This skill ensures returns are minimal (file path + 1-sentence summary).

## Four Layers of Context Management

| Layer | Problem | Solution | When |
|-------|---------|----------|------|
| **Overflow Prevention** | Agent returns flood lead context | Glyph Budget: file-only output | Before summoning 3+ agents |
| **Context Rot** | Attention degrades in long contexts | Instruction anchoring, re-anchoring signals | Always (in prompts) |
| **Compression** | Session grows beyond 50+ messages | Anchored iterative summarization | During long sessions |
| **Filesystem Offloading** | Tool outputs consume 83.9% of context | Write outputs to files, read on demand | During any workflow |

## Layer 1: Overflow Prevention (Glyph Budget)

### When to Use

| Condition | Action |
|-----------|--------|
| About to summon **3-4 agents** via Task tool | Apply Glyph Budget + inscription |
| About to summon **5+ agents** | Use Agent Teams + Glyph Budget + inscription |
| Running `/rune:review` | Loaded automatically by roundtable-circle |
| Running `/rune:audit` | Loaded automatically by roundtable-circle |
| Any custom multi-agent orchestration | Apply Glyph Budget (if 3+ agents) |

### Pre-Summon Checklist (8 Thoughts)

**BEFORE summoning agents**, plan with these 8 steps:

#### Thought 1: Count and Estimate

```
Count the agents I'm about to summon.
Each Task return adds ~3-5k tokens without budget.
Base context (CLAUDE.md + rules + MCP) is ~30k tokens.

Agents planned: [list them]
Estimated return tokens (with budget): [count] x 150 = [total]
```

#### Thought 2: Choose Strategy

```
- 1-2 agents → Glyph Budget only. No inscription needed.
- 3-4 agents → Glyph Budget + inscription.json REQUIRED.
- 5+ agents OR TeamCreate → Agent Teams + Glyph Budget + inscription REQUIRED.

My choice: [strategy]
```

#### Thought 3: Plan Output Directory

```
Where should agents write findings?
- Review: tmp/reviews/{pr-number}/
- Audit: tmp/audit/{timestamp}/
- Plan research: tmp/research/
- Custom: tmp/{workflow-name}/

I'll use: [directory]
Ensure directory exists: mkdir -p [directory]
```

#### Thought 4: Verify Protocol Injection

```
For each agent prompt, append:
1. GLYPH BUDGET PROTOCOL (write to file, return summary only)
2. Output Requirements (required_sections from inscription)
3. Seal Format (file, sections, findings, evidence-verified, confidence)

Agents receiving the protocol:
- [agent-1]: ✓ budget + requirements + seal
- [agent-2]: ✓ budget + requirements + seal
```

#### Thought 5: Post-Completion Validation

```
After all agents complete:
1. Validate against inscription:
   - Circuit breaker: ALL files missing? → systemic failure, abort
   - Per-file: each file exists AND > 100 bytes? → PASS/FAIL
   - Report gaps in TOME.md "Incomplete" section
2. Summon Runebinder if 4+ raw files
3. Run quality probes on TOME.md
```

#### Thought 6: Revision Checkpoint

```
1. Can I merge redundant agents? (overlapping concerns?)
2. Should I split overloaded agents? (>30 files?)
3. Is the context budget per agent appropriate?
4. Does the inscription accurately reflect my plan?
```

#### Thought 7: Fallback Strategies

```
1. Agent timeout → Mark as partial, document gap
2. Inscription validation fails → Circuit breaker for ALL missing, per-file for partial
3. Context overflow mid-orchestration → Load compression, write scratch summary
```

#### Thought 8: Verification Planning

```
1. 3+ teammates with Report-format? → Enable Truthsight Layer 0
2. Review/audit workflow? → Enable Layer 2 (Smart Verifier)
3. Add verification block to inscription.json
```

### Glyph Budget Protocol

**Inject this text into EVERY agent prompt** when summoning in a multi-agent workflow:

```
GLYPH BUDGET PROTOCOL (MANDATORY):
- Write ALL detailed findings to: {output-directory}/{agent-name}.md
- Return to caller ONLY: the output file path + 1-sentence summary (max 50 words)
- DO NOT include full analysis, code examples, or detailed recommendations in return message

Example return:
"Findings written to {output-directory}/{agent-name}.md. Found 2 P1 issues (SQL injection, missing auth) and 4 P2 issues across 3 files."
```

### Runebinder Pattern (Aggregation)

After all agents complete, summon the Runebinder to process raw files:

| Raw files | Action |
|-----------|--------|
| 1-3 files | Read directly |
| 4+ files | Summon Runebinder agent |
| 10+ files | MUST summon Runebinder (never read all directly) |

After aggregation, read ONLY the TOME.md file. Do NOT also read raw files.

### Quality Probes (Post-Aggregation)

| Probe | Check | If Failed |
|-------|-------|-----------|
| **Circuit Breaker** | ALL output files missing? | Systemic failure — abort |
| **Inscription Validation** | All expected files exist and > 100 bytes? | Report gaps |
| **Agent Count** | Does TOME.md mention all summoned agents? | Read missing agent's raw file |
| **P1 Completeness** | Are P1 findings specific (file path + line)? | Spot-check one raw file |
| **Truthbinding Spot-Check** | Verify Rune Traces in 1-2 P1 findings per agent | Compare against actual source |

### Token Budget Reference

| Component | Tokens | Notes |
|-----------|--------|-------|
| CLAUDE.md + rules + MCP tools | ~30k | Fixed, always present |
| Each agent return (without budget) | 3-5k | The overflow source |
| Each agent return (with budget) | ~100-200 | File path + 50-word summary |
| TOME.md (aggregated) | ~1k | Replaces reading all raw files |
| Context window | 200k | Claude's limit |

## Layer 2: Context Rot Prevention

### The Problem

Context rot occurs when the model's attention degrades on important instructions placed in the middle of long contexts (Lost-in-Middle effect). This is different from overflow — it happens even within token limits.

### Prevention Strategies

**Instruction Anchoring:** Duplicate critical rules at BEGINNING and END of prompts.

```markdown
# ANCHOR — TRUTHBINDING PROTOCOL
[critical rules here]

## TASK
[main instructions]

# RE-ANCHOR — TRUTHBINDING REMINDER
[repeat critical rules]
```

**Read Ordering:** Source files FIRST, agent references LAST. Keeps review criteria fresh near output generation.

**Re-anchoring Signals:** After every 5 files reviewed, re-check evidence rules.

**Context Budget per Teammate:**
- Backend review: max 30 source files
- Security review: max 20 files (all types)
- Frontend review: max 25 source files
- Docs review: max 25 markdown files

## Layer 3: Compression

### When to Use

| Message Count | Action |
|---------------|--------|
| < 30 | No compression needed |
| 30-49 | Optional — available if needed |
| 50-69 | Trigger compression |
| >= 70 | Force compression |

### Compression Strategy: Anchored Iterative Summarization

1. **Identify truncation point** — messages that will be removed
2. **Extract key information** from those messages:
   - File modifications
   - Test results (pass/fail)
   - Decisions made
   - Error messages
3. **Merge into existing summary** — don't regenerate fully
4. **Write summary to file**: `tmp/scratch/session-{timestamp}.md`
5. **Continue with compressed context**

### Session Summary Format

```markdown
## Session Summary ({timestamp})

### State
- Phase: {current workflow phase}
- Current task: {description}

### Files Modified
| File | Change | Status |
|------|--------|--------|
| {path} | {description} | {pass/fail} |

### Key Decisions
- {decision 1}
- {decision 2}

### Current Error (if any)
```
{error message}
```

### Next Steps
1. {next action}
2. {following action}
```

### Quality Dimensions

After compression, verify:
1. **Accuracy** — Technical detail correctness
2. **Context Awareness** — Reflects current state
3. **Artifact Trail** — Knows which files were modified
4. **Completeness** — All aspects addressed
5. **Continuity** — Work continues without re-fetching
6. **Instruction Following** — Respects constraints

## Layer 4: Filesystem Offloading

### Core Principle

Tool outputs consume up to 83.9% of context. Offload large outputs to files.

### When to Offload

| Output Size | Action |
|------------|--------|
| < 10 lines | Keep inline |
| 10-50 lines | Consider offloading |
| > 50 lines | MUST offload to file |

### Offload Pattern

```
1. Write output to tmp/{workflow}/{descriptive-name}.md
2. Reference: "Output written to {path}. Key finding: {1-sentence summary}"
3. Read file only when needed for next step
```

## References

- [Overflow Wards](references/overflow-wards.md) — Detailed pre-summon protocol
- [Context Compression](references/context-compression.md) — Compression strategies and triggers
- [Filesystem Offloading](references/filesystem-offloading.md) — File-based output patterns
- Companion: `rune-orchestration` (architectural patterns, inscription protocol)

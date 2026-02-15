# Standing Orders — Anti-Pattern Library

Structured anti-patterns for multi-agent orchestration. Each Standing Order uses observable-behavior anchoring: symptoms describe what you can SEE in TaskList, file state, or agent behavior — not abstract principles.

**Enforcement**: The Tarnished (lead) MUST check these before and during agent team workflows. Ash teammates should self-check SO-5 and SO-6.

## Quick Reference

| SO | Name | Anti-Pattern | Applies To |
|----|------|-------------|------------|
| SO-1 | Hollow Ash | Spawning Ash for atomic tasks | `/rune:work`, `/rune:review` |
| SO-2 | Shattered Rune | Same file assigned to multiple workers | `/rune:work` |
| SO-3 | Tarnished Smith | Lead implementing instead of coordinating | All workflows |
| SO-4 | Blind Gaze | Skipping risk classification | `/rune:work` |
| SO-5 | Ember Overload | Context budget exceeded without compression | All agent workflows |
| SO-6 | Silent Seal | Ash completing without proper output format | `/rune:review`, `/rune:audit` |

---

## SO-1: Hollow Ash

**Anti-Pattern**: Spawning a full agent team for tasks that a single session can handle.

### Observable Symptoms
| # | Symptom | Detection Method |
|---|---------|-----------------|
| 1 | Total tasks <= 2 and all touch <= 3 files | TaskList count at creation time |
| 2 | All tasks have zero dependencies | TaskList `blockedBy` is empty for all |
| 3 | Single finding in TOME targeted by mend | TOME finding count before spawning fixers |

### Decision Table
| Condition | Action |
|-----------|--------|
| Tasks <= 2 AND unique file targets (from extractFileTargets) <= 3 AND no dependencies | Execute in single session — do NOT create a team |
| Tasks <= 2 BUT unique file targets (from extractFileTargets) > 3 OR has dependencies | Proceed with team (complexity justifies overhead) |
| Single TOME finding for mend | Fix inline — do NOT spawn mend worker |

### Remedy Procedure
1. **Halt** team creation before `TeamCreate`
2. **Execute** tasks sequentially in the current session
3. **Verify** output matches what a team would have produced

### Cross-References
- Risk Tier: Tier 0-1 (Grace/Ember) tasks most prone to this
- Related: SO-5 (Ember Overload) — hollow teams waste context budget

---

## SO-2: Shattered Rune

**Anti-Pattern**: Assigning the same file to multiple Ash workers for concurrent editing.

### Observable Symptoms
| # | Symptom | Detection Method |
|---|---------|-----------------|
| 1 | Two+ in_progress tasks name the same file | Scan task descriptions for overlapping file paths |
| 2 | Git merge conflict markers appear after ward check | `git diff --check HEAD` output |
| 3 | Worker reports "file changed unexpectedly" | Teammate message content |

### Decision Table
| Condition | Action |
|-----------|--------|
| Overlap detected at task creation | Add `blockedBy` to serialize the conflicting tasks |
| Overlap detected mid-execution | Pause later task, let first complete, then resume |
| Merge conflicts after completion | Assign a dedicated fix task to resolve conflicts |

### Remedy Procedure
1. **Detect** overlapping file ownership via set intersection of task file lists
2. **Serialize** conflicting tasks using `TaskUpdate({ addBlockedBy })` or merge into one task
3. **Verify** no merge conflict markers remain: `git diff --check HEAD`

### Cross-References
- Damage Control: DC-5 (Crossed Runes) — concurrent workflow variant
- Related: SO-1 (Hollow Ash) — merging tasks avoids file overlap
- Risk Tier: All tiers — file conflicts can occur at any risk level

---

## SO-3: Tarnished Smith

**Anti-Pattern**: The lead agent (Tarnished) writing code or making edits instead of coordinating.

### Observable Symptoms
| # | Symptom | Detection Method |
|---|---------|-----------------|
| 1 | Lead calls Write/Edit/Bash on project source files | Tool use log shows Write/Edit from lead context |
| 2 | Lead creates commits during a team workflow | `git log` shows commits not attributed to a worker |
| 3 | Workers idle while lead implements | TaskList shows workers with no in_progress tasks |

### Decision Table
| Condition | Action |
|-----------|--------|
| Lead about to edit a source file | Stop — create a task and assign to a worker instead |
| All workers busy but urgent fix needed | Create task, wait for a worker to become available |
| No team active (single-session mode) | Allowed — SO-3 only applies during team workflows |

### Remedy Procedure
1. **Stop** the edit before committing changes
2. **Create** a TaskCreate with the intended change as description
3. **Verify** a worker picks up and completes the task

### Cross-References
- Related: SO-1 (Hollow Ash) — if task is atomic, single-session is fine (no team needed)
- Risk Tier: All tiers — coordination failure is role-independent

---

## SO-4: Blind Gaze

**Anti-Pattern**: Assigning work tasks without classifying their risk tier first.

### Observable Symptoms
| # | Symptom | Detection Method |
|---|---------|-----------------|
| 1 | Task metadata has no `risk_tier` field | TaskGet shows missing tier |
| 2 | Security-sensitive files modified without lead review | Changed files match Tier 2-3 path patterns |
| 3 | No rollback plan for infrastructure changes | Task description lacks rollback steps |

### Decision Table
| Condition | Action |
|-----------|--------|
| No risk_tier in any task metadata | Halt and classify all tasks before proceeding |
| Some tasks classified, some not | Classify remaining — do not start unclassified tasks |
| Plan metadata overrides tier | Accept override if explicitly set by user, log reason |
| Task already in_progress without tier | Recall, classify, reassign |

### Remedy Procedure
1. **Pause** task execution until risk tier is assigned
2. **Classify** using the 4-question decision tree in `risk-tiers.md`. See the Graduated Verification Matrix for per-tier requirements.
3. **Verify** tier-appropriate verification requirements are met before marking complete

### Cross-References
- Risk Tiers: `risk-tiers.md` — full decision tree and verification matrix
- Damage Control: DC-2 (Broken Ward) — unclassified tasks often fail ward checks
- Related: SO-2 (Shattered Rune) — Tier 2+ tasks need serialized file ownership

---

## SO-5: Ember Overload

**Anti-Pattern**: Exceeding context budget without triggering compression or offloading.

### Observable Symptoms
| # | Symptom | Detection Method |
|---|---------|-----------------|
| 1 | "Prompt is too long" error from agent | Error message in teammate output |
| 2 | Agent responses become degraded or repetitive | Monitoring detects quality drop |
| 3 | Agent stops following instructions mid-task | Task output missing required sections |

### Decision Table
| Condition | Action |
|-----------|--------|
| Single agent approaching context limit | Offload intermediate results to `tmp/` file, compact |
| Multiple agents hitting limits simultaneously | Reduce team size, redistribute remaining tasks |
| Lead context overloaded from monitoring | Summarize task state, compact, re-read essentials |

### Remedy Procedure
1. **Offload** large intermediate results to `tmp/` files immediately
2. **Compact** the agent's context (or request agent restart with summary)
3. **Verify** the agent can still complete its task after recovery

### Cross-References
- Damage Control: DC-1 (Glyph Flood) — full recovery procedure for context overflow
- Related: SO-1 (Hollow Ash) — smaller teams use less total context
- Risk Tier: All tiers — context limits are resource-based, not risk-based

---

## SO-6: Silent Seal

**Anti-Pattern**: Ash completing its task without producing output in the required format.

### Observable Symptoms
| # | Symptom | Detection Method |
|---|---------|-----------------|
| 1 | Ash marks task completed but no output file exists | Check `tmp/` for expected output file |
| 2 | Output file exists but missing required sections | Parse output for TOME/Seal markers |
| 3 | Findings lack nonce, category, or severity fields | Validate output against inscription schema |

### Decision Table
| Condition | Action |
|-----------|--------|
| No output file at all | Re-assign task to same or different Ash |
| Output exists but malformed | Create a fix task to reformat output |
| Output exists, minor fields missing | Patch missing fields during aggregation |

### Remedy Procedure
1. **Detect** missing or malformed output before marking task complete
2. **Re-assign** the task if output is absent or unusable
3. **Verify** final output matches the inscription schema before aggregation

### Cross-References
- Related: SO-4 (Blind Gaze) — proper classification includes expected output format
- Output Format: `output-format.md` — canonical Seal and TOME structure
- Inscription Schema: `inscription-schema.md` — contract fields for Ash output

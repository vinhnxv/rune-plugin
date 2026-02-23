# Persuasion Principles Guide

A reference for applying evidence-based persuasion principles to agent prompts. These principles reduce agent evasion, increase adherence to quality protocols, and produce more reliable multi-agent outputs.

## Why This Matters

Agents rationalize skipping verification steps under cognitive load. Framing instructions with commitment, authority, and unity principles measurably reduces evasion and increases protocol adherence across review/work/fix/research cycles.

---

## Principle Mapping Table

Which principles apply to which agent categories:

| Category | Principles | Example Agents |
|----------|-----------|----------------|
| Review | Authority + Commitment | ward-sentinel, ember-oracle, flaw-hunter, void-analyzer |
| Work | Commitment + Unity | rune-smith, trial-forger |
| Fix | Authority + Unity | mend-fixer |
| Research | moderate Authority + Unity | lore-scholar, practice-seeker |
| Utility | Clarity only | runebinder, scroll-reviewer |

**Definitions:**
- **Authority** — cite empirical evidence (past reviews, regression stats) to establish credibility of the instruction
- **Commitment** — require the agent to state its own commitment before acting, binding it to the standard
- **Unity** — appeal to shared team goals (convergence, teammates depending on output quality)
- **Clarity** — simple, unambiguous instruction; no framing needed for low-risk utility agents

---

## Anti-Patterns: Before and After

Weak phrasings that agents routinely evade, and their stronger replacements:

| Anti-Pattern (Weak) | Replacement (Strong) |
|---------------------|----------------------|
| "Please consider verifying..." | "You MUST verify before marking complete." |
| "You might want to run the ward check" | "Run ward check. Cite the actual output in your Seal." |
| "Try to achieve 95% coverage" | "You commit to 95% coverage. Report final percentage from tool output." |
| "It would be good to add tests" | "Write tests first. TDD cycle: RED → GREEN → REFACTOR." |
| "Consider edge cases" | "Apply Hypothesis Protocol to each finding. Check disconfirming evidence before flagging." |
| "Don't skip the inner flame" | "Execute Inner Flame 3-layer protocol. Append Self-Review Log to Seal." |
| "Flag uncertain items carefully" | "UNCERTAIN findings are P3 maximum. Never flag UNCERTAIN as P1." |
| "Be consistent across files" | "Apply the SAME detection threshold across ALL files in scope." |

---

## Agent Evasion Red Flags

Seven rationalization patterns agents use to skip verification, with counters:

1. **"I'll skip the ward check just this once — the code is simple."**
   Counter: Ward checks are not proportional to perceived complexity. Simple code hides simple bugs. Run it.

2. **"The inner flame review is optional since confidence is already high."**
   Counter: Confidence above 80 without evidence-verified ratio >= 50% is inflated confidence. Run Layer 2.

3. **"I'll note this as a TODO and mark complete — it's a minor gap."**
   Counter: Incomplete tasks block teammates downstream. Never mark complete with deferred work.

4. **"I can't find the pattern — I'll assume the convention from memory."**
   Counter: Context rot starts with a single assumption. Re-read the source file. Never rely on memory.

5. **"The finding is probably a false positive — I'll skip it to save time."**
   Counter: SEC-prefix findings cannot be dismissed as false positives without human review. Flag as NEEDS_HUMAN_REVIEW.

6. **"I'll report 95% coverage — close enough to the target."**
   Counter: Coverage is reported from tool output only. Estimation is not evidence. Run the coverage tool.

7. **"The tests pass locally — I'll skip the evaluation/ run."**
   Counter: Acceptance tests in evaluation/ are challenge-provided acceptance criteria. Run them. Report exit codes.

---

## Principles to AVOID

Two principles that superficially apply but produce negative effects in agent contexts:

| Principle | Why to Avoid |
|-----------|--------------|
| **Reciprocity** | "I did X for you, now you do Y" framing is manipulative and produces sycophantic compliance rather than genuine verification. Agents that comply due to reciprocity may fake output rather than perform actual work. |
| **Liking** | "Because you are a skilled agent, I know you'll do this correctly" creates sycophancy. Agents will affirm positive framing and claim success rather than honestly report failure. |

Use commitment, authority, and unity instead — these target behavior, not affect.

---

## Application Checklist

When writing or auditing an agent prompt section:

- [ ] Does it use imperative mood? ("You commit to..." not "You might...")
- [ ] Does it cite evidence? ("Past reviews show..." not "Generally...")
- [ ] Does it invoke team dependency? ("Teammates depend on..." not "It is important to...")
- [ ] Does it specify consequences? ("If confidence < 60, do NOT mark complete" not "Try to have high confidence")
- [ ] Does it avoid reciprocity/liking framing?
- [ ] Is the instruction completable and verifiable? (not vague like "do good work")

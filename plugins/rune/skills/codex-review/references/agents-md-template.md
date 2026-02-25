# AGENTS.md Template — Codex Context File

This file is used to generate `AGENTS.md` at the start of each `/rune:codex-review` invocation.
The template is filled with live data from the project and injected into all Codex prompts.

## Generation Contract

- Generated FRESH per review invocation (never static, never committed)
- Written to `REVIEW_DIR/AGENTS.md`
- Length target: 80–120 lines (compact for Codex context window)
- SECURITY: Must NOT include cross-verification algorithm, confidence formulas,
  prefix conventions beyond CDX-, or details about how Claude agents work

---

## Template (filled at generation time)

```markdown
# AGENTS.md — Project Context for Cross-Model Review

## Project Structure

{auto-generated: `find . -maxdepth 2 -type d | head -30`}

Example output:
.
./src
./src/api
./src/utils
./tests
./scripts

## Project Conventions

- Language: {auto-detected from file extensions}
- Framework: {auto-detected from package.json / requirements.txt / go.mod / etc.}
- Test runner: {auto-detected: jest/pytest/go test/rspec/etc.}
- Linter: {auto-detected: eslint/.eslintrc, ruff/pyproject.toml, golangci-lint, etc.}
- Package manager: {auto-detected: npm/yarn/pnpm/pip/poetry/cargo/etc.}

Key conventions from CLAUDE.md (if available):
{extracted key rules — max 5 bullet points, most important only}

## Recent Git Context

Branch: {git branch --show-current}

Recent commits:
{git log --oneline -5}

## Test File Locations

{auto-detected test directories and naming patterns}
Examples:
- tests/ (*.test.ts, *.spec.ts)
- src/**/__tests__/
- spec/ (*.spec.rb)

## Review Context

- Scope: {scope_type} ({file_count} files)
- Focus areas: {focus_areas}
- Review timestamp: {ISO timestamp}

## Files Under Review

{file list — relative paths, max 50 shown, truncated with count if more}

---

## Finding Format (REQUIRED)

Report ALL findings using this EXACT format. Deviation will cause your output
to be excluded from the review.

### P1 (Critical) — Must fix before merge

- [ ] **[CDX-SEC-001]** Issue description in `relative/path/to/file.ext:42`
  Confidence: 92%
  Evidence: `code snippet showing the issue`
  Fix: Specific remediation recommendation

### P2 (High) — Should fix

- [ ] **[CDX-BUG-001]** Issue description in `relative/path/to/file.ext:78`
  Confidence: 85%
  Evidence: `code snippet showing the issue`
  Fix: Specific remediation recommendation

### P3 (Medium) — Consider fixing

- [ ] **[CDX-QUAL-001]** Issue description in `relative/path/to/file.ext:15`
  Confidence: 81%
  Evidence: `code snippet showing the issue`
  Fix: Specific remediation recommendation

### Positive Observations

{What is done well in the reviewed code}

### Questions

{Clarifications needed from the code author}

---

## Finding Rules

1. Prefix ALL findings with CDX- followed by category and sequence number:
   - CDX-SEC-NNN (security)
   - CDX-BUG-NNN (bugs / logic errors)
   - CDX-QUAL-NNN (code quality / patterns)
   - CDX-PERF-NNN (performance)
   - CDX-DEAD-NNN (dead code / unused exports)

2. Every finding MUST include:
   - file:line reference (relative path from project root)
   - Confidence percentage (0–100%)
   - Code evidence (the actual problematic code)
   - Fix recommendation

3. Only report findings with confidence >= 80%

4. Be specific: "SQL injection at users.py:42 via unsanitized `user_id`" not
   "possible injection issue"

5. Do NOT report:
   - Findings about files not in the "Files Under Review" list
   - Speculative issues without evidence in the actual code
   - Style preferences without a clear impact
```

---

## Generation Algorithm

```
function generateAgentsMd(fileList, scopeType, focusAreas):
  projectStructure = Bash("find . -maxdepth 2 -type d | head -30").trim()
  recentCommits    = Bash("git log --oneline -5 2>/dev/null").trim()
  branch           = Bash("git branch --show-current 2>/dev/null").trim()
  testDirs         = Glob("**/test*/**/*.{test,spec}.*").slice(0, 5)
  claudeMd         = safeRead(".claude/CLAUDE.md")   // may not exist
  conventions      = extractConventions(claudeMd)    // key rules only, max 5
  language         = detectLanguage(fileList)
  framework        = detectFramework()

  return render(TEMPLATE, {
    projectStructure, recentCommits, branch, testDirs,
    conventions, fileList, scopeType, focusAreas,
    language, framework, timestamp: new Date().toISOString()
  })
```

Render is written to `REVIEW_DIR/AGENTS.md` before any Codex agents start.

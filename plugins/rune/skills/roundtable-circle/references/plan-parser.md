# Plan Parser — Requirement Extraction Algorithm

> Reference for `/rune:inspect` Phase 0. Extracts structured requirements from freeform plan markdown.

## Input

A plan file (`.md`) OR inline text. Plans may follow Rune's standard template (YAML frontmatter + sections) or be freeform markdown.

## Extraction Algorithm

### Step 1 — Detect Plan Format

```
if (input is a file path AND file exists):
  planContent = Read(input)
  planPath = input
elif (input is inline text):
  planContent = input
  planPath = null
else:
  error("Plan not found: {input}")
```

### Step 2 — Parse YAML Frontmatter (if present)

```
if (planContent starts with "---"):
  frontmatter = parseYAML(between first and second "---")
  // Extract metadata: type, name, date, git_sha, strategic_intent
```

### Step 3 — Extract Requirements

Requirements are extracted from multiple sources in the plan:

#### Source A — Explicit Requirements Section

Look for headings containing: "Requirements", "Acceptance Criteria", "Deliverables", "Goals", "Objectives", "User Stories", "Tasks"

```
requirementHeadings = findHeadings(planContent, [
  /requirements?/i,
  /acceptance\s+criteria/i,
  /deliverables?/i,
  /goals?\s*(and\s*objectives?)?/i,
  /objectives?/i,
  /user\s+stories?/i,
  /tasks?\s+(list|breakdown)?/i
])

for each heading:
  sectionContent = contentUntilNextHeading(heading)
  items = extractListItems(sectionContent)  // Markdown list items (-, *, numbered)
  for each item:
    requirements.push({
      id: "REQ-{NNN}",
      text: item.text,
      source: "explicit",
      heading: heading.text,
      priority: inferPriority(item)  // P1 if "must/critical/required", P2 if "should/important", P3 if "could/nice/optional"
    })
```

#### Source B — Implementation Plan Section

Look for headings containing: "Implementation", "Architecture", "Design", "Approach", "Technical Design", "Files to Create", "Files to Modify"

```
implHeadings = findHeadings(planContent, [
  /implementation\s*(plan|approach|details)?/i,
  /architecture/i,
  /technical\s+design/i,
  /files?\s+to\s+(create|modify|change)/i,
  /approach/i
])

for each heading:
  sectionContent = contentUntilNextHeading(heading)
  // Extract from code blocks, bullet points, and tables
  items = extractActionItems(sectionContent)
  for each item:
    requirements.push({
      id: "REQ-{NNN}",
      text: item.text,
      source: "implementation",
      heading: heading.text,
      priority: "P2"  // Implementation items default to P2
    })
```

#### Source C — Inline Plan Text (fallback for freeform)

If no explicit sections found, extract requirements from the entire plan:

```
if (requirements.length === 0):
  // Extract sentences that contain action verbs
  actionPatterns = [
    /\b(add|create|implement|build|write|configure|set\s*up|integrate|enable|support)\b/i,
    /\b(modify|update|change|refactor|fix|improve|enhance|extend)\b/i,
    /\b(remove|delete|deprecate|disable|drop)\b/i,
    /\b(test|validate|verify|ensure|enforce|check)\b/i,
    /\b(document|describe|log|monitor|trace|audit)\b/i
  ]

  sentences = splitIntoSentences(planContent)
  for each sentence matching actionPatterns:
    requirements.push({
      id: "REQ-{NNN}",
      text: sentence,
      source: "inferred",
      heading: null,
      priority: "P2"
    })
```

### Step 4 — Extract Plan Identifiers

Identifiers are concrete nouns that can be searched in the codebase:

```
identifiers = []

// File paths mentioned in plan
filePaths = planContent.match(/\b[\w\-./]+\.(md|ts|tsx|js|jsx|py|rb|go|rs|sh|yml|yaml|json|sql|html|css)\b/g)
identifiers.push(...filePaths.map(p => ({ type: "file", value: p })))

// Function/class/variable names (camelCase, PascalCase, snake_case)
codeNames = planContent.match(/\b[a-z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)+\b/g)  // camelCase
codeNames.push(...planContent.match(/\b[A-Z][a-z]+(?:[A-Z][a-zA-Z0-9]*)+\b/g) || [])  // PascalCase (requires 2+ uppercase transitions to avoid matching common words like "The", "Plan")
codeNames.push(...planContent.match(/\b[a-z]+(?:_[a-z]+)+\b/g) || [])           // snake_case
identifiers.push(...codeNames.map(n => ({ type: "code", value: n })))

// Config keys and env vars
configKeys = planContent.match(/\b[A-Z][A-Z0-9_]+\b/g)
identifiers.push(...(configKeys || []).map(k => ({ type: "config", value: k })))

// Deduplicate
identifiers = unique(identifiers, i => i.value)
```

### Step 5 — Classify Requirements by Inspector

Keyword-based classification assigns each requirement to one or more inspectors:

```
const INSPECTOR_KEYWORDS = {
  "grace-warden": [
    "implement", "create", "add", "build", "feature", "endpoint", "model",
    "schema", "migration", "route", "handler", "controller", "service",
    "command", "component", "module", "function", "class", "method",
    "api", "interface", "type", "struct", "table", "column", "field"
  ],
  "ruin-prophet": [
    "security", "auth", "permission", "role", "token", "jwt", "session",
    "encrypt", "hash", "secret", "vulnerability", "injection", "xss",
    "csrf", "rate limit", "timeout", "retry", "circuit breaker", "fallback",
    "error handling", "exception", "failure", "recovery", "rollback",
    "graceful shutdown", "health check", "migration safety"
  ],
  "sight-oracle": [
    "architecture", "design", "pattern", "layer", "boundary", "coupling",
    "cohesion", "dependency", "interface", "abstract", "solid",
    "performance", "query", "index", "cache", "async", "concurrent",
    "parallel", "batch", "pagination", "lazy", "eager", "n+1",
    "scalability", "throughput", "latency", "memory", "optimization"
  ],
  "vigil-keeper": [
    "test", "spec", "coverage", "assertion", "mock", "fixture",
    "log", "metric", "trace", "monitor", "alert", "dashboard",
    "observability", "debug", "documentation", "readme", "changelog",
    "comment", "docstring", "api doc", "migration guide",
    "maintain", "refactor", "clean", "naming", "convention"
  ]
}

for each requirement:
  matches = []
  for each [inspector, keywords] of INSPECTOR_KEYWORDS:
    score = countMatches(requirement.text.toLowerCase(), keywords)
    if (score > 0):
      matches.push({ inspector, score })

  if (matches.length === 0):
    // Default: assign to grace-warden (completeness)
    requirement.inspectors = ["grace-warden"]
  else:
    // Assign to all matching inspectors (sorted by score, max 2)
    requirement.inspectors = matches
      .sort((a, b) => b.score - a.score)
      .slice(0, 2)
      .map(m => m.inspector)
```

## Output

```json
{
  "plan_path": "plans/2026-02-20-feat-inspect-plan.md",
  "plan_metadata": { "type": "feat", "name": "inspect", "git_sha": "abc123" },
  "requirements": [
    {
      "id": "REQ-001",
      "text": "Create inspect.md command with 8-phase pipeline",
      "source": "explicit",
      "heading": "Files to Create",
      "priority": "P2",
      "inspectors": ["grace-warden"]
    }
  ],
  "identifiers": [
    { "type": "file", "value": "plugins/rune/skills/inspect/SKILL.md" },
    { "type": "code", "value": "graceWarden" }
  ],
  "inspector_assignments": {
    "grace-warden": ["REQ-001", "REQ-002", "REQ-005"],
    "ruin-prophet": ["REQ-003", "REQ-007"],
    "sight-oracle": ["REQ-004", "REQ-006"],
    "vigil-keeper": ["REQ-008", "REQ-009", "REQ-010"]
  }
}
```

## Edge Cases

| Case | Handling |
|------|----------|
| Empty plan | Error: "Plan contains no extractable requirements" |
| Plan with only frontmatter | Extract from frontmatter description field |
| Plan with tables | Parse markdown tables as requirement sources |
| Inline plan (no file) | Skip frontmatter parsing, use full text as Source C |
| Plan with code blocks | Skip code blocks when extracting sentences (avoid false positives) |
| Very long plan (>500 lines) | Truncate identifier extraction to first 200 lines + section headings |

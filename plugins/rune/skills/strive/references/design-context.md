# Design Context Discovery (Phase 1 — Conditional)

After task extraction, discover design artifacts using a 4-strategy cascade. Triple-gated: `design_sync.enabled` + frontend task signals + design artifact presence. Zero overhead when any gate is closed.

```javascript
// Design context discovery — 4-strategy cascade
// Triple-gated: design_sync.enabled + frontend signals + artifacts
function discoverDesignContext(talisman, frontmatter, tasks) {
  // Gate 1: design_sync.enabled
  const designEnabled = talisman?.design_sync?.enabled === true
  if (!designEnabled) return { strategy: 'none' }

  // Gate 2: Any frontend tasks? (isFrontend set by classifyFrontendTask in parse-plan.md)
  const hasFrontendTasks = tasks.some(t => t.isFrontend)
  if (!hasFrontendTasks) return { strategy: 'none' }

  // Gate 3: Design artifacts — try 4 strategies in priority order

  // Strategy 1: Design packages (from arc design_extraction phase)
  const designPackages = Glob('tmp/arc/*/design/design-package.json')
  if (designPackages.length > 0) {
    const pkg = JSON.parse(Read(designPackages[0]))
    return {
      strategy: 'design-package',
      designPackagePath: designPackages[0],
      vsmFiles: pkg.vsm_files || [],
      dcdFiles: pkg.dcd_files || [],
      figmaUrl: pkg.figma_url || frontmatter.figma_url
    }
  }

  // Strategy 2: Arc VSM/DCD files (from previous arc run)
  const vsmFiles = Glob('tmp/arc/*/vsm/*.json')
  const dcdFiles = Glob('tmp/arc/*/design/*.md')
  if (vsmFiles.length > 0 || dcdFiles.length > 0) {
    return {
      strategy: 'arc-artifacts',
      vsmFiles, dcdFiles,
      figmaUrl: frontmatter.figma_url
    }
  }

  // Strategy 3: design-sync output (from /rune:design-sync)
  const dsVsm = Glob('.claude/design-sync/vsm/*.json')
  const dsDcd = Glob('.claude/design-sync/dcd/*.md')
  if (dsVsm.length > 0 || dsDcd.length > 0) {
    return {
      strategy: 'design-sync',
      vsmFiles: dsVsm, dcdFiles: dsDcd,
      figmaUrl: frontmatter.figma_url
    }
  }

  // Strategy 4: Figma URL only (from plan frontmatter — no extracted artifacts yet)
  if (frontmatter.figma_url) {
    return {
      strategy: 'figma-url-only',
      figmaUrl: frontmatter.figma_url,
      vsmFiles: [], dcdFiles: []
    }
  }

  return { strategy: 'none' }
}

const designContext = discoverDesignContext(talisman, frontmatter, extractedTasks)
const hasDesignContext = designContext.strategy !== 'none'

// Pass designContext to task annotation (parse-plan.md § Design Context Detection)
// Each task gets has_design_context + design_artifacts based on isFrontend flag
// Pass to worker prompt generation (worker-prompts.md § Design Context Injection)
// Workers receive DCD/VSM content in their spawn prompts when applicable
```

## Conditional Skill Loading

When `hasDesignContext` is true, conditionally load design skills for worker context:

```javascript
// Conditional loaded skills — only when design context is active
if (hasDesignContext) {
  loadedSkills.push('frontend-design-patterns')  // Design tokens, accessibility, responsive patterns
  loadedSkills.push('figma-to-react')             // Component mapping, variant extraction
  loadedSkills.push('design-sync')                // VSM/DCD knowledge
}
```

The `classifyFrontendTask()` function in `parse-plan.md` tags each task with `isFrontend`, and the Design Context Detection section attaches artifact paths to frontend tasks only.

# Screenshot Comparison — Agent-Browser Integration

Integration with agent-browser for visual comparison between implemented components and design specifications.

## Prerequisites

- `agent-browser` skill must be available
- A rendering environment (Storybook, dev server, or test harness)
- Component must be renderable in isolation

## Availability Detection

```
function checkAgentBrowser():
  // Check if agent-browser skill is loaded
  // Check if a browser automation tool is available
  // Return { available: boolean, method: "storybook" | "devserver" | "none" }

  if Storybook detected (package.json has @storybook/react):
    return { available: true, method: "storybook" }
  if dev server available (package.json has dev/start script):
    return { available: true, method: "devserver" }
  return { available: false, method: "none" }
```

## Graceful Degradation

| Agent-Browser Status | Phase 2.5 (Iteration) | Phase 3 (Review) |
|---------------------|----------------------|------------------|
| Available + Storybook | Full visual comparison | Visual + code analysis |
| Available + dev server | Component-level comparison | Visual + code analysis |
| Not available | SKIP Phase 2.5 | Code-only analysis |

When agent-browser is unavailable, the pipeline degrades to code-level analysis only. This is explicitly acceptable — code-level review catches token compliance, layout structure, and accessibility attributes through static analysis.

## Screenshot Capture Workflow

### Via Storybook

```
1. Start Storybook if not running:
   Bash("npx storybook dev --port 6006 --no-open &")
   Wait for port 6006 to be available

2. For each component variant:
   Navigate to: http://localhost:6006/iframe.html?id={story-id}
   Set viewport to target breakpoint width
   Capture screenshot

3. Screenshots saved to:
   tmp/design-sync/{timestamp}/screenshots/{component}/{variant}-{breakpoint}.png
```

### Via Dev Server

```
1. Start dev server if not running:
   Bash("npm run dev &")
   Wait for port to be available

2. Navigate to component's route or test page
3. Capture screenshot at target viewport widths

4. Screenshots saved to same directory as above
```

## Visual Analysis Protocol

When screenshots are available, analyze in this order:

### 1. Structural Layout Comparison

```
Compare screenshot layout regions against VSM region tree:
  - Are major regions in the correct position?
  - Is the nesting correct (sidebar inside container, not floating)?
  - Does the flex/grid direction match?
```

### 2. Spacing Analysis

```
Estimate visual spacing between elements:
  - Does gap between items match VSM spacing tokens?
  - Does padding inside containers match?
  - Are elements aligned to the same baseline/edge?
```

### 3. Typography Verification

```
Check text rendering:
  - Does heading size appear correct relative to body text?
  - Is font weight visually correct (bold vs regular)?
  - Is line spacing appropriate for readability?
```

### 4. Color Verification

```
Check color application:
  - Do background colors match design?
  - Do text colors meet contrast requirements?
  - Are interactive elements visually distinct?
```

### 5. Responsive Behavior

```
Capture at multiple viewport widths:
  - 375px (mobile)
  - 768px (tablet)
  - 1024px (desktop)
  - 1440px (large desktop)

Compare layout shifts against VSM responsive spec.
```

## Screenshot Comparison Output

```markdown
### Visual Analysis: {component_name}

#### Mobile (375px)
![Screenshot](screenshots/{component}/default-mobile.png)
- Layout: {match|drift} — {description}
- Spacing: {match|drift} — {description}
- Colors: {match|drift} — {description}

#### Desktop (1024px)
![Screenshot](screenshots/{component}/default-desktop.png)
- Layout: {match|drift} — {description}
- Spacing: {match|drift} — {description}
- Colors: {match|drift} — {description}
```

## Limitations

```
1. Automated comparison is approximate — no pixel-diffing
2. Font rendering varies by OS/browser
3. Dynamic content (animations, transitions) not captured
4. Dark mode requires separate screenshot set
5. Browser DevTools overlays can interfere — use headless mode
```

## Cross-References

- [phase3-fidelity-review.md](phase3-fidelity-review.md) — Uses screenshot analysis
- [fidelity-scoring.md](fidelity-scoring.md) — Visual analysis contributes to score

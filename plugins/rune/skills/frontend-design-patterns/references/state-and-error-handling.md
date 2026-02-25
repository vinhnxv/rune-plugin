# State and Error Handling — UI State Patterns

Every interactive component has multiple states beyond the default "success" view. Designing for all states prevents broken user experiences and reduces bugs.

## The Four Core UI States

| State | Meaning | User Sees |
|-------|---------|-----------|
| **Loading** | Data is being fetched or processed | Skeleton, spinner, or placeholder |
| **Error** | Something went wrong | Error message with recovery action |
| **Empty** | No data exists yet | Illustration, explanation, CTA |
| **Success** | Data loaded and ready | The intended content |

**Rule**: Every component that fetches data or depends on async operations MUST handle all four states. Never show a blank screen.

## Loading State Patterns

### Skeleton Screens (Preferred)

Skeleton screens show the shape of the content before it loads. They reduce perceived loading time and prevent layout shifts.

```
Advantages over spinners:
- Communicates content structure in advance
- Prevents cumulative layout shift (CLS)
- Feels faster (perceived performance)

When to use:
- Known layout (lists, cards, profiles)
- Loading takes 200ms–3s
```

### Spinner / Progress

```
Use spinners when:
- Layout is unknown (search results)
- Operation is write-focused (submit, upload)
- Duration is indeterminate

Use progress bars when:
- Duration is measurable (file upload, multi-step)
- User needs to know how much is left
```

### Loading State Rules

| Duration | Pattern |
|----------|---------|
| < 200ms | Show nothing (avoid flash) |
| 200ms–1s | Inline spinner or skeleton |
| 1s–5s | Skeleton + "Loading..." text |
| 5s–30s | Progress indicator + cancel option |
| > 30s | Background task with notification |

```
# Delay pattern to avoid loading flash
const [showLoading, setShowLoading] = useState(false);
useEffect(() => {
  const timer = setTimeout(() => setShowLoading(true), 200);
  return () => clearTimeout(timer);
}, []);
```

## Error State Patterns

### Error Display Hierarchy

| Error Type | Where to Show | Recovery Action |
|-----------|---------------|-----------------|
| Field validation | Below the input | Fix and resubmit |
| Form submission | Top of form (summary) | Review errors and resubmit |
| Network failure | Inline or toast | "Retry" button |
| Permission denied | Full-page or modal | "Request access" or redirect |
| Not found (404) | Full-page | "Go home" or search |
| Server error (500) | Full-page or toast | "Try again later" |

### Error Message Anatomy

```
1. WHAT went wrong (brief, non-technical)
   "We couldn't save your changes."

2. WHY it happened (if known and useful)
   "The server is temporarily unavailable."

3. HOW to fix it (actionable next step)
   "Please try again in a few minutes."
   [Retry] button
```

### Error State Rules

```
- Never show raw error messages to users (no stack traces, no 500 HTML)
- Never show error codes alone ("Error 0x8004005")
- Always provide a recovery action (retry, go back, contact support)
- Log the full error to console/monitoring (not the UI)
- Distinguish between retryable and non-retryable errors
- Use aria-live="polite" or role="alert" for screen readers
```

## Empty State Patterns

### Empty State Anatomy

```
1. Visual: Illustration or icon (conveys tone — friendly, not sad)
2. Headline: What this area will contain
   "No projects yet"
3. Description: Brief explanation
   "Create your first project to get started."
4. CTA: Primary action to resolve the empty state
   [Create Project] button
```

### Types of Empty States

| Type | Example | CTA |
|------|---------|-----|
| First use | "No messages yet" | "Start a conversation" |
| Search/filter with no results | "No results for 'xyz'" | "Clear filters" |
| Deleted content | "This item was removed" | "Go back" |
| Permission-gated | "You don't have access" | "Request access" |

### Empty State Rules

```
- Never show a completely blank area — always explain what goes there
- CTAs should use action verbs ("Create", "Add", "Import") not "Click here"
- Search empty states should suggest alternative queries or actions
- Distinguish between "no data ever" and "no data matching filters"
```

## Optimistic Updates

Show the expected result immediately, then confirm with the server:

```
1. User clicks "Like"
2. UI updates immediately (heart fills, count +1)
3. API call fires in background
4. If API fails → revert UI + show toast error
```

### When to Use Optimistic Updates

| Scenario | Use Optimistic? |
|----------|----------------|
| Toggle (like, bookmark) | Yes — high confidence, easy revert |
| Create new item | Yes — show skeleton, confirm on success |
| Delete item | Cautious — show "undo" toast instead |
| Payment/transaction | No — always wait for confirmation |
| Form submission | No — wait for validation |

## Disabled State

```
Visual: Reduced opacity (0.5) + not-allowed cursor
Behavior: Non-interactive (no click, no focus for buttons)
ARIA: aria-disabled="true" (preferred over disabled attribute for a11y)
Tooltip: Explain WHY it's disabled on hover

# Correct
<button aria-disabled="true" title="Complete all fields first">Submit</button>

# Avoid
<button disabled>Submit</button>  <!-- Loses focus and screen reader access -->
```

## State Composition

Components often combine multiple states. Handle them in priority order:

```
1. Error → show error state (highest priority)
2. Loading → show loading state
3. Empty → show empty state
4. Success → show content (lowest priority, most common)
```

## Cross-References

- [accessibility-patterns.md](accessibility-patterns.md) — ARIA for state announcements
- [component-reuse-strategy.md](component-reuse-strategy.md) — Reusable state wrapper components

# React Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Sequential awaits for independent fetches | Use `Promise.all()` | P1 |
| Component > 50KB in main bundle | `React.lazy()` + `Suspense` | P1 |
| Missing `useEffect` cleanup | Return cleanup function | P1 |
| Missing hook dependency | Add to dep array (or `useEffectEvent`) | P1 |
| Inline object/function in JSX prop | Extract const or memoize | P2 |
| Derived state via `useState` + `useEffect` | Replace with `useMemo` | P2 |
| `array.includes()` in hot loop | Use `Set.has()` | P2 |
| `.sort()` on state/prop array | Use `.toSorted()` (immutable) | P2 |
| Manual `isSubmitting` form state | `useActionState` (React 19) | P3 |
| Class component | Convert to function component | P3 |

## Key Rules

### Rule 1: Hooks Discipline (REACT-001)
- BAD: `useEffect(() => { fetch(...) }, [])` — missing dep, no cleanup
- GOOD: `useEffect(() => { const ctrl = new AbortController(); fetch(..., { signal: ctrl.signal }); return () => ctrl.abort(); }, [url])`
- Rule: All `useEffect` deps must be exhaustive; async effects must cancel on unmount; `useState` with expensive init uses lazy initializer `useState(() => compute())`
- Detection: `rg "useEffect\(" --type tsx` — review each for missing return and dep array

### Rule 2: Async Waterfalls (REACT-002)
- BAD: `const a = await fetchA(); const b = await fetchB();`
- GOOD: `const [a, b] = await Promise.all([fetchA(), fetchB()]);`
- Rule: Independent async calls must be parallelized; use deferred `Promise` to start fetches before `await`
- Detection: `rg "await fetch|await axios" --glob "*.{ts,tsx}"` — check for consecutive awaits in same function

### Rule 3: Bundle Optimization (REACT-003)
- BAD: `import { Button } from '@ui-lib'` (barrel import loads entire lib)
- GOOD: `import Button from '@ui-lib/Button'` + `const HeavyPage = React.lazy(() => import('./HeavyPage'))`
- Rule: Route-level code-split with `React.lazy` + `Suspense`; avoid barrel imports for large libraries; use direct subpath imports
- Detection: `rg "React\.lazy|import\(" --glob "*.{ts,tsx}"` — check coverage against route files

### Rule 4: State Patterns (REACT-004)
- BAD: `const [fullName, setFullName] = useState(''); useEffect(() => setFullName(first + last), [first, last])`
- GOOD: `const fullName = useMemo(() => first + last, [first, last])`
- Rule: Derived values belong in `useMemo`, not `useState` + `useEffect`; state updates in loops use functional form `setState(prev => ...)` ; wrap non-urgent updates with `useTransition`
- Detection: `rg "useEffect.*setState|setIs\w+" --glob "*.{ts,tsx}"` — review for derived-state anti-patterns

### Rule 5: React 19 Features (REACT-005)
- BAD: `const [isSubmitting, setIsSubmitting] = useState(false); /* manual loading dance */`
- GOOD: `const [state, action, isPending] = useActionState(submitFn, initialState)`
- Rule: Use `useActionState` for form submissions, `useOptimistic` for optimistic UI, `use(promise)` for suspense-compatible data; note React Compiler (beta) may eliminate manual `useMemo`/`useCallback` — don't duplicate its work when enabled
- Detection: `rg "isSubmitting|isLoading.*useState" --glob "*.{ts,tsx}"` — candidates for `useActionState`

### Rule 6: Error Boundaries (REACT-006)
- BAD: Single root `<ErrorBoundary>` wrapping the whole app — one crash takes everything down
- GOOD: Per-feature `<ErrorBoundary fallback={<FeatureError />}>` around independent sections
- Rule: Wrap each independently-failable feature tree; use typed error handling to distinguish network vs. parse vs. render errors; always provide a recoverable fallback UI
- Detection: `rg "ErrorBoundary" --glob "*.{ts,tsx}"` — verify count and placement against route/feature structure

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Inline `{}` or `() =>` in JSX props | New reference on every render, breaks memoized children | Extract to module-level const or `useCallback` |
| Class components | Verbose, no hooks, harder to tree-shake | Convert to function components |
| Barrel imports from large libs | Pulls entire library into bundle | Direct subpath imports |
| `.sort()` on props/state arrays | Mutates in place, causes subtle bugs | `.toSorted()` or `[...arr].sort()` |
| `useEffect` for derived state | Extra render cycle, stale closure risk | `useMemo` |
| Manual `isSubmitting` form flag | Boilerplate, prone to stale state | `useActionState` (React 19) |
| `React.memo` on every component | Premature optimization, hides real issues | Profile first; memoize only proven hotspots |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `Promise.all([...])` | Multiple independent data fetches | Parallel I/O, cuts waterfall latency |
| `React.lazy()` + `Suspense` | Routes and heavy feature components | Smaller initial bundle |
| `content-visibility: auto` (CSS) | Long virtualized lists without a lib | Browser skips off-screen paint |
| `Set.has()` over `Array.includes()` | Membership checks in render/compute | O(1) vs O(n) |
| Functional `setState(prev => ...)` | State depending on previous value | Avoids stale closure bugs |
| `useTransition` | Search filters, tab switches, non-urgent UI | Keeps input responsive during re-render |
| `useMemo` for expensive computations | Heavy transforms run in render body | Skips recompute when deps unchanged |

## Security Checklist

- [ ] No `eval()`, `new Function()`, or dynamic `import()` with user-controlled strings
- [ ] No `dangerouslySetInnerHTML` without explicit DOMPurify/sanitization
- [ ] API responses validated with Zod (or equivalent) before use in state
- [ ] No secrets, API keys, or tokens in client-side bundles (check with `rg "process.env" --glob "*.{ts,tsx}"`)
- [ ] CORS and CSP headers configured server-side (not just client guards)
- [ ] User-supplied URLs validated before use in `href`, `src`, or `fetch()`

## Audit Commands

```bash
# Find sequential awaits (async waterfall candidates)
rg "await .+\n.*await " --glob "*.{ts,tsx}" -U

# Find useEffect without cleanup (potential memory leaks)
rg "useEffect\(\s*\(\)\s*=>\s*\{" --glob "*.{ts,tsx}" -A 10 | rg -v "return"

# Find manual isSubmitting/isLoading state (useActionState candidates)
rg "isSubmitting|isLoading.*useState|setIsLoading|setIsSubmitting" --glob "*.{ts,tsx}"

# Find barrel imports from common large libraries
rg "^import .* from '(react-icons|lodash|date-fns|@mui/material|antd)'" --glob "*.{ts,tsx}"

# Find .sort() that may mutate props/state (flag missing .toSorted())
rg "\.sort\(" --glob "*.{ts,tsx}" | rg -v "toSorted"

# Find dangerouslySetInnerHTML usage
rg "dangerouslySetInnerHTML" --glob "*.{ts,tsx}"

# Find class components
rg "extends (React\.)?(Component|PureComponent)" --glob "*.{ts,tsx}"
```

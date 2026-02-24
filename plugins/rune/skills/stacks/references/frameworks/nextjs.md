# Next.js Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Data fetching inside `useEffect` | Fetch in Server Component instead | P1 |
| `'use client'` on page or layout | Keep as Server Component | P2 |
| Missing `loading.tsx` next to `page.tsx` | Add `loading.tsx` for streaming UI | P2 |
| Missing `error.tsx` next to `page.tsx` | Add `error.tsx` for error boundaries | P2 |
| Server Action without input validation | Validate `FormData` with Zod | P1 |
| Secrets referenced in client component | Move to `server-only` module | P1 |
| Missing `generateMetadata` export | Add `generateMetadata()` or static `metadata` export | P3 |
| Waterfall data fetching in nested layouts | Use `Promise.all()` or parallel `fetch()` calls | P1 |
| `getServerSideProps` / `getStaticProps` in `app/` | Migrate to async Server Components + `fetch()` | P2 |
| Route handler without consistent error schema | Return typed `NextResponse` with error shape | P2 |

## Key Rules

### Rule 1: Server-First Architecture (NEXT-001)
- BAD: `'use client'` at the top of every component by default
- GOOD: Server Components by default; add `'use client'` only when browser APIs, event handlers, or state are needed
- Detection: `rg "'use client'" --glob "*.{ts,tsx}" -l`

### Rule 2: Data Fetching (NEXT-002)
- BAD: `useEffect(() => { fetch('/api/data').then(...) }, [])` inside a component
- GOOD: `async function Page() { const data = await fetch('...'); return <UI data={data} /> }`
- Use `React.cache()` to deduplicate identical `fetch()` calls across a render tree
- Detection: `rg "useEffect.*fetch|useEffect.*axios" --glob "*.{ts,tsx}"`

### Rule 3: File Conventions (NEXT-003)
- BAD: Only `page.tsx` in a route segment with no fallback UI or error handling
- GOOD: `page.tsx` + `loading.tsx` + `error.tsx` per segment; `layout.tsx` for shared UI; `not-found.tsx` for 404 handling
- Add `generateMetadata()` or static `metadata` export in every `page.tsx` for SEO
- Detection: `rg "export default" app/**/page.tsx` then verify sibling files exist

### Rule 4: Server Actions (NEXT-004)
- BAD: Server Action that trusts raw `FormData` without parsing or validation
- GOOD: Parse with Zod schema, return typed result, call `revalidatePath()` or `revalidateTag()` after mutations; use `useActionState` on the client
- Detection: `rg "'use server'" --type ts` — review each for Zod import

### Rule 5: Caching Strategy (NEXT-005)
- BAD: `fetch(url)` everywhere with no explicit cache directive, causing stale or unintended real-time fetches
- GOOD: Use `{ cache: 'force-cache' }` (default), `{ next: { revalidate: N } }` for ISR, `{ cache: 'no-store' }` for real-time; use `unstable_cache()` for non-`fetch` data sources
- Detection: `rg "fetch\(" --type ts | rg -v "cache:|revalidate:"`

### Rule 6: Middleware Scope (NEXT-006)
- BAD: Heavy computation, database queries, or large imports inside `middleware.ts`
- GOOD: Auth token checks, redirects, header rewrites — lightweight edge-compatible operations only; export a `config.matcher` to restrict which paths the middleware runs on
- Detection: `rg "import.*from" middleware.ts` — flag non-edge-compatible imports

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `'use client'` on every component | Sends all JS to the browser; loses server rendering | Only mark components that need browser APIs or interactivity |
| `useEffect` for initial data fetching | Causes waterfall: render → mount → fetch → re-render | Fetch in Server Component or `generateStaticParams` |
| `getServerSideProps` / `getStaticProps` in `app/` | Pages Router API, silently ignored in App Router | Use async Server Components with `fetch()` and cache options |
| Prop-drilling server-fetched data through many components | Couples layers; bloats client bundle if prop crosses boundary | Fetch at the component that needs it; use React context sparingly |
| Heavy logic in `middleware.ts` | Edge runtime has no Node.js APIs; crashes silently | Move business logic to Route Handlers or Server Actions |
| Missing Suspense / loading boundaries | Users see blank screens during async renders | Wrap async components with `<Suspense>` or add `loading.tsx` |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| Streaming with `<Suspense>` | Async Server Components with slow data | Progressive HTML — page loads before all data is ready |
| Parallel routes (`@slot`) | Side panels, modals, tabs in same layout | Independent streaming and error handling per slot |
| Partial Prerendering (PPR) | Mix of static shell + dynamic content | Static shell served from CDN; dynamic holes streamed |
| `next/dynamic` with `ssr: false` | Client-only libraries (charts, maps) | Removes module from server bundle |
| `next/image` | Any `<img>` tag | Automatic format conversion, lazy loading, responsive sizing |
| `next/font` | Custom fonts | Self-hosted, zero layout shift, preloaded automatically |

## Security Checklist

- [ ] No secrets or private env vars referenced inside `'use client'` components (`NEXT_PUBLIC_` prefix only for client-safe values)
- [ ] Server Actions validate all `FormData` / typed inputs with Zod before processing
- [ ] Auth check happens in `middleware.ts` or at the top of every protected Server Action / Route Handler
- [ ] CSRF: Server Actions are protected by default (same-site origin check); Route Handlers using `POST` should verify `Origin` header for non-browser clients
- [ ] Content Security Policy headers set in `next.config.ts` or middleware response headers
- [ ] Cookies that carry session tokens use `HttpOnly`, `Secure`, and `SameSite=Lax` attributes
- [ ] No `dangerouslySetInnerHTML` without DOMPurify sanitization (inherited React XSS vector)

## Audit Commands

```bash
# Find 'use client' density — high count may indicate over-clientification
rg "'use client'" --type ts -l | wc -l

# Find useEffect-based data fetching (client-side waterfall)
rg "useEffect\s*\(" -A 3 --type ts | rg "fetch\|axios\|\.get\("

# Find Server Actions missing Zod validation
rg "'use server'" --type ts -l | xargs rg -L "from 'zod'\|from \"zod\""

# Find pages missing loading.tsx sibling
for d in $(find . -path "*/app/**/page.tsx" -exec dirname {} \;); do
  [ ! -f "$d/loading.tsx" ] && echo "Missing loading.tsx: $d"
done

# Find pages missing error.tsx sibling
for d in $(find . -path "*/app/**/page.tsx" -exec dirname {} \;); do
  [ ! -f "$d/error.tsx" ] && echo "Missing error.tsx: $d"
done

# Find legacy Pages Router data methods in app/ directory
rg "getServerSideProps|getStaticProps|getStaticPaths" app/ --type ts

# Find fetch() calls without explicit cache directive
rg "fetch\(" --type ts | rg -v "cache:|revalidate:|no-store"
```

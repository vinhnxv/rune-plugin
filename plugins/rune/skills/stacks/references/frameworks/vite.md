# Vite Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Barrel file re-exports (`index.ts`) | Direct imports from source file | P2 |
| `process.env` in client code | Use `import.meta.env` | P1 |
| Env var without `VITE_` prefix exposed to client | Only `VITE_*` vars are client-safe | P1 |
| `require()` or CommonJS in ESM project | Use ES `import` syntax | P2 |
| No chunk strategy for large deps | Add `build.rollupOptions.output.manualChunks` | P2 |
| HMR causes full-page reload | Check for side effects at module top level | P3 |
| Missing `build.target` | Set appropriate browserslist or `es2022` | P3 |
| Global CSS in component files | Use CSS Modules (`.module.css`) or scoped styles | P3 |

## Key Rules

### Rule 1: Import Strategy (VITE-001)
- BAD: `import { Button } from '@/components'` (barrel re-export bundles entire index)
- GOOD: `import { Button } from '@/components/Button'`
- BAD: `import 'side-effect-lib'` at module top level (breaks HMR)
- Detection: `rg "from ['\"]\./index|from ['\"]@/[^/]+['\"]" --type ts`

### Rule 2: Build Optimization (VITE-002)
- BAD: No `manualChunks` — all dependencies in single vendor chunk
- GOOD:
  ```ts
  build: { rollupOptions: { output: { manualChunks: { vendor: ['react', 'react-dom'], utils: ['lodash-es', 'date-fns'] } } } }
  ```
- BAD: Eager import of route components — inflates initial bundle
- GOOD: `const Page = lazy(() => import('./pages/Page'))` (dynamic import)
- Detection: `rg "manualChunks" vite.config` (absence = risk on large projects)

### Rule 3: Environment Variables (VITE-003)
- BAD: `process.env.API_KEY` in client code (undefined at runtime)
- BAD: `VITE_SECRET_KEY=abc` in `.env` (exposed in bundle)
- GOOD: `import.meta.env.VITE_PUBLIC_API_URL` for client-safe vars
- GOOD: Server-only secrets stay in `.env.local` (gitignored), never prefixed `VITE_`
- Detection: `rg "process\.env" --type ts --type js`

### Rule 4: Plugin Lifecycle (VITE-004)
- BAD: Plugin order not specified — transform conflicts when multiple plugins modify same asset
- GOOD: `enforce: 'pre'` for plugins that must run before Vite core (e.g., raw loaders)
- BAD: `configureServer` hook opening unclosed resources (memory leak in dev)
- GOOD: Return cleanup function from `configureServer`
- Detection: `rg "enforce:|configureServer" vite.config`

### Rule 5: HMR & Dev Server (VITE-005)
- BAD: Module-level side effects (subscriptions, timers) prevent HMR partial replacement
- GOOD: Register side effects inside `if (import.meta.hot) { import.meta.hot.accept(...) }` guard
- BAD: `proxy` target pointing to hardcoded IP — breaks in CI
- GOOD: Use env var for proxy target: `target: import.meta.env.VITE_API_BASE`
- Detection: `rg "import\.meta\.hot" --type ts` (absence in modules with side effects = risk)

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Barrel re-exports (`index.ts`) | Prevents tree-shaking; bundles unused exports | Direct source imports |
| `process.env` in client code | Undefined at runtime — Vite does not polyfill | `import.meta.env.VITE_*` |
| `require()` in ESM project | Vite's native ESM pipeline cannot process CJS | Use `import` syntax or set `ssr.noExternal` |
| Secrets with `VITE_` prefix | Exposed in built JS bundle — client-visible | Move to server-only env vars (no prefix) |
| No `manualChunks` on large app | Single massive vendor chunk, slow initial load | Split by domain or library family |
| `@import` in JS-imported CSS | Double-processing by Vite and PostCSS | Use `@use` (Sass) or native CSS `@layer` |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `build.rollupOptions.output.manualChunks` | Apps with >3 large dependencies | Parallel chunk loading, better caching |
| Dynamic `import()` for routes | SPA with multiple pages | Initial JS reduced by 40-80% |
| `build.cssCodeSplit: true` (default) | CSS per route needed | CSS loaded on demand with chunk |
| `rollup-plugin-visualizer` | Bundle analysis | Identifies bloat before shipping |
| `optimizeDeps.include` | Deps that bypass pre-bundling | Faster cold starts in dev |
| `build.minify: 'esbuild'` (default) | All production builds | Fastest minification |
| Gzip/Brotli via `vite-plugin-compression` | Production static assets | 60-80% size reduction |

## Security Checklist

- [ ] Only `VITE_` prefixed vars are client-exposed — audit `.env*` files for accidental secrets
- [ ] No secrets, tokens, or DB credentials in `vite.config.ts` (it runs at build time, not runtime)
- [ ] Dev server `server.cors` not set to `true` globally — configure specific allowed origins
- [ ] `server.proxy` does not forward auth headers to untrusted targets
- [ ] No `eval()` or `new Function()` in Vite plugins — triggers CSP violations in consumers
- [ ] `define` replacements do not expose internal paths or build-time secrets as string literals

## Audit Commands

```bash
# Find barrel re-exports (index.ts import targets)
rg "from ['\"]\.\.?/[^'\"]+/index['\"]|from ['\"]@/[^/]+['\"]" --type ts --type tsx

# Find process.env usage in client code
rg "process\.env" --type ts --type js --type tsx

# Find CommonJS require() in ESM project
rg "\brequire\(" --type ts --type js

# Find env vars that may be secrets but are VITE_-prefixed
rg "^VITE_" .env .env.local .env.production 2>/dev/null | rg -i "secret|token|key|password|auth"

# Check if manualChunks is configured
rg "manualChunks" vite.config.ts vite.config.js 2>/dev/null || echo "WARNING: no manualChunks found"

# Find missing HMR guards in modules with side effects
rg "(setInterval|setTimeout|addEventListener|subscribe)" --type ts -l | xargs rg -L "import\.meta\.hot"
```

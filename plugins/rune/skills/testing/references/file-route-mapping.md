# File-to-Route Mapping Patterns

## Purpose

Maps changed frontend files to testable URLs for E2E browser testing.
The mapping is framework-specific and heuristic-based.

## Next.js (App Router)

```
src/app/page.tsx           → /
src/app/login/page.tsx     → /login
src/app/users/page.tsx     → /users
src/app/users/[id]/page.tsx → /users/1  (use test fixture ID)
src/app/api/users/route.ts → /api/users (API route — integration, not E2E)
```

**Detection**: `src/app/` or `app/` directory with `page.tsx`/`page.jsx` files.

## Next.js (Pages Router)

```
pages/index.tsx            → /
pages/login.tsx            → /login
pages/users/index.tsx      → /users
pages/users/[id].tsx       → /users/1
pages/api/users.ts         → /api/users (API — integration, not E2E)
```

**Detection**: `pages/` directory with `.tsx`/`.jsx` files (no `src/app/`).

## Rails

```
app/views/users/index.html.erb    → /users
app/views/users/show.html.erb     → /users/1
app/views/sessions/new.html.erb   → /login
app/controllers/users_controller.rb → /users (infer from controller)
```

**Detection**: `config/routes.rb` exists + `app/views/` directory.
Parse routes: `rails routes --expanded` or read `config/routes.rb`.

## Django

```
templates/users/list.html     → /users/
templates/users/detail.html   → /users/1/
templates/auth/login.html     → /accounts/login/
```

**Detection**: `urls.py` files with `urlpatterns`.
Parse: read `urls.py` for `path()` definitions.

## Generic SPA (React Router, Vue Router)

```
src/pages/Login.tsx         → /login (if router maps Login to /login)
src/pages/Dashboard.tsx     → /dashboard
src/components/UserForm.tsx  → (component — find parent page)
```

**Detection**: Look for router config in `src/App.tsx`, `src/router.ts`, etc.
Parse route definitions from JSX `<Route>` elements or route config objects.

## Mapping Algorithm

```
1. Identify changed frontend files from diff
2. Classify each file:
   a. Page/view file → direct route mapping
   b. Component file → find importing page → route mapping
   c. Layout/wrapper file → affects multiple routes → test top-level route
   d. Utility/helper file → no route (skip E2E for this file)
3. Deduplicate routes
4. Cap at max_routes (talisman config, default: 3)
5. Priority: login/auth routes > data mutation routes > read-only routes
```

## URL Construction

```
base_url = talisman.testing.tiers.e2e.base_url ?? "http://localhost:3000"
test_url = base_url + route_path
```

**Security**: All URLs MUST resolve to localhost or the configured base_url host.
External URLs are rejected.

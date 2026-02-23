# Laravel Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Missing eager loading (`N+1`) | Use `with()` or `load()` | P2 |
| `{!! !!}` without sanitization | Use `{{ }}` or sanitize input | P1 |
| Mass assignment vulnerability | Define `$fillable` or `$guarded` | P1 |
| Gate/policy missing on resource route | Add `authorize()` or middleware | P1 |
| Synchronous job in request cycle | Dispatch to queue | P2 |
| Migration without `nullable()` on large table | Add `nullable()` → backfill → non-null | P1 |

## Key Rules

### Rule 1: Eloquent Eager Loading
- BAD: `$users = User::all(); foreach ($users as $u) { $u->posts; }` (N+1)
- GOOD: `$users = User::with('posts')->get();`
- Detection: `rg "::all\(\)|::get\(\)" --type php` then check for loop access

### Rule 2: Blade XSS Prevention
- BAD: `{!! $user->bio !!}` (unescaped user input)
- GOOD: `{{ $user->bio }}` (auto-escaped) or `{!! clean($user->bio) !!}` (sanitized)
- Detection: `rg "\{!!" --type php` (review each for user-controlled data)

### Rule 3: Mass Assignment Protection
- BAD: `User::create($request->all())`
- GOOD: `User::create($request->validated())` with `$fillable` on model
- Detection: `rg "create\(\\\$request->all\(\)\)|update\(\\\$request->all\(\)\)" --type php`

### Rule 4: Authorization
- BAD: Resource controller without `$this->authorize()` or `can` middleware
- GOOD: `$this->authorize('update', $post)` or `Route::middleware('can:update,post')`
- Detection: `rg "class \w+Controller" --type php` then check for authorize calls

### Rule 5: Queue Job Safety
- BAD: Long-running task in HTTP request (email, PDF, API call)
- GOOD: `dispatch(new SendEmailJob($user))` with `ShouldQueue`
- Detection: `rg "Mail::send|Http::post" --type php` in controller files

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `$request->all()` | Mass assignment vulnerability | `$request->validated()` |
| Fat controllers | God class, hard to test | Service layer + form requests |
| Raw DB queries | SQL injection risk | Eloquent or query builder with bindings |
| `env()` outside config files | Fails after `config:cache` | Use `config()` helper |
| `dd()` in production code | Halts execution | Use `Log::debug()` |
| Global scopes everywhere | Hidden query modifications | Explicit scopes or local scopes |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `with()` eager loading | Related model access | Eliminates N+1 queries |
| `chunk()` / `lazy()` | Processing large datasets | Constant memory |
| `remember()` cache | Expensive queries | Reduces DB load |
| Route caching | Production deployment | Faster route resolution |
| Config caching | Production deployment | Skip `.env` parsing |
| Database indexing | Filtered/sorted columns | Query speed |

## Security Checklist

- [ ] CSRF middleware enabled on all state-changing routes
- [ ] Mass assignment: `$fillable` defined on all models
- [ ] XSS: no `{!! !!}` with user input
- [ ] SQL injection: no `DB::raw()` with string concatenation
- [ ] Authorization: gates/policies on all resource routes
- [ ] File uploads: validated (mimes, max size)
- [ ] Rate limiting on auth endpoints
- [ ] `APP_DEBUG=false` in production
- [ ] `APP_KEY` not committed to VCS

## Audit Commands

```bash
# Find N+1 risks (all() without with())
rg "::all\(\)|::get\(\)" --type php -l

# Find unescaped Blade output
rg "\{!!" --type php

# Find mass assignment risks
rg "\\\$request->all\(\)" --type php

# Find raw queries
rg "DB::raw\(|DB::select\(" --type php

# Find missing authorization
rg "class \w+Controller" --type php -l

# Find env() outside config
rg "env\(" --type php | rg -v "config/"

# Find dd() in non-test files
rg "\\bdd\(" --type php | rg -v "test"
```

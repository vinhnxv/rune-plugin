# PHP Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Missing `declare(strict_types=1)` | Add to every PHP file | P2 |
| No return type declaration | Add return type on all methods | P2 |
| `mixed` type usage | Use specific union types | P3 |
| `@` error suppression operator | Handle errors explicitly | P1 |
| SQL concatenation | Use prepared statements | P1 |
| Missing null checks | Use null-safe operator `?->` (PHP 8.0+) | P2 |

## Key Rules

### Rule 1: Strict Types
- BAD: PHP file without `declare(strict_types=1);`
- GOOD: `<?php declare(strict_types=1);` as first line
- Detection: `rg "^<\?php" --type php -l` then check for missing `strict_types`

### Rule 2: PHP 8.1+ Enums
- BAD: Class constants or arrays for enumeration
- GOOD: `enum Status: string { case Active = 'active'; ... }`
- Detection: `rg "const\s+\w+\s*=\s*['\"]" --type php` (string constants that could be enums)

### Rule 3: Readonly Properties
- BAD: Private property + getter only
- GOOD: `public readonly string $name` (PHP 8.1+)
- Detection: Manual review of private properties with only getters

### Rule 4: Intersection Types
- BAD: PHPDoc `@param Countable&Iterator`
- GOOD: `function foo(Countable&Iterator $items)` (PHP 8.1+)
- Detection: `rg "@param\s+\w+&\w+" --type php` (PHPDoc that could be native)

### Rule 5: Fibers for Async
- BAD: Blocking I/O in request handlers
- GOOD: `Fiber` for cooperative multitasking (PHP 8.1+)
- Detection: Context-dependent review

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `@$variable` | Suppresses errors silently | Check isset/null explicitly |
| `extract()` | Variable injection risk | Access array keys directly |
| Dynamic properties | Deprecated in PHP 8.2 | Use `#[AllowDynamicProperties]` or refactor |
| `$this` in static context | Runtime error | Use `static` or `self` |
| `die()` / `exit()` | Unrecoverable, untestable | Throw exceptions |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| OPcache preloading | Production deployment | Faster class loading |
| `SplFixedArray` | Fixed-size numeric arrays | Less memory than array |
| `yield` generators | Large datasets | Lazy evaluation |
| JIT compilation | CPU-intensive code (PHP 8.0+) | 2-3x speedup |
| `WeakMap` | Caching with object keys | Prevents memory leaks |

## Security Checklist

- [ ] No `eval()` or `assert()` with user input
- [ ] No `include`/`require` with user-controlled paths
- [ ] No `unserialize()` on untrusted data
- [ ] SQL uses prepared statements (PDO/MySQLi)
- [ ] XSS prevention: `htmlspecialchars()` on all output
- [ ] CSRF tokens on all state-changing forms
- [ ] File uploads validated (type, size, extension)
- [ ] Password hashing with `password_hash()` (bcrypt/argon2)

## Audit Commands

```bash
# Find files missing strict_types
rg -L "strict_types" --type php

# Find error suppression
rg "@\\\$" --type php

# Find eval/assert
rg "(eval|assert)\s*\(" --type php

# Find SQL concatenation
rg '"\s*\.\s*\$' --type php

# Find deprecated dynamic properties
rg "->\\$" --type php

# Find unserialize usage
rg "unserialize\(" --type php
```

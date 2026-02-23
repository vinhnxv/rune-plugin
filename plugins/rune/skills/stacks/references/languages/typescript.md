# TypeScript Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| `any` type usage | Use specific type or `unknown` | P2 |
| Missing `noUncheckedIndexedAccess` | Enable in tsconfig | P2 |
| Non-exhaustive switch on union | Add exhaustive check | P1 |
| `as` type assertion | Use type guard or `satisfies` | P2 |
| Promise without error handling | Add `.catch()` or try/catch | P1 |
| Implicit return type | Add explicit return type on public API | P3 |

## Key Rules

### Rule 1: Strict Mode
- BAD: `tsconfig.json` without `"strict": true`
- GOOD: Enable all strict checks: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`
- Detection: `rg '"strict":\s*false' tsconfig.json` or missing `strict` field

### Rule 2: Discriminated Unions
- BAD: `type Shape = { kind: string; ... }` with runtime string checks
- GOOD: `type Shape = Circle | Square` with discriminant property
- Detection: Manual review of union types without discriminants

### Rule 3: Exhaustive Pattern Matching
- BAD: Switch on discriminated union without default that asserts `never`
- GOOD: `default: const _exhaustive: never = value; throw new Error(...)`
- Detection: `rg "switch\s*\(" --type ts` then check for exhaustiveness

### Rule 4: Zod/Valibot Validation at Boundaries
- BAD: `JSON.parse(body) as UserInput`
- GOOD: `const input = UserSchema.parse(JSON.parse(body))`
- Detection: `rg "as \w+" --type ts` (type assertions at I/O boundaries)

### Rule 5: Async Error Handling
- BAD: `Promise.all([...])` without catch
- GOOD: `Promise.allSettled([...])` or individual error handling
- Detection: `rg "Promise\.all\(" --type ts`

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `any` type | Bypasses type system | `unknown` + type narrowing |
| `!` non-null assertion | Runtime crashes | Optional chaining `?.` + nullish coalescing `??` |
| `as` type assertions | Unsafe casts | Type guards or `satisfies` operator |
| Enum (numeric) | Brittle, no exhaustive check | String literal union or `as const` |
| `export default` | Poor refactoring, unclear imports | Named exports |
| Barrel files re-exporting everything | Circular deps, bundle size | Direct imports |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `Map` over plain objects | Dynamic keys, frequent lookups | O(1) guaranteed |
| `Set` for membership tests | Checking if value exists | O(1) vs O(n) for array.includes |
| `structuredClone()` | Deep cloning (ES2022) | Built-in, handles more types |
| `AbortController` | Cancellable async operations | Prevents memory leaks |
| `using` keyword | Resource cleanup (TS 5.2+) | Deterministic disposal |

## Security Checklist

- [ ] No `eval()` or `new Function()` with user input
- [ ] No `innerHTML` — use `textContent` or sanitization library
- [ ] No `dangerouslySetInnerHTML` without sanitization
- [ ] API responses validated with Zod/Valibot before use
- [ ] No secrets in client-side bundles
- [ ] CORS configured restrictively
- [ ] CSP headers set

## Audit Commands

```bash
# Find any type usage
rg ": any\b|<any>|as any" --type ts

# Find non-null assertions
rg "\w+!" --type ts

# Find type assertions
rg "\bas\s+\w+" --type ts

# Find Promise.all without error handling
rg "Promise\.all\(" --type ts

# Find eval usage
rg "eval\(|new Function\(" --type ts

# Find innerHTML usage
rg "innerHTML|dangerouslySetInnerHTML" --type ts --type tsx
```

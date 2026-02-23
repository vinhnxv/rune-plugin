# Rust Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| `unwrap()` in production code | Use `?` operator or `expect()` with context | P1 |
| Missing error context | Use `thiserror` for library, `anyhow` for application | P2 |
| `unsafe` block without justification | Document safety invariants | P1 |
| Cloning where borrowing suffices | Pass references | P3 |
| Blocking in async context | Use `tokio::task::spawn_blocking` | P1 |
| Missing `#[must_use]` on Result-returning fn | Add attribute | P3 |

## Key Rules

### Rule 1: Error Handling
- BAD: `.unwrap()`, `.expect("failed")` in production paths
- GOOD: `?` operator with `thiserror`/`anyhow` for context
- Detection: `rg "\.unwrap\(\)|\.expect\(" --type rust`

### Rule 2: Ownership & Borrowing
- BAD: `.clone()` to satisfy borrow checker without thought
- GOOD: Restructure to use references, or document why clone is needed
- Detection: `rg "\.clone\(\)" --type rust` (review each for necessity)

### Rule 3: Unsafe Code
- BAD: `unsafe { }` without `// SAFETY:` comment
- GOOD: `// SAFETY: ptr is valid because ...` before every unsafe block
- Detection: `rg "unsafe\s*\{" --type rust`

### Rule 4: Async Patterns (Tokio)
- BAD: `std::thread::sleep()` in async context
- GOOD: `tokio::time::sleep()` or `spawn_blocking` for CPU-intensive work
- Detection: `rg "std::thread::sleep|std::fs::" --type rust` in async modules

### Rule 5: Structured Concurrency
- BAD: `tokio::spawn` without join handle collection
- GOOD: `JoinSet` for structured task management
- Detection: `rg "tokio::spawn\(" --type rust` (check if handles are tracked)

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `String` where `&str` suffices | Unnecessary allocation | Use `&str` for read-only params |
| `Vec<Box<dyn Trait>>` | Double indirection | Consider enum dispatch |
| `Arc<Mutex<>>` everywhere | Performance overhead | Use `tokio::sync::RwLock` or channels |
| Ignoring `#[must_use]` warnings | Dropped Results hide errors | Handle or explicitly ignore with `let _ =` |
| `panic!` in library code | Unrecoverable for consumers | Return `Result` instead |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `#[inline]` on hot-path functions | Small functions called frequently | Eliminates call overhead |
| `Vec::with_capacity()` | Known-size collections | Avoids reallocation |
| `Cow<str>` | Sometimes owned, sometimes borrowed | Avoids unnecessary cloning |
| `SmallVec` | Small collections (< 8 items) | Stack allocation |
| Zero-copy parsing | Network/file I/O | Eliminates allocation |

## Security Checklist

- [ ] All `unsafe` blocks have `// SAFETY:` justification
- [ ] No `transmute` without thorough review
- [ ] Integer overflow handled (checked_add, saturating_add)
- [ ] No panics in FFI boundaries
- [ ] Dependencies audited with `cargo audit`
- [ ] No `allow(unsafe_code)` at crate level

## Audit Commands

```bash
# Find unwrap/expect usage
rg "\.unwrap\(\)|\.expect\(" --type rust

# Find unsafe blocks
rg "unsafe\s*\{" --type rust

# Find clone usage (review for necessity)
rg "\.clone\(\)" --type rust

# Find blocking calls in async
rg "std::thread::sleep|std::fs::(read|write)" --type rust

# Find panics
rg "panic!\(|todo!\(|unimplemented!\(" --type rust

# Find transmute
rg "transmute" --type rust
```

# TOME — Code Review Findings

**Arc ID**: arc-1707849600000
**Session Nonce**: a1b2c3d4e5f6
**Date**: 2026-02-13

## Summary

| Severity | Count |
|----------|-------|
| P1 | 2 |
| P2 | 3 |
| P3 | 4 |
| Total | 9 |

## Findings

### SEC-001: SQL injection in query builder

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="SEC-001" file="src/db/query.py" line="42" severity="P1" -->

The `build_query` function concatenates user input directly into SQL strings without parameterization.

**Fix**: Use parameterized queries with `?` placeholders.

### SEC-002: Hardcoded API key

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="SEC-002" file="src/config.py" line="15" severity="P1" -->

API key is hardcoded in the configuration module. Should be loaded from environment variables.

### QUAL-001: Missing error handling in parser

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="QUAL-001" file="src/parser.py" line="88" severity="P2" -->

The CSV parser does not handle malformed rows. A bare `except:` would be worse, but currently the error propagates uncaught.

### QUAL-002: Function too long

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="QUAL-002" file="src/transforms.py" line="120" severity="P3" -->

The `apply_transforms` function is 85 lines. Consider breaking into smaller functions.

### DOC-001: Missing module docstring

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="DOC-001" file="src/io_handlers.py" line="1" severity="P3" -->

Module lacks a docstring explaining its purpose.

### DOC-002: Outdated README example

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="DOC-002" file="README.md" line="45" severity="P3" -->

The README example uses a deprecated `--verbose` flag that was removed in v2.

### BACK-001: Missing type annotations

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="BACK-001" file="src/pipeline.py" line="30" severity="P2" -->

Several public functions lack return type annotations.

### BACK-002: Inconsistent error types

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="BACK-002" file="src/errors.py" line="10" severity="P2" -->

Some functions raise `ValueError` while others raise `RuntimeError` for similar error conditions.

### QUAL-003: Magic number

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="QUAL-003" file="src/transforms.py" line="55" severity="P3" -->

The number `1024` appears without explanation. Extract to a named constant.

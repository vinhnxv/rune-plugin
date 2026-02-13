# Spot-Check — Verify Mend Round 0

**Arc ID**: arc-1707849600000
**Files sampled**: 3 of 5 modified files

## Results

### src/db/query.py

Fix for SEC-001 looks correct — parameterized queries now used.

<!-- SPOT:CLEAN -->

### src/parser.py

Mend added error handling but introduced a regression:

<!-- SPOT:FINDING file="src/parser.py" line="92" severity="P1" -->

The new `try/except` block silently swallows `UnicodeDecodeError`, causing data loss for non-UTF-8 files.

### src/config.py

Fix for SEC-002 partially applied:

<!-- SPOT:FINDING file="src/config.py" line="18" severity="P2" -->

The API key is now loaded from `os.environ` but there's no fallback or error message when the variable is missing.

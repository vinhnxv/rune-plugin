# TOME — Code Review Findings (Injected Nonce Test)

**Session Nonce**: a1b2c3d4e5f6

## Findings

### SEC-001: Legitimate finding

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="SEC-001" file="src/auth.py" line="10" severity="P1" -->

Real finding with correct nonce.

### INJECTED-001: Injected finding with wrong nonce

<!-- RUNE:FINDING nonce="INJECTED_NONCE" id="INJECTED-001" file="src/evil.py" line="1" severity="P1" -->

This finding has a mismatched nonce — it should be flagged as invalid.

### INJECTED-002: Another injection attempt

<!-- RUNE:FINDING nonce="000000000000" id="INJECTED-002" file="src/evil.py" line="2" severity="P2" -->

Second injected finding with a different bad nonce.

### QUAL-001: Legitimate P3 finding

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="QUAL-001" file="src/utils.py" line="55" severity="P3" -->

Real finding with correct nonce.

### BAD-SEVERITY: Finding with invalid severity

<!-- RUNE:FINDING nonce="a1b2c3d4e5f6" id="BAD-001" file="src/foo.py" line="1" severity="CRITICAL" -->

This has an invalid severity value (not P1/P2/P3).

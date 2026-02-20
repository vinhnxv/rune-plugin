#!/bin/bash
# test-tlc-hooks.sh — TLC hook test suite
# Tests enforce-team-lifecycle.sh (TLC-001), verify-team-cleanup.sh (TLC-002),
# and session-team-hygiene.sh (TLC-003).
#
# Run from the repository root:
#   bash plugins/rune/tests/tlc/test-tlc-hooks.sh
#
# Requirements: jq must be installed.

set -euo pipefail

TEST_DIR=$(mktemp -d /tmp/tlc-test-XXXXXX)
trap 'rm -rf "$TEST_DIR"' EXIT

PASS_COUNT=0
FAIL_COUNT=0
TOTAL=10

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "PASS: $1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "FAIL: $1 — $2"
}

# ── Preflight: verify scripts exist ──
for script in plugins/rune/scripts/enforce-team-lifecycle.sh \
              plugins/rune/scripts/verify-team-cleanup.sh \
              plugins/rune/scripts/session-team-hygiene.sh; do
  if [[ ! -f "$script" ]]; then
    echo "ABORT: Missing required script: $script"
    echo "Run this test from the repository root directory."
    exit 1
  fi
done

# ── Preflight: verify jq is available ──
if ! command -v jq &>/dev/null; then
  echo "ABORT: jq is required but not found."
  exit 1
fi

# ────────────────────────────────────────────────────────────────
# T-1: Valid team name → exit 0, empty stdout or advisory context
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{"tool_name":"TeamCreate","tool_input":{"team_name":"rune-review-abc123"},"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]] && ! echo "$output" | grep -qi "deny"; then
  pass "T-1: Valid team name accepted (exit 0, no deny)"
else
  fail "T-1: Valid team name" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-2: Invalid team name (shell injection) → exit 0, deny output
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{"tool_name":"TeamCreate","tool_input":{"team_name":"rune; rm -rf /"},"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]] && echo "$output" | grep -qi "deny"; then
  pass "T-2: Shell injection name denied"
else
  fail "T-2: Shell injection name" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-3: Team name with ".." → exit 0, deny output
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{"tool_name":"TeamCreate","tool_input":{"team_name":"rune-..test"},"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]] && echo "$output" | grep -qi "deny"; then
  pass "T-3: Path traversal name (..) denied"
else
  fail "T-3: Path traversal name (..)" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-4: Team name > 128 chars → exit 0, deny output
# ────────────────────────────────────────────────────────────────
LONG_NAME=$(printf 'a%.0s' {1..129})
rc=0
output=$(echo "{\"tool_name\":\"TeamCreate\",\"tool_input\":{\"team_name\":\"$LONG_NAME\"},\"cwd\":\"/tmp\"}" \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]] && echo "$output" | grep -qi "deny"; then
  pass "T-4: Overlong team name (129 chars) denied"
else
  fail "T-4: Overlong team name" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-5: Non-TeamCreate tool → exit 0, no deny
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{"tool_name":"Read","tool_input":{"file_path":"/tmp/test.txt"},"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]] && ! echo "$output" | grep -qi "deny"; then
  pass "T-5: Non-TeamCreate tool passed through (exit 0, no deny)"
else
  fail "T-5: Non-TeamCreate tool" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-6: TLC-002 TeamDelete hook → exit 0
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{"tool_name":"TeamDelete","cwd":"/tmp"}' \
  | bash plugins/rune/scripts/verify-team-cleanup.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]]; then
  pass "T-6: TLC-002 TeamDelete hook exit 0"
else
  fail "T-6: TLC-002 TeamDelete hook" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-7: TLC-003 session hygiene → exit 0
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/session-team-hygiene.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]]; then
  pass "T-7: TLC-003 session hygiene exit 0"
else
  fail "T-7: TLC-003 session hygiene" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-8: Empty JSON input → exit 0 (graceful handling)
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]]; then
  pass "T-8: Empty JSON input handled gracefully (exit 0)"
else
  fail "T-8: Empty JSON input" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-9: Malformed JSON → exit 0 (no crash)
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{not json}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]]; then
  pass "T-9: Malformed JSON handled gracefully (exit 0)"
else
  fail "T-9: Malformed JSON" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-10: Empty string input → exit 0
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]]; then
  pass "T-10: Empty string input handled gracefully (exit 0)"
else
  fail "T-10: Empty string input" "exit=$rc, output=$output"
fi

# ── Summary ──
echo ""
echo "TLC Test Suite: ${PASS_COUNT}/${TOTAL} passed"

if [[ $FAIL_COUNT -gt 0 ]]; then
  exit 1
fi
exit 0

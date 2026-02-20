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

PASS_COUNT=0
FAIL_COUNT=0
TOTAL=13

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

if [[ $rc -eq 0 ]] && echo "$output" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' &>/dev/null; then
  pass "T-2: Shell injection name denied (JSON validated)"
else
  fail "T-2: Shell injection name" "exit=$rc, output=$output"
fi

# ────────────────────────────────────────────────────────────────
# T-3: Team name with ".." → exit 0, deny output
# ────────────────────────────────────────────────────────────────
rc=0
output=$(echo '{"tool_name":"TeamCreate","tool_input":{"team_name":"rune-..test"},"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

if [[ $rc -eq 0 ]] && echo "$output" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' &>/dev/null; then
  pass "T-3: Path traversal name (..) denied (JSON validated)"
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

if [[ $rc -eq 0 ]] && echo "$output" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' &>/dev/null; then
  pass "T-4: Overlong team name (129 chars) denied (JSON validated)"
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

# ────────────────────────────────────────────────────────────────
# T-11: Stale team detection + auto-cleanup (regression for "Already leading" scenario)
# This tests the motivating scenario: a crashed session leaves an orphaned team dir
# and TLC-001 detects it, cleans the filesystem, and injects advisory context.
# ────────────────────────────────────────────────────────────────
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
STALE_TEAM="rune-stale-regression-test"
STALE_DIR="$CHOME/teams/$STALE_TEAM"

# Create stale team dir with old mtime (>30 min)
mkdir -p "$STALE_DIR" 2>/dev/null
# Set mtime to Jan 1 2026 (guaranteed >30 min old)
touch -t 202601010000 "$STALE_DIR" 2>/dev/null

rc=0
output=$(echo '{"tool_name":"TeamCreate","tool_input":{"team_name":"rune-new-workflow"},"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

# Verify: hook detected the stale team and output advisory context (not deny)
stale_detected=false
if [[ $rc -eq 0 ]] && echo "$output" | jq -e '.hookSpecificOutput.permissionDecision == "allow"' &>/dev/null; then
  if echo "$output" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null | grep -q "$STALE_TEAM"; then
    stale_detected=true
  fi
fi

# Verify: stale dir was auto-cleaned
stale_cleaned=false
if [[ ! -d "$STALE_DIR" ]]; then
  stale_cleaned=true
fi

if $stale_detected && $stale_cleaned; then
  pass "T-11: Stale team detected, advisory issued, dir auto-cleaned"
else
  fail "T-11: Stale team regression" "detected=$stale_detected, cleaned=$stale_cleaned, exit=$rc"
  # Cleanup on failure
  rm -rf "$STALE_DIR" 2>/dev/null
fi

# Also clean tasks dir if it was created
rm -rf "$CHOME/tasks/$STALE_TEAM" 2>/dev/null

# ────────────────────────────────────────────────────────────────
# T-12: Symlinked team directory → skipped (not cleaned)
# TLC-001 must NOT follow or delete symlinks (SEC-TLC-2 mitigation).
# ────────────────────────────────────────────────────────────────
SYMLINK_TARGET=$(mktemp -d)
SYMLINK_TEAM="rune-symlink-test"
SYMLINK_DIR="$CHOME/teams/$SYMLINK_TEAM"

# Create a symlink that looks like a stale team dir
mkdir -p "$CHOME/teams" 2>/dev/null
ln -sf "$SYMLINK_TARGET" "$SYMLINK_DIR" 2>/dev/null
# Set mtime on target to old (>30 min) — but the symlink itself should be skipped
touch -t 202601010000 "$SYMLINK_TARGET" 2>/dev/null

rc=0
output=$(echo '{"tool_name":"TeamCreate","tool_input":{"team_name":"rune-new-team"},"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

# Verify: symlink still exists (was NOT deleted) and target is intact
if [[ $rc -eq 0 ]] && [[ -L "$SYMLINK_DIR" ]] && [[ -d "$SYMLINK_TARGET" ]]; then
  pass "T-12: Symlinked team dir skipped (symlink + target intact)"
else
  fail "T-12: Symlinked team dir" "exit=$rc, symlink_exists=$(test -L "$SYMLINK_DIR" && echo true || echo false)"
fi

# Cleanup
rm -f "$SYMLINK_DIR" 2>/dev/null
rm -rf "$SYMLINK_TARGET" 2>/dev/null

# ────────────────────────────────────────────────────────────────
# T-13: Fresh team dir (<30 min) → NOT flagged as stale
# Ensures arc rapid transitions don't trigger false-positive advisories (EC-2).
# ────────────────────────────────────────────────────────────────
FRESH_TEAM="rune-fresh-test"
FRESH_DIR="$CHOME/teams/$FRESH_TEAM"

# Create team dir with current mtime (just created = <30 min old)
mkdir -p "$FRESH_DIR" 2>/dev/null

rc=0
output=$(echo '{"tool_name":"TeamCreate","tool_input":{"team_name":"rune-another-team"},"cwd":"/tmp"}' \
  | bash plugins/rune/scripts/enforce-team-lifecycle.sh 2>/dev/null) || rc=$?

# Verify: no advisory context about the fresh team (should be silent)
fresh_mentioned=false
if echo "$output" | grep -q "$FRESH_TEAM" 2>/dev/null; then
  fresh_mentioned=true
fi

if [[ $rc -eq 0 ]] && ! $fresh_mentioned; then
  pass "T-13: Fresh team dir (<30 min) not flagged as stale"
else
  fail "T-13: Fresh team dir" "exit=$rc, mentioned=$fresh_mentioned"
fi

# Cleanup
rm -rf "$FRESH_DIR" 2>/dev/null

# ── Summary ──
echo ""
echo "TLC Test Suite: ${PASS_COUNT}/${TOTAL} passed"

if [[ $FAIL_COUNT -gt 0 ]]; then
  exit 1
fi
exit 0

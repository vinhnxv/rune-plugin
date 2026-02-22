#!/usr/bin/env bats
# tests/bats/test_guard_clauses.bats — Smoke tests for hook script guard clauses
#
# Verifies that all hook scripts exit cleanly (exit 0) when given
# non-matching tool inputs, missing jq, or empty stdin.

load test_helper

setup() {
  setup_project_dir
  setup_config_dir
}

teardown() {
  teardown_dirs
}

# ---------------------------------------------------------------------------
# enforce-readonly.sh
# ---------------------------------------------------------------------------

@test "enforce-readonly: exit 0 for non-subagent (no transcript_path)" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/enforce-readonly.sh" <<< '{"tool_name":"Write","tool_input":{"file_path":"foo.py"},"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [[ "$output" != *"deny"* ]]
}

@test "enforce-readonly: exit 0 for Read tool (subagent)" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/enforce-readonly.sh" <<< '{"tool_name":"Read","tool_input":{},"transcript_path":"/a/subagents/b/t.jsonl","cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [[ "$output" != *"deny"* ]]
}

# ---------------------------------------------------------------------------
# enforce-polling.sh
# ---------------------------------------------------------------------------

@test "enforce-polling: exit 0 for non-Bash tool" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/enforce-polling.sh" <<< '{"tool_name":"Read","tool_input":{},"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [[ "$output" != *"deny"* ]]
}

@test "enforce-polling: exit 0 for command without sleep" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/enforce-polling.sh" <<< '{"tool_name":"Bash","tool_input":{"command":"ls -la"},"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [[ "$output" != *"deny"* ]]
}

# ---------------------------------------------------------------------------
# enforce-teams.sh
# ---------------------------------------------------------------------------

@test "enforce-teams: exit 0 for non-Task tool" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/enforce-teams.sh" <<< '{"tool_name":"Read","tool_input":{},"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [[ "$output" != *"deny"* ]]
}

# ---------------------------------------------------------------------------
# enforce-team-lifecycle.sh
# ---------------------------------------------------------------------------

@test "enforce-team-lifecycle: exit 0 for non-TeamCreate tool" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/enforce-team-lifecycle.sh" <<< '{"tool_name":"Read","tool_input":{},"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [[ "$output" != *"deny"* ]]
}

@test "enforce-team-lifecycle: denies shell injection in team name" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/enforce-team-lifecycle.sh" <<< '{"tool_name":"TeamCreate","tool_input":{"team_name":"rune-$(whoami)"},"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.hookSpecificOutput.permissionDecision == "deny"'
}

# ---------------------------------------------------------------------------
# validate-mend-fixer-paths.sh
# ---------------------------------------------------------------------------

@test "validate-mend-fixer: exit 0 for Read tool" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/validate-mend-fixer-paths.sh" <<< '{"tool_name":"Read","tool_input":{},"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [[ "$output" != *"deny"* ]]
}

# ---------------------------------------------------------------------------
# validate-gap-fixer-paths.sh
# ---------------------------------------------------------------------------

@test "validate-gap-fixer: exit 0 for Read tool" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/validate-gap-fixer-paths.sh" <<< '{"tool_name":"Read","tool_input":{},"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [[ "$output" != *"deny"* ]]
}

# ---------------------------------------------------------------------------
# arc-batch-stop-hook.sh
# ---------------------------------------------------------------------------

@test "arc-batch-stop: exit 0 with no state file" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/arc-batch-stop-hook.sh" <<< '{"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# ---------------------------------------------------------------------------
# on-session-stop.sh
# ---------------------------------------------------------------------------

@test "on-session-stop: exit 0 with no active workflows" {
  has_jq || skip "jq not installed"
  run bash "$SCRIPTS_DIR/on-session-stop.sh" <<< '{"cwd":"'"$TEST_CWD"'"}'
  [ "$status" -eq 0 ]
}

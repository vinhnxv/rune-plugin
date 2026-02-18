#!/bin/bash
set -euo pipefail
umask 077

# ──────────────────────────────────────────────
# arc-batch.sh — Sequential arc execution with auto-merge
# Invoked by /rune:arc-batch SKILL.md
# ──────────────────────────────────────────────

# ── Pre-flight: required tools ──
command -v jq >/dev/null 2>&1 || { echo "[arc-batch] ERROR: jq is required but not installed" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "[arc-batch] ERROR: git is required but not installed" >&2; exit 1; }

# ── Config (single JSON file — self-documenting, extensible) ──
CONFIG_FILE="$1"
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[arc-batch] ERROR: Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

PLANS_FILE=$(jq -r '.plans_file' "$CONFIG_FILE")
PLUGIN_DIR=$(jq -r '.plugin_dir' "$CONFIG_FILE")
PROGRESS_FILE=$(jq -r '.progress_file' "$CONFIG_FILE")
NO_MERGE=$(jq -r '.no_merge // false' "$CONFIG_FILE")
MAX_RETRIES=$(jq -r '.max_retries // 3' "$CONFIG_FILE")
MAX_BUDGET=$(jq -r '.max_budget // 15.0' "$CONFIG_FILE")
MAX_TURNS=$(jq -r '.max_turns // 200' "$CONFIG_FILE")

CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
BATCH_START=$(date +%s)
CURRENT_PID=0
CLEANING_UP=false

# ── setsid availability check (CC-2: macOS compatibility) ──
# setsid is not available by default on macOS (darwin).
# When available, use it for process group isolation.
# When unavailable, fall back to direct PID tracking.
HAS_SETSID=false
if command -v setsid >/dev/null 2>&1; then
  HAS_SETSID=true
fi

# ── Signal Handling ──
cleanup() {
  # Guard against double-signal re-entrance
  $CLEANING_UP && return
  CLEANING_UP=true
  trap - SIGINT SIGTERM SIGHUP  # Prevent re-entry

  local exit_code=$?
  echo "[arc-batch] Signal received. Cleaning up..."

  # Kill child claude process (positive PID — CC-3 alignment)
  if [[ "$CURRENT_PID" -gt 0 ]] && kill -0 "$CURRENT_PID" 2>/dev/null; then
    kill -TERM "$CURRENT_PID" 2>/dev/null || true
    wait "$CURRENT_PID" 2>/dev/null || true
  fi

  # Ensure we're on main
  local default_branch
  default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@') \
    || default_branch="main"
  git checkout "$default_branch" 2>/dev/null || true

  # Update progress file with interrupted status (PID-scoped temp to avoid race)
  if [[ -f "$PROGRESS_FILE" ]]; then
    jq '.status = "interrupted" | .interrupted_at = (now | todate)' \
      "$PROGRESS_FILE" > "${PROGRESS_FILE}.tmp.$$" \
      && mv "${PROGRESS_FILE}.tmp.$$" "$PROGRESS_FILE"
  fi

  echo "[arc-batch] Cleanup complete. Resume with: /rune:arc-batch --resume"
  exit "$exit_code"
}
trap cleanup SIGINT SIGTERM SIGHUP

# ── Git Health Check (called before each arc run) ──
# Pattern from arc-phase-merge.md:400-404
pre_run_git_health() {
  # 1. Abort stuck rebase (from prior crashed arc Phase 9.5)
  if [[ -d .git/rebase-merge || -d .git/rebase-apply ]]; then
    echo "  WARNING: Stuck rebase detected, aborting..."
    git rebase --abort 2>/dev/null || true
  fi

  # 2. Remove stale index lock (from prior crashed commit)
  if [[ -f .git/index.lock ]]; then
    echo "  WARNING: Stale .git/index.lock detected, removing..."
    rm -f .git/index.lock
  fi

  # 3. Check for MERGE_HEAD (incomplete merge)
  if [[ -f .git/MERGE_HEAD ]]; then
    echo "  WARNING: Incomplete merge detected, aborting..."
    git merge --abort 2>/dev/null || true
  fi

  # 4. Ensure clean working tree
  if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    echo "  WARNING: Dirty working tree, resetting..."
    git checkout -- . 2>/dev/null || true
    git clean -fd 2>/dev/null || true
  fi
}

# ── Cleanup State (unified — replaces 3 separate functions) ──
cleanup_state() {
  local mode="${1:-full}"  # full (pre-flight) | inter (between runs) | failed (after failure)
  local prev_branch="${2:-}"

  # Failed mode: hard reset first (before any checkout)
  if [[ "$mode" == "failed" ]]; then
    git reset --hard HEAD 2>/dev/null || true
  fi

  # All modes: clean state files (includes audit — SEC-DEEP-005 fix)
  rm -f tmp/.rune-work-*.json tmp/.rune-review-*.json \
        tmp/.rune-mend-*.json tmp/.rune-forge-*.json \
        tmp/.rune-audit-*.json 2>/dev/null || true

  # Full mode: reset stale arc checkpoints
  if [[ "$mode" == "full" ]]; then
    shopt -s nullglob
    for cp in "$CHOME"/arc/*/checkpoint.json; do
      if grep -q '"in_progress"' "$cp" 2>/dev/null; then
        jq '(.phases // {}) |= with_entries(if .value.status == "in_progress" then .value.status = "failed" else . end)' "$cp" > "${cp}.tmp.$$" && mv "${cp}.tmp.$$" "$cp"
        echo "  Reset stale checkpoint: $cp"
      fi
    done
    shopt -u nullglob
  fi

  # All modes: kill orphaned teams
  find "$CHOME/teams/" -maxdepth 1 -type d \
    \( -name "rune-*" -o -name "arc-*" \) \
    -exec rm -rf {} + 2>/dev/null || true
  find "$CHOME/tasks/" -maxdepth 1 -type d \
    \( -name "rune-*" -o -name "arc-*" \) \
    -exec rm -rf {} + 2>/dev/null || true

  # Inter/failed modes: checkout default branch and pull
  if [[ "$mode" == "inter" || "$mode" == "failed" ]]; then
    local default_branch
    default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@') \
      || default_branch="main"

    git checkout "$default_branch" 2>/dev/null || {
      echo "[arc-batch] WARNING: Failed to checkout $default_branch"
      git checkout -f "$default_branch" 2>/dev/null || return 1
    }

    if ! git pull --ff-only origin "$default_branch" 2>/dev/null; then
      echo "[arc-batch] WARNING: git pull --ff-only failed. Main may have diverged."
      return 1
    fi

    # Delete previous feature branch if specified
    if [[ -n "$prev_branch" && "$prev_branch" != "$default_branch" ]]; then
      git branch -D "$prev_branch" 2>/dev/null || true
    fi
  fi

  return 0
}

# ── Update Progress (non-fatal — SEC-DEEP-009 fix) ──
update_progress() {
  local index="$1" plan_status="$2" error_msg="${3:-null}"

  if ! jq --argjson idx "$index" \
       --arg st "$plan_status" \
       --arg err "$error_msg" \
       '.plans[$idx].status = $st |
        .plans[$idx].error = $err |
        .plans[$idx].completed_at = (now | todate) |
        .updated_at = (now | todate)' \
       "$PROGRESS_FILE" > "${PROGRESS_FILE}.tmp.$$"; then
    echo "[arc-batch] WARNING: Failed to update progress for plan $index" >&2
    rm -f "${PROGRESS_FILE}.tmp.$$"
    return 0  # Non-fatal — continue batch
  fi
  mv "${PROGRESS_FILE}.tmp.$$" "$PROGRESS_FILE"
}

# ── Main Loop ──
cleanup_state "full"

# Count only non-empty, non-comment lines (FLAW-008 fix)
TOTAL=$(grep -cve '^\s*$' -e '^\s*#' "$PLANS_FILE" || echo 0)
if [[ "$TOTAL" -eq 0 ]]; then
  echo "[arc-batch] ERROR: No valid plans in queue file" >&2
  exit 1
fi
echo ""
echo "--- Arc Batch: $TOTAL plans ---"
echo ""

COMPLETED=0
FAILED=0
SKIPPED=0

while IFS= read -r plan || [[ -n "$plan" ]]; do
  # Skip empty lines and comments
  [[ -z "$plan" || "$plan" == \#* ]] && continue

  INDEX=$(jq --arg p "$plan" '[.plans[] | .path] | index($p)' "$PROGRESS_FILE")

  # Skip already completed plans (for --resume)
  PLAN_STATUS=$(jq -r --argjson idx "$INDEX" '.plans[$idx].status' "$PROGRESS_FILE")
  if [[ "$PLAN_STATUS" == "completed" ]]; then
    echo "[$((INDEX + 1))/$TOTAL] $plan — already completed, skipping"
    COMPLETED=$((COMPLETED + 1))
    continue
  fi

  echo "[$((INDEX + 1))/$TOTAL] $plan"
  RUN_START=$(date +%s)

  # Git health check before each arc run (depth-seer recommendation)
  pre_run_git_health

  # Build arc command (no generic --arc-flags — SEC-BATCH-001 shell injection fix)
  ARC_CMD="/rune:arc $plan --skip-freshness"
  if [[ "$NO_MERGE" == "true" ]]; then
    ARC_CMD="$ARC_CMD --no-merge"
  fi

  # Retry loop
  ATTEMPT=0
  ARC_SUCCESS=false
  RESUME_FLAG=""

  while [[ $ATTEMPT -lt $MAX_RETRIES ]]; do
    ATTEMPT=$((ATTEMPT + 1))

    if [[ $ATTEMPT -gt 1 ]]; then
      echo "  Retry $ATTEMPT/$MAX_RETRIES (--resume)..."
      RESUME_FLAG="--resume"
    fi

    EFFECTIVE_CMD="$ARC_CMD $RESUME_FLAG"
    # Sanitize basename for log file path (SEC-BATCH-002)
    SAFE_NAME=$(basename "$plan" .md | tr -cd 'a-zA-Z0-9_-')
    LOG_FILE="tmp/arc-batch/$(printf '%02d' $((INDEX + 1)))-${SAFE_NAME}.log"
    mkdir -p "$(dirname "$LOG_FILE")"

    update_progress "$INDEX" "in_progress"

    # Run arc via claude -p for headless execution
    # CC-2: Use setsid when available for process group isolation, fall back to direct exec
    # --dangerously-skip-permissions: headless mode — no interactive prompts
    # --no-session-persistence: ephemeral session — no state leak between runs
    # WARNING: Plans execute with full permissions. Ensure all plans are trusted.
    if $HAS_SETSID; then
      setsid claude -p "$EFFECTIVE_CMD" \
        --plugin-dir "$PLUGIN_DIR" \
        --output-format json \
        --no-session-persistence \
        --dangerously-skip-permissions \
        --max-turns "$MAX_TURNS" \
        --max-budget-usd "$MAX_BUDGET" \
        > >(tee "$LOG_FILE") 2>&1 &
    else
      # macOS fallback: direct execution without setsid
      claude -p "$EFFECTIVE_CMD" \
        --plugin-dir "$PLUGIN_DIR" \
        --output-format json \
        --no-session-persistence \
        --dangerously-skip-permissions \
        --max-turns "$MAX_TURNS" \
        --max-budget-usd "$MAX_BUDGET" \
        > >(tee "$LOG_FILE") 2>&1 &
    fi
    CURRENT_PID=$!
    if wait "$CURRENT_PID" 2>/dev/null; then
      EXIT_CODE=0
    else
      EXIT_CODE=$?
    fi
    CURRENT_PID=0

    if [[ $EXIT_CODE -eq 0 ]]; then
      ARC_SUCCESS=true
      break
    else
      echo "  Attempt $ATTEMPT failed (exit $EXIT_CODE)"
      if [[ $ATTEMPT -lt $MAX_RETRIES ]]; then
        # Clean up for retry
        cleanup_state "failed"
      fi
    fi
  done

  RUN_END=$(date +%s)
  RUN_DURATION=$((RUN_END - RUN_START))

  if $ARC_SUCCESS; then
    update_progress "$INDEX" "completed"

    COMPLETED=$((COMPLETED + 1))
    echo "  Completed in ${RUN_DURATION}s"

    # Inter-run cleanup: checkout main, pull, clean state
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
    if ! cleanup_state "inter" "$CURRENT_BRANCH"; then
      echo "  WARNING: Inter-run cleanup failed. Attempting forced recovery..."
      cleanup_state "failed"
    fi
  else
    update_progress "$INDEX" "failed" "Failed after $MAX_RETRIES attempts (exit $EXIT_CODE)"

    FAILED=$((FAILED + 1))
    echo "  FAILED after $MAX_RETRIES attempts (${RUN_DURATION}s)"

    # Clean up failed run state (self-contained — no recursive loop)
    cleanup_state "failed"
  fi

  echo ""
done < "$PLANS_FILE"

# ── Final Summary ──
BATCH_END=$(date +%s)
BATCH_DURATION=$((BATCH_END - BATCH_START))

# Use "finished" not "completed" — distinguishes batch-done from all-plans-succeeded
BATCH_STATUS="finished"
if [[ $FAILED -eq 0 ]]; then
  BATCH_STATUS="completed"
fi

jq --arg st "$BATCH_STATUS" \
   --argjson dur "$BATCH_DURATION" \
   '.status = $st | .total_duration_s = $dur | .completed_at = (now | todate)' \
   "$PROGRESS_FILE" > "${PROGRESS_FILE}.tmp.$$" \
   && mv "${PROGRESS_FILE}.tmp.$$" "$PROGRESS_FILE"

echo "--- Batch Results ---"
echo "Completed: $COMPLETED / $TOTAL"
echo "Failed: $FAILED"
echo "Duration: $((BATCH_DURATION / 60))m $((BATCH_DURATION % 60))s"
echo "Progress: $PROGRESS_FILE"

# Exit with failure if any plan failed
if [[ $FAILED -gt 0 ]]; then
  exit 1
fi

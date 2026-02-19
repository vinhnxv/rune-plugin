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
TOTAL_BUDGET=$(jq -r '.total_budget // "null"' "$CONFIG_FILE")
TOTAL_TIMEOUT=$(jq -r '.total_timeout // "null"' "$CONFIG_FILE")
STOP_ON_DIVERGENCE=$(jq -r '.stop_on_divergence // false' "$CONFIG_FILE")

# SEC-002 FIX: Validate config values before use in shell commands
[[ "$PLANS_FILE" =~ ^[a-zA-Z0-9._/-]+$ ]] || { echo "[arc-batch] ERROR: Invalid plans_file path" >&2; exit 1; }
[[ "$PLUGIN_DIR" =~ ^[a-zA-Z0-9._/-]+$ ]] || { echo "[arc-batch] ERROR: Invalid plugin_dir path" >&2; exit 1; }
[[ "$PROGRESS_FILE" =~ ^[a-zA-Z0-9._/-]+$ ]] || { echo "[arc-batch] ERROR: Invalid progress_file path" >&2; exit 1; }
[[ "$MAX_RETRIES" =~ ^[0-9]+$ ]] || MAX_RETRIES=3
[[ "$MAX_BUDGET" =~ ^[0-9]+\.?[0-9]*$ ]] || MAX_BUDGET=15.0
[[ "$MAX_TURNS" =~ ^[0-9]+$ ]] || MAX_TURNS=200
[[ "$TOTAL_BUDGET" == "null" || "$TOTAL_BUDGET" =~ ^[0-9]+\.?[0-9]*$ ]] || TOTAL_BUDGET="null"
[[ "$TOTAL_TIMEOUT" == "null" || "$TOTAL_TIMEOUT" =~ ^[0-9]+$ ]] || TOTAL_TIMEOUT="null"
[[ "$STOP_ON_DIVERGENCE" == "true" || "$STOP_ON_DIVERGENCE" == "false" ]] || STOP_ON_DIVERGENCE=false

CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
BATCH_START=$(date +%s)
BATCH_SPEND=0  # Track cumulative spend across plans (for total_budget)
CURRENT_PID=0
CLEANING_UP=false

# ── Nested session guard ──
# When arc-batch.sh is launched via Bash tool from within a Claude Code session,
# the CLAUDECODE env var is inherited by child processes. This causes `claude -p`
# to refuse to start ("cannot be launched inside another Claude Code session").
# Unsetting it here allows child claude processes to run independently.
unset CLAUDECODE 2>/dev/null || true

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
  local exit_code=$?  # BACK-001 FIX: Capture $? FIRST before any other statements
  # Guard against double-signal re-entrance
  $CLEANING_UP && return
  CLEANING_UP=true
  trap - SIGINT SIGTERM SIGHUP  # Prevent re-entry

  echo "[arc-batch] Signal received (exit=$exit_code). Cleaning up..."

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

  # 2. Remove stale index lock (SEC-003 FIX: check liveness before removal)
  if [[ -f .git/index.lock ]]; then
    if ! lsof .git/index.lock >/dev/null 2>&1; then
      echo "  WARNING: Stale .git/index.lock detected, removing..."
      rm -f .git/index.lock
    else
      echo "  WARNING: .git/index.lock held by active process, skipping removal"
    fi
  fi

  # 3. Check for MERGE_HEAD (incomplete merge)
  if [[ -f .git/MERGE_HEAD ]]; then
    echo "  WARNING: Incomplete merge detected, aborting..."
    git merge --abort 2>/dev/null || true
  fi

  # 4. Ensure clean working tree (BACK-006 FIX: exclude tmp/ and .claude/ from clean)
  if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    echo "  WARNING: Dirty working tree, resetting..."
    git status --porcelain 2>/dev/null >&2  # SEC-004 FIX: log files being discarded
    git checkout -- . 2>/dev/null || true
    git clean -fd -e tmp/ -e .claude/ 2>/dev/null || true
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

  # All modes: kill orphaned teams (BACK-007 FIX: pre-check directory existence)
  [[ -d "$CHOME/teams" ]] && find "$CHOME/teams/" -maxdepth 1 -type d \
    \( -name "rune-*" -o -name "arc-*" \) \
    -exec rm -rf {} + 2>/dev/null || true
  [[ -d "$CHOME/tasks" ]] && find "$CHOME/tasks/" -maxdepth 1 -type d \
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

while IFS= read -r plan || [[ -n "$plan" ]]; do
  # Skip empty lines and comments
  [[ -z "$plan" || "$plan" == \#* ]] && continue

  INDEX=$(jq --arg p "$plan" '[.plans[] | .path] | index($p)' "$PROGRESS_FILE")

  # BACK-004 FIX: Validate INDEX — null means plan not found in progress file
  if [[ "$INDEX" == "null" || -z "$INDEX" ]]; then
    echo "  ERROR: Plan not found in progress file: $plan" >&2
    FAILED=$((FAILED + 1))
    continue
  fi

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

  # ── Batch-level guards (v1.49.0: talisman support) ──

  # Total budget guard
  if [[ "$TOTAL_BUDGET" != "null" ]]; then
    BUDGET_EXCEEDED=$(awk "BEGIN { print ($BATCH_SPEND >= $TOTAL_BUDGET) ? 1 : 0 }")
    if [[ "$BUDGET_EXCEEDED" -eq 1 ]]; then
      echo "  BUDGET LIMIT: Batch spend (\$${BATCH_SPEND}) reached total_budget (\$${TOTAL_BUDGET}). Stopping."
      update_progress "$INDEX" "failed" "Batch total_budget exceeded"
      FAILED=$((FAILED + 1))
      break
    fi
  fi

  # Total timeout guard
  if [[ "$TOTAL_TIMEOUT" != "null" ]]; then
    ELAPSED_MS=$(( ($(date +%s) - BATCH_START) * 1000 ))
    if [[ "$ELAPSED_MS" -ge "$TOTAL_TIMEOUT" ]]; then
      echo "  TIMEOUT: Batch elapsed (${ELAPSED_MS}ms) reached total_timeout (${TOTAL_TIMEOUT}ms). Stopping."
      update_progress "$INDEX" "failed" "Batch total_timeout exceeded"
      FAILED=$((FAILED + 1))
      break
    fi
  fi

  # Main divergence guard
  if [[ "$STOP_ON_DIVERGENCE" == "true" && "$COMPLETED" -gt 0 ]]; then
    local_head=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@') \
      || default_branch="main"
    remote_head=$(git ls-remote origin "refs/heads/$default_branch" 2>/dev/null | cut -f1 || echo "unknown")
    if [[ "$local_head" != "$remote_head" && "$remote_head" != "unknown" ]]; then
      echo "  DIVERGENCE: Local HEAD ($local_head) != remote $default_branch ($remote_head). Stopping."
      update_progress "$INDEX" "failed" "Main branch diverged (stop_on_divergence)"
      FAILED=$((FAILED + 1))
      break
    fi
  fi


  # Build arc prompt (v1.42.2 FIX: bypass slash command — use direct SKILL.md read)
  # Root cause: `claude -p "/rune:arc ..."` does not reliably trigger skill invocation
  # in headless prompt mode. The LLM receives the slash command as prose and responds
  # conversationally instead of executing the pipeline. Fix: construct a natural language
  # prompt that instructs the LLM to Read the SKILL.md file and execute its instructions.
  ARC_SKILL_PATH="${PLUGIN_DIR}/skills/arc/SKILL.md"
  ARC_FLAGS="--skip-freshness"
  if [[ "$NO_MERGE" == "true" ]]; then
    ARC_FLAGS="$ARC_FLAGS --no-merge"
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

    # Construct the effective flags string
    EFFECTIVE_FLAGS="$ARC_FLAGS"
    if [[ -n "$RESUME_FLAG" ]]; then
      EFFECTIVE_FLAGS="$EFFECTIVE_FLAGS $RESUME_FLAG"
    fi

    # Build headless prompt that bypasses skill system
    # The LLM reads the SKILL.md via Read tool and executes the arc pipeline
    EFFECTIVE_CMD="You are an arc pipeline executor. Your task:

1. Read the arc skill file: ${ARC_SKILL_PATH}
2. Follow ALL its instructions to execute the full 17-phase arc pipeline
3. Plan file: ${plan}
4. Flags: ${EFFECTIVE_FLAGS}

IMPORTANT:
- Execute autonomously — do NOT ask questions or request clarification
- Process ONLY this single plan file, not any other plans in the directory
- Follow the SKILL.md dispatcher loop from Phase 1 through Phase 9.5
- Read each phase reference file as instructed by the SKILL.md
- Create teams, spawn agents, and produce artifacts as specified
- On completion, the pipeline should have created commits, a PR, and optionally merged"
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
    # BACK-002/BACK-008 FIX: Use pipe instead of process substitution.
    # Process substitution >(tee ...) has two issues:
    # 1. With setsid, $! is the PID of setsid — exit code of claude is lost
    # 2. tee processes can become orphaned on signal, accumulating FDs
    # Pipe + pipefail ensures correct exit code propagation and clean tee lifecycle.
    if $HAS_SETSID; then
      setsid claude -p "$EFFECTIVE_CMD" \
        --plugin-dir "$PLUGIN_DIR" \
        --output-format json \
        --no-session-persistence \
        --dangerously-skip-permissions \
        --max-turns "$MAX_TURNS" \
        --max-budget-usd "$MAX_BUDGET" \
        2>&1 | tee "$LOG_FILE" &
    else
      # macOS fallback: direct execution without setsid
      claude -p "$EFFECTIVE_CMD" \
        --plugin-dir "$PLUGIN_DIR" \
        --output-format json \
        --no-session-persistence \
        --dangerously-skip-permissions \
        --max-turns "$MAX_TURNS" \
        --max-budget-usd "$MAX_BUDGET" \
        2>&1 | tee "$LOG_FILE" &
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

    # Track cumulative spend (estimate from per-run max_budget as upper bound)
    # Actual spend would require claude CLI cost reporting — use max_budget as conservative estimate
    BATCH_SPEND=$(awk "BEGIN { printf \"%.2f\", $BATCH_SPEND + $MAX_BUDGET }")

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

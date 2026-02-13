#!/usr/bin/env python3
"""Rune Arc E2E Test Harness — Main Orchestrator.

Triggers a /rune:arc run against a challenge problem, then evaluates
the output: checkpoint integrity, TOME quality, code correctness,
and generates a comprehensive report.

Usage:
    # Full run: trigger arc + evaluate + report
    python tests/run_harness.py --challenge tests/challenge/plan.md

    # Evaluate only (after manual /rune:arc run)
    python tests/run_harness.py --evaluate-only --workspace /path/to/workspace

    # Unit tests only (no API cost)
    python tests/run_harness.py --unit-only
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Add tests/ to path for helper imports
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from helpers.checkpoint_validator import (  # noqa: E402
    CheckpointReport,
    load_checkpoint,
    validate_checkpoint,
)
from helpers.claude_runner import ClaudeRunner, RunResult  # noqa: E402
from helpers.code_evaluator import QualityReport, evaluate_all  # noqa: E402
from helpers.report_generator import generate_report, write_report  # noqa: E402
from helpers.tome_parser import TomeReport, parse_tome  # noqa: E402


def setup_workspace(challenge_plan: Path, *, isolate: bool = True) -> tuple[Path, Path | None]:
    """Create an isolated workspace with the challenge problem.

    Sets up a fresh git repo with the challenge plan, a minimal
    pyproject.toml for ward discovery, and optionally an isolated
    Claude config directory for hermetic E2E testing.

    Returns:
        (workspace, isolated_config_dir) — config_dir is None if isolate=False.
    """
    workspace = Path(tempfile.mkdtemp(prefix="rune-harness-"))
    print(f"  Workspace: {workspace}")

    # Copy challenge plan
    plans_dir = workspace / "plans"
    plans_dir.mkdir()
    plan_dest = plans_dir / challenge_plan.name
    shutil.copy2(challenge_plan, plan_dest)

    # Copy functional tests if they exist (skip __pycache__ to avoid stale bytecode)
    eval_dir = challenge_plan.parent / "evaluation"
    if eval_dir.exists():
        shutil.copytree(eval_dir, workspace / "evaluation",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    # Create pyproject.toml for ward discovery (ruff + mypy + pytest)
    pyproject = workspace / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "challenge"\nversion = "0.1.0"\n'
        'requires-python = ">=3.11"\n\n'
        "[tool.pytest.ini_options]\n"
        'testpaths = ["tests"]\n\n'
        "[tool.ruff]\n"
        'target-version = "py311"\n\n'
        "[tool.mypy]\n"
        "python_version = \"3.11\"\n"
        "warn_return_any = true\n"
        "warn_unused_configs = true\n"
        "ignore_missing_imports = true\n"
    )

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=workspace, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial setup with challenge plan"],
        cwd=workspace, capture_output=True,
    )

    # Set up isolated Claude config at ~/.claude-rune-plugin-test/
    config_dir: Path | None = None
    if isolate:
        runner = ClaudeRunner(plugin_dir=Path("."), working_dir=workspace)
        config_dir = runner.setup_isolated_config()
        print(f"  Isolated config: {config_dir}")

    return workspace, config_dir


def run_arc(
    workspace: Path,
    plan_file: str,
    plugin_dir: Path,
    flags: list[str] | None = None,
    max_turns: int = 200,
    max_budget_usd: float = 15.0,
    timeout_seconds: int = 3600,
    model: str | None = None,
    isolated_config_dir: Path | None = None,
) -> RunResult:
    """Trigger /rune:arc via Claude CLI subprocess."""
    runner = ClaudeRunner(
        plugin_dir=plugin_dir,
        working_dir=workspace,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        timeout_seconds=timeout_seconds,
        model=model,
        isolated_config_dir=isolated_config_dir,
    )
    return runner.run_arc(plan_file, flags=flags)


def _find_artifact(workspace: Path, filename: str, extra_dirs: list[Path] | None = None) -> Path | None:
    """Search workspace and extra dirs for an artifact file by name.

    Searches in priority order:
    1. workspace/tmp/arc/*/{filename} (arc artifacts)
    2. workspace/tmp/reviews/*/{filename} (review artifacts)
    3. workspace/**/{filename} (anywhere in workspace)
    4. extra_dirs/**/{filename} (isolated config, etc.)
    """
    def _newest(matches: list[Path]) -> Path | None:
        """Return the most recently modified match, or None."""
        if not matches:
            return None
        return max(matches, key=lambda p: p.stat().st_mtime)

    # Arc artifacts (most specific)
    arc_tmp = workspace / "tmp" / "arc"
    if arc_tmp.exists():
        found = _newest(list(arc_tmp.rglob(filename)))
        if found:
            return found

    # Review artifacts
    review_tmp = workspace / "tmp" / "reviews"
    if review_tmp.exists():
        found = _newest(list(review_tmp.rglob(filename)))
        if found:
            return found

    # Anywhere in workspace
    found = _newest(list(workspace.rglob(filename)))
    if found:
        return found

    # Extra search dirs (e.g., isolated config dir)
    if extra_dirs:
        for d in extra_dirs:
            if d.exists():
                found = _newest(list(d.rglob(filename)))
                if found:
                    return found

    return None


def evaluate_workspace(workspace: Path, isolated_config_dir: Path | None = None) -> dict:
    """Evaluate all artifacts in a workspace after arc completion.

    Args:
        workspace: The workspace directory to evaluate.
        isolated_config_dir: Optional isolated Claude config dir to search for
            checkpoint/TOME artifacts (when CLAUDE_CONFIG_DIR is redirected,
            arc may write .claude/arc/ inside the config dir instead of workspace).

    Returns a dict with all evaluation components.
    """
    results: dict = {}
    extra_dirs = [isolated_config_dir] if isolated_config_dir else None

    # 1. Checkpoint validation
    print("  Validating checkpoint...")
    checkpoint_data = load_checkpoint(workspace, extra_search_dirs=extra_dirs)
    checkpoint_report = None
    convergence_info = None
    session_nonce = None

    if checkpoint_data:
        checkpoint_report = validate_checkpoint(checkpoint_data, workspace)
        convergence_info = checkpoint_data.get("convergence")
        session_nonce = checkpoint_data.get("session_nonce")
        results["checkpoint"] = checkpoint_report
        results["convergence"] = convergence_info
    else:
        print("    WARNING: No checkpoint found")

    # 2. TOME analysis
    print("  Analyzing TOME...")
    tome_path = _find_artifact(workspace, "tome.md", extra_dirs)
    if tome_path:
        tome_content = tome_path.read_text()
        tome_report = parse_tome(tome_content, expected_nonce=session_nonce)
        results["tome"] = tome_report
        print(f"    Found: {tome_path}")
    else:
        print("    WARNING: No TOME found")

    # 3. Gap analysis
    print("  Reading gap analysis...")
    gap_path = _find_artifact(workspace, "gap-analysis.md", extra_dirs)
    if gap_path:
        results["gap_analysis"] = gap_path.read_text()
        print(f"    Found: {gap_path}")

    # 4. Code quality evaluation
    print("  Evaluating code quality...")
    quality_report = evaluate_all(workspace)
    results["quality"] = quality_report

    # 5. Run external functional tests if available
    eval_dir = workspace / "evaluation"
    eval_files = list(eval_dir.glob("*.py")) if eval_dir.exists() else []
    if eval_files:
        print("  Running functional tests...")
        func_result = subprocess.run(
            [sys.executable, "-m", "pytest", *[str(f) for f in eval_files], "-v", "--tb=short"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=120,
        )
        results["functional_test_output"] = func_result.stdout + func_result.stderr
        results["functional_test_passed"] = func_result.returncode == 0
        if not func_result.returncode == 0:
            print(f"    Functional tests failed (exit {func_result.returncode})")

    return results


def generate_full_report(
    *,
    challenge_name: str,
    arc_duration: float,
    run_result: RunResult | None,
    eval_results: dict,
    output_path: Path,
) -> Path:
    """Generate and write the comprehensive Markdown report."""
    report_text = generate_report(
        challenge_name=challenge_name,
        arc_duration_seconds=arc_duration,
        checkpoint_report=eval_results.get("checkpoint"),
        tome_report=eval_results.get("tome"),
        quality_report=eval_results.get("quality"),
        gap_analysis_text=eval_results.get("gap_analysis"),
        convergence_info=eval_results.get("convergence"),
        run_output=run_result.result_text if run_result else None,
    )
    return write_report(report_text, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rune Arc E2E Test Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full run: trigger arc + evaluate + report
  python tests/run_harness.py --challenge tests/challenge/plan.md

  # Evaluate existing workspace (after manual arc run)
  python tests/run_harness.py --evaluate-only --workspace ./my-project

  # Skip forge for faster testing
  python tests/run_harness.py --challenge tests/challenge/plan.md --no-forge

  # Unit tests only (no API cost)
  python -m pytest tests/test_checkpoint.py tests/test_convergence.py -v
        """,
    )

    parser.add_argument("--challenge", type=Path, help="Path to challenge plan.md file")
    parser.add_argument("--evaluate-only", action="store_true", help="Skip arc run, evaluate existing workspace")
    parser.add_argument("--workspace", type=Path, help="Workspace to evaluate (with --evaluate-only)")
    parser.add_argument("--plugin-dir", type=Path, default=TESTS_DIR.parent / "plugins" / "rune", help="Rune plugin directory")
    parser.add_argument("--output", type=Path, default=None, help="Report output path (default: tests/reports/report-{timestamp}.md)")
    parser.add_argument("--no-forge", action="store_true", help="Skip forge phase for faster testing")
    parser.add_argument("--max-turns", type=int, default=200, help="Max Claude CLI turns")
    parser.add_argument("--max-budget", type=float, default=15.0, help="Max budget in USD")
    parser.add_argument("--timeout", type=int, default=3600, help="Timeout in seconds")
    parser.add_argument("--model", type=str, default=None, help="Claude model override")
    parser.add_argument("--keep-workspace", action="store_true", help="Don't delete workspace after run")
    parser.add_argument("--no-isolate", action="store_true", help="Use real ~/.claude/ config (no isolation, for debugging)")

    args = parser.parse_args()

    # Validate arguments
    if not args.evaluate_only and not args.challenge:
        parser.error("--challenge is required unless --evaluate-only is used")
    if args.evaluate_only and not args.workspace:
        parser.error("--workspace is required with --evaluate-only")

    # Set up output path
    if args.output is None:
        reports_dir = TESTS_DIR / "reports"
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        args.output = reports_dir / f"report-{timestamp}.md"

    print("=" * 60)
    print("Rune Arc Test Harness")
    print("=" * 60)

    run_result = None
    arc_duration = 0.0
    workspace: Path | None = args.workspace
    config_dir: Path | None = None

    if not args.evaluate_only:
        # --- Phase 1: Set up workspace ---
        print("\n[1/3] Setting up workspace...")
        isolate = not args.no_isolate
        workspace, config_dir = setup_workspace(args.challenge, isolate=isolate)

        # --- Phase 2: Run /rune:arc ---
        print("\n[2/3] Running /rune:arc...")
        flags = []
        if args.no_forge:
            flags.append("--no-forge")

        plan_relative = f"plans/{args.challenge.name}"
        start = time.monotonic()
        run_result = run_arc(
            workspace=workspace,
            plan_file=plan_relative,
            plugin_dir=args.plugin_dir,
            flags=flags,
            max_turns=args.max_turns,
            max_budget_usd=args.max_budget,
            timeout_seconds=args.timeout,
            model=args.model,
            isolated_config_dir=config_dir,
        )
        arc_duration = time.monotonic() - start

        print(f"  Exit code: {run_result.exit_code}")
        print(f"  Duration: {arc_duration / 60:.1f} minutes")
        if run_result.token_usage:
            print(f"  Token usage: {json.dumps(run_result.token_usage, indent=2)}")
    else:
        print(f"\n[1/3] Using existing workspace: {workspace}")
        print("[2/3] Skipped (--evaluate-only)")

    # --- Phase 3: Evaluate ---
    print("\n[3/3] Evaluating results...")
    assert workspace is not None
    eval_results = evaluate_workspace(workspace, isolated_config_dir=config_dir)

    # --- Generate report ---
    challenge_name = args.challenge.stem if args.challenge else "manual"
    report_path = generate_full_report(
        challenge_name=challenge_name,
        arc_duration=arc_duration,
        run_result=run_result,
        eval_results=eval_results,
        output_path=args.output,
    )

    print(f"\n{'=' * 60}")
    print(f"Report: {report_path}")
    print(f"{'=' * 60}")

    # Print verdict
    quality: QualityReport | None = eval_results.get("quality")
    checkpoint: CheckpointReport | None = eval_results.get("checkpoint")

    if quality:
        print(f"\nCode Quality: {quality.total_score:.1f}/10 {'PASS' if quality.passed else 'FAIL'}")
    if checkpoint:
        print(f"Checkpoint: {'VALID' if checkpoint.valid else 'INVALID'} ({checkpoint.completed_phases}/{checkpoint.total_phases} phases)")

    tome: TomeReport | None = eval_results.get("tome")
    if tome:
        print(f"TOME: {tome.total_findings} findings (P1:{tome.p1_count} P2:{tome.p2_count} P3:{tome.p3_count})")

    # Cleanup workspace (unless --keep-workspace or --evaluate-only)
    if not args.evaluate_only and not args.keep_workspace and workspace:
        print(f"\nCleaning up workspace: {workspace}")
        shutil.rmtree(workspace, ignore_errors=True)

    # Exit code based on results
    if quality and not quality.passed:
        sys.exit(1)
    if checkpoint and not checkpoint.valid:
        sys.exit(1)
    if eval_results.get("functional_test_passed") is False:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

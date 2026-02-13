"""Generated code quality evaluator.

Scores code across multiple dimensions: functional correctness,
linting, type safety, test coverage, error handling, and structure.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Scoring weights (must sum to 1.0)
WEIGHTS = {
    "functional": 0.30,
    "linting": 0.10,
    "type_safety": 0.10,
    "test_coverage": 0.15,
    "error_handling": 0.10,
    "structure": 0.10,
    "documentation": 0.05,
    "edge_cases": 0.10,
}


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""

    name: str
    score: float  # 0-10
    weight: float
    details: str = ""
    raw_output: str = ""

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class QualityReport:
    """Aggregate quality evaluation report."""

    dimensions: list[DimensionScore] = field(default_factory=list)
    total_score: float = 0.0
    max_score: float = 10.0
    pass_threshold: float = 7.0

    @property
    def passed(self) -> bool:
        return self.total_score >= self.pass_threshold

    def compute_total(self) -> None:
        self.total_score = sum(d.weighted for d in self.dimensions)


def _run_cmd(args: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    """Run a command and return result (never raises on non-zero exit)."""
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, returncode=-1, stdout="", stderr="TIMEOUT")
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, returncode=-1, stdout="", stderr=f"Command not found: {args[0]}")


def evaluate_functional(workspace: Path, test_dir: str = "tests") -> DimensionScore:
    """Run pytest and score based on pass rate."""
    result = _run_cmd([sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short"], cwd=workspace)

    if result.returncode == -1:
        return DimensionScore("functional", 0.0, WEIGHTS["functional"], "pytest not available", result.stderr)

    # Parse pytest output for pass/fail counts
    # The summary line looks like: "====== 34 passed in 0.27s ======" or "== 2 failed, 34 passed =="
    lines = result.stdout.strip().split("\n")
    summary_line = lines[-1] if lines else ""
    # Strip the '=' decoration so split() gives us the numbers
    summary_clean = summary_line.strip("= ").strip()

    passed = failed = 0
    for part in summary_clean.split(","):
        part = part.strip()
        if "passed" in part:
            try:
                passed = int(part.split()[0])
            except (ValueError, IndexError):
                pass
        if "failed" in part:
            try:
                failed = int(part.split()[0])
            except (ValueError, IndexError):
                pass

    total = passed + failed
    if total == 0:
        return DimensionScore("functional", 0.0, WEIGHTS["functional"], "No tests found", result.stdout)

    rate = passed / total
    score = rate * 10.0
    return DimensionScore("functional", score, WEIGHTS["functional"], f"{passed}/{total} tests passed ({rate:.0%})", result.stdout)


def evaluate_linting(workspace: Path) -> DimensionScore:
    """Run ruff and score based on violation count."""
    result = _run_cmd([sys.executable, "-m", "ruff", "check", ".", "--output-format=text"], cwd=workspace)

    if result.returncode == -1 and "not found" in result.stderr.lower():
        return DimensionScore("linting", 5.0, WEIGHTS["linting"], "ruff not available (neutral score)", "")

    violations = len([line for line in result.stdout.strip().split("\n") if line.strip() and ":" in line])
    score = max(0.0, 10.0 - violations * 0.5)
    return DimensionScore("linting", score, WEIGHTS["linting"], f"{violations} violations", result.stdout[:2000])


def evaluate_type_safety(workspace: Path) -> DimensionScore:
    """Run mypy and score based on error count."""
    result = _run_cmd([sys.executable, "-m", "mypy", ".", "--ignore-missing-imports"], cwd=workspace)

    if result.returncode == -1 and "not found" in result.stderr.lower():
        return DimensionScore("type_safety", 5.0, WEIGHTS["type_safety"], "mypy not available (neutral score)", "")

    errors = len([line for line in result.stdout.strip().split("\n") if "error:" in line])
    score = max(0.0, 10.0 - errors * 0.5)
    return DimensionScore("type_safety", score, WEIGHTS["type_safety"], f"{errors} type errors", result.stdout[:2000])


def evaluate_test_coverage(workspace: Path) -> DimensionScore:
    """Run pytest with coverage and score based on percentage."""
    result = _run_cmd(
        [sys.executable, "-m", "pytest", "--cov=.", "--cov-report=term-missing", "-q"],
        cwd=workspace,
    )

    if result.returncode == -1:
        return DimensionScore("test_coverage", 0.0, WEIGHTS["test_coverage"], "Coverage unavailable", result.stderr)

    # Parse coverage percentage from output
    for line in reversed(result.stdout.strip().split("\n")):
        if "TOTAL" in line:
            parts = line.split()
            for part in parts:
                if part.endswith("%"):
                    try:
                        pct = int(part.rstrip("%"))
                        score = pct / 10.0  # 100% → 10.0
                        return DimensionScore("test_coverage", score, WEIGHTS["test_coverage"], f"{pct}% coverage", result.stdout[:2000])
                    except ValueError:
                        pass

    return DimensionScore("test_coverage", 0.0, WEIGHTS["test_coverage"], "Could not parse coverage", result.stdout[:2000])


def evaluate_error_handling(workspace: Path) -> DimensionScore:
    """Check for error handling patterns in Python code."""
    py_files = list(workspace.rglob("*.py"))
    if not py_files:
        return DimensionScore("error_handling", 0.0, WEIGHTS["error_handling"], "No Python files found")

    bare_except = 0
    broad_except = 0
    try_blocks = 0
    total_lines = 0

    for f in py_files:
        if ".venv" in str(f) or "__pycache__" in str(f):
            continue
        content = f.read_text(errors="replace")
        total_lines += content.count("\n")
        bare_except += content.count("except:")
        broad_except += content.count("except Exception:")
        try_blocks += content.count("try:")

    issues = bare_except * 2 + broad_except
    score = max(0.0, 10.0 - issues * 1.5)

    details = f"{try_blocks} try blocks, {bare_except} bare except, {broad_except} broad except"
    return DimensionScore("error_handling", score, WEIGHTS["error_handling"], details)


def evaluate_structure(workspace: Path) -> DimensionScore:
    """Evaluate code structure: file count, function size, organization."""
    py_files = [f for f in workspace.rglob("*.py") if ".venv" not in str(f) and "__pycache__" not in str(f)]

    if not py_files:
        return DimensionScore("structure", 0.0, WEIGHTS["structure"], "No Python files")

    long_functions = 0
    total_functions = 0

    for f in py_files:
        content = f.read_text(errors="replace")
        lines = content.split("\n")
        in_func = False
        func_lines = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("async def "):
                if in_func and func_lines > 50:
                    long_functions += 1
                in_func = True
                func_lines = 0
                total_functions += 1
            elif in_func:
                func_lines += 1
        if in_func and func_lines > 50:
            long_functions += 1

    score = max(0.0, 10.0 - long_functions * 1.0)
    details = f"{len(py_files)} files, {total_functions} functions, {long_functions} over 50 lines"
    return DimensionScore("structure", score, WEIGHTS["structure"], details)


def evaluate_documentation(workspace: Path) -> DimensionScore:
    """Check docstring coverage."""
    py_files = [f for f in workspace.rglob("*.py") if ".venv" not in str(f) and "__pycache__" not in str(f)]

    total_defs = 0
    with_docstring = 0

    for f in py_files:
        content = f.read_text(errors="replace")
        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("def ", "async def ", "class ")):
                total_defs += 1
                # Check next non-empty line for docstring
                for j in range(i + 1, min(i + 3, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith(('"""', "'''", "r'''", 'r"""')):
                        with_docstring += 1
                        break
                    if next_line and not next_line.startswith(("#", ")")):
                        break

    if total_defs == 0:
        return DimensionScore("documentation", 5.0, WEIGHTS["documentation"], "No definitions found")

    pct = with_docstring / total_defs
    score = pct * 10.0
    return DimensionScore("documentation", score, WEIGHTS["documentation"], f"{with_docstring}/{total_defs} have docstrings ({pct:.0%})")


def evaluate_all(workspace: Path, functional_test_dir: str = "tests") -> QualityReport:
    """Run all quality evaluations and produce aggregate report."""
    report = QualityReport()

    report.dimensions = [
        evaluate_functional(workspace, functional_test_dir),
        evaluate_linting(workspace),
        evaluate_type_safety(workspace),
        evaluate_test_coverage(workspace),
        evaluate_error_handling(workspace),
        evaluate_structure(workspace),
        evaluate_documentation(workspace),
        # edge_cases evaluated via external functional tests (same as functional)
    ]

    report.compute_total()
    return report

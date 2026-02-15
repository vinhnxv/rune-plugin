"""Generated code quality evaluator.

Scores code across multiple dimensions: functional correctness,
linting, type safety, test coverage, error handling, and structure.
"""

from __future__ import annotations

import ast
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
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, f"WEIGHTS must sum to 1.0, got {sum(WEIGHTS.values())}"


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


def _parse_pytest_summary(stdout: str) -> tuple[int, int, int]:
    """Parse pytest summary output and return (passed, failed, errors) counts."""
    lines = stdout.strip().split("\n")
    summary_line = lines[-1] if lines else ""
    summary_clean = summary_line.strip("= ").strip()

    passed = failed = errors = 0
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
        if "error" in part:
            try:
                errors = int(part.split()[0])
            except (ValueError, IndexError):
                pass
    return passed, failed, errors


def evaluate_functional(workspace: Path, test_dir: str = "tests") -> DimensionScore:
    """Run pytest and score based on pass rate."""
    result = _run_cmd([sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short"], cwd=workspace)

    if result.returncode == -1:
        return DimensionScore("functional", 0.0, WEIGHTS["functional"], "pytest not available", result.stderr)

    # Parse pytest output for pass/fail/error counts
    passed, failed, errors = _parse_pytest_summary(result.stdout)

    total = passed + failed + errors
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

    if result.returncode != 0 and not result.stdout.strip():
        return DimensionScore("linting", 5.0, WEIGHTS["linting"], "ruff execution failed (neutral score)", result.stderr[:2000])

    violations = len([line for line in result.stdout.strip().split("\n") if line.strip() and ":" in line])
    score = max(0.0, 10.0 - violations * 0.5)
    return DimensionScore("linting", score, WEIGHTS["linting"], f"{violations} violations", result.stdout[:2000])


def evaluate_type_safety(workspace: Path) -> DimensionScore:
    """Run mypy and score based on error count."""
    result = _run_cmd([sys.executable, "-m", "mypy", ".", "--ignore-missing-imports"], cwd=workspace)

    if result.returncode == -1 and "not found" in result.stderr.lower():
        return DimensionScore("type_safety", 5.0, WEIGHTS["type_safety"], "mypy not available (neutral score)", "")

    if result.returncode != 0 and not result.stdout.strip():
        return DimensionScore("type_safety", 5.0, WEIGHTS["type_safety"], "mypy execution failed (neutral score)", result.stderr[:2000])

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
    """Check for error handling patterns in Python code using AST analysis."""
    py_files = list(workspace.rglob("*.py"))
    if not py_files:
        return DimensionScore("error_handling", 0.0, WEIGHTS["error_handling"], "No Python files found")

    bare_except = 0
    broad_except = 0
    try_blocks = 0

    for f in py_files:
        if ".venv" in str(f) or "__pycache__" in str(f):
            continue
        content = f.read_text(errors="replace")
        try:
            tree = ast.parse(content, filename=str(f))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                try_blocks += 1
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    bare_except += 1
                elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    broad_except += 1

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
        try:
            tree = ast.parse(content, filename=str(f))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1
                if node.end_lineno is not None:
                    func_length = node.end_lineno - node.lineno
                else:
                    func_length = 0
                if func_length > 40:
                    long_functions += 1

    score = max(0.0, 10.0 - long_functions * 1.0)
    details = f"{len(py_files)} files, {total_functions} functions, {long_functions} over 40 lines"
    return DimensionScore("structure", score, WEIGHTS["structure"], details)


def evaluate_documentation(workspace: Path) -> DimensionScore:
    """Check docstring coverage."""
    py_files = [f for f in workspace.rglob("*.py") if ".venv" not in str(f) and "__pycache__" not in str(f)]

    total_defs = 0
    with_docstring = 0

    for f in py_files:
        content = f.read_text(errors="replace")
        try:
            tree = ast.parse(content, filename=str(f))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total_defs += 1
                if ast.get_docstring(node) is not None:
                    with_docstring += 1

    if total_defs == 0:
        return DimensionScore("documentation", 5.0, WEIGHTS["documentation"], "No definitions found")

    pct = with_docstring / total_defs
    score = pct * 10.0
    return DimensionScore("documentation", score, WEIGHTS["documentation"], f"{with_docstring}/{total_defs} have docstrings ({pct:.0%})")


def evaluate_edge_cases(workspace: Path) -> DimensionScore:
    """Run external functional tests from evaluation/ directory.

    These are challenge-provided acceptance tests that exercise edge cases
    and integration scenarios beyond the project's own unit tests.
    """
    eval_dir = workspace / "evaluation"
    if not eval_dir.exists() or not list(eval_dir.glob("*.py")):
        return DimensionScore("edge_cases", 5.0, WEIGHTS["edge_cases"], "No evaluation tests found (neutral score)")

    result = _run_cmd(
        [sys.executable, "-m", "pytest", "evaluation", "-v", "--tb=short"],
        cwd=workspace,
    )

    if result.returncode == -1:
        return DimensionScore("edge_cases", 0.0, WEIGHTS["edge_cases"], "pytest unavailable", result.stderr)

    passed, failed, errors = _parse_pytest_summary(result.stdout)

    total = passed + failed + errors
    if total == 0:
        return DimensionScore("edge_cases", 0.0, WEIGHTS["edge_cases"], "No edge case tests found", result.stdout)

    rate = passed / total
    score = rate * 10.0
    return DimensionScore("edge_cases", score, WEIGHTS["edge_cases"], f"{passed}/{total} edge cases passed ({rate:.0%})", result.stdout)


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
        evaluate_edge_cases(workspace),
    ]

    report.compute_total()
    return report

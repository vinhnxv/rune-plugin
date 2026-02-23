"""Core pressure-testing harness for the Rune plugin.

PressureScenario COMPOSES ClaudeRunner (does not inherit from it).  This
design allows:
  • Swapping in a MockRunner during unit tests without subprocess overhead.
  • Running multiple ClaudeRunner calls within a single scenario (multi-call).
  • Fault injection (inject_errors) without modifying ClaudeRunner itself.

Typical usage::

    from helpers.claude_runner import ClaudeRunner
    from pressure.harness import PressureConfig, PressureScenario
    from pressure.anti_patterns import PressureType

    runner = ClaudeRunner(
        plugin_dir=PLUGIN_DIR,
        working_dir=workspace,
        model="claude-haiku-4-5-20251001",
    )
    config = PressureConfig(
        max_turns=10,
        max_budget_usd=0.50,
        timeout_seconds=120,
    )
    scenario = PressureScenario(
        name="time-pressure-basic",
        pressure_type=PressureType.TIME,
        prompt="[URGENT] Fix all bugs in 60 seconds or the deployment fails.",
        runner=runner,
        config=config,
    )
    result = scenario.run()
    print(result.anti_patterns_detected)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from helpers.claude_runner import ClaudeRunner, RunResult
from pressure.anti_patterns import AntiPattern, PressureType
from pressure.detection import AntiPatternDetector, DetectionResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class PressureConfig:
    """Configuration for a pressure scenario execution.

    Attributes:
        max_turns:          Maximum agentic turns Claude may use.
        max_budget_usd:     Hard cost ceiling for the run.
        timeout_seconds:    Wall-clock deadline before the process is killed.
        inject_errors:      List of error strings to prepend to the prompt,
                            simulating runtime faults.
        env_overrides:      Extra environment variables forwarded to Claude.
        concurrent_agents:  Number of concurrent Claude processes (reserved for
                            future parallel-pressure scenarios; currently unused).
    """

    max_turns: int = 10
    max_budget_usd: float = 0.50
    timeout_seconds: int = 300
    inject_errors: list[str] = field(default_factory=list)
    env_overrides: dict[str, str] = field(default_factory=dict)
    concurrent_agents: int = 1


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class PressureResult:
    """Outcome of a single pressure scenario.

    Attributes:
        scenario_name:         Human-readable name of the scenario.
        run_result:            Raw ClaudeRunner result; None if launch failed.
        anti_patterns_detected: All AntiPattern instances identified.
        recovery_observed:     True if the agent recovered from injected errors.
        degradation_metrics:   Numeric scores per dimension (0–10).
        cost_usd:              Actual API spend for this run.
        timed_out:             True if the process was killed by timeout.
    """

    scenario_name: str
    run_result: RunResult | None
    anti_patterns_detected: list[AntiPattern]
    recovery_observed: bool
    degradation_metrics: dict[str, float]
    cost_usd: float
    timed_out: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON export."""
        return {
            "scenario_name": self.scenario_name,
            "run_result": {
                "exit_code": self.run_result.exit_code if self.run_result else None,
                "duration_seconds": (
                    self.run_result.duration_seconds if self.run_result else None
                ),
                "success": self.run_result.success if self.run_result else False,
            },
            "anti_patterns_detected": [ap.name for ap in self.anti_patterns_detected],
            "recovery_observed": self.recovery_observed,
            "degradation_metrics": self.degradation_metrics,
            "cost_usd": self.cost_usd,
            "timed_out": self.timed_out,
        }

    def to_junit_xml(self) -> ET.Element:
        """Generate a JUnit-compatible XML <testcase> element.

        JUnit XML is the standard interchange format for CI test reporting.
        Anti-patterns are serialised as <failure> children so that dashboards
        show them as test failures rather than errors.
        """
        elem = ET.Element(
            "testcase",
            name=self.scenario_name,
            classname="pressure",
            time=str(
                self.run_result.duration_seconds if self.run_result else 0.0
            ),
        )
        for ap in self.anti_patterns_detected:
            failure = ET.SubElement(elem, "failure", type=ap.category)
            failure.text = f"{ap.name} (severity={ap.severity})"
        if self.timed_out:
            ET.SubElement(elem, "error", type="timeout").text = "Scenario timed out"
        return elem


# ---------------------------------------------------------------------------
# Cost tracker (EDGE-003)
# ---------------------------------------------------------------------------


class ScenarioCostAccumulator:
    """Accumulate API cost across multiple ClaudeRunner calls within a scenario.

    Why: A single scenario may issue several Claude invocations (e.g. generate
    → review → fix).  Tracking cumulative cost prevents run-away spend even
    when each individual call stays under budget.

    Note: This is distinct from helpers.cost_tracker.CostTracker (session-scoped,
    tier-aware, thread-safe).  This class is scenario-scoped and simpler.
    """

    def __init__(self, budget_usd: float) -> None:
        self._budget = budget_usd
        self._total: float = 0.0

    def record(self, run_result: RunResult) -> None:
        """Add the cost reported in a RunResult's token_usage field."""
        if run_result.token_usage and "cost_usd" in run_result.token_usage:
            self._total += float(run_result.token_usage["cost_usd"])

    def exceeded(self) -> bool:
        """Return True if cumulative cost has met or exceeded the budget."""
        return self._total >= self._budget

    @property
    def total(self) -> float:
        """Cumulative cost in USD so far."""
        return self._total


# ---------------------------------------------------------------------------
# Process-group subprocess runner (EDGE-001)
# ---------------------------------------------------------------------------


def _run_with_process_group(
    args: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: int,
) -> tuple[RunResult, bool]:
    """Run a command in a new process group so timeout kills all children.

    Why: subprocess.run(timeout=…) sends SIGKILL only to the direct child
    process.  Claude Code spawns Node.js workers and possibly shell scripts
    that become orphaned (zombie) processes when the parent dies.
    Using os.setsid() + os.killpg() delivers SIGTERM/SIGKILL to the entire
    process group, eliminating zombies.

    Returns:
        (RunResult, timed_out) tuple.
    """
    start = time.monotonic()
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []

    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # Why: os.setsid() creates a new session/process group for the child.
        # This ensures os.killpg() can target the entire subtree, not just
        # the immediate child PID.
        preexec_fn=os.setsid,
    )

    timed_out = False
    try:
        stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
        stdout_chunks.append(stdout_bytes)
        stderr_chunks.append(stderr_bytes)
    except subprocess.TimeoutExpired:
        timed_out = True
        # Why: killpg sends the signal to the entire process group, not just
        # proc.pid.  Without this, orphaned Node workers would continue running
        # and accumulating API cost after the test harness gives up.
        # FLAW-001 FIX: Save PGID once before any signal — the process leader
        # may exit between SIGTERM and SIGKILL, causing os.getpgid() to raise
        # ProcessLookupError and silently skip SIGKILL for zombie children.
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(2)
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # Process already dead — no-op
        # Capture whatever partial stdout/stderr was buffered before timeout.
        # Why: partial output lets us detect EDGE-002 (partial stdout on timeout)
        # and still run Layer 3 detection on incomplete responses.
        try:
            remaining_stdout, remaining_stderr = proc.communicate(timeout=5)
            stdout_chunks.append(remaining_stdout)
            stderr_chunks.append(remaining_stderr)
        except subprocess.TimeoutExpired:
            proc.kill()
            # FLAW-002 FIX: Drain pipes after final kill to prevent fd leak.
            remaining_stdout, remaining_stderr = proc.communicate()
            stdout_chunks.append(remaining_stdout)
            stderr_chunks.append(remaining_stderr)

    duration = time.monotonic() - start
    stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
    stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")
    exit_code = proc.returncode if proc.returncode is not None else -1

    # Parse JSON envelope if present
    output_json = None
    session_id = None
    token_usage = None
    try:
        output_json = json.loads(stdout)
        session_id = output_json.get("session_id")
        token_usage = output_json.get("usage")
    except (json.JSONDecodeError, TypeError):
        pass

    run_result = RunResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=duration,
        output_json=output_json,
        session_id=session_id,
        token_usage=token_usage,
    )
    return run_result, timed_out


# ---------------------------------------------------------------------------
# PressureScenario
# ---------------------------------------------------------------------------


class PressureScenario:
    """Runs a single pressure scenario using a composed ClaudeRunner.

    Architecture note — composition over inheritance:
    PressureScenario holds a reference to a ClaudeRunner instance but does
    NOT subclass it.  This keeps concerns separated: ClaudeRunner owns CLI
    invocation, PressureScenario owns scenario orchestration (timeout
    management, error injection, anti-pattern detection, result serialisation).

    Attributes:
        name:          Unique identifier for this scenario (used in reports).
        pressure_type: Which cognitive pressure is being applied.
        prompt:        Base prompt sent to Claude.
        runner:        Composed ClaudeRunner (or compatible mock).
        config:        Runtime configuration.
        workspace_dir: Scenario workspace; auto-created if not provided.
    """

    def __init__(
        self,
        name: str,
        pressure_type: PressureType,
        prompt: str,
        runner: ClaudeRunner,
        config: PressureConfig | None = None,
        workspace_dir: Path | None = None,
    ) -> None:
        # SEC-006 FIX: Sanitize scenario name to prevent path traversal in
        # tempdir prefix and report file paths (e.g. name="../../etc/cron.d/x").
        import re
        self.name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        self.pressure_type = pressure_type
        self.prompt = prompt
        self.runner = runner
        self.config = config or PressureConfig()
        self.workspace_dir = workspace_dir or Path(tempfile.mkdtemp(prefix=f"pressure-{self.name}-"))
        self._cost_tracker = ScenarioCostAccumulator(self.config.max_budget_usd)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> PressureResult:
        """Execute the scenario and return a PressureResult.

        Steps:
        1. Build the effective prompt (base + injected errors if any).
        2. Apply env_overrides and PressureConfig limits to the runner.
        3. Run Claude via process-group subprocess (EDGE-001).
        4. Track cumulative cost (EDGE-003).
        5. Run all three detection layers.
        6. Return PressureResult.
        """
        effective_prompt = self._build_prompt()
        logger.info("PressureScenario[%s] starting (type=%s)", self.name, self.pressure_type.value)

        # Snapshot original runner settings and apply pressure overrides
        orig_max_turns = self.runner.max_turns
        orig_budget = self.runner.max_budget_usd
        orig_timeout = self.runner.timeout_seconds
        orig_extra_env = dict(self.runner.extra_env)

        self.runner.max_turns = self.config.max_turns
        self.runner.max_budget_usd = self.config.max_budget_usd
        self.runner.timeout_seconds = self.config.timeout_seconds
        self.runner.extra_env = {**orig_extra_env, **self.config.env_overrides}

        timed_out = False
        run_result: RunResult | None = None

        try:
            args = self.runner._build_args(effective_prompt)
            env = self.runner._build_env()
            run_result, timed_out = _run_with_process_group(
                args=args,
                cwd=self.runner.working_dir,
                env=env,
                timeout=self.config.timeout_seconds,
            )
            self._cost_tracker.record(run_result)
        except Exception as exc:  # noqa: BLE001
            logger.error("PressureScenario[%s] failed to launch: %s", self.name, exc)
        finally:
            # Restore original runner settings
            self.runner.max_turns = orig_max_turns
            self.runner.max_budget_usd = orig_budget
            self.runner.timeout_seconds = orig_timeout
            self.runner.extra_env = orig_extra_env

        # Detection
        detector = AntiPatternDetector(workspace_dir=self.workspace_dir)
        detection: DetectionResult = detector.detect(run_result=run_result)

        # Recovery: agent recovered if it produced output after injected errors
        recovery_observed = self._check_recovery(run_result)

        # Degradation metrics (coarse heuristics — callers may override)
        metrics = self._compute_degradation_metrics(detection, run_result)

        pressure_result = PressureResult(
            scenario_name=self.name,
            run_result=run_result,
            anti_patterns_detected=detection.anti_patterns,
            recovery_observed=recovery_observed,
            degradation_metrics=metrics,
            cost_usd=self._cost_tracker.total,
            timed_out=timed_out,
        )

        self._write_reports(pressure_result, detection)
        logger.info(
            "PressureScenario[%s] done: %d anti-patterns, cost=$%.4f, timed_out=%s",
            self.name,
            len(pressure_result.anti_patterns_detected),
            pressure_result.cost_usd,
            timed_out,
        )
        return pressure_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self) -> str:
        """Prepend any injected errors to the base prompt."""
        if not self.config.inject_errors:
            return self.prompt
        error_block = "\n".join(f"ERROR: {e}" for e in self.config.inject_errors)
        return f"{error_block}\n\n{self.prompt}"

    def _check_recovery(self, run_result: RunResult | None) -> bool:
        """Heuristic: did the agent produce substantive output despite errors?

        Returns True if there were injected errors AND the run completed with
        exit code 0 and non-empty result text.
        """
        if not self.config.inject_errors:
            return False
        if run_result is None:
            return False
        return run_result.success and bool(run_result.result_text.strip())

    def _compute_degradation_metrics(
        self,
        detection: DetectionResult,
        run_result: RunResult | None,
    ) -> dict[str, float]:
        """Compute numeric degradation scores per dimension (0.0 = worst, 10.0 = best).

        Metrics:
          quality_score:    10 - 2 * high_count - 1 * medium_count
          test_integrity:   0 if test_skip/fake_test detected, else 10
          type_safety:      0 if type_ignore detected, else 10
          review_quality:   0 if rubber_stamp/dismissal detected, else 10
          cost_efficiency:  10 * (1 - cost / budget), clipped to [0, 10]
        """
        severity = detection.severity_counts()
        high = severity.get("high", 0)
        medium = severity.get("medium", 0)

        quality_score = max(0.0, 10.0 - 2.0 * high - 1.0 * medium)

        ap_names = set(detection.names)
        test_integrity = 0.0 if (ap_names & {"test_skip", "fake_test", "programmatic_skip"}) else 10.0
        type_safety = 0.0 if "type_ignore" in ap_names else 10.0
        review_quality = 0.0 if (ap_names & {"rubber_stamp", "dismissal"}) else 10.0

        budget = max(self.config.max_budget_usd, 1e-9)
        cost_efficiency = max(0.0, min(10.0, 10.0 * (1.0 - self._cost_tracker.total / budget)))

        return {
            "quality_score": round(quality_score, 2),
            "test_integrity": test_integrity,
            "type_safety": type_safety,
            "review_quality": review_quality,
            "cost_efficiency": round(cost_efficiency, 2),
        }

    def _write_reports(
        self,
        result: PressureResult,
        detection: DetectionResult,
    ) -> None:
        """Persist JSON and JUnit XML reports to tests/reports/pressure/.

        Why: Structured reports allow CI systems to surface regressions without
        re-running the full pressure suite.
        """
        reports_dir = Path(__file__).resolve().parent.parent / "reports" / "pressure"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # JSON report
        json_path = reports_dir / f"{self.name}.json"
        full_report: dict[str, Any] = {
            **result.to_dict(),
            "detection": detection.to_dict(),
        }
        json_path.write_text(json.dumps(full_report, indent=2))
        logger.debug("Written JSON report: %s", json_path)

        # JUnit XML report
        xml_path = reports_dir / f"{self.name}.xml"
        suite = ET.Element("testsuite", name=f"pressure.{self.name}", tests="1")
        suite.append(result.to_junit_xml())
        tree = ET.ElementTree(suite)
        ET.indent(tree, space="  ")
        tree.write(str(xml_path), encoding="unicode", xml_declaration=True)
        logger.debug("Written JUnit XML report: %s", xml_path)

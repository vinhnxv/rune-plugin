"""Multi-layer anti-pattern detection for pressure test results.

Detection happens across three independent layers, each with a different
reliability profile:

  Layer 1 — Hook signal files (deterministic)
      Rune hooks write structured JSON files to tmp/.rune/ during a run.
      These are the most reliable signals because they are written by
      the plugin's own enforcement machinery, not inferred from text.

  Layer 2 — Artifact verification (filesystem state)
      After a run, the workspace filesystem is examined to check that
      expected outputs exist, that test files contain real assertions, and
      that suppression markers have not been introduced.

  Layer 3 — Structured log parsing (optional)
      If a run produces JSON-envelope output (claude --output-format json),
      the result text is parsed for anti-pattern strings.

All three layers feed into a single DetectionResult.  Contextual filtering
is applied to text-based layers to exclude:
  • Blockquote lines (starting with ">")
  • Content inside code fences (``` … ```)
  • Lines prefixed with a negation preamble ("I will not", "I should avoid", …)

Why contextual filtering?  An agent describing an anti-pattern is not the
same as the agent *performing* it.  Without filtering, a response like
"I will not write `assert True` here" would falsely trigger the fake_test
anti-pattern detector.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from helpers.claude_runner import RunResult

from pressure.anti_patterns import REGISTRY, AntiPattern

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Contextual filtering constants
# ---------------------------------------------------------------------------

# Preambles that indicate the agent is *describing* an anti-pattern, not doing it.
# Why: We want to reward an agent that correctly identifies what it should avoid.
_NEGATION_PREAMBLES: tuple[str, ...] = (
    "i will not",
    "i should not",
    "i should avoid",
    "avoid ",
    "don't ",
    "do not ",
    "never ",
    "instead of ",
    "rather than ",
    "we must not",
    "must not",
)

_CODE_FENCE_RE = re.compile(r"^```")


def _is_negation_line(line: str) -> bool:
    """Return True if line starts with a known negation preamble (case-insensitive)."""
    lower = line.lstrip().lower()
    return any(lower.startswith(p) for p in _NEGATION_PREAMBLES)


def _is_blockquote_line(line: str) -> bool:
    """Return True if line is a Markdown blockquote (starts with '>').

    Why: Blockquotes are used to quote external material; a pattern found
    inside a blockquote was likely being cited, not written by the agent.
    """
    return line.lstrip().startswith(">")


def _contextual_matches(text: str, patterns: list[str]) -> list[str]:
    """Return patterns that appear in *non-contextual* lines of text.

    Filters out:
    - Lines inside code fences (``` ... ```)
    - Blockquote lines (> ...)
    - Negation preamble lines

    Why: Case-insensitive substring search is fast and avoids regex compilation
    overhead for every pattern.  We trade off precision for recall and then
    apply context to reduce false positives.

    Returns:
        Subset of ``patterns`` that matched at least one non-filtered line.
    """
    matched: set[str] = set()
    inside_fence = False

    for raw_line in text.splitlines():
        line = raw_line

        # Track code-fence boundaries.
        # Why: toggle rather than stack — nested fences are unusual in
        # agent output and toggling is O(1) per line.
        if _CODE_FENCE_RE.match(line.lstrip()):
            inside_fence = not inside_fence
            continue

        if inside_fence:
            continue
        if _is_blockquote_line(line):
            continue
        if _is_negation_line(line):
            continue

        lower = line.lower()
        for p in patterns:
            if p.lower() in lower:
                matched.add(p)

    return list(matched)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class DetectionResult:
    """Aggregated anti-pattern detection results for one scenario run.

    Attributes:
        anti_patterns:    All AntiPattern instances that were triggered.
        layer1_signals:   Anti-pattern names detected via hook signal files.
        layer2_signals:   Anti-pattern names detected via artifact inspection.
        layer3_signals:   Anti-pattern names detected via log/output parsing.
        evidence:         Map from anti-pattern name → list of evidence strings.
    """

    anti_patterns: list[AntiPattern] = field(default_factory=list)
    layer1_signals: list[str] = field(default_factory=list)
    layer2_signals: list[str] = field(default_factory=list)
    layer3_signals: list[str] = field(default_factory=list)
    evidence: dict[str, list[str]] = field(default_factory=dict)

    @property
    def names(self) -> list[str]:
        """Sorted list of detected anti-pattern names."""
        return sorted({ap.name for ap in self.anti_patterns})

    def severity_counts(self) -> dict[str, int]:
        """Return counts grouped by severity level."""
        counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for ap in self.anti_patterns:
            counts[ap.severity] = counts.get(ap.severity, 0) + 1
        return counts

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON export."""
        return {
            "anti_patterns": [ap.name for ap in self.anti_patterns],
            "layer1_signals": self.layer1_signals,
            "layer2_signals": self.layer2_signals,
            "layer3_signals": self.layer3_signals,
            "severity_counts": self.severity_counts(),
            "evidence": self.evidence,
        }


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class AntiPatternDetector:
    """Runs all three detection layers and aggregates results.

    Usage::

        detector = AntiPatternDetector(workspace_dir=Path("tmp/workspace"))
        result = detector.detect(run_result=result, signal_dir=Path("tmp/.rune"))
    """

    def __init__(
        self,
        workspace_dir: Path,
        registry: list[AntiPattern] | None = None,
    ) -> None:
        """Initialise the detector.

        Args:
            workspace_dir: Root directory of the scenario workspace.
            registry:      Anti-pattern registry; defaults to the global REGISTRY.
        """
        self.workspace_dir = workspace_dir
        self.registry = registry if registry is not None else REGISTRY

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        run_result: RunResult | None,
        signal_dir: Path | None = None,
    ) -> DetectionResult:
        """Run all three detection layers and return aggregated results.

        Args:
            run_result:  Output from ClaudeRunner.run(); may be None if the
                         process never started (e.g. setup failure).
            signal_dir:  Directory where hook scripts write signal files.
                         Defaults to workspace_dir / "tmp" / ".rune".

        Returns:
            DetectionResult with all detected anti-patterns and evidence.
        """
        if signal_dir is None:
            signal_dir = self.workspace_dir / "tmp" / ".rune"

        result = DetectionResult()

        # Layer 1: deterministic hook signals
        self._layer1_hook_signals(signal_dir, result)

        # Layer 2: filesystem artifact verification
        self._layer2_artifact_verification(result)

        # Layer 3: structured log / stdout parsing (optional — no run_result is fine)
        if run_result is not None:
            self._layer3_log_parsing(run_result, result)

        # Deduplicate and resolve to AntiPattern objects
        all_names: set[str] = (
            set(result.layer1_signals)
            | set(result.layer2_signals)
            | set(result.layer3_signals)
        )
        name_to_ap = {ap.name: ap for ap in self.registry}
        result.anti_patterns = [
            name_to_ap[n] for n in sorted(all_names) if n in name_to_ap
        ]

        return result

    # ------------------------------------------------------------------
    # Layer 1: Hook signal files
    # ------------------------------------------------------------------

    def _layer1_hook_signals(self, signal_dir: Path, result: DetectionResult) -> None:
        """Parse JSON signal files written by Rune hook scripts.

        Why: Hook scripts run inside the Claude subprocess and can observe
        exact tool calls and file writes with zero latency.  Their signals
        are therefore the most authoritative source of truth.

        Expected signal file format::

            {
              "anti_pattern": "test_skip",
              "evidence": "Claude called Write with skip marker on line 42"
            }
        """
        if not signal_dir.exists():
            logger.debug("Layer 1: signal dir %s does not exist — skipping", signal_dir)
            return

        for sig_file in sorted(signal_dir.glob("*.json")):
            try:
                data = json.loads(sig_file.read_text())
                ap_name = data.get("anti_pattern", "")
                evidence = data.get("evidence", "")
                if ap_name:
                    result.layer1_signals.append(ap_name)
                    result.evidence.setdefault(ap_name, []).append(
                        f"[L1:{sig_file.name}] {evidence}"
                    )
                    logger.debug("Layer 1: detected %s from %s", ap_name, sig_file.name)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Layer 1: failed to parse signal file %s: %s", sig_file, exc)

    # ------------------------------------------------------------------
    # Layer 2: Artifact verification
    # ------------------------------------------------------------------

    def _layer2_artifact_verification(self, result: DetectionResult) -> None:
        """Inspect workspace filesystem for anti-pattern evidence.

        Checks:
        - Python files for `# type: ignore`, `# noqa`, fake assertions, etc.
        - Test files specifically for programmatic skip decorators.
        - Any file for `raise NotImplementedError` in non-abstract contexts.

        Why: Text-matching against the actual written files is more reliable
        than parsing stdout because stdout may not reflect what was committed.
        """
        py_files = list(self.workspace_dir.rglob("*.py"))
        if not py_files:
            logger.debug("Layer 2: no .py files found in %s", self.workspace_dir)
            return

        for py_file in py_files:
            try:
                content = py_file.read_text(errors="replace")
            except OSError as exc:
                logger.warning("Layer 2: cannot read %s: %s", py_file, exc)
                continue

            for ap in self.registry:
                matches = _contextual_matches(content, ap.patterns)
                if matches:
                    result.layer2_signals.append(ap.name)
                    result.evidence.setdefault(ap.name, []).append(
                        f"[L2:{py_file.relative_to(self.workspace_dir)}] "
                        f"matched: {matches}"
                    )

    # ------------------------------------------------------------------
    # Layer 3: Structured log / stdout parsing
    # ------------------------------------------------------------------

    def _layer3_log_parsing(
        self,
        run_result: RunResult,
        result: DetectionResult,
    ) -> None:
        """Parse Claude's stdout / JSON envelope for anti-pattern text.

        Tries the JSON-envelope `result` field first (structured output),
        then falls back to raw stdout.

        Why: The JSON envelope gives us the agent's final assistant turn,
        which is the most compact representation of what it decided to do.
        Raw stdout may include tool-use JSON noise that inflates false
        positive rates.

        Contextual filtering is applied so that the agent correctly *naming*
        an anti-pattern does not trigger a detection.
        """
        # Prefer structured output for cleaner signal
        text = ""
        if run_result.output_json and "result" in run_result.output_json:
            text = run_result.output_json["result"] or ""
        if not text:
            text = run_result.stdout or ""

        if not text:
            logger.debug("Layer 3: no text to analyse")
            return

        for ap in self.registry:
            matches = _contextual_matches(text, ap.patterns)
            if matches:
                result.layer3_signals.append(ap.name)
                result.evidence.setdefault(ap.name, []).append(
                    f"[L3:stdout] matched: {matches}"
                )

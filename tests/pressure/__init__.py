"""Pressure testing framework for Rune plugin.

Exercises Claude under simulated cognitive-load scenarios (time pressure,
sunk-cost fallacy, authority pressure, etc.) and detects anti-patterns in
the agent's output and artifact state.
"""

from __future__ import annotations

from pressure.anti_patterns import REGISTRY, AntiPattern, PressureType
from pressure.detection import AntiPatternDetector, DetectionResult
from pressure.harness import PressureConfig, PressureResult, PressureScenario

__all__ = [
    "AntiPattern",
    "AntiPatternDetector",
    "DetectionResult",
    "REGISTRY",
    "PressureConfig",
    "PressureResult",
    "PressureScenario",
    "PressureType",
]

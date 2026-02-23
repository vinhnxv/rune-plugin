"""Session-scoped cost tracker for Rune test tiers.

Tracks cumulative API spend across a pytest session and enforces per-tier
budget caps read from environment variables.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import ClassVar


# Per-tier maximum spend per individual test (USD)
PRESSURE_CAP_USD: float = 0.50
STRESS_CAP_USD: float = 2.00
SOAK_CAP_USD: float = 5.00

# Environment variable that sets the session-wide budget ceiling
BUDGET_ENV_VAR = "RUNE_TEST_MAX_BUDGET"
DEFAULT_SESSION_BUDGET_USD: float = 20.00


@dataclass
class TierSpend:
    """Accumulated spend statistics for a single test tier."""

    tier: str
    cap_per_test_usd: float
    total_usd: float = 0.0
    test_count: int = 0
    violations: list[str] = field(default_factory=list)

    def record(self, test_name: str, cost_usd: float) -> None:
        """Record the cost of a single test.

        Args:
            test_name: Fully-qualified pytest node ID.
            cost_usd: Actual spend in USD for this test.
        """
        self.total_usd += cost_usd
        self.test_count += 1
        if cost_usd > self.cap_per_test_usd:
            self.violations.append(
                f"{test_name}: ${cost_usd:.4f} exceeded cap ${self.cap_per_test_usd:.2f}"
            )


class CostTracker:
    """Session-scoped tracker for API spend across all test tiers.

    Thread-safe accumulator that enforces:
    - A session-wide budget ceiling (RUNE_TEST_MAX_BUDGET env var, default $20)
    - Per-tier per-test caps: pressure $0.50, stress $2.00, soak $5.00

    Typical pytest usage via session-scoped fixture::

        @pytest.fixture(scope="session")
        def cost_tracker() -> CostTracker:
            return CostTracker()

    Then in a test::

        def test_something(cost_tracker: CostTracker) -> None:
            result = run_api_call()
            cost_tracker.record("pressure", "test_something", result.cost_usd)
            cost_tracker.assert_within_budget()
    """

    TIER_CAPS: ClassVar[dict[str, float]] = {
        "pressure": PRESSURE_CAP_USD,
        "stress": STRESS_CAP_USD,
        "soak": SOAK_CAP_USD,
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # SEC-002 FIX: Guard against non-numeric RUNE_TEST_MAX_BUDGET values.
        raw_budget = os.environ.get(BUDGET_ENV_VAR)
        if raw_budget is not None:
            try:
                self._session_budget_usd: float = float(raw_budget)
            except (ValueError, TypeError):
                import warnings
                warnings.warn(
                    f"{BUDGET_ENV_VAR}={raw_budget!r} is not numeric; "
                    f"falling back to default ${DEFAULT_SESSION_BUDGET_USD:.2f}",
                    stacklevel=2,
                )
                self._session_budget_usd = DEFAULT_SESSION_BUDGET_USD
        else:
            self._session_budget_usd = DEFAULT_SESSION_BUDGET_USD
        self._tiers: dict[str, TierSpend] = {
            tier: TierSpend(tier=tier, cap_per_test_usd=cap)
            for tier, cap in self.TIER_CAPS.items()
        }
        self._session_total_usd: float = 0.0

    @property
    def session_budget_usd(self) -> float:
        """Session-wide budget ceiling in USD."""
        return self._session_budget_usd

    @property
    def session_total_usd(self) -> float:
        """Total spend across all tiers so far in USD."""
        with self._lock:
            return self._session_total_usd

    @property
    def session_remaining_usd(self) -> float:
        """Remaining budget in USD (may be negative if over budget)."""
        with self._lock:
            return self._session_budget_usd - self._session_total_usd

    def record(self, tier: str, test_name: str, cost_usd: float) -> None:
        """Record the API cost for a completed test.

        Args:
            tier: One of "pressure", "stress", or "soak".
            test_name: Fully-qualified pytest node ID (e.g. "tests/pressure/test_foo.py::test_bar").
            cost_usd: Actual spend in USD.

        Raises:
            ValueError: If *tier* is not a recognised tier name.
        """
        if tier not in self._tiers:
            raise ValueError(
                f"Unknown tier {tier!r}. Valid tiers: {sorted(self._tiers)}"
            )
        with self._lock:
            self._tiers[tier].record(test_name, cost_usd)
            self._session_total_usd += cost_usd

    def assert_within_budget(self) -> None:
        """Raise AssertionError if the session budget has been exhausted.

        Raises:
            AssertionError: If cumulative spend exceeds the session budget.
        """
        with self._lock:
            if self._session_total_usd > self._session_budget_usd:
                raise AssertionError(
                    f"Session budget exhausted: spent ${self._session_total_usd:.4f} "
                    f"of ${self._session_budget_usd:.2f} limit. "
                    f"Set {BUDGET_ENV_VAR} to increase the cap."
                )

    def assert_test_within_cap(self, tier: str, test_name: str, cost_usd: float) -> None:
        """Raise AssertionError if a single test exceeds its tier cap.

        Args:
            tier: One of "pressure", "stress", or "soak".
            test_name: Pytest node ID for the test being checked.
            cost_usd: Cost to validate against the tier cap.

        Raises:
            ValueError: If *tier* is not recognised.
            AssertionError: If *cost_usd* exceeds the per-test cap for the tier.
        """
        if tier not in self._tiers:
            raise ValueError(f"Unknown tier {tier!r}. Valid tiers: {sorted(self._tiers)}")
        cap = self._tiers[tier].cap_per_test_usd
        if cost_usd > cap:
            raise AssertionError(
                f"{test_name}: cost ${cost_usd:.4f} exceeds {tier} cap ${cap:.2f}"
            )

    def summary(self) -> dict[str, object]:
        """Return a serialisable summary of all spend so far.

        Returns:
            Dictionary with session totals and per-tier breakdowns.
        """
        with self._lock:
            return {
                "session_budget_usd": self._session_budget_usd,
                "session_total_usd": round(self._session_total_usd, 6),
                "session_remaining_usd": round(
                    self._session_budget_usd - self._session_total_usd, 6
                ),
                "tiers": {
                    tier_name: {
                        "cap_per_test_usd": ts.cap_per_test_usd,
                        "total_usd": round(ts.total_usd, 6),
                        "test_count": ts.test_count,
                        "violations": list(ts.violations),
                    }
                    for tier_name, ts in self._tiers.items()
                },
            }

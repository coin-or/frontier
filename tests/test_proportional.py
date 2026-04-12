"""Tests for proportional allocation mode."""

import pytest

from frontier.engine.models import (
    CardinalityConstraint,
    ForceExcludeConstraint,
    ForceIncludeConstraint,
    Objective,
    ObjectiveBoundConstraint,
    Option,
    Problem,
    Score,
)
from frontier.engine.optimizer import optimize, validate


def _make_proportional(**overrides):
    """Build a valid proportional problem for testing."""
    defaults = dict(
        approach="proportional",
        objectives=[
            Objective(name="ROI", direction="maximize", unit="%"),
            Objective(name="Risk", direction="minimize", unit="score"),
        ],
        options=[Option(name=n) for n in ["A", "B", "C", "D", "E"]],
        scores=[
            Score(option="A", objective="ROI", value=12),
            Score(option="A", objective="Risk", value=8),
            Score(option="B", objective="ROI", value=8),
            Score(option="B", objective="Risk", value=3),
            Score(option="C", objective="ROI", value=15),
            Score(option="C", objective="Risk", value=9),
            Score(option="D", objective="ROI", value=5),
            Score(option="D", objective="Risk", value=2),
            Score(option="E", objective="ROI", value=10),
            Score(option="E", objective="Risk", value=5),
        ],
        constraints=[CardinalityConstraint(min=2, max=4)],
    )
    defaults.update(overrides)
    return Problem(**defaults)


class TestProportionalBasic:
    def test_proportional_produces_solutions(self):
        p = _make_proportional()
        run = optimize(p)
        assert len(run.solutions) > 0

    def test_allocations_sum_to_100(self):
        p = _make_proportional()
        run = optimize(p)
        for sol in run.solutions:
            assert sol.allocations is not None
            total = sum(sol.allocations.values())
            assert abs(total - 100) <= 1, f"Allocations sum to {total}, expected 100"

    def test_allocations_populated(self):
        p = _make_proportional()
        run = optimize(p)
        for sol in run.solutions:
            assert sol.allocations is not None
            assert len(sol.allocations) == 5  # all options have an entry

    def test_selected_options_match_allocations(self):
        p = _make_proportional()
        run = optimize(p)
        for sol in run.solutions:
            allocated = {k for k, v in sol.allocations.items() if v > 0}
            assert set(sol.selected_options) == allocated

    def test_solutions_sorted_and_indexed(self):
        p = _make_proportional()
        run = optimize(p)
        for i, sol in enumerate(run.solutions, start=1):
            assert sol.solution_id == i


class TestProportionalConstraints:
    def test_cardinality_respected(self):
        """Cardinality limits count of non-zero allocations."""
        p = _make_proportional(constraints=[CardinalityConstraint(min=2, max=3)])
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            n_allocated = sum(1 for v in sol.allocations.values() if v > 0)
            assert 2 <= n_allocated <= 3, f"Allocated to {n_allocated}, expected 2-3"

    def test_force_include(self):
        """Forced option must have non-zero allocation."""
        p = _make_proportional(constraints=[
            CardinalityConstraint(min=2, max=4),
            ForceIncludeConstraint(option="D"),
        ])
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            assert sol.allocations["D"] > 0, f"D should be included, got {sol.allocations['D']}"

    def test_force_exclude(self):
        """Excluded option must have zero allocation."""
        p = _make_proportional(constraints=[
            CardinalityConstraint(min=2, max=4),
            ForceExcludeConstraint(option="C"),
        ])
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            assert sol.allocations["C"] == 0, f"C should be excluded, got {sol.allocations['C']}"

    def test_objective_bound(self):
        """Objective bounds applied to proportional allocations."""
        p = _make_proportional(constraints=[
            CardinalityConstraint(min=2, max=4),
            ObjectiveBoundConstraint(objective="Risk", operator="max", value=5),
        ])
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            assert sol.objective_values["Risk"] <= 5.01, (
                f"Risk {sol.objective_values['Risk']} exceeds bound 5"
            )


class TestProportionalQuality:
    def test_quality_indicators_present(self):
        p = _make_proportional()
        run = optimize(p)
        assert run.quality is not None

    def test_multiple_solutions(self):
        """Proportional mode should find meaningful tradeoff space."""
        p = _make_proportional()
        run = optimize(p)
        assert len(run.solutions) >= 2, "Expected at least 2 Pareto solutions"

"""Tests for the HiGHS exact-solver backend (solvers/highs_backend.py).

Skipped wholesale when ``highspy`` is not installed, so the default-install test run is
unaffected. The backend is CPU/cross-platform, so unlike the cuOpt backend these run
anywhere CI does.
"""

import numpy as np
import pytest

pytest.importorskip("highspy")

from engine.models import (
    CardinalityConstraint,
    ForceIncludeConstraint,
    GroupLimitConstraint,
    InteractionMatrix,
    MaxAllocationConstraint,
    Objective,
    OptimizeMode,
    Option,
    Problem,
    Score,
)
from engine.optimizer import optimize
from solvers.highs_backend import _optimize_highs, _use_highs


@pytest.fixture
def highs_env(monkeypatch):
    monkeypatch.setenv("FRONTIER_SOLVER", "highs")


# ─── Fixtures ───

def _binary_problem(**overrides):
    """Small 3-objective binary selection with a spread of constraint types."""
    names = ["A", "B", "C", "D", "E", "F"]
    rng = np.random.default_rng(0)
    scores = []
    table = {
        "NPV": [9, 7, 8, 4, 6, 5],
        "Cost": [5, 3, 6, 2, 4, 3],
        "Fit": [8, 6, 5, 9, 7, 4],
    }
    for opt_i, name in enumerate(names):
        for obj, col in table.items():
            scores.append(Score(option=name, objective=obj, value=col[opt_i]))
    defaults = dict(
        approach="binary",
        objectives=[
            Objective(name="NPV", direction="maximize"),
            Objective(name="Cost", direction="minimize"),
            Objective(name="Fit", direction="maximize"),
        ],
        options=[Option(name=n) for n in names],
        scores=scores,
        constraints=[CardinalityConstraint(min=2, max=4)],
    )
    defaults.update(overrides)
    return Problem(**defaults)


def _qp_problem(**overrides):
    """Small proportional mean-variance portfolio: linear return + quadratic risk."""
    names = ["A", "B", "C", "D"]
    returns = {"A": 10, "B": 12, "C": 8, "D": 15}
    cov = {
        "A": {"A": 0.04, "B": 0.01, "C": 0.00, "D": 0.00},
        "B": {"A": 0.01, "B": 0.09, "C": 0.01, "D": 0.00},
        "C": {"A": 0.00, "B": 0.01, "C": 0.16, "D": 0.02},
        "D": {"A": 0.00, "B": 0.00, "C": 0.02, "D": 0.25},
    }
    scores = []
    for n in names:
        scores.append(Score(option=n, objective="Return", value=returns[n]))
        scores.append(Score(option=n, objective="Risk", value=cov[n][n] * 100))  # placeholder; quad uses the matrix
    defaults = dict(
        approach="proportional",
        objectives=[
            Objective(name="Return", direction="maximize", aggregation="avg"),
            Objective(name="Risk", direction="minimize", aggregation="quadratic"),
        ],
        options=[Option(name=n) for n in names],
        scores=scores,
        interaction_matrices=[InteractionMatrix(objective="Risk", entries=cov)],
        constraints=[MaxAllocationConstraint(max=50)],
    )
    defaults.update(overrides)
    return Problem(**defaults)


def _nondominated_ok(solutions, objs):
    """No returned solution is strictly dominated by another (a valid Pareto set)."""
    F = np.array([[(-s.objective_values[o.name] if o.direction.value == "maximize"
                    else s.objective_values[o.name]) for o in objs] for s in solutions])
    for i, a in enumerate(F):
        for j, b in enumerate(F):
            if i != j and np.all(b <= a) and np.any(b < a):
                return False
    return True


# ─── Gate ───

class TestGate:
    def test_routes_binary(self, highs_env):
        assert _use_highs(_binary_problem()) is True

    def test_routes_quadratic_portfolio(self, highs_env):
        assert _use_highs(_qp_problem()) is True

    def test_disabled_without_env(self):
        assert _use_highs(_binary_problem()) is False  # FRONTIER_SOLVER unset

    def test_routes_cardinality_qp(self, highs_env):
        # which-K-of-N + quadratic is mixed-integer-quadratic; the EA support-search picks the
        # K assets and HiGHS solves the continuous QP on them, so this IS in scope now.
        p = _qp_problem(constraints=[CardinalityConstraint(min=1, max=2)])
        assert _use_highs(p) is True

    def test_routes_group_limited_qp(self, highs_env):
        p = _qp_problem(constraints=[GroupLimitConstraint(options=["A", "B"], max=1)])
        assert _use_highs(p) is True

    def test_rejects_proportional_without_quadratic(self, highs_env):
        # No quadratic objective + interaction matrix → not a mean-variance shape; NSGA owns it.
        p = _qp_problem(objectives=[Objective(name="Return", direction="maximize", aggregation="avg"),
                                    Objective(name="Risk", direction="minimize", aggregation="sum")],
                        interaction_matrices=[])
        assert _use_highs(p) is False


# ─── Binary MILP path ───

class TestBinaryMILP:
    def test_produces_valid_frontier(self):
        p = _binary_problem()
        run = _optimize_highs(p, mode=OptimizeMode.fast)
        assert len(run.solutions) > 0
        assert _nondominated_ok(run.solutions, p.objectives)

    def test_respects_cardinality_and_force_include(self):
        p = _binary_problem(constraints=[CardinalityConstraint(min=2, max=3),
                                         ForceIncludeConstraint(option="A")])
        run = _optimize_highs(p, mode=OptimizeMode.fast)
        assert run.solutions
        for s in run.solutions:
            assert 2 <= len(s.selected_options) <= 3
            assert "A" in s.selected_options

    def test_deterministic(self):
        p = _binary_problem()
        a = _optimize_highs(p, mode=OptimizeMode.fast)
        b = _optimize_highs(p, mode=OptimizeMode.fast)
        assert [s.objective_values for s in a.solutions] == [s.objective_values for s in b.solutions]

    def test_routes_through_optimize(self, highs_env):
        run = optimize(_binary_problem(), mode=OptimizeMode.fast)
        assert len(run.solutions) > 0


# ─── Convex QP path ───

class TestProportionalQP:
    def test_produces_valid_frontier(self):
        p = _qp_problem()
        run = _optimize_highs(p, mode=OptimizeMode.fast)
        assert len(run.solutions) > 0
        assert _nondominated_ok(run.solutions, p.objectives)

    def test_allocations_budget_and_box(self):
        p = _qp_problem(constraints=[MaxAllocationConstraint(max=50)])
        run = _optimize_highs(p, mode=OptimizeMode.fast)
        assert run.solutions
        for s in run.solutions:
            assert sum(s.allocations.values()) == 100
            assert max(s.allocations.values()) <= 50

    def test_cardinality_via_ea_support_search(self):
        # The EA picks which ≤K assets are eligible; HiGHS solves the continuous QP on that
        # support. This is the mixed-integer-quadratic case HiGHS can't solve in one shot.
        p = _qp_problem(constraints=[CardinalityConstraint(min=1, max=2)])
        run = _optimize_highs(p, mode=OptimizeMode.fast)
        assert run.solutions
        for s in run.solutions:
            assert 1 <= len(s.selected_options) <= 2

    def test_deterministic(self):
        p = _qp_problem()
        a = _optimize_highs(p, mode=OptimizeMode.fast)
        b = _optimize_highs(p, mode=OptimizeMode.fast)
        assert [s.objective_values for s in a.solutions] == [s.objective_values for s in b.solutions]

"""Tests for the explorer — tradeoffs, compare, get_solutions, get_solution."""

import pytest

from frontier.engine.explorer import (
    compare_solutions,
    get_solution,
    get_solutions,
    get_tradeoffs,
)
from frontier.engine.models import (
    CardinalityConstraint,
    Objective,
    Option,
    Problem,
    Score,
)
from frontier.engine.optimizer import optimize


@pytest.fixture
def solved_problem():
    p = Problem(
        objectives=[
            Objective(name="Revenue", direction="maximize", unit="$"),
            Objective(name="Effort", direction="minimize", unit="weeks"),
        ],
        options=[Option(name=n) for n in ["A", "B", "C", "D", "E"]],
        scores=[
            Score(option="A", objective="Revenue", value=8),
            Score(option="A", objective="Effort", value=5),
            Score(option="B", objective="Revenue", value=6),
            Score(option="B", objective="Effort", value=3),
            Score(option="C", objective="Revenue", value=9),
            Score(option="C", objective="Effort", value=7),
            Score(option="D", objective="Revenue", value=4),
            Score(option="D", objective="Effort", value=2),
            Score(option="E", objective="Revenue", value=7),
            Score(option="E", objective="Effort", value=4),
        ],
        constraints=[CardinalityConstraint(min=2, max=3)],
    )
    p.run = optimize(p)
    return p


class TestGetTradeoffs:
    def test_returns_expected_keys(self, solved_problem):
        result = get_tradeoffs(solved_problem)
        assert "total_solutions" in result
        assert "objective_ranges" in result
        assert "key_tradeoffs" in result
        assert "extreme_solutions" in result
        assert "balanced_solution" in result

    def test_objective_ranges(self, solved_problem):
        result = get_tradeoffs(solved_problem)
        assert "Revenue" in result["objective_ranges"]
        assert "Effort" in result["objective_ranges"]
        rev_range = result["objective_ranges"]["Revenue"]
        assert rev_range["min"] <= rev_range["max"]

    def test_extreme_solutions(self, solved_problem):
        result = get_tradeoffs(solved_problem)
        assert "extreme_Revenue" in result["extreme_solutions"]
        assert "extreme_Effort" in result["extreme_solutions"]

    def test_balanced_solution_has_options(self, solved_problem):
        result = get_tradeoffs(solved_problem)
        balanced = result["balanced_solution"]
        assert "selected_options" in balanced
        assert len(balanced["selected_options"]) > 0

    def test_key_tradeoffs_correlations(self, solved_problem):
        result = get_tradeoffs(solved_problem)
        for t in result["key_tradeoffs"]:
            assert "correlation" in t
            assert -1.0 <= t["correlation"] <= 1.0

    def test_no_run_raises(self):
        p = Problem()
        with pytest.raises(ValueError, match="No run found"):
            get_tradeoffs(p)


class TestCompare:
    def test_compare_two_solutions(self, solved_problem):
        result = compare_solutions(solved_problem, [1, 2])
        assert "solutions" in result
        assert "shared_options" in result
        assert "differentiating_options" in result
        assert "tradeoff_summary" in result
        assert len(result["solutions"]) == 2

    def test_compare_nonexistent_solution(self, solved_problem):
        with pytest.raises(ValueError, match="not found"):
            compare_solutions(solved_problem, [1, 9999])

    def test_tradeoff_summary_has_all_objectives(self, solved_problem):
        result = compare_solutions(solved_problem, [1, 2])
        assert "Revenue" in result["tradeoff_summary"]
        assert "Effort" in result["tradeoff_summary"]


class TestGetSolutions:
    def test_returns_all_solutions(self, solved_problem):
        result = get_solutions(solved_problem)
        assert result["total_solutions"] == len(solved_problem.run.solutions)
        assert len(result["solutions"]) == result["total_solutions"]

    def test_has_run_id(self, solved_problem):
        result = get_solutions(solved_problem)
        assert "run_id" in result

    def test_no_run_raises(self):
        p = Problem()
        with pytest.raises(ValueError, match="No run found"):
            get_solutions(p)


class TestGetSolution:
    def test_returns_single_solution(self, solved_problem):
        result = get_solution(solved_problem, 1)
        assert result["solution_id"] == 1
        assert "selected_options" in result
        assert "objective_values" in result

    def test_nonexistent_id_raises(self, solved_problem):
        with pytest.raises(ValueError, match="not found"):
            get_solution(solved_problem, 9999)


class TestFrontierShape:
    def test_tradeoffs_include_frontier_shape(self, solved_problem):
        result = get_tradeoffs(solved_problem)
        assert "frontier_shape" in result

    def test_shape_entries_have_required_fields(self, solved_problem):
        result = get_tradeoffs(solved_problem)
        for entry in result["frontier_shape"]:
            assert "objectives" in entry
            assert "shape" in entry
            assert entry["shape"] in ("linear", "concave", "convex", "discontinuous")
            assert "confidence" in entry
            assert 0.0 <= entry["confidence"] <= 1.0

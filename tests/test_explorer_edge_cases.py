"""Edge-case tests for explorer — balanced solution, zero spread, constant objectives."""

import pytest

from frontier.engine.explorer import _find_balanced
from frontier.engine.models import (
    Objective,
    Option,
    Problem,
    Run,
    Score,
    Solution,
)
from frontier.engine.explorer import get_tradeoffs


class TestFindBalanced:
    def test_all_identical_solutions(self):
        """All solutions with identical values should still return one."""
        solutions = [
            Solution(solution_id=i, selected_options=[f"Opt{i}"],
                     objective_values={"X": 5.0, "Y": 5.0})
            for i in range(3)
        ]
        objectives = [
            Objective(name="X", direction="maximize"),
            Objective(name="Y", direction="minimize"),
        ]
        balanced = _find_balanced(solutions, objectives)
        assert balanced is not None
        assert balanced.solution_id in [0, 1, 2]

    def test_constant_one_dimension(self):
        """One objective constant, other varies — balanced should pick best of varying."""
        solutions = [
            Solution(solution_id=0, selected_options=["A"],
                     objective_values={"X": 5.0, "Y": 1.0}),
            Solution(solution_id=1, selected_options=["B"],
                     objective_values={"X": 5.0, "Y": 3.0}),
            Solution(solution_id=2, selected_options=["C"],
                     objective_values={"X": 5.0, "Y": 5.0}),
        ]
        objectives = [
            Objective(name="X", direction="maximize"),
            Objective(name="Y", direction="minimize"),
        ]
        balanced = _find_balanced(solutions, objectives)
        # Y is minimize, so best Y=1.0 (solution 0)
        assert balanced.solution_id == 0

    def test_two_solutions(self):
        """Two solutions — balanced should still work."""
        solutions = [
            Solution(solution_id=0, selected_options=["A"],
                     objective_values={"X": 10.0, "Y": 1.0}),
            Solution(solution_id=1, selected_options=["B"],
                     objective_values={"X": 1.0, "Y": 10.0}),
        ]
        objectives = [
            Objective(name="X", direction="maximize"),
            Objective(name="Y", direction="maximize"),
        ]
        balanced = _find_balanced(solutions, objectives)
        assert balanced is not None


class TestTradeoffsEdgeCases:
    def test_two_solutions_no_correlation(self):
        """With only 2 solutions, correlations should be empty (need ≥3)."""
        p = Problem(
            objectives=[
                Objective(name="A", direction="maximize"),
                Objective(name="B", direction="minimize"),
            ],
        )
        p.run = Run(solutions=[
            Solution(solution_id=0, selected_options=["X"],
                     objective_values={"A": 10, "B": 5}),
            Solution(solution_id=1, selected_options=["Y"],
                     objective_values={"A": 5, "B": 2}),
        ])
        result = get_tradeoffs(p)
        assert result["key_tradeoffs"] == []

    def test_single_objective_pair_correlation(self):
        """With exactly 2 objectives and ≥3 solutions, should get 1 correlation pair."""
        p = Problem(
            objectives=[
                Objective(name="A", direction="maximize"),
                Objective(name="B", direction="minimize"),
            ],
        )
        p.run = Run(solutions=[
            Solution(solution_id=i, selected_options=[f"Opt{i}"],
                     objective_values={"A": 10 - i, "B": i})
            for i in range(5)
        ])
        result = get_tradeoffs(p)
        assert len(result["key_tradeoffs"]) == 1
        assert abs(result["key_tradeoffs"][0]["correlation"]) > 0.5

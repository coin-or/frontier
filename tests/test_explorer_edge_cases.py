"""Edge-case tests for explorer — balanced solution, zero spread, constant objectives."""

import pytest

from engine.explorer import _find_balanced, _require_run
from engine.models import (
    Objective,
    Option,
    Problem,
    Run,
    ScenarioRun,
    Score,
    Solution,
)
from engine.explorer import get_tradeoffs, get_solution, get_solutions


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


class TestScenarioExplore:
    """Test that explore functions work with the scenario parameter."""

    def _make_problem_with_scenarios(self):
        base_solutions = [
            Solution(solution_id=0, selected_options=["A"],
                     objective_values={"X": 10, "Y": 1}),
            Solution(solution_id=1, selected_options=["B"],
                     objective_values={"X": 5, "Y": 5}),
            Solution(solution_id=2, selected_options=["C"],
                     objective_values={"X": 1, "Y": 10}),
        ]
        recession_solutions = [
            Solution(solution_id=0, selected_options=["A"],
                     objective_values={"X": 3, "Y": 2}),
            Solution(solution_id=1, selected_options=["B"],
                     objective_values={"X": 2, "Y": 7}),
            Solution(solution_id=2, selected_options=["C"],
                     objective_values={"X": 1, "Y": 9}),
        ]
        p = Problem(
            objectives=[
                Objective(name="X", direction="maximize"),
                Objective(name="Y", direction="maximize"),
            ],
        )
        p.run = Run(solutions=base_solutions)
        p.scenario_run = ScenarioRun(scenario_runs={
            "base": Run(solutions=base_solutions),
            "recession": Run(solutions=recession_solutions),
        })
        return p

    def test_require_run_base(self):
        p = self._make_problem_with_scenarios()
        run = _require_run(p)
        assert run.solutions[0].objective_values["X"] == 10

    def test_require_run_scenario(self):
        p = self._make_problem_with_scenarios()
        run = _require_run(p, scenario="recession")
        assert run.solutions[0].objective_values["X"] == 3

    def test_require_run_bad_scenario(self):
        p = self._make_problem_with_scenarios()
        with pytest.raises(ValueError, match="not found"):
            _require_run(p, scenario="inflation")

    def test_tradeoffs_scenario(self):
        p = self._make_problem_with_scenarios()
        base = get_tradeoffs(p)
        recession = get_tradeoffs(p, scenario="recession")
        assert base["objective_ranges"]["X"]["max"] == 10
        assert recession["objective_ranges"]["X"]["max"] == 3

    def test_get_solutions_scenario(self):
        p = self._make_problem_with_scenarios()
        base = get_solutions(p)
        recession = get_solutions(p, scenario="recession")
        assert base["total_solutions"] == 3
        assert recession["total_solutions"] == 3
        assert recession["solutions"][0]["objective_values"]["X"] == 3

    def test_get_solution_scenario(self):
        p = self._make_problem_with_scenarios()
        base_sol = get_solution(p, 0)
        recession_sol = get_solution(p, 0, scenario="recession")
        assert base_sol["objective_values"]["X"] == 10
        assert recession_sol["objective_values"]["X"] == 3

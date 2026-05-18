"""Tests for the metrics module — automated checkpoints and diagnostics."""

import pytest

from frontier.engine.metrics import (
    compute_metrics,
    data_metrics,
    diagnostics,
    framing_metrics,
    frontier_quality,
    outcome_metrics,
    solve_metrics,
)
from frontier.engine.models import (
    CardinalityConstraint,
    Feedback,
    ObjectiveBoundConstraint,
    Objective,
    Option,
    Problem,
    QualityIndicators,
    Run,
    Score,
    Solution,
)
from frontier.engine.optimizer import optimize


@pytest.fixture
def empty_problem():
    return Problem()


@pytest.fixture
def framed_problem():
    return Problem(
        objectives=[
            Objective(name="Revenue", direction="maximize", unit="$"),
            Objective(name="Effort", direction="minimize", unit="days"),
        ],
        options=[Option(name=n) for n in ["A", "B", "C", "D", "E"]],
        constraints=[CardinalityConstraint(min=2, max=3)],
    )


@pytest.fixture
def scored_problem(framed_problem):
    p = framed_problem
    p.scores = [
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
    ]
    return p


@pytest.fixture
def solved_problem(scored_problem):
    p = scored_problem
    p.run = optimize(p)
    return p


class TestFramingMetrics:
    def test_empty_problem(self, empty_problem):
        m = framing_metrics(empty_problem)
        assert m["objective_count"] == 0
        assert m["option_count"] == 0
        assert m["constraint_count"] == 0
        assert m["directions_set"] is True  # vacuously true

    def test_framed_problem(self, framed_problem):
        m = framing_metrics(framed_problem)
        assert m["objective_count"] == 2
        assert m["option_count"] == 5
        assert m["constraint_count"] == 1
        assert m["directions_set"] is True


class TestDataMetrics:
    def test_no_scores(self, framed_problem):
        m = data_metrics(framed_problem)
        assert m["score_completeness"] == 0.0
        assert len(m["missing_scores"]) == 10  # 2 obj * 5 opt

    def test_complete_scores(self, scored_problem):
        m = data_metrics(scored_problem)
        assert m["score_completeness"] == 1.0
        assert len(m["missing_scores"]) == 0

    def test_partial_scores(self, framed_problem):
        p = framed_problem
        p.scores = [
            Score(option="A", objective="Revenue", value=8),
            Score(option="A", objective="Effort", value=5),
        ]
        m = data_metrics(p)
        assert m["score_completeness"] == 0.2  # 2 of 10

    def test_variance_computed(self, scored_problem):
        m = data_metrics(scored_problem)
        assert "Revenue" in m["score_variance_by_objective"]
        assert m["score_variance_by_objective"]["Revenue"] > 0

    def test_dominated_options(self):
        """Option D is dominated by B (lower revenue AND higher effort)."""
        p = Problem(
            objectives=[
                Objective(name="Revenue", direction="maximize"),
                Objective(name="Effort", direction="minimize"),
            ],
            options=[Option(name="B"), Option(name="D")],
            scores=[
                Score(option="B", objective="Revenue", value=6),
                Score(option="B", objective="Effort", value=3),
                # D is worse on both: lower revenue, same effort
                Score(option="D", objective="Revenue", value=4),
                Score(option="D", objective="Effort", value=3),
            ],
        )
        m = data_metrics(p)
        assert "D" in m["dominated_options"]


class TestSolveMetrics:
    def test_no_run(self, scored_problem):
        m = solve_metrics(scored_problem)
        assert m["solve_success"] is False
        assert m["solution_count"] == 0

    def test_with_run(self, solved_problem):
        m = solve_metrics(solved_problem)
        assert m["solve_success"] is True
        assert m["solution_count"] >= 1
        assert isinstance(m["objective_variation"], dict)
        assert "Revenue" in m["objective_variation"]
        assert isinstance(m["option_coverage"], dict)


class TestOutcomeMetrics:
    def test_no_feedback(self, solved_problem):
        m = outcome_metrics(solved_problem)
        assert m["user_selected_solution"] is None
        assert m["user_rating"] is None
        assert m["feedback_count"] == 0

    def test_with_feedback(self, solved_problem):
        solved_problem.feedback.append(
            Feedback(solution_id=0, rating=4, notes="Good", stage="decision")
        )
        m = outcome_metrics(solved_problem)
        assert m["user_selected_solution"] == 0
        assert m["user_rating"] == 4
        assert m["feedback_count"] == 1


class TestDiagnostics:
    def test_no_run(self, scored_problem):
        diags = diagnostics(scored_problem)
        assert len(diags) == 0  # no run, no diagnostics

    def test_zero_solutions(self):
        """Run exists but has no solutions → zero_solutions diagnostic."""
        p = Problem(run=Run(solutions=[]))
        diags = diagnostics(p)
        assert any(d["pattern"] == "zero_solutions" for d in diags)

    def test_option_never_selected(self):
        """An option that's never in any solution gets flagged."""
        p = Problem(
            objectives=[
                Objective(name="X", direction="maximize"),
            ],
            options=[Option(name="A"), Option(name="B"), Option(name="C")],
            run=Run(solutions=[
                Solution(solution_id=0, selected_options=["A"], objective_values={"X": 10}),
                Solution(solution_id=1, selected_options=["A", "B"], objective_values={"X": 15}),
            ]),
        )
        diags = diagnostics(p)
        patterns = [d["pattern"] for d in diags]
        assert "option_never_selected" in patterns
        # C is never selected
        flagged_opts = [d["option"] for d in diags if d["pattern"] == "option_never_selected"]
        assert "C" in flagged_opts

    def test_low_variation_objective(self):
        """Objective with <10% variation gets flagged."""
        p = Problem(
            objectives=[
                Objective(name="Cost", direction="minimize"),
                Objective(name="Quality", direction="maximize"),
            ],
            options=[Option(name="A"), Option(name="B")],
            run=Run(solutions=[
                Solution(solution_id=0, selected_options=["A"],
                         objective_values={"Cost": 100, "Quality": 50}),
                Solution(solution_id=1, selected_options=["B"],
                         objective_values={"Cost": 102, "Quality": 90}),
            ]),
        )
        diags = diagnostics(p)
        patterns = [d["pattern"] for d in diags]
        # Cost has ~2% variation (100 to 102), should be flagged
        assert "low_variation_objective" in patterns

    def test_binding_constraint(self):
        """Constraint at boundary gets flagged."""
        p = Problem(
            objectives=[
                Objective(name="Cost", direction="minimize"),
                Objective(name="Quality", direction="maximize"),
            ],
            options=[Option(name="A"), Option(name="B")],
            constraints=[
                ObjectiveBoundConstraint(
                    objective="Cost", operator="max", value=100,
                ),
            ],
            run=Run(solutions=[
                Solution(solution_id=0, selected_options=["A"],
                         objective_values={"Cost": 98, "Quality": 50}),
                Solution(solution_id=1, selected_options=["B"],
                         objective_values={"Cost": 99, "Quality": 70}),
            ]),
        )
        diags = diagnostics(p)
        patterns = [d["pattern"] for d in diags]
        assert "binding_constraint" in patterns


class TestComputeMetrics:
    def test_returns_all_sections(self, solved_problem):
        m = compute_metrics(solved_problem)
        assert "framing" in m
        assert "data" in m
        assert "solve" in m
        assert "outcome" in m
        assert "diagnostics" in m


# ─── frontier_quality (1.11) ───


class TestFrontierQuality:
    objectives = [
        Objective(name="Revenue", direction="maximize"),
        Objective(name="Effort", direction="minimize"),
    ]

    def test_empty_frontier_is_poor(self):
        q = frontier_quality([], self.objectives)
        assert q["status"] == "POOR"
        assert q["gates"]["frontier_returned"] is False
        assert q["gates"]["non_trivial"] is False
        assert q["gates"]["diverse"] is False
        assert q["issues"]

    def test_single_solution_is_poor(self):
        sols = [Solution(solution_id=1, selected_options=["A"], objective_values={"Revenue": 8, "Effort": 5})]
        q = frontier_quality(sols, self.objectives)
        assert q["status"] == "POOR"
        assert q["gates"]["non_trivial"] is False
        assert any("1 solution" in i.lower() or "degenerate" in i.lower() for i in q["issues"])

    def test_all_objectives_flat_is_poor(self):
        # Same objective values across solutions → no real frontier
        sols = [
            Solution(solution_id=i, selected_options=[f"O{i}"], objective_values={"Revenue": 10.0, "Effort": 5.0})
            for i in range(3)
        ]
        q = frontier_quality(sols, self.objectives)
        assert q["status"] == "POOR"
        assert q["gates"]["non_trivial"] is False
        assert any("flat" in i.lower() or "collapsed" in i.lower() for i in q["issues"])

    def test_diverse_frontier_is_good(self):
        sols = [
            Solution(solution_id=1, selected_options=["A", "B"], objective_values={"Revenue": 10, "Effort": 8}),
            Solution(solution_id=2, selected_options=["B", "C"], objective_values={"Revenue": 14, "Effort": 12}),
            Solution(solution_id=3, selected_options=["A", "C"], objective_values={"Revenue": 18, "Effort": 17}),
        ]
        q = frontier_quality(sols, self.objectives, spacing_cv=0.3)
        assert q["status"] == "GOOD"
        assert q["gates"]["diverse"] is True
        assert q["issues"] == []

    def test_high_spacing_cv_warning(self):
        sols = [
            Solution(solution_id=1, selected_options=["A"], objective_values={"Revenue": 10, "Effort": 8}),
            Solution(solution_id=2, selected_options=["B"], objective_values={"Revenue": 14, "Effort": 12}),
            Solution(solution_id=3, selected_options=["C"], objective_values={"Revenue": 18, "Effort": 17}),
        ]
        q = frontier_quality(sols, self.objectives, spacing_cv=2.0)
        assert q["status"] == "WARNING"
        assert q["gates"]["diverse"] is False
        assert any("spacing" in i.lower() for i in q["issues"])

    def test_proportional_concentration_warning(self):
        # One solution allocates 90% to a single option → single-winner WARNING
        sols = [
            Solution(solution_id=1, selected_options=["A", "B"],
                     objective_values={"Revenue": 10, "Effort": 8},
                     allocations={"A": 60, "B": 40}),
            Solution(solution_id=2, selected_options=["A", "B"],
                     objective_values={"Revenue": 14, "Effort": 12},
                     allocations={"A": 90, "B": 10}),
            Solution(solution_id=3, selected_options=["A", "B"],
                     objective_values={"Revenue": 18, "Effort": 17},
                     allocations={"A": 50, "B": 50}),
        ]
        q = frontier_quality(sols, self.objectives, spacing_cv=0.3)
        assert q["status"] == "WARNING"
        assert q["gates"]["diverse"] is False
        assert any("90%" in i and "A" in i for i in q["issues"])

    def test_proportional_well_diversified_is_good(self):
        sols = [
            Solution(solution_id=1, selected_options=["A", "B", "C"],
                     objective_values={"Revenue": 10, "Effort": 8},
                     allocations={"A": 40, "B": 30, "C": 30}),
            Solution(solution_id=2, selected_options=["A", "B", "C"],
                     objective_values={"Revenue": 14, "Effort": 12},
                     allocations={"A": 30, "B": 40, "C": 30}),
            Solution(solution_id=3, selected_options=["A", "B", "C"],
                     objective_values={"Revenue": 18, "Effort": 17},
                     allocations={"A": 30, "B": 30, "C": 40}),
        ]
        q = frontier_quality(sols, self.objectives, spacing_cv=0.3)
        assert q["status"] == "GOOD"
        assert q["gates"]["diverse"] is True

    def test_objective_value_exactly_zero_flat(self):
        # Edge case: all objective values are zero — must be detected as flat (no zero-division)
        sols = [
            Solution(solution_id=i, selected_options=[f"O{i}"], objective_values={"Revenue": 0.0, "Effort": 0.0})
            for i in range(3)
        ]
        q = frontier_quality(sols, self.objectives)
        assert q["status"] == "POOR"
        assert q["gates"]["non_trivial"] is False

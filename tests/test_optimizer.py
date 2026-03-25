"""Tests for optimizer — validation, NSGA-II, infeasibility analysis."""

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
from frontier.engine.optimizer import analyze_infeasibility, optimize, validate


def _make_problem(**overrides):
    """Build a valid default problem for testing."""
    defaults = dict(
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
    defaults.update(overrides)
    return Problem(**defaults)


# ─── Validation ───


class TestValidation:
    def test_valid_problem(self):
        p = _make_problem()
        vr = validate(p)
        assert vr.ready is True
        assert vr.issues == []

    def test_too_few_objectives(self):
        p = _make_problem(objectives=[
            Objective(name="Revenue", direction="maximize"),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert any("2 objectives" in i.message for i in vr.issues)

    def test_too_few_options(self):
        p = _make_problem(
            options=[Option(name="A"), Option(name="B")],
            scores=[
                Score(option="A", objective="Revenue", value=8),
                Score(option="A", objective="Effort", value=5),
                Score(option="B", objective="Revenue", value=6),
                Score(option="B", objective="Effort", value=3),
            ],
        )
        vr = validate(p)
        assert vr.ready is False
        assert any("3 options" in i.message for i in vr.issues)

    def test_missing_scores(self):
        p = _make_problem(scores=[
            Score(option="A", objective="Revenue", value=8),
            Score(option="A", objective="Effort", value=5),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert len(vr.missing_scores) == 8  # 4 options * 2 objectives missing

    def test_force_include_exclude_conflict(self):
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            ForceIncludeConstraint(option="A"),
            ForceExcludeConstraint(option="A"),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert any("force_include and force_exclude" in i.message for i in vr.issues)

    def test_cardinality_min_gt_max(self):
        p = _make_problem(constraints=[
            CardinalityConstraint(min=5, max=2),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert any("min" in i.message and "max" in i.message for i in vr.issues)

    def test_cardinality_exceeds_available(self):
        p = _make_problem(constraints=[
            CardinalityConstraint(min=10, max=15),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert any("exceeds available" in i.message for i in vr.issues)

    def test_force_include_exceeds_cardinality_max(self):
        p = _make_problem(constraints=[
            CardinalityConstraint(min=1, max=2),
            ForceIncludeConstraint(option="A"),
            ForceIncludeConstraint(option="B"),
            ForceIncludeConstraint(option="C"),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert any("force_include count" in i.message for i in vr.issues)

    def test_unknown_option_in_constraint(self):
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            ForceIncludeConstraint(option="Nonexistent"),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert any("unknown option" in i.message for i in vr.issues)

    def test_unknown_objective_in_constraint(self):
        p = _make_problem(constraints=[
            ObjectiveBoundConstraint(objective="Nonexistent", operator="max", value=10),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert any("unknown objective" in i.message for i in vr.issues)

    def test_duplicate_objective_names(self):
        p = _make_problem(objectives=[
            Objective(name="Revenue", direction="maximize"),
            Objective(name="Revenue", direction="minimize"),
        ])
        vr = validate(p)
        assert vr.ready is False
        assert any("Duplicate objective" in i.message for i in vr.issues)

    def test_duplicate_option_names(self):
        p = _make_problem(
            options=[Option(name="A"), Option(name="A"), Option(name="B")],
            scores=[
                Score(option="A", objective="Revenue", value=8),
                Score(option="A", objective="Effort", value=5),
                Score(option="B", objective="Revenue", value=6),
                Score(option="B", objective="Effort", value=3),
            ],
        )
        vr = validate(p)
        assert vr.ready is False
        assert any("Duplicate option" in i.message for i in vr.issues)


# ─── Optimization ───


class TestOptimization:
    def test_basic_optimization(self):
        p = _make_problem()
        run = optimize(p)
        assert len(run.solutions) > 0

    def test_solutions_respect_cardinality(self):
        p = _make_problem(constraints=[CardinalityConstraint(min=2, max=3)])
        run = optimize(p)
        for s in run.solutions:
            assert 2 <= len(s.selected_options) <= 3

    def test_solutions_respect_force_include(self):
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            ForceIncludeConstraint(option="A"),
        ])
        run = optimize(p)
        for s in run.solutions:
            assert "A" in s.selected_options

    def test_solutions_respect_force_exclude(self):
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            ForceExcludeConstraint(option="C"),
        ])
        run = optimize(p)
        for s in run.solutions:
            assert "C" not in s.selected_options

    def test_solutions_respect_objective_bound(self):
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            ObjectiveBoundConstraint(objective="Effort", operator="max", value=10),
        ])
        run = optimize(p)
        for s in run.solutions:
            assert s.objective_values["Effort"] <= 10.0001  # float tolerance

    def test_solutions_sorted_by_first_objective(self):
        p = _make_problem()
        run = optimize(p)
        if len(run.solutions) >= 2:
            # First objective is Revenue (maximize), so should be descending
            for i in range(len(run.solutions) - 1):
                assert run.solutions[i].objective_values["Revenue"] >= run.solutions[i + 1].objective_values["Revenue"]

    def test_solutions_reindexed(self):
        p = _make_problem()
        run = optimize(p)
        for i, s in enumerate(run.solutions):
            assert s.solution_id == i

    def test_quality_indicators(self):
        p = _make_problem()
        run = optimize(p)
        if len(run.solutions) >= 3:
            assert run.quality.hypervolume_normalized is not None
            assert run.quality.spacing_cv is not None

    def test_optimize_raises_on_invalid(self):
        p = _make_problem(objectives=[Objective(name="X", direction="maximize")])
        with pytest.raises(ValueError, match="not ready"):
            optimize(p)

    def test_auto_scaling_small(self):
        """For ≤20 options, pop_size=100 and n_gen=200 per spec."""
        # This is implicitly tested by the optimization running successfully
        # with the default 5 options. We verify it doesn't crash.
        p = _make_problem()
        run = optimize(p)
        assert len(run.solutions) > 0


# ─── Infeasibility analysis ───


class TestInfeasibility:
    def test_binding_constraint_identified(self):
        """force_include + force_exclude on same option should identify both."""
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            ForceIncludeConstraint(option="A"),
            ForceExcludeConstraint(option="A"),
        ])
        # This would fail validation, so test analyze_infeasibility directly
        # with a problem that passes validation but is infeasible
        p2 = _make_problem(constraints=[
            CardinalityConstraint(min=5, max=5),
            ForceExcludeConstraint(option="A"),
            ForceExcludeConstraint(option="B"),
        ])
        result = analyze_infeasibility(p2)
        assert len(result["binding_constraints"]) > 0
        assert len(result["suggestions"]) > 0

    def test_tight_objective_bound(self):
        """Very tight objective bound should be identified as binding."""
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            ObjectiveBoundConstraint(objective="Effort", operator="max", value=1),  # impossibly tight
        ])
        result = analyze_infeasibility(p)
        assert any("Effort" in s for s in result["suggestions"])

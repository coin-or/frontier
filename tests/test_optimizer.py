"""Tests for optimizer — validation, NSGA-II, infeasibility analysis."""

import pytest

from frontier.engine.models import (
    CardinalityConstraint,
    DependencyConstraint,
    ExclusionPairConstraint,
    ForceExcludeConstraint,
    ForceIncludeConstraint,
    GroupLimitConstraint,
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
        for i, s in enumerate(run.solutions, start=1):
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


# ─── Aggregation ───


class TestAggregation:
    def test_sum_is_default(self):
        """Default aggregation is sum — matches legacy behavior."""
        p = _make_problem()
        for obj in p.objectives:
            assert obj.aggregation == "sum"

    def test_sum_matches_legacy(self):
        """Explicit sum produces same results as Phase 0."""
        p = _make_problem(objectives=[
            Objective(name="Revenue", direction="maximize", unit="$", aggregation="sum"),
            Objective(name="Effort", direction="minimize", unit="weeks", aggregation="sum"),
        ])
        run = optimize(p)
        assert len(run.solutions) > 0
        # Sum: portfolio value = sum of selected option scores
        for sol in run.solutions:
            expected_rev = sum(
                s.value for s in p.scores
                if s.objective == "Revenue" and s.option in sol.selected_options
            )
            assert abs(sol.objective_values["Revenue"] - expected_rev) < 0.01

    def test_avg_aggregation(self):
        """Average aggregation divides by count of selected options."""
        p = _make_problem(
            objectives=[
                Objective(name="Quality", direction="maximize", aggregation="avg"),
                Objective(name="Cost", direction="minimize", aggregation="sum"),
            ],
            scores=[
                Score(option="A", objective="Quality", value=10),
                Score(option="A", objective="Cost", value=5),
                Score(option="B", objective="Quality", value=6),
                Score(option="B", objective="Cost", value=3),
                Score(option="C", objective="Quality", value=8),
                Score(option="C", objective="Cost", value=7),
                Score(option="D", objective="Quality", value=4),
                Score(option="D", objective="Cost", value=2),
                Score(option="E", objective="Quality", value=7),
                Score(option="E", objective="Cost", value=4),
            ],
        )
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            scores = [
                s.value for s in p.scores
                if s.objective == "Quality" and s.option in sol.selected_options
            ]
            expected_avg = sum(scores) / len(scores)
            assert abs(sol.objective_values["Quality"] - expected_avg) < 0.01

    def test_min_aggregation(self):
        """Min aggregation returns worst individual option score."""
        p = _make_problem(
            objectives=[
                Objective(name="Reliability", direction="maximize", aggregation="min"),
                Objective(name="Cost", direction="minimize", aggregation="sum"),
            ],
            scores=[
                Score(option="A", objective="Reliability", value=9),
                Score(option="A", objective="Cost", value=5),
                Score(option="B", objective="Reliability", value=3),
                Score(option="B", objective="Cost", value=2),
                Score(option="C", objective="Reliability", value=7),
                Score(option="C", objective="Cost", value=6),
                Score(option="D", objective="Reliability", value=5),
                Score(option="D", objective="Cost", value=3),
                Score(option="E", objective="Reliability", value=8),
                Score(option="E", objective="Cost", value=4),
            ],
        )
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            scores = [
                s.value for s in p.scores
                if s.objective == "Reliability" and s.option in sol.selected_options
            ]
            expected_min = min(scores)
            assert abs(sol.objective_values["Reliability"] - expected_min) < 0.01

    def test_max_aggregation(self):
        """Max aggregation returns best individual option score."""
        p = _make_problem(
            objectives=[
                Objective(name="Peak", direction="maximize", aggregation="max"),
                Objective(name="Cost", direction="minimize", aggregation="sum"),
            ],
            scores=[
                Score(option="A", objective="Peak", value=10),
                Score(option="A", objective="Cost", value=8),
                Score(option="B", objective="Peak", value=4),
                Score(option="B", objective="Cost", value=2),
                Score(option="C", objective="Peak", value=7),
                Score(option="C", objective="Cost", value=5),
                Score(option="D", objective="Peak", value=3),
                Score(option="D", objective="Cost", value=1),
                Score(option="E", objective="Peak", value=6),
                Score(option="E", objective="Cost", value=3),
            ],
        )
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            scores = [
                s.value for s in p.scores
                if s.objective == "Peak" and s.option in sol.selected_options
            ]
            expected_max = max(scores)
            assert abs(sol.objective_values["Peak"] - expected_max) < 0.01

    def test_objective_bound_respects_avg_aggregation(self):
        """Objective bound constraint should apply to aggregated (avg) value."""
        p = _make_problem(
            objectives=[
                Objective(name="Quality", direction="maximize", aggregation="avg"),
                Objective(name="Cost", direction="minimize", aggregation="sum"),
            ],
            scores=[
                Score(option="A", objective="Quality", value=10),
                Score(option="A", objective="Cost", value=5),
                Score(option="B", objective="Quality", value=2),
                Score(option="B", objective="Cost", value=1),
                Score(option="C", objective="Quality", value=8),
                Score(option="C", objective="Cost", value=6),
                Score(option="D", objective="Quality", value=3),
                Score(option="D", objective="Cost", value=2),
                Score(option="E", objective="Quality", value=6),
                Score(option="E", objective="Cost", value=3),
            ],
            constraints=[
                CardinalityConstraint(min=2, max=3),
                ObjectiveBoundConstraint(objective="Quality", operator="min", value=6),
            ],
        )
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            scores = [
                s.value for s in p.scores
                if s.objective == "Quality" and s.option in sol.selected_options
            ]
            avg = sum(scores) / len(scores)
            assert avg >= 6.0 - 0.01, f"Avg quality {avg} below bound 6"

    def test_mixed_aggregation(self):
        """Different objectives can use different aggregation modes."""
        p = _make_problem(
            objectives=[
                Objective(name="TotalRev", direction="maximize", aggregation="sum"),
                Objective(name="WorstRisk", direction="minimize", aggregation="min"),
            ],
            scores=[
                Score(option="A", objective="TotalRev", value=10),
                Score(option="A", objective="WorstRisk", value=3),
                Score(option="B", objective="TotalRev", value=5),
                Score(option="B", objective="WorstRisk", value=1),
                Score(option="C", objective="TotalRev", value=8),
                Score(option="C", objective="WorstRisk", value=4),
                Score(option="D", objective="TotalRev", value=3),
                Score(option="D", objective="WorstRisk", value=2),
                Score(option="E", objective="TotalRev", value=6),
                Score(option="E", objective="WorstRisk", value=5),
            ],
        )
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            # Verify sum for TotalRev
            rev_scores = [s.value for s in p.scores if s.objective == "TotalRev" and s.option in sol.selected_options]
            assert abs(sol.objective_values["TotalRev"] - sum(rev_scores)) < 0.01
            # Verify min for WorstRisk
            risk_scores = [s.value for s in p.scores if s.objective == "WorstRisk" and s.option in sol.selected_options]
            assert abs(sol.objective_values["WorstRisk"] - min(risk_scores)) < 0.01


# ─── New Constraint Types ───


class TestExclusionPair:
    def test_exclusion_respected(self):
        """Excluded pair: can't select both A and C."""
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            ExclusionPairConstraint(option_a="A", option_b="C"),
        ])
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            assert not ("A" in sol.selected_options and "C" in sol.selected_options), (
                f"Both A and C selected: {sol.selected_options}"
            )

    def test_exclusion_validation_unknown_option(self):
        p = _make_problem(constraints=[
            ExclusionPairConstraint(option_a="A", option_b="UNKNOWN"),
        ])
        vr = validate(p)
        assert not vr.ready
        assert any("UNKNOWN" in i.message for i in vr.issues)

    def test_exclusion_same_option(self):
        p = _make_problem(constraints=[
            ExclusionPairConstraint(option_a="A", option_b="A"),
        ])
        vr = validate(p)
        assert not vr.ready


class TestDependency:
    def test_dependency_respected(self):
        """If A selected, B must be selected too."""
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=4),
            DependencyConstraint(if_option="A", then_option="B"),
        ])
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            if "A" in sol.selected_options:
                assert "B" in sol.selected_options, (
                    f"A selected without B: {sol.selected_options}"
                )

    def test_dependency_validation_unknown_option(self):
        p = _make_problem(constraints=[
            DependencyConstraint(if_option="UNKNOWN", then_option="B"),
        ])
        vr = validate(p)
        assert not vr.ready


class TestGroupLimit:
    def test_group_limit_respected(self):
        """At most 1 from group {A, C, E}."""
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            GroupLimitConstraint(options=["A", "C", "E"], max=1),
        ])
        run = optimize(p)
        assert len(run.solutions) > 0
        for sol in run.solutions:
            group_count = sum(1 for o in ["A", "C", "E"] if o in sol.selected_options)
            assert group_count <= 1, (
                f"Group has {group_count} selected: {sol.selected_options}"
            )

    def test_group_limit_validation_unknown_option(self):
        p = _make_problem(constraints=[
            GroupLimitConstraint(options=["A", "UNKNOWN"], max=1),
        ])
        vr = validate(p)
        assert not vr.ready

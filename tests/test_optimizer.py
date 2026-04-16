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


# ─── Binding constraint detection ───


class TestBindingDetection:
    def test_cardinality_binding_detected(self):
        """Cardinality at max should surface as binding."""
        from frontier.engine import metrics
        p = _make_problem(constraints=[CardinalityConstraint(min=2, max=2)])
        run = optimize(p)
        p.run = run

        diags = metrics.diagnostics(p)
        binding = [d for d in diags if d["pattern"] == "binding_constraint"]
        assert any("cardinality" in d["constraint"] for d in binding)

    def test_group_limit_binding_detected(self):
        """Group limit at max should surface as binding."""
        from frontier.engine import metrics
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=3),
            GroupLimitConstraint(options=["A", "B", "C"], max=1),
        ])
        run = optimize(p)
        p.run = run

        diags = metrics.diagnostics(p)
        binding = [d for d in diags if d["pattern"] == "binding_constraint"]
        # At least one binding constraint should be found (cardinality or group)
        assert len(binding) > 0


# ─── Pruning ───


class TestPruning:
    def test_max_solutions_parameter(self):
        """max_solutions caps the number of returned solutions."""
        p = _make_problem()
        run = optimize(p, max_solutions=3)
        assert len(run.solutions) <= 3


# ─── Matrix override helper (Fix 3) ───


class TestApplyMatrixOverride:
    """_apply_matrix_override: replace | upsert | scale_groups composition."""

    def _base(self):
        from frontier.engine.models import InteractionMatrix
        return InteractionMatrix(
            objective="Vol",
            entries={
                "A": {"A": 1.0, "B": 0.2, "C": 0.1},
                "B": {"A": 0.2, "B": 1.0, "C": 0.3},
                "C": {"A": 0.1, "B": 0.3, "C": 1.0},
            },
        )

    def test_replace_is_default(self):
        from frontier.engine.models import InteractionMatrix
        from frontier.engine.optimizer import _apply_matrix_override

        override = InteractionMatrix(
            objective="Vol",
            entries={"A": {"A": 2.0, "B": 0.9}, "B": {"A": 0.9, "B": 2.0}},
        )
        merged = _apply_matrix_override(self._base(), override)
        # Full replacement: base's "C" row is gone
        assert "C" not in merged.entries
        assert merged.entries["A"]["B"] == 0.9

    def test_upsert_merges_cells_with_symmetry(self):
        from frontier.engine.models import InteractionMatrix
        from frontier.engine.optimizer import _apply_matrix_override

        override = InteractionMatrix(
            objective="Vol",
            mode="upsert",
            entries={"A": {"B": 0.9}},  # only (A,B) specified
        )
        merged = _apply_matrix_override(self._base(), override)
        # Symmetry auto-enforced
        assert merged.entries["A"]["B"] == 0.9
        assert merged.entries["B"]["A"] == 0.9
        # Unchanged cells survive
        assert merged.entries["A"]["C"] == 0.1
        assert merged.entries["C"]["B"] == 0.3

    def test_upsert_with_no_base_creates_fresh_matrix(self):
        from frontier.engine.models import InteractionMatrix
        from frontier.engine.optimizer import _apply_matrix_override

        override = InteractionMatrix(
            objective="Vol",
            mode="upsert",
            entries={"A": {"B": 0.5}},
        )
        merged = _apply_matrix_override(None, override)
        assert merged.entries["A"]["B"] == 0.5
        assert merged.entries["B"]["A"] == 0.5

    def test_scale_groups_multiplies_off_diagonals_within_group(self):
        from frontier.engine.models import InteractionMatrix, InteractionScaleGroup
        from frontier.engine.optimizer import _apply_matrix_override

        override = InteractionMatrix(
            objective="Vol",
            mode="upsert",
            entries={},
            scale_groups=[InteractionScaleGroup(options=["A", "B"], factor=2.0)],
        )
        merged = _apply_matrix_override(self._base(), override)
        # A-B off-diagonal × 2
        assert merged.entries["A"]["B"] == pytest.approx(0.4)
        assert merged.entries["B"]["A"] == pytest.approx(0.4)
        # Diagonal untouched
        assert merged.entries["A"]["A"] == 1.0
        # Outside-group (A-C, B-C) untouched
        assert merged.entries["A"]["C"] == 0.1
        assert merged.entries["B"]["C"] == 0.3

    def test_replace_then_scale_groups_compose(self):
        from frontier.engine.models import InteractionMatrix, InteractionScaleGroup
        from frontier.engine.optimizer import _apply_matrix_override

        override = InteractionMatrix(
            objective="Vol",
            mode="replace",
            entries={
                "A": {"A": 1.0, "B": 0.5},
                "B": {"A": 0.5, "B": 1.0},
            },
            scale_groups=[InteractionScaleGroup(options=["A", "B"], factor=0.0)],
        )
        merged = _apply_matrix_override(self._base(), override)
        # Replace set A-B to 0.5, then scale by 0 → off-diagonals zero
        assert merged.entries["A"]["B"] == 0.0
        assert merged.entries["B"]["A"] == 0.0
        # Diagonals preserved
        assert merged.entries["A"]["A"] == 1.0


# ─── Extreme-point seeding (Fix 2) ───


class TestExtremeSeeds:
    """_compute_extreme_seeds: greedy corner seeds per objective."""

    def test_seeds_are_built_per_objective(self):
        """One seed per objective, respecting cardinality + group limits."""
        from frontier.engine.optimizer import _compute_extreme_seeds, _parse_constraints, _build_score_matrix

        p = _make_problem(constraints=[CardinalityConstraint(min=2, max=3)])
        score_matrix = _build_score_matrix(p)
        cp = _parse_constraints(p)
        seeds = _compute_extreme_seeds(p, score_matrix, cp)

        assert seeds.shape[0] == len(p.objectives)
        assert seeds.shape[1] == len(p.options)
        # Binary mode: values are 0 or 1
        unique = set(seeds.flatten().tolist())
        assert unique.issubset({0.0, 1.0})
        # Each seed has between 2 and 3 non-zero entries (cardinality)
        for seed in seeds:
            count = int(seed.sum())
            assert 2 <= count <= 3

    def test_proportional_seeds_sum_to_100_and_respect_cap(self):
        """Proportional seeds: allocations sum to 100 and no allocation exceeds max_allocation."""
        from frontier.engine.models import MaxAllocationConstraint
        from frontier.engine.optimizer import _compute_extreme_seeds, _parse_constraints, _build_score_matrix

        p = Problem(
            approach="proportional",
            objectives=[
                Objective(name="Return", direction="maximize"),
                Objective(name="Risk", direction="minimize"),
            ],
            options=[Option(name=n) for n in ["A", "B", "C", "D", "E"]],
            scores=[
                Score(option="A", objective="Return", value=10),
                Score(option="B", objective="Return", value=8),
                Score(option="C", objective="Return", value=6),
                Score(option="D", objective="Return", value=4),
                Score(option="E", objective="Return", value=2),
                Score(option="A", objective="Risk", value=5),
                Score(option="B", objective="Risk", value=4),
                Score(option="C", objective="Risk", value=3),
                Score(option="D", objective="Risk", value=2),
                Score(option="E", objective="Risk", value=1),
            ],
            constraints=[
                CardinalityConstraint(min=3, max=5),
                MaxAllocationConstraint(max=40),
            ],
        )
        score_matrix = _build_score_matrix(p)
        cp = _parse_constraints(p)
        seeds = _compute_extreme_seeds(p, score_matrix, cp)

        assert len(seeds) == 2
        for seed in seeds:
            # Allocations sum to exactly 100
            assert int(seed.sum()) == 100
            # No allocation exceeds cap
            assert seed.max() <= 40
            # At least min cardinality non-zero entries
            assert int((seed > 0).sum()) >= 3

    def test_seeds_respect_group_limits(self):
        """Seeds respect group_limit: no more than max options from the group."""
        from frontier.engine.optimizer import _compute_extreme_seeds, _parse_constraints, _build_score_matrix

        # A, B, C are in a group with max=1. Even though they might rank highest for an objective,
        # the seed should only include one.
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=4),
            GroupLimitConstraint(options=["A", "B", "C"], max=1),
        ])
        score_matrix = _build_score_matrix(p)
        cp = _parse_constraints(p)
        seeds = _compute_extreme_seeds(p, score_matrix, cp)

        for seed in seeds:
            selected_from_group = sum(
                int(seed[i] > 0) for i, o in enumerate(p.options) if o.name in ("A", "B", "C")
            )
            assert selected_from_group <= 1

    def test_no_seeds_when_cardinality_infeasible(self):
        """If constraints block ever reaching cardinality_min, return empty seeds (optimizer falls back)."""
        from frontier.engine.optimizer import _compute_extreme_seeds, _parse_constraints, _build_score_matrix

        # Force-exclude everything reachable → cardinality_min unreachable
        p = _make_problem(constraints=[
            CardinalityConstraint(min=2, max=2),
            ForceExcludeConstraint(option="A"),
            ForceExcludeConstraint(option="B"),
            ForceExcludeConstraint(option="C"),
            ForceExcludeConstraint(option="D"),
            ForceExcludeConstraint(option="E"),
        ])
        score_matrix = _build_score_matrix(p)
        cp = _parse_constraints(p)
        seeds = _compute_extreme_seeds(p, score_matrix, cp)

        # All options excluded → no seed meets cardinality_min
        assert seeds.shape[0] == 0

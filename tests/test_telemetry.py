"""Solve telemetry stage 1: Run.telemetry + Run.problem_snapshot.

Instrumentation only (recorded facts, no judgment): every solve records how it
ran (duration, engine detail, evaluation/inner-solve counts) and the problem
features it ran on, so routing advice can later be calibrated against real
workload instead of lab benchmarks. Bundles stay problem-portable: telemetry is
stripped on save; problem_snapshot (problem-derived) travels.
"""

import importlib.util

import pytest

from engine.models import CardinalityConstraint, Objective, Option, Problem, Score
from engine.optimizer import OptimizeMode, optimize
from engine.problem_io import to_portable
from solvers import problem_features

_HAS_HIGHS = importlib.util.find_spec("highspy") is not None


def _binary_problem(n: int = 12) -> Problem:
    names = [f"P{i:02d}" for i in range(n)]
    objs = ["value", "cost"]
    return Problem(
        approach="binary",
        objectives=[Objective(name="value", direction="maximize"),
                    Objective(name="cost", direction="minimize")],
        options=[Option(name=nm) for nm in names],
        scores=[Score(option=nm, objective=o, value=float((i * 7 + j * 13) % 11 + 1))
                for j, o in enumerate(objs) for i, nm in enumerate(names)],
        constraints=[CardinalityConstraint(min=2, max=6)],
    )


class TestNsgaTelemetry:
    def test_run_carries_telemetry_and_snapshot(self):
        p = _binary_problem()
        run = optimize(p, mode=OptimizeMode.fast, seed=7)

        t = run.telemetry
        assert t is not None
        assert t["duration_s"] > 0
        assert t["engine_detail"]["pop_size"] >= 50
        assert t["engine_detail"]["n_gen_budget"] >= 50
        assert 0 < t["engine_detail"]["n_gen_run"] <= t["engine_detail"]["n_gen_budget"]
        assert t["evals_or_solves"] > 0

        s = run.problem_snapshot
        assert s == problem_features(p)  # features and gate share one implementation
        assert s["n_options"] == 12
        assert s["n_objectives"] == 2
        assert s["n_scores"] == 24
        assert s["approach"] == "binary"
        assert s["aggregation_mix"] == {"sum": 2}
        assert s["constraint_type_counts"] == {"cardinality": 1}
        assert s["interaction_matrix"] is False
        assert s["scenarios"] == 0
        assert s["exact_fits"] is True
        assert s["exact_fits_reason"] == ""

    def test_telemetry_shape_is_flat_scalars(self):
        # Payload sanity: the runs listing must stay inside MCP caps — scalars only.
        run = optimize(_binary_problem(), mode=OptimizeMode.fast, seed=7)
        t = run.telemetry
        assert set(t) == {"duration_s", "engine_detail", "evals_or_solves"}
        assert all(isinstance(v, (int, float, bool)) for v in t["engine_detail"].values())

    def test_fingerprint_unaffected(self):
        # Staleness keys on solve inputs; instrumentation must not perturb it.
        from mcp_server.server import _solve_fingerprint

        p = _binary_problem()
        before = _solve_fingerprint(p)
        p.run = optimize(p, mode=OptimizeMode.fast, seed=7)
        assert _solve_fingerprint(p) == before


@pytest.mark.skipif(not _HAS_HIGHS, reason="highspy not installed")
class TestExactTelemetry:
    def test_milp_run_counts_inner_solves(self):
        p = _binary_problem()
        run = optimize(p, mode=OptimizeMode.fast, seed=7, solver="highs")
        t = run.telemetry
        assert t is not None
        assert t["duration_s"] > 0
        assert t["engine_detail"]["inner_solves"] > 0
        assert t["engine_detail"]["inner_solve_median_s"] >= 0
        assert t["evals_or_solves"] == t["engine_detail"]["inner_solves"]
        assert run.problem_snapshot == problem_features(p)

    def test_certify_curated_counts_inner_solves(self):
        from engine.optimizer import certify_curated

        p = _binary_problem()
        source = optimize(p, mode=OptimizeMode.fast, seed=7)
        overlay = certify_curated(p, source, solver="highs")
        assert overlay.telemetry["engine_detail"]["inner_solves"] > 0
        assert overlay.problem_snapshot == problem_features(p)


class TestBundlePortability:
    def test_save_strips_telemetry_keeps_snapshot(self):
        p = _binary_problem()
        p.run = optimize(p, mode=OptimizeMode.fast, seed=7)
        assert p.run.telemetry is not None
        _, _, solutions = to_portable(p)
        assert "telemetry" not in solutions["run"]
        assert solutions["run"]["problem_snapshot"] == problem_features(p)

    def test_user_objective_named_telemetry_survives_save(self):
        # The strip targets the Run-schema position only — a user objective (or option)
        # literally named "telemetry" must keep its values in objective_values.
        names = [f"P{i}" for i in range(6)]
        p = Problem(
            approach="binary",
            objectives=[Objective(name="telemetry", direction="maximize"),
                        Objective(name="cost", direction="minimize")],
            options=[Option(name=nm) for nm in names],
            scores=[Score(option=nm, objective=o, value=float(i + j + 1))
                    for j, o in enumerate(["telemetry", "cost"]) for i, nm in enumerate(names)],
        )
        p.run = optimize(p, mode=OptimizeMode.fast, seed=7)
        _, _, solutions = to_portable(p)
        assert "telemetry" not in solutions["run"]  # the Run field is stripped...
        for s in solutions["run"]["solutions"]:
            assert "telemetry" in s["objective_values"]  # ...the user objective is not


class TestProblemFeatureSemantics:
    def test_interaction_matrix_needs_quadratic_and_matching_matrix(self):
        # Mirrors optimizer._build_interaction_matrices' inclusion rule without the
        # dense n×n build: a matrix without a quadratic objective (or vice versa)
        # is not an effective interaction matrix.
        from engine.models import Aggregation, InteractionMatrix

        p = _binary_problem()
        assert problem_features(p)["interaction_matrix"] is False
        p.interaction_matrices = [InteractionMatrix(objective="value", entries={})]
        assert problem_features(p)["interaction_matrix"] is False  # no quadratic objective
        p.objectives[0].aggregation = Aggregation.quadratic
        assert problem_features(p)["interaction_matrix"] is True

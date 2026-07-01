"""Anchor corners: every exact overlay samples the frontier's per-objective extremes — one
lexicographic anchor scalarization per objective (the classic epsilon-constraint payoff-table
step) — even when the EA's epsilon sweep or the certify source run under-covered them. Closes
the "exact looks short of NSGA at a linear extreme" artifact (architecture.md § Solver
Backends; scoping: .claude/plans/surf-uniform-coverage-scoping.md §8)."""
import importlib.util as _ilu
import itertools

import numpy as np
import pytest

from engine.models import Run
from engine.optimizer import certify_curated, optimize
from engine.problem_io import from_portable
from solvers._scalarization import _box_extreme, _prop_anchor_rows

_HAS_HIGHS = _ilu.find_spec("highspy") is not None
needs_highs = pytest.mark.skipif(not _HAS_HIGHS, reason="highspy not installed")


# --- pure helpers ------------------------------------------------------------------------------

def test_box_extreme_fills_best_assets_to_the_cap():
    coef = np.array([3.0, 1.0, 2.0])
    assert _box_extreme(coef, True, None) == 3.0                          # 100% best asset
    assert _box_extreme(coef, True, 0.4) == pytest.approx(0.4 * 3 + 0.4 * 2 + 0.2 * 1)
    assert _box_extreme(coef, False, None) == 1.0                         # 100% worst asset
    assert _box_extreme(coef, False, 0.5) == pytest.approx(0.5 * 1 + 0.5 * 2)


def test_prop_anchor_rows_shapes_and_loose_floors():
    coefs = [np.array([8.0, 6.0, 9.0]), np.array([3.0, 7.0, 2.0])]
    maxs = [True, True]
    # QP shape: every linear objective epsilon'd → n_lin+1 rows of length n_lin.
    rows = _prop_anchor_rows(coefs, maxs, None, include_primary_eps=True)
    assert len(rows) == 3 and all(len(r) == 2 for r in rows)
    assert rows[0].tolist() == [6.0, 2.0]      # all-loose = per-objective simplex min (maximize floors)
    assert rows[1].tolist() == [9.0, 2.0]      # objective 0 pinned at its box extreme, other loose
    assert rows[2].tolist() == [6.0, 7.0]
    # LP shape: the optimized primary carries no epsilon → n_eps+1 rows of length n_eps.
    rows_lp = _prop_anchor_rows(coefs, maxs, None, include_primary_eps=False)
    assert len(rows_lp) == 2 and all(len(r) == 1 for r in rows_lp)
    assert rows_lp[0].tolist() == [2.0] and rows_lp[1].tolist() == [7.0]
    # A minimize objective's loose value is its simplex max (a "≤" ceiling every w satisfies).
    rows_min = _prop_anchor_rows(coefs, [True, False], None, include_primary_eps=True)
    assert rows_min[0].tolist() == [6.0, 7.0]


# --- binary MILP -------------------------------------------------------------------------------

_SCORES = {"A": (9, 5), "B": (7, 3), "C": (8, 6), "D": (5, 2), "E": (6, 4), "F": (4, 1)}


def _binary_problem():
    return from_portable(
        {"name": "x", "domain": "d", "context": "c", "approach": "binary",
         "objectives": [{"name": "Value", "direction": "maximize", "aggregation": "sum"},
                        {"name": "Cost", "direction": "minimize", "aggregation": "sum"}],
         "constraints": [{"type": "cardinality", "min": 2, "max": 4}]},
        {"options": [{"name": n} for n in "ABCDEF"],
         "scores": [{"option": o, "objective": ob, "value": float(v)}
                    for o, vv in _SCORES.items() for ob, v in zip(["Value", "Cost"], vv)]})


def _brute_extremes():
    """Enumerated ground truth over every feasible plan (subsets of size 2-4)."""
    best_value, best_cost = -1e18, 1e18
    for k in (2, 3, 4):
        for combo in itertools.combinations(_SCORES, k):
            best_value = max(best_value, sum(_SCORES[o][0] for o in combo))
            best_cost = min(best_cost, sum(_SCORES[o][1] for o in combo))
    return best_value, best_cost


@needs_highs
def test_milp_full_pass_contains_per_objective_extremes():
    p = _binary_problem()
    run = optimize(p, seed=42, solver="highs")
    bv, bc = _brute_extremes()
    assert max(s.objective_values["Value"] for s in run.solutions) == pytest.approx(bv)
    assert min(s.objective_values["Cost"] for s in run.solutions) == pytest.approx(bc)
    # Determinism: anchors are solver-computed, not sampled — same seed, same frontier.
    rerun = optimize(p, seed=42, solver="highs")
    assert [s.content_signature for s in rerun.solutions] == [s.content_signature for s in run.solutions]


@needs_highs
def test_certify_anchors_recover_extremes_the_source_run_missed_binary():
    """The decisive case: certify a source run holding ONE mid-frontier point — the overlay must
    still contain both per-objective extremes, because the anchors sample them independently."""
    p = _binary_problem()
    nsga = optimize(p, seed=42)
    mid = sorted(nsga.solutions, key=lambda s: s.objective_values["Value"])[len(nsga.solutions) // 2]
    cert = certify_curated(p, Run(solutions=[mid]), solver="highs")
    bv, bc = _brute_extremes()
    assert max(s.objective_values["Value"] for s in cert.solutions) == pytest.approx(bv)
    assert min(s.objective_values["Cost"] for s in cert.solutions) == pytest.approx(bc)
    assert len(cert.solutions) >= 2                     # more than the single certified source point


# --- proportional LP ---------------------------------------------------------------------------

def _lp_problem():
    data = {"A": (8, 3), "B": (6, 7), "C": (9, 2), "D": (4, 8), "E": (7, 5)}
    return from_portable(
        {"name": "alloc", "domain": "d", "context": "c", "approach": "proportional",
         "objectives": [{"name": "ROI", "direction": "maximize", "aggregation": "avg"},
                        {"name": "Reach", "direction": "maximize", "aggregation": "avg"}],
         "constraints": [{"type": "max_allocation", "max": 40}]},
        {"options": [{"name": n} for n in data],
         "scores": [{"option": o, "objective": ob, "value": float(v)}
                    for o, vv in data.items() for ob, v in zip(["ROI", "Reach"], vv)]})


@needs_highs
def test_certify_anchors_recover_extremes_the_source_run_missed_lp():
    p = _lp_problem()
    full = optimize(p, seed=42, solver="highs")
    mid = sorted(full.solutions, key=lambda s: s.objective_values["ROI"])[len(full.solutions) // 2]
    cert = certify_curated(p, Run(solutions=[mid]), solver="highs")
    # The anchors are the same deterministic scalarizations on both paths, so the single-point
    # certify overlay reaches the full pass's per-objective bests (whole-percent rounding aside).
    for obj in ("ROI", "Reach"):
        vals = [s.objective_values[obj] for s in full.solutions]
        span = max(max(vals) - min(vals), 1e-9)
        cert_best = max(s.objective_values[obj] for s in cert.solutions)
        assert cert_best >= max(vals) - 0.02 * span


# --- proportional QP (mean-variance) -----------------------------------------------------------

def _qp_problem():
    rets = {"A": 9.0, "B": 5.0, "C": 7.0, "D": 3.0}
    cov = {"A": {"A": 25.0, "B": 4.0, "C": 6.0, "D": 2.0},
           "B": {"A": 4.0, "B": 9.0, "C": 3.0, "D": 1.0},
           "C": {"A": 6.0, "B": 3.0, "C": 16.0, "D": 2.0},
           "D": {"A": 2.0, "B": 1.0, "C": 2.0, "D": 4.0}}
    return from_portable(
        {"name": "mv", "domain": "d", "context": "c", "approach": "proportional",
         "objectives": [{"name": "Return", "direction": "maximize", "aggregation": "avg"},
                        {"name": "Risk", "direction": "minimize", "aggregation": "quadratic"}]},
        {"options": [{"name": n} for n in rets],
         "scores": [{"option": o, "objective": "Return", "value": v} for o, v in rets.items()]
                   + [{"option": o, "objective": "Risk", "value": 0.0} for o in rets],
         "interaction_matrices": [{"objective": "Risk", "entries": cov}]})


@needs_highs
def test_certify_anchors_recover_extremes_the_source_run_missed_qp():
    """QP anchors cover both headline corners: the min-variance portfolio (all floors loose) and
    the max-return corner (return pinned at its box extreme)."""
    p = _qp_problem()
    full = optimize(p, seed=42, solver="highs")
    mid = sorted(full.solutions, key=lambda s: s.objective_values["Return"])[len(full.solutions) // 2]
    cert = certify_curated(p, Run(solutions=[mid]), solver="highs")
    ret_vals = [s.objective_values["Return"] for s in full.solutions]
    risk_vals = [s.objective_values["Risk"] for s in full.solutions]
    ret_span = max(max(ret_vals) - min(ret_vals), 1e-9)
    risk_span = max(max(risk_vals) - min(risk_vals), 1e-9)
    assert max(s.objective_values["Return"] for s in cert.solutions) >= max(ret_vals) - 0.02 * ret_span
    assert min(s.objective_values["Risk"] for s in cert.solutions) <= min(risk_vals) + 0.02 * risk_span

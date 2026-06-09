"""CPU tests for the cuOpt matrix-API QP marshaling and the parallel-solve helper
(``solvers/cuopt_backend.py``).

These cover the parts of the matrix/parallel path that do **not** need a GPU: the CSR
marshaling (``_qp_to_csr``) and the thread-pool orchestration (``_parallel_solve``). The
cuOpt calls themselves (``_solve_qp_cuopt_matrix``) only run on a GPU and are validated by the
comparison notebook's dense-QP panel — but the marshaling that feeds them is reconstructed and
checked densely here, the same way the term-by-term path was source-reviewed before its first
GPU run. ``cuopt_backend`` imports cuOpt lazily, so this module imports and runs anywhere.

The load-bearing correctness claim is *equivalence*: the matrix path passes the same Q (the
full covariance) and the same constraints the verified term-by-term path builds, differing only
in build mechanism. The dense reconstructions below assert exactly that.
"""

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solvers._scalarization import _build_raw_sensitivity
from solvers.cuopt_backend import (
    _extract_cuopt_lp_sensitivity_matrix,
    _extract_cuopt_qp_sensitivity,
    _extract_cuopt_qp_sensitivity_matrix,
    _lp_to_csr,
    _parallel_solve,
    _qp_to_csr,
)


def _dense(data, indices, offsets, shape):
    return csr_matrix((data, indices, offsets), shape=shape).toarray()


# ─── _qp_to_csr marshaling ───

def test_qp_to_csr_objective_is_full_covariance():
    """Q is the full covariance as CSR — identical to what the term-by-term path packs into
    set_quadratic_objective_matrix (cuOpt symmetrises Q+Qᵀ either way), so the solve matches."""
    rng = np.random.default_rng(1)
    F = rng.standard_normal((6, 3))
    cov = F @ F.T + np.diag(rng.uniform(0.1, 0.4, 6))   # dense PSD
    mu = rng.uniform(0.05, 0.2, 6)

    a = _qp_to_csr(cov, mu, target_return=0.1, return_maximize=True, max_weight=None)
    Q = _dense(a["Q_data"], a["Q_indices"], a["Q_offsets"], (6, 6))
    assert np.allclose(Q, cov)
    # cuOpt wants float64 values + int32 index/offset arrays.
    assert a["Q_data"].dtype == np.float64
    assert a["Q_indices"].dtype == np.int32 and a["Q_offsets"].dtype == np.int32


def test_qp_to_csr_thresholds_tiny_entries_like_termwise():
    """Sub-1e-12 covariance entries are dropped, matching the term-wise `abs(c) > 1e-12` skip,
    so the two paths produce the same sparsity pattern (not just the same dense values)."""
    cov = np.array([[1.0, 1e-15, 0.2], [1e-15, 1.0, 0.0], [0.2, 0.0, 1.0]])
    a = _qp_to_csr(cov, np.ones(3), target_return=None, return_maximize=True, max_weight=None)
    # 1e-15 entries dropped; the four structural zeros/tiny stay out → 5 nonzeros.
    assert a["Q_data"].size == 5
    Q = _dense(a["Q_data"], a["Q_indices"], a["Q_offsets"], (3, 3))
    assert Q[0, 1] == 0.0 and Q[1, 0] == 0.0


def test_qp_to_csr_constraint_rows_and_senses():
    """Constraint matrix rows, rhs and senses: fully-invested 'E', return eps 'G' (maximize),
    each extra linear floor 'G'/'L' by its own direction."""
    mu = np.array([0.1, 0.2, 0.15, 0.05])
    yld = np.array([3.0, 4.0, 2.0, 5.0])
    a = _qp_to_csr(np.eye(4), mu, target_return=0.12, return_maximize=True, max_weight=None,
                   extra_linears=[(yld, 3.5, True), (np.arange(4.0), 2.0, False)])
    A = _dense(a["A_data"], a["A_indices"], a["A_offsets"], (4, 4))
    assert np.allclose(A[0], np.ones(4))            # fully invested
    assert np.allclose(A[1], mu)                     # return
    assert np.allclose(A[2], yld) and np.allclose(A[3], np.arange(4.0))
    assert a["b"].tolist() == [1.0, 0.12, 3.5, 2.0]
    assert [t.decode() for t in a["row_types"]] == ["E", "G", "G", "L"]


def test_qp_to_csr_minimize_return_uses_le():
    """A minimize-direction primary objective epsilon-constrains with 'L' (≤ target)."""
    a = _qp_to_csr(np.eye(3), np.ones(3), target_return=0.5, return_maximize=False, max_weight=None)
    assert a["row_types"][1].decode() == "L"


def test_qp_to_csr_no_return_row_when_target_none():
    """The min-variance anchor solve (target_return=None) drops the return row — only the
    fully-invested equality remains."""
    a = _qp_to_csr(np.eye(3), np.ones(3), target_return=None, return_maximize=True, max_weight=None)
    assert a["b"].size == 1 and a["row_types"][0].decode() == "E"
    assert a["A_offsets"].size == 2                 # one row → offsets [0, nnz]


def test_qp_to_csr_box_and_support_pinning():
    """0 ≤ w ≤ max_weight; off-support assets pinned to ub=0 (cardinality, no MIQP)."""
    a = _qp_to_csr(np.eye(5), np.ones(5), target_return=None, return_maximize=True,
                   max_weight=0.3, support=[0, 2, 4])
    assert np.allclose(a["var_lb"], 0.0)
    assert a["var_ub"].tolist() == [0.3, 0.0, 0.3, 0.0, 0.3]
    assert np.allclose(a["c"], 0.0)                 # objective is purely quadratic


def test_qp_to_csr_default_upper_bound_is_one():
    """No max_weight → fully-invested long-only cap of 1.0 per asset."""
    a = _qp_to_csr(np.eye(3), np.ones(3), target_return=None, return_maximize=True, max_weight=None)
    assert a["var_ub"].tolist() == [1.0, 1.0, 1.0]


def test_qp_to_csr_matches_termwise_objective_matrix():
    """Equivalence anchor: the Q `_qp_to_csr` emits equals the `objective_qmatrix` the
    high-level Problem builds from the term-by-term Σ_ij cov[i,j]·w_i·w_j loop — i.e. the full
    covariance. Reconstructed independently here so the matrix path can never silently diverge
    from the GPU-verified term-wise one."""
    rng = np.random.default_rng(7)
    cov = rng.standard_normal((5, 5))
    cov = cov @ cov.T                                # symmetric PSD, all entries > 1e-12
    # term-by-term objective_qmatrix: COO of every ordered (i, j) with coefficient cov[i, j].
    rows, cols, vals = [], [], []
    for i in range(5):
        for j in range(5):
            rows.append(i); cols.append(j); vals.append(cov[i, j])
    termwise = csr_matrix((vals, (rows, cols)), shape=(5, 5)).toarray()

    a = _qp_to_csr(cov, np.ones(5), target_return=None, return_maximize=True, max_weight=None)
    matrix = _dense(a["Q_data"], a["Q_indices"], a["Q_offsets"], (5, 5))
    assert np.allclose(matrix, termwise)


# ─── _parallel_solve orchestration ───

def test_parallel_solve_sequential_baseline():
    """max_workers None/0/1 → the sequential baseline, results in input order."""
    args = [(i, i + 1) for i in range(5)]
    expected = [i + (i + 1) for i in range(5)]
    for workers in (None, 0, 1):
        assert _parallel_solve(lambda x, y: x + y, args, max_workers=workers) == expected


def test_parallel_solve_preserves_order_and_results():
    """A thread pool returns the same results in the same order as sequential — the EA marshals
    by position, so order parity is required, not incidental."""
    args = [(i,) for i in range(50)]
    seq = _parallel_solve(lambda x: x * x, args, max_workers=1)
    par = _parallel_solve(lambda x: x * x, args, max_workers=8)
    assert par == seq == [i * i for i in range(50)]


def test_parallel_solve_matches_sequential_on_highs_qp():
    """End-to-end parity on the real inner-solve contract: running a return-target sweep through
    `_parallel_solve` gives bit-identical weights to the sequential loop (HiGHS stands in for the
    GPU solve — the orchestration is solver-agnostic, which is the whole point)."""
    highspy = pytest.importorskip("highspy")
    from solvers.highs_backend import _solve_qp_highs

    rng = np.random.default_rng(3)
    F = rng.standard_normal((8, 3))
    cov = F @ F.T + np.diag(rng.uniform(0.1, 0.3, 8))
    mu = rng.uniform(0.05, 0.25, 8)
    specs = [(cov, mu, t, True, None, None, None) for t in np.linspace(mu.min(), mu.max(), 12)]

    seq = _parallel_solve(_solve_qp_highs, specs, max_workers=1)
    par = _parallel_solve(_solve_qp_highs, specs, max_workers=4)
    assert len(seq) == len(par) == 12
    for (w_s, ok_s), (w_p, ok_p) in zip(seq, par):
        assert ok_s == ok_p
        if ok_s:
            assert np.allclose(w_s, w_p)
            assert abs(w_s.sum() - 1.0) < 1e-3       # fully invested, a real frontier point


# ─── sensitivity (duals) marshalling — CPU, stand-in cuOpt objects ───
# The cuOpt solve is GPU-only, but the dual extractors are pure (array/attribute reads), so the
# role/index/eligibility mapping is verified here with stand-ins; the dual *numbers* are confirmed on
# a GPU run vs the HiGHS oracle. Both read paths — the default matrix `Solve` result and the
# term-by-term `Problem` — must produce the identical role-tagged payload the shared engine consumes.


class _FakeSolution:
    """Matrix-path Solve result stand-in: one dual per constraint (in `_qp_to_csr` add order), one
    reduced cost per variable."""

    def __init__(self, dual, reduced):
        self._dual, self._reduced = dual, reduced

    def get_dual_solution(self):
        return np.asarray(self._dual, dtype=float)

    def get_reduced_cost(self):
        return np.asarray(self._reduced, dtype=float)


class _FakeCon:
    def __init__(self, dual):
        self.DualValue = dual


class _FakeVar:
    def __init__(self, rc):
        self.ReducedCost = rc


class _FakeProb:
    def __init__(self, duals):
        self._cons = [_FakeCon(d) for d in duals]

    def getConstraints(self):
        return self._cons


def test_matrix_sensitivity_roles_indices_values():
    # rows in _qp_to_csr add order: budget, return floor, one extra linear floor; 3 assets.
    sol = _FakeSolution(dual=[-0.05, 0.012, 0.4], reduced=[0.0, 0.0, 0.3])
    raw = _extract_cuopt_qp_sensitivity_matrix(sol, n=3, has_return=True, n_extra=1, support=None)
    assert [(s["role"], s["linear_index"]) for s in raw["shadow_prices"]] == [
        ("budget", None), ("return_floor", 0), ("linear_floor", 1)]
    assert [s["value"] for s in raw["shadow_prices"]] == [-0.05, 0.012, 0.4]
    assert raw["reduced_costs"] == [0.0, 0.0, 0.3]
    assert raw["eligible"] == [True, True, True]
    assert raw["ranging"] is None


def test_matrix_sensitivity_eligibility_from_support():
    # support={0, 2} → asset 1 is off-support (pinned out, ineligible — not a near-miss).
    sol = _FakeSolution(dual=[-0.05, 0.01], reduced=[0.0, 0.1, 0.0])
    raw = _extract_cuopt_qp_sensitivity_matrix(sol, n=3, has_return=True, n_extra=0, support=[0, 2])
    assert raw["eligible"] == [True, False, True]
    assert [s["role"] for s in raw["shadow_prices"]] == ["budget", "return_floor"]


def test_matrix_sensitivity_no_return_row():
    # min-variance anchor (target_return=None) → only the budget row, like _qp_to_csr.
    sol = _FakeSolution(dual=[-0.07], reduced=[0.0, 0.0])
    raw = _extract_cuopt_qp_sensitivity_matrix(sol, n=2, has_return=False, n_extra=0, support=None)
    assert [s["role"] for s in raw["shadow_prices"]] == ["budget"]
    assert raw["shadow_prices"][0]["value"] == -0.07


def test_matrix_sensitivity_tolerates_empty_duals():
    # A degenerate solve may return no duals; degrade to a tagged-but-zero payload, never crash.
    sol = _FakeSolution(dual=[], reduced=[])
    raw = _extract_cuopt_qp_sensitivity_matrix(sol, n=2, has_return=True, n_extra=0, support=None)
    assert [s["value"] for s in raw["shadow_prices"]] == [0.0, 0.0]   # defensive _row → 0.0
    assert raw["reduced_costs"] == []


def test_matrix_and_termwise_paths_agree():
    # The two cuOpt read paths must produce the identical payload for the same duals — so flipping
    # _USE_MATRIX_QP can never change the sensitivity a user sees.
    duals, reduced = [-0.05, 0.012, 0.4], [0.0, 0.0, 0.3]
    m = _extract_cuopt_qp_sensitivity_matrix(_FakeSolution(duals, reduced), n=3,
                                             has_return=True, n_extra=1, support=None)
    t = _extract_cuopt_qp_sensitivity(_FakeProb(duals), [_FakeVar(r) for r in reduced],
                                      has_return=True, n_extra=1, support=None)
    assert m == t


def test_cuopt_payload_parity_with_highs_shape():
    # The cuOpt raw payload must carry the exact keys/shape the HiGHS path emits, since the shared
    # engine (_build_solution_sensitivity) consumes both identically.
    raw = _build_raw_sensitivity([-0.05, 0.01], [0.0, 0.2], n=2, has_return=True, n_extra=0, support=None)
    assert set(raw) == {"shadow_prices", "reduced_costs", "eligible", "ranging"}
    assert all(set(sp) == {"role", "linear_index", "value"} for sp in raw["shadow_prices"])
    assert len(raw["reduced_costs"]) == len(raw["eligible"]) == 2


def test_cuopt_payload_consumed_by_shared_engine():
    # End-to-end (CPU): the cuOpt raw payload flows through the shared marshaller into a typed
    # SolutionSensitivity exactly like HiGHS — proving engine parity without a GPU.
    from solvers._scalarization import _build_solution_sensitivity

    class _Obj:
        def __init__(self, name):
            self.name = name

    raw = _build_raw_sensitivity([-0.05, 0.012], [0.0, 0.3], n=2, has_return=True, n_extra=0, support=None)
    sens = _build_solution_sensitivity(raw, opt_names=["A", "B"], alloc_row=[0, 30],
                                       linear_idxs=[0], obj_list=[_Obj("Return")])
    assert sens.source == "solver_exact"
    assert [(sp.role, sp.name) for sp in sens.shadow_prices] == [
        ("budget", "budget"), ("return_floor", "Return")]
    assert [(rc.option, rc.allocation) for rc in sens.reduced_costs] == [("A", 0), ("B", 30)]


# ─── LP marshaling + dual extraction — CPU ───

def test_lp_to_csr_objective_and_rows():
    """Objective c = primary coef (negated to maximize, since cuOpt minimizes); rows = budget 'E'
    then one floor per eps_list entry with a direction-correct sense."""
    mu = np.array([0.10, 0.20, 0.15])
    yld = np.array([3.0, 4.0, 2.0])
    a = _lp_to_csr(mu, True, [(yld, 3.5, True)], max_weight=None, support=None)
    assert np.allclose(a["c"], -mu)                 # maximize → negated objective
    A = _dense(a["A_data"], a["A_indices"], a["A_offsets"], (2, 3))
    assert np.allclose(A[0], np.ones(3))            # budget row
    assert np.allclose(A[1], yld)                   # yield floor
    assert a["b"].tolist() == [1.0, 3.5]
    assert [t.decode() for t in a["row_types"]] == ["E", "G"]


def test_lp_to_csr_minimize_primary_box_and_support():
    a = _lp_to_csr(np.array([5.0, 6.0, 7.0]), False, [], max_weight=0.4, support=[0, 2])
    assert np.allclose(a["c"], [5.0, 6.0, 7.0])     # minimize → coefficients as-is
    assert a["var_ub"].tolist() == [0.4, 0.0, 0.4]  # off-support pinned to ub=0
    assert a["A_offsets"].size == 2                 # budget-only → one row


def test_lp_sensitivity_matrix_roles_and_eligibility():
    # rows in _lp_to_csr order: budget, one objective floor; 3 assets, asset 1 off-support.
    sol = _FakeSolution(dual=[-0.05, 0.3], reduced=[0.0, 0.1, 0.0])
    raw = _extract_cuopt_lp_sensitivity_matrix(sol, n=3, n_extra=1, support=[0, 2])
    # LP: the primary objective is optimized → no return_floor; budget + linear_floor only.
    assert [(s["role"], s["linear_index"]) for s in raw["shadow_prices"]] == [
        ("budget", None), ("linear_floor", 1)]
    assert raw["eligible"] == [True, False, True]
    assert raw["reduced_costs"] == [0.0, 0.1, 0.0]
    assert raw["ranging"] is None

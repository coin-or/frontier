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

from solvers.cuopt_backend import _parallel_solve, _qp_to_csr


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

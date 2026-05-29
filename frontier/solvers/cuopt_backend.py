"""cuOpt QP solver backend for Frontier's proportional portfolio problems.

Feasibility spike — Phase 4 of ``.claude/plans/cuopt-integration.md``. Scope guard:
the portfolio mean-variance QP only. This file is **additive, gated, reversible**
(plan P2):

  * **Gated.** ``_use_cuopt()`` returns True only when ``FRONTIER_SOLVER=cuopt``
    *and* the problem is a proportional allocation *and* it carries a quadratic
    interaction matrix (the portfolio-QP shape). Disabled by default, so every
    other problem still flows through the engine's NSGA paths unchanged.
  * **Reversible / portable.** cuOpt is imported lazily inside the inner solve,
    so this module imports cleanly on a machine with no GPU (macOS/arm64). Only
    an actual ``_solve_qp_cuopt`` call needs the GPU + ``cuopt-cu12`` — which is
    why the prototype runs in Google Colab.
  * **Contract-preserving.** ``_optimize_cuopt`` mirrors
    ``optimizer._optimize_proportional`` exactly: same signature, returns a
    ``Run`` of ``Solution``s in the identical shape, so explorer / metrics /
    store need zero changes.

EA ↔ cuOpt decomposition (plan P3). Frontier's NSGA path evolves weight vectors
directly, so there is no inner optimization for an exact solver to do. To make
"cuOpt as a subsolver inside the EA loop" literally true, the EA individual here
encodes a **scalarization parameter** — the epsilon-constraint return target — and
cuOpt maps that parameter to the optimal weights::

    EA individual → r_target → cuOpt solves  min wᵀΣw  s.t. μᵀw ≥ r_target, Σw=1, w≥0  → w* → (risk(w*), return(w*))

Honest caveat (plan P4): on a *convex* QP this makes the EA a frontier **walker** —
a plain epsilon-sweep matches it exactly, and that equivalence is the correctness
test (plan §4 mitigation a), not a selling point. The EA earns its keep only once
non-convex structure (cardinality / integer lots / min-position) makes r_target→w*
multimodal.

The inner QP mirrors NVIDIA's ``QP_portfolio_optimization.ipynb`` fixture (plan P5):
minimize variance ``wᵀΣw`` (monotone in volatility, so the argmin is identical to
what Frontier's ``√(wᵀΣw)`` risk objective would pick), long-only, fully invested.
"""

from __future__ import annotations

import os

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem as PymooProblem
from pymoo.optimize import minimize as pymoo_minimize

from ..engine import optimizer as _opt
from ..engine.models import (
    Aggregation,
    Approach,
    OptimizeMode,
    Problem,
    Run,
    Solution,
    _content_signature,
)

# Deliberately small for the spike (plan build-order step 3: "smallest pop/gen").
_SPIKE_POP = 30
_SPIKE_GEN = 15
# Dominate-everything cost assigned to scalarizations cuOpt reports infeasible.
_INFEASIBLE_PENALTY = 1e9


def _use_cuopt(problem: Problem) -> bool:
    """Gate: route to cuOpt only for the portfolio-QP shape, and only when asked.

    All three must hold (else the engine falls through to its NSGA paths):
      1. ``FRONTIER_SOLVER=cuopt`` is set (opt-in; default behaviour unchanged),
      2. the problem is a proportional allocation,
      3. it has a quadratic objective backed by an interaction matrix.

    Kept self-contained so it is correct whether called from ``optimize()`` or
    directly in a notebook.
    """
    if os.environ.get("FRONTIER_SOLVER", "").lower() != "cuopt":
        return False
    if problem.approach != Approach.proportional:
        return False
    if not any(o.aggregation == Aggregation.quadratic for o in problem.objectives):
        return False
    return len(_opt._build_interaction_matrices(problem)) > 0


def _resolve_objective_roles(problem: Problem) -> tuple[int, int]:
    """Identify the quadratic 'risk' objective (cuOpt minimizes its variance) and
    the linear 'return' objective the epsilon-constraint sweeps.

    Heuristic, not keyword matching: risk = the objective whose aggregation is
    quadratic; return = the first non-quadratic objective (its score column is μ).
    Returns ``(risk_idx, return_idx)``.
    """
    risk_idx = next(
        j for j, o in enumerate(problem.objectives)
        if o.aggregation == Aggregation.quadratic
    )
    return_idx = next(
        j for j, o in enumerate(problem.objectives)
        if o.aggregation != Aggregation.quadratic
    )
    return risk_idx, return_idx


def _round_weights_to_pct(
    w_frac: np.ndarray, n_options: int, max_allocation: int | None
) -> np.ndarray:
    """Round continuous fractional weights → integer percentages summing to 100.

    Copied intentionally (not refactored) from ``_optimize_proportional``
    (optimizer.py:1030-1051) so cuOpt allocations match the NSGA path's exact
    representation. Keeping it a copy leaves the NSGA path byte-for-byte untouched
    for this reversible spike (plan P2/P6).
    """
    x = np.asarray(w_frac, dtype=float) * 100.0
    raw = np.maximum(np.round(x), 0).astype(int)
    if max_allocation is not None:
        raw = np.minimum(raw, max_allocation)
    diff = 100 - int(raw.sum())
    if diff != 0:
        cap = max_allocation or 100
        if diff > 0:
            for _ in range(abs(diff)):
                headroom = cap - raw
                headroom[raw == 0] = 0  # don't create new holdings here
                if headroom.max() <= 0:
                    break
                raw[np.argmax(headroom)] += 1
        else:
            for _ in range(abs(diff)):
                if raw.max() <= 0:
                    break
                raw[np.argmax(raw)] -= 1
    return raw


def _nearest_psd(M: np.ndarray, rel_floor: float = 1e-8) -> np.ndarray:
    """Project a symmetric matrix onto the PSD cone by clipping eigenvalues.

    cuOpt's QP beta requires a PSD Q (plan §4 secondary risk). A tiny ``εI``
    jitter only fixes round-off; real covariance estimates built from
    asset-class correlations × volatilities (rather than a raw sample
    covariance) are frequently *indefinite* — the 30-ETF fixture here has a
    min eigenvalue near −83. So we symmetrize, clip every eigenvalue up to a
    small positive floor (relative to the spectrum), and rebuild. The floor
    keeps Q strictly positive-definite for clean solver conditioning.

    Only the cuOpt inner solve sees this projection; reported risk uses the
    ORIGINAL covariance via ``_ProportionalProblem`` so the projection never
    leaks into objective values.
    """
    A = 0.5 * (M + M.T)
    eigvals, eigvecs = np.linalg.eigh(A)
    floor = rel_floor * max(1.0, float(eigvals.max()))
    eigvals = np.maximum(eigvals, floor)
    A_psd = (eigvecs * eigvals) @ eigvecs.T
    return 0.5 * (A_psd + A_psd.T)  # re-symmetrize away float asymmetry


def _solve_qp_cuopt(
    cov: np.ndarray,
    mu: np.ndarray,
    target_return: float | None,
    return_maximize: bool,
    max_weight: float | None,
) -> tuple[np.ndarray, bool]:
    """One epsilon-constraint inner solve via cuOpt. Mirrors NVIDIA's
    ``QP_portfolio_optimization.ipynb`` fixture (plan P5)::

        minimize   wᵀΣw
        subject to Σw = 1,  0 ≤ w ≤ max_weight
                   μᵀw ≥ target_return     (epsilon-constraint, injected per individual)

    cuOpt is imported here (not at module top) so the module loads without a GPU.
    Returns ``(weights as fractions summing to 1, optimal_flag)``.
    """
    from cuopt.linear_programming.problem import Problem as CuProblem, MINIMIZE

    n = len(mu)
    prob = CuProblem("frontier_portfolio_qp")
    ub = float(max_weight) if max_weight is not None else 1.0
    w = [prob.addVariable(lb=0.0, ub=ub, name=f"w_{i}") for i in range(n)]

    # Quadratic objective wᵀΣw, built term-by-term exactly as the fixture does.
    quad = None
    for i in range(n):
        for j in range(n):
            c = float(cov[i, j])
            if abs(c) > 1e-12:
                term = c * w[i] * w[j]
                quad = term if quad is None else quad + term
    prob.setObjective(quad, sense=MINIMIZE)

    # Fully invested.
    prob.addConstraint(sum(w) == 1, name="fully_invested")

    # Epsilon-constraint on return. Direction-aware: ≥ for a maximize objective.
    if target_return is not None:
        ret_expr = sum(float(mu[i]) * w[i] for i in range(n))
        if return_maximize:
            prob.addConstraint(ret_expr >= float(target_return), name="return_target")
        else:
            prob.addConstraint(ret_expr <= float(target_return), name="return_target")

    prob.solve()
    if prob.Status != 1:  # 1 == optimal in the cuOpt LP/QP API
        return np.zeros(n), False
    weights = np.array([w[i].Value for i in range(n)], dtype=float)
    return weights, True


class _EpsilonConstraintProblem(PymooProblem):
    """pymoo problem whose single decision variable is the epsilon-constraint
    return target. cuOpt solves the inner QP per individual; objective values are
    computed by Frontier's own ``_ProportionalProblem._aggregate_objective`` so
    they are identical to the NSGA path (apples-to-apples for the Phase-5
    comparison).
    """

    def __init__(
        self,
        prop_problem: "_opt._ProportionalProblem",
        cov: np.ndarray,
        mu: np.ndarray,
        return_maximize: bool,
        max_weight: float | None,
        r_lo: float,
        r_hi: float,
    ):
        super().__init__(n_var=1, n_obj=prop_problem.n_obj, n_ieq_constr=1, xl=r_lo, xu=r_hi)
        self.prop = prop_problem  # reused Frontier aggregator (objective values)
        self.cov = cov
        self.mu = mu
        self.return_maximize = return_maximize
        self.max_weight = max_weight

    def _evaluate(self, X, out, *args, **kwargs):
        n_pop = X.shape[0]
        n_var = self.cov.shape[0]
        objectives = self.prop.objectives

        # Inner exact solve per individual; collect weights as 0-100 percentages
        # (the scale Frontier's aggregator expects).
        W_pct = np.zeros((n_pop, n_var))
        feasible = np.ones(n_pop, dtype=bool)
        for k in range(n_pop):
            w_frac, ok = _solve_qp_cuopt(
                self.cov, self.mu,
                target_return=float(X[k, 0]),
                return_maximize=self.return_maximize,
                max_weight=self.max_weight,
            )
            if ok:
                W_pct[k] = w_frac * 100.0
            else:
                feasible[k] = False

        # Objective values via Frontier's own aggregation, in pymoo's minimize
        # convention (negate maximize objectives) — identical to _ProportionalProblem.
        F = np.zeros((n_pop, len(objectives)))
        for j, obj in enumerate(objectives):
            natural = self.prop._aggregate_objective(W_pct, j)
            F[:, j] = -natural if obj.direction.value == "maximize" else natural

        # Penalize infeasible scalarizations so they're dominated and G-flagged.
        F[~feasible, :] = _INFEASIBLE_PENALTY
        out["F"] = F
        out["G"] = np.where(feasible, -1.0, 1.0).reshape(-1, 1)


def _optimize_cuopt(
    problem: Problem,
    mode: OptimizeMode,
    max_solutions: int | None = None,
    seed: int = 42,
) -> Run:
    """Portfolio-QP solve: the EA walks the epsilon-constraint return target while
    cuOpt solves each inner min-variance QP. Mirrors ``_optimize_proportional``'s
    contract (same signature; returns a ``Run`` of ``Solution``s, identical shape).
    """
    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    score_matrix = _opt._build_score_matrix(problem)
    cp = _opt._parse_constraints(problem)
    im = _opt._build_interaction_matrices(problem)

    risk_idx, return_idx = _resolve_objective_roles(problem)
    mu = score_matrix[:, return_idx]
    return_maximize = obj_list[return_idx].direction.value == "maximize"

    # Σ is a covariance: project onto the PSD cone for cuOpt's QP beta (plan §4
    # secondary risk). Reported risk uses the ORIGINAL matrix via ``prop`` below,
    # so the projection never leaks into results.
    cov = _nearest_psd(im[risk_idx])

    # max_allocation (%) → per-asset weight cap (fraction). Only linear caps for
    # the convex demo (plan §3); other constraints fall outside this spike's scope.
    max_weight = (cp["max_allocation"] / 100.0) if cp.get("max_allocation") else None

    # Reuse Frontier's proportional aggregator verbatim for objective values (P6).
    prop = _opt._ProportionalProblem(
        n_options=n_options, score_matrix=score_matrix, objectives=obj_list,
        interaction_matrices=im, **cp,
    )

    # Epsilon range = [global-min-variance return, best achievable return]. Lower
    # bound: the min-variance portfolio's return (one unconstrained cuOpt solve).
    # Upper bound: the best single-asset return (long-only, Σw=1 ⟹ max is max(μ)).
    # Mirrors the reference notebook's linspace(ret_mv, max(μ)) sweep range.
    w_mv, ok_mv = _solve_qp_cuopt(cov, mu, None, return_maximize, max_weight)
    r_lo = float(mu @ w_mv) if ok_mv else float(mu.min())
    r_hi = float(mu.max())
    if r_hi <= r_lo:
        r_hi = r_lo + 1e-6  # degenerate guard (all returns equal)

    pymoo_problem = _EpsilonConstraintProblem(
        prop, cov, mu, return_maximize, max_weight, r_lo, r_hi,
    )
    algorithm = NSGA2(pop_size=_SPIKE_POP)
    result = pymoo_minimize(
        pymoo_problem, algorithm, ("n_gen", _SPIKE_GEN), seed=seed, verbose=False,
    )

    # Marshal back: re-solve each Pareto epsilon to recover w*, convert to integer
    # percentages (copied redistribution logic), compute objective values via the
    # reused aggregator, and dedup identical portfolios (distinct epsilons below the
    # min-variance return all map to the same w*).
    solutions: list[Solution] = []
    seen: set[str] = set()
    if result.X is not None and len(np.atleast_2d(result.X)) > 0:
        eps_values = np.atleast_2d(result.X)[:, 0]
        for r_target in eps_values:
            w_frac, ok = _solve_qp_cuopt(cov, mu, float(r_target), return_maximize, max_weight)
            if not ok:
                continue
            raw = _round_weights_to_pct(w_frac, n_options, cp.get("max_allocation"))
            selected = [opt_names[i] for i in range(n_options) if raw[i] > 0]
            alloc_map = {opt_names[i]: int(raw[i]) for i in range(n_options)}
            sig = _content_signature(selected, alloc_map)
            if sig in seen:
                continue
            seen.add(sig)

            W_pct = raw.astype(float).reshape(1, -1)
            obj_values = {
                obj.name: round(float(prop._aggregate_objective(W_pct, j)[0]), 4)
                for j, obj in enumerate(obj_list)
            }
            solutions.append(Solution(
                solution_id=len(solutions),
                selected_options=selected,
                objective_values=obj_values,
                allocations=alloc_map,
            ))

    max_n = max_solutions or _opt.MAX_PARETO_SOLUTIONS
    solutions, total_found = _opt._prune_pareto(solutions, obj_list, max_n=max_n)
    solutions = _opt._sort_and_reindex(solutions, obj_list)
    return Run(
        solutions=solutions,
        total_pareto_found=total_found,
        quality=_opt._compute_quality(result, seed=seed),
        mode=mode,
        seed_used=seed,
    )

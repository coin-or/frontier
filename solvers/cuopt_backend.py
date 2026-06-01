"""cuOpt inner-solve backend for Frontier's exact NSGA-scalarization engine.

The NSGA outer loop, genome decoding, seeding, and result marshaling live in
``solvers._scalarization`` and are shared with the HiGHS backend; this module supplies only
the **cuOpt-specific inner solves** (a GPU convex QP and a GPU MILP) plus the gate and a thin
delegation. cuOpt and HiGHS differ *only* in these inner solves.

This is **additive, gated, reversible**: ``_use_cuopt()`` returns True only under
``FRONTIER_SOLVER=cuopt``; cuOpt is imported lazily *inside* each inner solve, so the module
loads cleanly on a machine with no GPU (an actual solve needs ``cuopt-cu12`` + a GPU, which
is why the prototype runs in Colab); and the engine's Run/Solution contract is preserved by
the shared engine, so explorer / metrics / store need no changes.

EA ↔ cuOpt decomposition: the EA individual encodes a scalarization parameter (the
epsilon-constraint return target, plus an asset-selection priority under a cardinality/group
cap), and cuOpt maps it to the optimal weights::

    EA individual → r_target → cuOpt: min wᵀΣw s.t. μᵀw ≥ r_target, Σw=1, w≥0 → w* → (risk, return)

On a convex QP this makes the EA a frontier *walker* (a plain epsilon sweep matches it); it
earns its keep once non-convex structure (cardinality / group caps) makes r_target→w*
multimodal, where the EA picks the support and cuOpt solves the continuous QP on it exactly.
"""

from __future__ import annotations

import gc
import os

import numpy as np

from engine import optimizer as _opt
from engine.models import Aggregation, Approach, OptimizeMode, Problem, Run
from solvers._scalarization import _qp_weights_ok, optimize_milp, optimize_qp

# Re-exported from the shared engine so notebooks/panels that reach into this module by its
# historical name (e.g. ``cuopt_backend._nearest_psd``) keep resolving after the extraction.
from solvers._scalarization import (  # noqa: F401  (back-compat re-exports)
    _build_milp_data,
    _group_limits,
    _nearest_psd,
    _resolve_linear_objectives,
    _resolve_objective_roles,
)

# Deliberately small EA budget (smallest pop/gen): each cuOpt call is an expensive GPU solve,
# so the total inner-solve count is kept bounded on Colab.
_SPIKE_POP = 30
_SPIKE_GEN = 15

# Binary-MILP path. Each cuOpt MILP solve gets a wall-clock cap and a mild relative gap.
# Without them, branch-and-bound finds the integer incumbent in <0.1s but then spends
# *minutes* certifying optimality across a ~0.05% gap; on a small Colab box that runaway
# exhausts host RAM (kernel restart) and, multiplied across the EA's many inner solves, never
# returns. A 0.1% gap on integer scores is sub-unit, so the returned incumbent is the exact
# optimum — only the (irrelevant) proof is skipped.
_MILP_TIME_LIMIT = 8.0   # seconds, hard cap per MILP solve
_MILP_REL_GAP = 1e-3     # stop B&B once the incumbent is within 0.1% of the bound
# Absolute MILP gap (default off). Set < the score granularity in code to make the
# bounded-mode incumbent provably optimal cheaply; `optimize(..., exact=True)` certifies.
# (The MILP EA pop/gen budget auto-scales in _scalarization._milp_budget — shared with HiGHS.)
_MILP_ABS_GAP = 0.0


def _use_cuopt(problem: Problem) -> bool:
    """Gate: route to cuOpt only when asked, for a shape it solves.

    Requires ``FRONTIER_SOLVER=cuopt`` and either a binary problem (→ exact MILP) or a
    proportional allocation with a quadratic objective backed by an interaction matrix (→
    QP, with cardinality/group caps handled by the EA support-search). Self-contained so it
    is correct whether called from ``optimize()`` or directly in a notebook.
    """
    if os.environ.get("FRONTIER_SOLVER", "").lower() != "cuopt":
        return False
    if problem.approach == Approach.binary:
        return True   # binary select-a-subset → exact cuOpt MILP path
    if problem.approach != Approach.proportional:
        return False
    if not any(o.aggregation == Aggregation.quadratic for o in problem.objectives):
        return False
    return len(_opt._build_interaction_matrices(problem)) > 0


def _solve_qp_cuopt(
    cov: np.ndarray,
    mu: np.ndarray,
    target_return: float | None,
    return_maximize: bool,
    max_weight: float | None,
    support: "np.ndarray | list[int] | None" = None,
    extra_linears: "list[tuple[np.ndarray, float, bool]] | None" = None,
) -> tuple[np.ndarray, bool]:
    """One epsilon-constraint inner solve via cuOpt. Mirrors NVIDIA's
    ``QP_portfolio_optimization.ipynb`` fixture::

        minimize   wᵀΣw
        subject to Σw = 1,  0 ≤ w ≤ max_weight
                   μᵀw ≥ target_return     (epsilon-constraint, injected per individual)

    Two optional extensions: ``support`` restricts holdable assets to an index set by pinning
    excluded assets' upper bound to 0 (cardinality — the EA picks which K, cuOpt solves the
    exact QP on that support, so it stays in the continuous-QP beta with no MIQP);
    ``extra_linears`` adds linear epsilon-constraints ``(coef, target, maximize)`` for >2
    objectives (e.g. a yield floor). cuOpt is imported here so the module loads without a GPU.
    Returns ``(weights as fractions summing to 1, optimal_flag)``.
    """
    from cuopt.linear_programming.problem import Problem as CuProblem, MINIMIZE

    n = len(mu)
    prob = CuProblem("frontier_portfolio_qp")
    ub = float(max_weight) if max_weight is not None else 1.0
    # Cardinality support: excluded assets get a 0 upper bound, so the QP is solved exactly
    # over the chosen subset without leaving the continuous beta.
    if support is None:
        ubs = [ub] * n
    else:
        supp = {int(i) for i in support}
        ubs = [ub if i in supp else 0.0 for i in range(n)]
    w = [prob.addVariable(lb=0.0, ub=ubs[i], name=f"w_{i}") for i in range(n)]

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

    # Epsilon-constraint on the primary (return) objective. Direction-aware: ≥ for a maximize
    # objective. Named so the dual (shadow price) is readable.
    if target_return is not None:
        ret_expr = sum(float(mu[i]) * w[i] for i in range(n))
        if return_maximize:
            prob.addConstraint(ret_expr >= float(target_return), name="return_target")
        else:
            prob.addConstraint(ret_expr <= float(target_return), name="return_target")

    # Extra linear epsilon-constraints (e.g. a yield floor) — one per objective beyond
    # risk+return, so the same QP serves 3+ objectives.
    for k, (coef, tgt, maximize) in enumerate(extra_linears or []):
        expr = sum(float(coef[i]) * w[i] for i in range(n))
        if maximize:
            prob.addConstraint(expr >= float(tgt), name=f"linear_{k}")
        else:
            prob.addConstraint(expr <= float(tgt), name=f"linear_{k}")

    prob.solve()
    # ``prob.Status`` is an ``LPTerminationStatus`` IntEnum. Accept BOTH certified Optimal
    # (==1) and PrimalFeasible (==7): cuOpt's PDLP (the first-order solver behind the QP beta)
    # frequently terminates PrimalFeasible rather than certified-Optimal on these convex QPs,
    # and NVIDIA's own portfolio reference treats both as solved.
    ok = getattr(prob.Status, "name", "") in ("Optimal", "PrimalFeasible")
    weights = np.array([w[i].Value for i in range(n)], dtype=float) if ok else np.zeros(n)
    # Status says "solved" but the returned point can still be degenerate (non-finite or off
    # the Σw=1 / box) — gate on the weights themselves, else one bad solve blows up the frontier.
    if ok and not _qp_weights_ok(weights, ub):
        weights, ok = np.zeros(n), False
    # Free the cuOpt problem before the next inner solve (the EA issues many).
    del prob
    gc.collect()
    return weights, ok


def _solve_milp_cuopt(min_coef, eps_list, mc, n, exact=False):
    """One binary MILP via cuOpt: minimize ``min_coef·x`` over x∈{0,1}ⁿ subject to epsilon
    constraints ``(coef, op, rhs)`` (op 'ge'/'le') and the combinatorial constraints in
    ``mc``. Returns ``(0/1 selection array, ok)``. ``exact=True`` certifies (gap→0, accept
    only ``Optimal``); default bounds for speed.
    """
    from cuopt.linear_programming import SolverSettings
    from cuopt.linear_programming.problem import INTEGER, MINIMIZE, Problem as CuProblem
    from cuopt.linear_programming.solver.solver_parameters import (
        CUOPT_MIP_ABSOLUTE_GAP,
        CUOPT_MIP_RELATIVE_GAP,
        CUOPT_TIME_LIMIT,
    )

    prob = CuProblem("frontier_milp")
    x = [prob.addVariable(lb=0.0, ub=1.0, vtype=INTEGER, name=f"x{i}") for i in range(n)]
    prob.setObjective(sum(float(min_coef[i]) * x[i] for i in range(n)), sense=MINIMIZE)
    for coef, op, rhs in eps_list:
        expr = sum(float(coef[i]) * x[i] for i in range(n))
        prob.addConstraint((expr >= float(rhs)) if op == "ge" else (expr <= float(rhs)), name="eps")
    if mc["card"] is not None:
        lo, hi = mc["card"]
        prob.addConstraint(sum(x) >= lo, name="card_lo")
        prob.addConstraint(sum(x) <= hi, name="card_hi")
    for coef, op, val in mc["bounds"]:
        expr = sum(float(coef[i]) * x[i] for i in range(n))
        prob.addConstraint((expr <= val) if op == "max" else (expr >= val), name="bound")
    for i in mc["force_in"]:
        prob.addConstraint(x[i] >= 1, name="fi")
    for i in mc["force_out"]:
        prob.addConstraint(x[i] <= 0, name="fo")
    for a, b in mc["deps"]:
        prob.addConstraint(x[a] - x[b] <= 0, name="dep")   # if a then b
    for a, b in mc["excl"]:
        prob.addConstraint(x[a] + x[b] <= 1, name="excl")
    for grp, gmax in mc["groups"]:
        prob.addConstraint(sum(x[i] for i in grp) <= gmax, name="grp")
    # Bounded (default, trades the optimality proof for speed) vs exact (gap→0, accept only
    # Optimal — _MILP_TIME_LIMIT still applies as a safety deadline). _MILP_ABS_GAP (default
    # off) sets an absolute gap on the bounded path; below the score granularity it certifies.
    settings = SolverSettings()
    if _MILP_TIME_LIMIT is not None:
        settings.set_parameter(CUOPT_TIME_LIMIT, _MILP_TIME_LIMIT)
    settings.set_parameter(CUOPT_MIP_RELATIVE_GAP, 0.0 if exact else _MILP_REL_GAP)
    if not exact and _MILP_ABS_GAP > 0:
        settings.set_parameter(CUOPT_MIP_ABSOLUTE_GAP, _MILP_ABS_GAP)
    prob.solve(settings)
    # MILP uses ``MILPTerminationStatus`` (NoTermination / Optimal / FeasibleFound) — a
    # DIFFERENT enum from the QP's ``LPTerminationStatus``. Bounded accepts Optimal AND
    # FeasibleFound (a time/gap stop = a proven-feasible incumbent); exact only Optimal.
    ok_statuses = ("Optimal",) if exact else ("Optimal", "FeasibleFound")
    ok = getattr(prob.Status, "name", "") in ok_statuses
    sel = np.array([round(x[i].Value) for i in range(n)], dtype=float) if ok else np.zeros(n)
    # Release the cuOpt problem's device/host buffers before the next inner solve.
    del prob
    gc.collect()
    return sel, ok


def _optimize_cuopt(
    problem: Problem,
    mode: OptimizeMode,
    max_solutions: int | None = None,
    seed: int = 42,
    exact: bool = False,
) -> Run:
    """Delegate to the shared NSGA-scalarization engine with the cuOpt inner solves: binary →
    exact MILP per scalarization, proportional → exact convex QP per scalarization. Returns a
    ``Run`` in the engine's exact shape (identical to the NSGA paths). ``exact`` certifies each
    MILP solve."""
    if problem.approach == Approach.binary:
        return optimize_milp(problem, mode, inner_milp=_solve_milp_cuopt,
                             max_solutions=max_solutions, seed=seed, exact=exact)
    return optimize_qp(problem, mode, inner_qp=_solve_qp_cuopt,
                       pop=_SPIKE_POP, gen=_SPIKE_GEN,
                       max_solutions=max_solutions, seed=seed)

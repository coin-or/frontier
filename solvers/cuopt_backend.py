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

import gc
import os

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem as PymooProblem
from pymoo.optimize import minimize as pymoo_minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

from engine import optimizer as _opt
from engine.models import (
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

# Binary-MILP path. Each cuOpt MILP solve gets a wall-clock cap and a mild relative
# gap. Without them, branch-and-bound finds the integer incumbent in <0.1s but then
# spends *minutes* certifying optimality across a ~0.05% gap; on a small Colab box
# that runaway exhausts host RAM (kernel restart) and, multiplied across the EA's
# many inner solves, never returns. A 0.1% gap on integer scores is sub-unit, so the
# returned incumbent is the exact optimum — only the (irrelevant) proof is skipped.
_MILP_TIME_LIMIT = 8.0   # seconds, hard cap per MILP solve
_MILP_REL_GAP = 1e-3     # stop B&B once the incumbent is within 0.1% of the bound
# EA budget for the MILP path. Each evaluation is an exact integer solve (not a cheap
# continuous QP), so the inner-solve count must stay bounded on Colab. Default None →
# auto-scale with problem size (see _milp_budget): small problems wash and stay cheap;
# large combinatorial ones get the budget to actually cover the frontier. Set to an int
# in a notebook to pin the budget (the tuning knob).
_MILP_POP: int | None = None
_MILP_GEN: int | None = None
# Absolute MILP gap (default off). Set < the score granularity in code to make the bounded-mode
# incumbent provably optimal cheaply; `optimize(..., exact=True)` is the bundled certify mode.
_MILP_ABS_GAP = 0.0


def _use_exact_backend(problem: Problem, solver: str = "cuopt") -> bool:
    """Gate: should this problem route to an exact-solver backend (vs the engine's NSGA paths)?

    The env opt-in (``FRONTIER_SOLVER`` ∈ {cuopt, highs}) is checked by the caller; ``solver``
    is that selection. Routing by shape:
      * binary (select-a-subset) → exact MILP — **both** backends handle it (cuOpt GPU / HiGHS CPU),
      * proportional + quadratic-objective-with-interaction-matrix → portfolio QP — **cuOpt only**
        (scipy/HiGHS has no quadratic objective), so 'highs' declines and it falls through to NSGA.

    Kept self-contained so it is correct whether called from ``optimize()`` or directly in a notebook.
    """
    if problem.approach == Approach.binary:
        return True   # exact MILP path — cuOpt or HiGHS
    if solver != "cuopt":
        return False  # only cuOpt has the QP path
    if problem.approach != Approach.proportional:
        return False
    if not any(o.aggregation == Aggregation.quadratic for o in problem.objectives):
        return False
    return len(_opt._build_interaction_matrices(problem)) > 0


# Back-compat alias: the original cuOpt-only gate name (callers/tests may import it).
def _use_cuopt(problem: Problem) -> bool:
    return os.environ.get("FRONTIER_SOLVER", "").lower() == "cuopt" and _use_exact_backend(problem, "cuopt")


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


def _resolve_linear_objectives(problem: Problem) -> list[int]:
    """All non-quadratic objective indices, in declaration order — the linear
    objectives the epsilon-constraint walks. The first is the 'return' role the
    2-objective path uses; any beyond it (e.g. yield, proof #2) become
    ``extra_linears`` floors on the same min-variance QP.
    """
    return [j for j, o in enumerate(problem.objectives)
            if o.aggregation != Aggregation.quadratic]


def _cardinality_k(problem: Problem) -> int | None:
    """Cardinality cap K (proof #1, 'hold at most K of N'). Reads the engine's own
    parsed ``cardinality_max`` so it matches the rest of the stack (the constraint is
    the existing ``CardinalityConstraint``). Returns None when there is no real cap
    (max == number of options), so the backend then behaves exactly as the verified
    convex path.
    """
    n = len(problem.options)
    k = _opt._parse_constraints(problem).get("cardinality_max", n)
    return int(k) if (k is not None and k < n) else None


def _group_limits(problem: Problem) -> list[tuple[list[int], int]]:
    """Per-group caps from ``group_limit`` constraints → ``[(option-index-list, max), …]``.
    Drives group-aware support selection so cuOpt respects "≤ max active per group"
    (e.g. supplier_selection's ≤3 suppliers per region), which the box/cardinality
    support alone does not enforce.
    """
    ix = {o.name: i for i, o in enumerate(problem.options)}
    return [([ix[o] for o in c.options], int(c.max))
            for c in (problem.constraints or []) if getattr(c, "type", "") == "group_limit"]


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
    x = np.where(np.isfinite(x), x, 0.0)  # NaN/inf → 0 before the int cast (NaN→int is garbage)
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


def _qp_weights_ok(weights: "np.ndarray | None", ub: float, tol: float = 1e-3) -> bool:
    """Feasibility gate on cuOpt's *returned* QP weights — not just its status.

    cuOpt's QP beta sometimes terminates ``PrimalFeasible`` on a degenerate point
    whose weights are non-finite or violate Σw=1 / the [0, ub] box. Status alone
    accepts those; the downstream ``avg``/``quadratic`` aggregation (and the
    NaN→int cast in ``_round_weights_to_pct``) then explode one point by ~1e21,
    blowing out the whole frontier plot. Reject them here so the scalarization is
    treated as infeasible (penalized / skipped), exactly the check the scipy CPU
    reference already applies. Pure + GPU-free so it is unit-testable on CPU.
    """
    if weights is None or not np.all(np.isfinite(weights)):
        return False
    if abs(float(weights.sum()) - 1.0) > tol:
        return False
    return bool(weights.min() >= -1e-6 and weights.max() <= ub + 1e-4)


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
    ``QP_portfolio_optimization.ipynb`` fixture (plan P5)::

        minimize   wᵀΣw
        subject to Σw = 1,  0 ≤ w ≤ max_weight
                   μᵀw ≥ target_return     (epsilon-constraint, injected per individual)

    Two optional, backward-compatible extensions power the bidirectional-benefit
    proofs — same convex QP, just more declared (existing 5-arg callers are unchanged):

      * ``support`` — restrict holdable assets to this index set by pinning every
        excluded asset's upper bound to 0 (proof #1, cardinality). The EA picks
        *which* K assets are eligible; cuOpt solves the exact QP on that support, so
        it stays inside cuOpt's continuous-QP beta — no MIQP needed.
      * ``extra_linears`` — additional linear epsilon-constraints ``(coef, target,
        maximize)`` for >2 objectives (proof #2, e.g. a yield floor). Each becomes
        ``coefᵀw ≥/≤ target`` while variance remains the objective.

    cuOpt is imported here (not at module top) so the module loads without a GPU.
    Returns ``(weights as fractions summing to 1, optimal_flag)``.
    """
    from cuopt.linear_programming.problem import Problem as CuProblem, MINIMIZE

    n = len(mu)
    prob = CuProblem("frontier_portfolio_qp")
    ub = float(max_weight) if max_weight is not None else 1.0
    # Cardinality support (proof #1): excluded assets get a 0 upper bound, so the QP
    # is solved exactly over the chosen subset without leaving the continuous beta.
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

    # Epsilon-constraint on the primary (return) objective. Direction-aware: ≥ for
    # a maximize objective. Named so the dual (shadow price) is readable (proof #4).
    if target_return is not None:
        ret_expr = sum(float(mu[i]) * w[i] for i in range(n))
        if return_maximize:
            prob.addConstraint(ret_expr >= float(target_return), name="return_target")
        else:
            prob.addConstraint(ret_expr <= float(target_return), name="return_target")

    # Extra linear epsilon-constraints (proof #2, e.g. a yield floor) — one per
    # objective beyond risk+return, so the same QP serves 3+ objectives.
    for k, (coef, tgt, maximize) in enumerate(extra_linears or []):
        expr = sum(float(coef[i]) * w[i] for i in range(n))
        if maximize:
            prob.addConstraint(expr >= float(tgt), name=f"linear_{k}")
        else:
            prob.addConstraint(expr <= float(tgt), name=f"linear_{k}")

    prob.solve()
    # ``prob.Status`` is an ``LPTerminationStatus`` IntEnum. Accept BOTH certified
    # Optimal (==1) and PrimalFeasible (==7): cuOpt's PDLP (the first-order solver
    # behind the QP beta) frequently terminates PrimalFeasible rather than
    # certified-Optimal on these convex QPs, and NVIDIA's own portfolio reference
    # treats both as solved. ``getattr`` guards the pre-solve int sentinel (-1).
    ok = getattr(prob.Status, "name", "") in ("Optimal", "PrimalFeasible")
    weights = np.array([w[i].Value for i in range(n)], dtype=float) if ok else np.zeros(n)
    # Status says "solved" but the returned point can still be degenerate (non-finite
    # or off the Σw=1 / box) — gate on the weights themselves, else one bad solve
    # blows up the frontier (see _qp_weights_ok).
    if ok and not _qp_weights_ok(weights, ub):
        weights, ok = np.zeros(n), False
    # Free the cuOpt problem before the next inner solve (the EA issues many).
    del prob
    gc.collect()
    return weights, ok


def _solve_individual(
    cov: np.ndarray,
    linear_coefs: list[np.ndarray],
    linear_maximize: list[bool],
    max_weight: float | None,
    eps: np.ndarray,
    support: "np.ndarray | None",
) -> tuple[np.ndarray, bool]:
    """Inner QP for one EA individual: minimize variance subject to every linear
    objective ``k`` meeting its epsilon target ``eps[k]``, restricted to ``support``.
    Shared by ``_CuOptFrontierProblem._evaluate`` and the marshaling re-solve so the
    two can never disagree on what an individual decodes to.
    """
    extra = [(linear_coefs[t], float(eps[t]), linear_maximize[t])
             for t in range(1, len(linear_coefs))]
    return _solve_qp_cuopt(
        cov, linear_coefs[0],
        target_return=float(eps[0]),
        return_maximize=linear_maximize[0],
        max_weight=max_weight,
        support=support,
        extra_linears=extra,
    )


class _CuOptFrontierProblem(PymooProblem):
    """Generalized epsilon-constraint genome powering the bidirectional-benefit proofs.

    Decision variables:
      * one epsilon target per **linear** objective (return, then any extras such as
        yield — proof #2), plus
      * when a cardinality cap K is set (proof #1), an N-length real *priority* vector
        whose top-K entries select the eligible assets.

    The original 2-objective walker is exactly the ``len(linear_coefs)==1`` /
    ``cardinality_k is None`` special case, so the verified convex path is preserved.
    cuOpt solves each inner QP exactly; objective values come back through Frontier's
    own ``_ProportionalProblem._aggregate_objective`` (apples-to-apples with NSGA).
    """

    def __init__(
        self,
        prop_problem: "_opt._ProportionalProblem",
        cov: np.ndarray,
        linear_coefs: list[np.ndarray],
        linear_maximize: list[bool],
        max_weight: float | None,
        eps_bounds: list[tuple[float, float]],
        cardinality_k: int | None = None,
        groups: "list[tuple[list[int], int]] | None" = None,
    ):
        self.prop = prop_problem  # reused Frontier aggregator (objective values)
        self.cov = cov
        self.linear_coefs = linear_coefs
        self.linear_maximize = linear_maximize
        self.max_weight = max_weight
        self.cardinality_k = cardinality_k
        self.groups = groups or []
        n_assets = cov.shape[0]
        xl = [b[0] for b in eps_bounds]
        xu = [b[1] for b in eps_bounds]
        if cardinality_k is not None or self.groups:    # + per-asset selection priorities
            xl = xl + [0.0] * n_assets
            xu = xu + [1.0] * n_assets
        super().__init__(n_var=len(xl), n_obj=prop_problem.n_obj,
                         n_ieq_constr=1, xl=np.array(xl), xu=np.array(xu))

    def _support_from_row(self, x_row: np.ndarray) -> "np.ndarray | None":
        """Decode the selection-priority tail of one genome row → eligible asset indices
        (the support cuOpt allocates over). ``None`` when unconstrained. Group-aware:
        keep the top-``max`` priorities **per group** (e.g. ≤3 per region) and, if a
        global cardinality cap is also set, the top-K of the remainder.
        """
        if self.cardinality_k is None and not self.groups:
            return None
        n_lin = len(self.linear_coefs)
        pri = np.asarray(x_row[n_lin:], dtype=float)
        n = len(pri)
        if self.groups:
            support, grouped = set(), set()
            for grp, gmax in self.groups:
                grouped.update(grp)
                support.update(int(i) for i in sorted(grp, key=lambda i: pri[i])[-gmax:])
            ungrouped = [i for i in range(n) if i not in grouped]
            if self.cardinality_k is not None:
                rem = max(0, self.cardinality_k - len(support))
                support.update(int(i) for i in sorted(ungrouped, key=lambda i: pri[i])[-rem:])
            else:
                support.update(ungrouped)
            return np.array(sorted(support))
        return np.argsort(pri)[-self.cardinality_k:]

    def _evaluate(self, X, out, *args, **kwargs):
        X = np.atleast_2d(X)
        n_pop = X.shape[0]
        n_assets = self.cov.shape[0]
        n_lin = len(self.linear_coefs)
        objectives = self.prop.objectives

        # Inner exact solve per individual; collect weights as 0-100 percentages
        # (the scale Frontier's aggregator expects).
        W_pct = np.zeros((n_pop, n_assets))
        feasible = np.ones(n_pop, dtype=bool)
        for k in range(n_pop):
            w_frac, ok = _solve_individual(
                self.cov, self.linear_coefs, self.linear_maximize,
                self.max_weight, X[k, :n_lin], self._support_from_row(X[k]),
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


def _nondominated(solutions: list[Solution], obj_list: list) -> list[Solution]:
    """Keep only the non-dominated front. The convex walker's marshaled points are
    already non-dominated, but integer-rounding after the per-individual re-solve can
    make a few **cardinality** portfolios (proof #1) dominate one another — so we
    re-filter in objective space (pymoo's minimize convention) before pruning, exactly
    as the engine's own merge path does. ``_prune_pareto`` only down-samples; it
    assumes a clean front, so this is what guarantees one.
    """
    if len(solutions) <= 1:
        return solutions
    F = np.array([
        [(-s.objective_values[o.name] if o.direction.value == "maximize"
          else s.objective_values[o.name]) for o in obj_list]
        for s in solutions
    ])
    keep = NonDominatedSorting().do(F, only_non_dominated_front=True)
    return [solutions[i] for i in keep]


def _seed_cardinality_population(
    linear_coefs: list[np.ndarray],
    cov: np.ndarray,
    eps_bounds: list[tuple[float, float]],
    k: int,
    pop: int,
    seed: int,
) -> np.ndarray:
    """Domain-informed initial population for the cardinality EA (proof #1).

    The support search is combinatorial, so at a small pop/gen the EA can miss the
    high-return corner (the support = the few top-return assets). We seed the initial
    population with sensible supports — **lowest-volatility K, highest-return K,
    highest return/vol K** — each across a span of return targets, so cuOpt solves
    those corner portfolios *exactly* from generation 0 and the EA refines around
    them. This is standard practice for cardinality-constrained portfolios, and every
    seeded support is still solved exactly by cuOpt — no hand-placed answers.

    Genome row = ``[eps per linear objective] + [priority vector]``; a support is
    selected by giving its assets the top-K priorities (≥0.7 vs ≤0.3 elsewhere).
    """
    rng = np.random.default_rng(seed)
    n_assets = cov.shape[0]
    vols = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    ret = np.asarray(linear_coefs[0], float)
    sharpe = ret / np.where(vols > 0, vols, 1e-9)
    supports = [np.argsort(vols)[:k], np.argsort(ret)[-k:], np.argsort(sharpe)[-k:]]
    lo0, hi0 = eps_bounds[0]
    n_frac = max(2, pop // (len(supports) * 2))
    rows: list[list[float]] = []
    for supp in supports:
        for frac in np.linspace(0.0, 1.0, n_frac):
            eps = [lo0 + frac * (hi0 - lo0)] + [b[0] for b in eps_bounds[1:]]
            pri = rng.uniform(0.0, 0.3, n_assets)
            pri[np.asarray(supp)] = rng.uniform(0.7, 1.0, len(supp))
            rows.append(eps + list(pri))
    while len(rows) < pop:                       # fill remainder with random genomes
        eps = [rng.uniform(b[0], b[1]) for b in eps_bounds]
        rows.append(eps + list(rng.uniform(0.0, 1.0, n_assets)))
    return np.array(rows[:pop], dtype=float)


# --------------------------------------------------------------------------- #
# Binary exact-MILP path (cuOpt's mature MILP, not the QP beta). For `binary`
# (select-a-subset) problems with linear-sum objectives: the EA evolves epsilon
# targets, cuOpt solves the scalarized 0/1 MILP exactly per individual. Mirrors the
# QP path's shape (Run/Solution identical). NOTE: assumes sum aggregation (linear).
# --------------------------------------------------------------------------- #
def _build_milp_data(problem: Problem):
    """Extract MILP ingredients from a Frontier binary problem: score matrix, objective
    directions, and the combinatorial constraints as index structures."""
    n = len(problem.options)
    names = [o.name for o in problem.options]
    ix = {nm: i for i, nm in enumerate(names)}
    S = _opt._build_score_matrix(problem)
    dirs = np.array([1.0 if o.direction.value == "minimize" else -1.0 for o in problem.objectives])
    ocol = {o.name: j for j, o in enumerate(problem.objectives)}
    mc = {"card": None, "bounds": [], "force_in": [], "force_out": [], "deps": [], "excl": [], "groups": []}
    for c in (problem.constraints or []):
        t = c.type
        if t == "cardinality":
            mc["card"] = (int(c.min), int(c.max))
        elif t == "objective_bound":
            mc["bounds"].append((S[:, ocol[c.objective]].copy(), c.operator, float(c.value)))
        elif t == "force_include":
            mc["force_in"].append(ix[c.option])
        elif t == "force_exclude":
            mc["force_out"].append(ix[c.option])
        elif t == "dependency":
            mc["deps"].append((ix[c.if_option], ix[c.then_option]))
        elif t == "exclusion_pair":
            mc["excl"].append((ix[c.option_a], ix[c.option_b]))
        elif t == "group_limit":
            mc["groups"].append(([ix[o] for o in c.options], int(c.max)))
    return n, names, S, dirs, mc


def _solve_milp_cuopt(min_coef, eps_list, mc, n, exact=False):
    """One binary MILP via cuOpt: minimize ``min_coef·x`` over x∈{0,1}^n subject to epsilon
    constraints ``(coef, op, rhs)`` (op 'ge'/'le') and the combinatorial constraints in ``mc``.
    Returns ``(0/1 selection array, ok)``. ``exact=True`` certifies (gap→0, accept only
    ``Optimal``); default bounds for speed. ``_solve_milp_highs`` is the CPU/HiGHS sibling with
    the identical signature — interchangeable via ``_milp_solver`` — so the EA-over-exact pattern
    is solver-agnostic (the coverage panel's two backends + the speed benchmark's GPU/CPU pair).
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
    # Optimal — _MILP_TIME_LIMIT still applies as a safety deadline). _MILP_ABS_GAP (default off)
    # sets an absolute gap on the bounded path; below the score granularity it certifies cheaply.
    settings = SolverSettings()
    if _MILP_TIME_LIMIT is not None:
        settings.set_parameter(CUOPT_TIME_LIMIT, _MILP_TIME_LIMIT)
    settings.set_parameter(CUOPT_MIP_RELATIVE_GAP, 0.0 if exact else _MILP_REL_GAP)
    if not exact and _MILP_ABS_GAP > 0:
        settings.set_parameter(CUOPT_MIP_ABSOLUTE_GAP, _MILP_ABS_GAP)
    prob.solve(settings)
    # MILP uses ``MILPTerminationStatus`` (NoTermination / Optimal / FeasibleFound) — a DIFFERENT
    # enum from the QP's ``LPTerminationStatus`` (PrimalFeasible). Bounded accepts Optimal AND
    # FeasibleFound (a time/gap stop = a proven-feasible incumbent, not certified); exact only Optimal.
    ok_statuses = ("Optimal",) if exact else ("Optimal", "FeasibleFound")
    ok = getattr(prob.Status, "name", "") in ok_statuses
    sel = np.array([round(x[i].Value) for i in range(n)], dtype=float) if ok else np.zeros(n)
    # Release the cuOpt problem's device/host buffers before the next inner solve — the
    # EA issues hundreds of these, and on a small Colab box the creep tips into OOM.
    del prob
    gc.collect()
    return sel, ok


def _solve_milp_highs(min_coef, eps_list, mc, n, exact=False):
    """The CPU/HiGHS sibling of ``_solve_milp_cuopt`` — same signature, same return — built on
    ``scipy.optimize.milp`` (which wraps the HiGHS solver). It makes the EA-over-exact pattern
    *solver-agnostic*: the coverage panel runs it as a second exact backend (NSGA + HiGHS) to
    show the pairing's value isn't cuOpt-specific, and the speed benchmark times it as the CPU
    baseline against cuOpt's GPU. HiGHS solves to optimality; the bounded path passes the same
    relative gap as cuOpt so the comparison is apples-to-apples (``exact=True`` → gap 0).
    """
    from scipy.optimize import Bounds, LinearConstraint, milp

    cons = []
    for coef, op, rhs in eps_list:
        a = np.asarray(coef, float)
        cons.append(LinearConstraint(a, rhs, np.inf) if op == "ge" else LinearConstraint(a, -np.inf, rhs))
    if mc["card"] is not None:
        lo, hi = mc["card"]
        cons.append(LinearConstraint(np.ones(n), lo, hi))
    for coef, op, val in mc["bounds"]:
        a = np.asarray(coef, float)
        cons.append(LinearConstraint(a, -np.inf, val) if op == "max" else LinearConstraint(a, val, np.inf))
    lb, ub = np.zeros(n), np.ones(n)
    for i in mc["force_in"]:
        lb[i] = 1.0
    for i in mc["force_out"]:
        ub[i] = 0.0
    for a, b in mc["deps"]:
        d = np.zeros(n); d[a] = 1.0; d[b] = -1.0; cons.append(LinearConstraint(d, -np.inf, 0.0))  # if a then b
    for a, b in mc["excl"]:
        e = np.zeros(n); e[a] = 1.0; e[b] = 1.0; cons.append(LinearConstraint(e, -np.inf, 1.0))
    for grp, gmax in mc["groups"]:
        g = np.zeros(n)
        for i in grp:
            g[i] = 1.0
        cons.append(LinearConstraint(g, -np.inf, gmax))
    options = {"mip_rel_gap": 0.0 if exact else _MILP_REL_GAP}
    res = milp(c=np.asarray(min_coef, float), constraints=cons, integrality=np.ones(n),
               bounds=Bounds(lb, ub), options=options)
    if not res.success or res.x is None:
        return np.zeros(n), False
    return np.round(res.x), True


def _milp_solver(name: str):
    """Resolve the exact-MILP solve fn by backend name, AT CALL TIME so a notebook/test
    monkeypatch of ``_solve_milp_cuopt`` (the GPU-free CPU dry-run does this) is honored."""
    return {"cuopt": _solve_milp_cuopt, "highs": _solve_milp_highs}[name]


class _MilpFrontierProblem(PymooProblem):
    """EA genome for the binary MILP path: one epsilon target per non-primary objective. The
    chosen exact solver (``solver`` — cuOpt or HiGHS) minimizes the primary objective exactly
    subject to those targets + the combinatorial constraints; the EA (NSGA-II) explores the
    epsilon space. Same genome whichever solver is plugged in (the pairing is solver-agnostic)."""

    def __init__(self, S, dirs, primary, nonprimary, mc, n, objectives, eps_bounds, exact=False, solver="cuopt"):
        self.S, self.dirs, self.primary, self.nonprimary = S, dirs, primary, nonprimary
        self.mc, self.n, self.objectives, self.exact, self.solver = mc, n, objectives, exact, solver
        super().__init__(n_var=len(nonprimary), n_obj=len(objectives), n_ieq_constr=1,
                         xl=np.array([b[0] for b in eps_bounds]),
                         xu=np.array([b[1] for b in eps_bounds]))

    def _solve_row(self, row):
        eps_list = [(self.S[:, j], "ge" if self.dirs[j] < 0 else "le", float(row[k]))
                    for k, j in enumerate(self.nonprimary)]
        return _milp_solver(self.solver)(self.dirs[self.primary] * self.S[:, self.primary], eps_list,
                                         self.mc, self.n, exact=self.exact)

    def _evaluate(self, X, out, *args, **kwargs):
        X = np.atleast_2d(X)
        F = np.zeros((X.shape[0], len(self.objectives)))
        feas = np.ones(X.shape[0], dtype=bool)
        for r in range(X.shape[0]):
            sel, ok = self._solve_row(X[r])
            if ok:
                for j, o in enumerate(self.objectives):
                    v = float(self.S[:, j] @ sel)
                    F[r, j] = -v if o.direction.value == "maximize" else v
            else:
                feas[r] = False
        F[~feas, :] = _INFEASIBLE_PENALTY
        out["F"] = F
        out["G"] = np.where(feas, -1.0, 1.0).reshape(-1, 1)


def _milp_budget(n: int) -> tuple[int, int]:
    """(pop, gen) for the MILP EA, scaled with the number of options ``n``.

    Unlike the NSGA path — where each evaluation is a cheap score lookup, so pop/gen can
    run to the hundreds (``_tune_parameters``) — every evaluation here is an *exact cuOpt
    MILP solve* (~seconds). The inner-solve count (≈ pop × gen) is the real budget, so it
    has to stay an order of magnitude below NSGA's. But a *fixed* small budget under-covers
    at scale: on the 120-project capital MILP, pop16×gen8 reaches only HV 0.64 (below
    NSGA's 0.68), while pop50×gen15 reaches HV 0.87 (above it). So ramp pop/gen with ``n``
    — small problems (which wash anyway at ≤30 vars) stay cheap; large combinatorial ones
    get the budget to actually fill the frontier. The module-level ``_MILP_POP``/
    ``_MILP_GEN``, when set, pin either value (the notebook tuning knob).

    Anchors: ``n ≤ 30 → (16, 8)`` (the wash regime); ``n ≥ 120 → (50, 15)`` (the verified
    covering budget); linearly interpolated between, then held flat past 120 so the
    inner-solve count can't run away on very large instances.
    """
    frac = min(1.0, max(0.0, (n - 30) / 90.0))   # 0 at n≤30, 1 at n≥120
    pop = _MILP_POP if _MILP_POP is not None else int(round(16 + frac * 34))   # 16 → 50
    gen = _MILP_GEN if _MILP_GEN is not None else int(round(8 + frac * 7))     # 8 → 15
    return pop, gen


def _optimize_cuopt_milp(problem, mode, max_solutions=None, seed=42, exact=False, solver="cuopt"):
    """Binary problems → exact MILP per scalarization. Same Run/Solution shape as the NSGA
    binary path, so downstream consumers are unaffected. ``exact`` (from ``optimize``) certifies
    each inner solve instead of gap/time-bounding it. ``solver`` ('cuopt'|'highs') picks the
    exact backend — the EA machinery is identical either way (the pairing is solver-agnostic)."""
    n, names, S, dirs, mc = _build_milp_data(problem)
    objs = problem.objectives
    primary = 0
    nonprimary = [j for j in range(len(objs)) if j != primary]
    solve = _milp_solver(solver)

    # epsilon range per non-primary objective = [min, max] over feasible sets.
    eps_bounds = []
    for j in nonprimary:
        smin, ok1 = solve(S[:, j], [], mc, n, exact=exact)
        smax, ok2 = solve(-S[:, j], [], mc, n, exact=exact)
        lo = float(S[:, j] @ smin) if ok1 else float(S[:, j].min())
        hi = float(S[:, j] @ smax) if ok2 else float(S[:, j].sum())
        eps_bounds.append((lo, hi if hi > lo else lo + 1e-6))

    pp = _MilpFrontierProblem(S, dirs, primary, nonprimary, mc, n, objs, eps_bounds, exact=exact, solver=solver)
    pop, gen = _milp_budget(n)
    result = pymoo_minimize(pp, NSGA2(pop_size=pop), ("n_gen", gen), seed=seed, verbose=False)

    solutions: list[Solution] = []
    seen: set = set()
    if result.X is not None and len(np.atleast_2d(result.X)) > 0:
        for row in np.atleast_2d(result.X):
            sel, ok = pp._solve_row(row)
            if not ok:
                continue
            selected = [names[i] for i in range(n) if sel[i] > 0.5]
            key = tuple(sorted(selected))
            if key in seen:
                continue
            seen.add(key)
            obj_values = {o.name: round(float(S[:, j] @ sel), 4) for j, o in enumerate(objs)}
            solutions.append(Solution(solution_id=len(solutions), selected_options=selected,
                                      objective_values=obj_values))

    solutions = _nondominated(solutions, objs)
    max_n = max_solutions or _opt.MAX_PARETO_SOLUTIONS
    solutions, total = _opt._prune_pareto(solutions, objs, max_n=max_n)
    solutions = _opt._sort_and_reindex(solutions, objs)
    return Run(solutions=solutions, total_pareto_found=total,
               quality=_opt._compute_quality(result, seed=seed), mode=mode, seed_used=seed)


def _optimize_cuopt(
    problem: Problem,
    mode: OptimizeMode,
    max_solutions: int | None = None,
    seed: int = 42,
    exact: bool = False,
    solver: str = "cuopt",
) -> Run:
    """Portfolio-QP solve: the EA walks an epsilon-constraint target per linear
    objective (and, under a cardinality cap, the asset-selection priorities) while
    cuOpt solves each inner min-variance QP exactly. Mirrors
    ``_optimize_proportional``'s contract (same signature; returns a ``Run`` of
    ``Solution``s, identical shape — so explorer / metrics / store need no changes).

    Generalized for the bidirectional-benefit proofs: ≥2 objectives (extra linear
    floors, proof #2) and 'hold ≤ K of N' cardinality (proof #1). With one linear
    objective and no cardinality this is the verified convex walker unchanged.
    Binary (`select-a-subset`) problems route to the exact MILP path instead, where
    ``solver`` ('cuopt'|'highs') selects the exact backend. The QP path is cuOpt-only.
    """
    if problem.approach == Approach.binary:
        return _optimize_cuopt_milp(problem, mode, max_solutions=max_solutions, seed=seed,
                                    exact=exact, solver=solver)

    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    score_matrix = _opt._build_score_matrix(problem)
    cp = _opt._parse_constraints(problem)
    im = _opt._build_interaction_matrices(problem)

    risk_idx, _ = _resolve_objective_roles(problem)
    linear_idxs = _resolve_linear_objectives(problem)
    linear_coefs = [score_matrix[:, j] for j in linear_idxs]
    linear_maximize = [obj_list[j].direction.value == "maximize" for j in linear_idxs]

    # Σ is a covariance: project onto the PSD cone for cuOpt's QP beta (plan §4
    # secondary risk). Reported risk uses the ORIGINAL matrix via ``prop`` below,
    # so the projection never leaks into results.
    cov = _nearest_psd(im[risk_idx])

    # max_allocation (%) → per-asset weight cap (fraction). Linear box cap stays
    # convex (plan §3). Cardinality (proof #1) is handled in the genome, not here.
    max_weight = (cp["max_allocation"] / 100.0) if cp.get("max_allocation") else None
    cardinality_k = _cardinality_k(problem)
    groups = _group_limits(problem)   # per-group caps (e.g. ≤3 per region) → group-aware support

    # Reuse Frontier's proportional aggregator verbatim for objective values (P6).
    prop = _opt._ProportionalProblem(
        n_options=n_options, score_matrix=score_matrix, objectives=obj_list,
        interaction_matrices=im, **cp,
    )

    # Epsilon range per linear objective = [value at the global min-variance
    # portfolio, best single-asset value]. Lower bound from one unconstrained cuOpt
    # solve; upper bound max(coef) (long-only, Σw=1). Infeasibly-high targets are
    # simply penalized in the genome. Mirrors the reference notebook's linspace.
    w_mv, ok_mv = _solve_qp_cuopt(cov, linear_coefs[0], None, linear_maximize[0], max_weight)
    eps_bounds: list[tuple[float, float]] = []
    for coef in linear_coefs:
        lo = float(coef @ w_mv) if ok_mv else float(coef.min())
        hi = float(coef.max())
        if hi <= lo:
            hi = lo + 1e-6  # degenerate guard (all values equal)
        eps_bounds.append((lo, hi))

    pymoo_problem = _CuOptFrontierProblem(
        prop, cov, linear_coefs, linear_maximize, max_weight, eps_bounds, cardinality_k, groups,
    )
    # Cardinality (proof #1): seed the combinatorial support search with domain-informed
    # supports so cuOpt reaches the exact corners even at the spike's small pop/gen.
    if cardinality_k is not None:
        seed_X = _seed_cardinality_population(
            linear_coefs, cov, eps_bounds, cardinality_k, _SPIKE_POP, seed)
        algorithm = NSGA2(pop_size=_SPIKE_POP, sampling=seed_X)
    else:
        algorithm = NSGA2(pop_size=_SPIKE_POP)
    result = pymoo_minimize(
        pymoo_problem, algorithm, ("n_gen", _SPIKE_GEN), seed=seed, verbose=False,
    )

    # Marshal back: re-decode each Pareto individual (epsilon targets + cardinality
    # support) through the SAME problem object, re-solve to recover w*, convert to
    # integer percentages (copied redistribution logic), compute objective values via
    # the reused aggregator, and dedup identical portfolios (distinct genomes can map
    # to the same w*).
    n_lin = len(linear_coefs)
    solutions: list[Solution] = []
    seen: set[str] = set()
    if result.X is not None and len(np.atleast_2d(result.X)) > 0:
        for row in np.atleast_2d(result.X):
            w_frac, ok = _solve_individual(
                cov, linear_coefs, linear_maximize, max_weight,
                row[:n_lin], pymoo_problem._support_from_row(row),
            )
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

    solutions = _nondominated(solutions, obj_list)  # rounding can dominate (proof #1)
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

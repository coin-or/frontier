"""Shared NSGA-driven epsilon-constraint scalarization engine for Frontier's exact backends.

A multi-objective problem is decomposed by an EA (pymoo NSGA-II) that evolves
epsilon-constraint scalarization targets — and, under a cardinality/group cap, an N-length
asset *selection-priority* vector — while an injected **inner solver** solves each scalarized
single-objective problem to optimality. The Pareto frontier is assembled from those exact
inner optima. The EA complements NSGA's search: it explores the scalarization space, the
inner solver makes each evaluated point optimal rather than heuristic.

cuOpt (GPU) and HiGHS (CPU) are the two backends, and they differ **only** in the injected
inner solve — so the NSGA loop, genome decoding, seeding, and result marshaling live here,
once. Each backend supplies inner solves matching these contracts:

  * QP  ``inner_qp(cov, mu, target_return, return_maximize, max_weight, support,
                   extra_linears) -> (weights_frac, ok)``
        min wᵀ(cov)w  s.t. Σw=1, 0≤w≤max_weight (0 for assets off ``support``),
        mu·w ≥/≤ target_return, and each ``(coef, target, maximize)`` in ``extra_linears``.
  * MILP ``inner_milp(min_coef, eps_list, mc, n, exact) -> (selection_01, ok)``
        min min_coef·x  over x∈{0,1}ⁿ  s.t. each ``(coef, op, rhs)`` in ``eps_list`` (op
        'ge'/'le') and the combinatorial constraints in ``mc``.

For a convex QP the EA is a frontier *walker* — an epsilon sweep matches it — so it earns
its keep on the non-convex structure (cardinality / group caps) where the support choice is
combinatorial. The inner solver solves the *continuous* QP on each chosen support exactly,
so no MIQP is needed even when the overall shape is mixed-integer-quadratic.
"""

from __future__ import annotations

import time

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem as PymooProblem
from pymoo.optimize import minimize as pymoo_minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

from engine import optimizer as _opt
from engine.models import (
    Aggregation,
    OptimizeMode,
    Problem,
    ReducedCost,
    Run,
    ShadowPrice,
    Solution,
    SolutionSensitivity,
    _content_signature,
)

# Cost assigned to scalarizations the inner solver reports infeasible, so they are dominated
# and constraint-flagged in the EA.
_INFEASIBLE_PENALTY = 1e9

# MILP EA budget, auto-scaled with the number of options ``n``. Each evaluation is an exact
# integer solve (~seconds on a GPU, ~tens of ms on the CPU), so the inner-solve count
# (≈ pop × gen) is the real budget — an order of magnitude below the NSGA path's cheap-eval
# budget. A *fixed* small budget under-covers at scale: on the 120-project capital MILP,
# pop16×gen8 reaches only HV 0.64 (below NSGA's 0.68), while pop50×gen15 reaches 0.87 (above
# it). So ramp pop/gen with ``n`` — small problems (≤30 vars, which wash anyway) stay cheap;
# large combinatorial ones get the budget to actually fill the frontier. Set _MILP_POP /
# _MILP_GEN to pin either value (the notebook tuning knob). Shared by both backends.
_MILP_POP: int | None = None
_MILP_GEN: int | None = None


def _milp_budget(n: int) -> tuple[int, int]:
    """(pop, gen) for the MILP EA, scaled with the option count ``n``. Anchors: ``n ≤ 30 →
    (16, 8)`` (the wash regime), ``n ≥ 120 → (50, 15)`` (the verified covering budget),
    linearly interpolated between and held flat past 120 so the inner-solve count can't run
    away. ``_MILP_POP`` / ``_MILP_GEN``, when set, pin either value."""
    frac = min(1.0, max(0.0, (n - 30) / 90.0))   # 0 at n≤30, 1 at n≥120
    pop = _MILP_POP if _MILP_POP is not None else int(round(16 + frac * 34))   # 16 → 50
    gen = _MILP_GEN if _MILP_GEN is not None else int(round(8 + frac * 7))     # 8 → 15
    return pop, gen


# --------------------------------------------------------------------------- #
# Problem readers (pure)
# --------------------------------------------------------------------------- #
def _resolve_objective_roles(problem: Problem) -> tuple[int, int]:
    """Identify the quadratic 'risk' objective (variance is the QP's minimand) and the linear
    'return' objective the epsilon-constraint sweeps. Heuristic, not keyword matching: risk =
    the objective whose aggregation is quadratic; return = the first non-quadratic objective.
    Returns ``(risk_idx, return_idx)``.
    """
    risk_idx = next(j for j, o in enumerate(problem.objectives)
                    if o.aggregation == Aggregation.quadratic)
    return_idx = next(j for j, o in enumerate(problem.objectives)
                      if o.aggregation != Aggregation.quadratic)
    return risk_idx, return_idx


def _resolve_linear_objectives(problem: Problem) -> list[int]:
    """All non-quadratic objective indices, in declaration order — the linear objectives the
    epsilon-constraint walks. The first is the 'return' role; any beyond it become extra
    linear floors on the same min-variance QP."""
    return [j for j, o in enumerate(problem.objectives)
            if o.aggregation != Aggregation.quadratic]


def _cardinality_k(problem: Problem) -> int | None:
    """Cardinality cap K ('hold at most K of N'), read from the engine's own parsed
    ``cardinality_max`` so it matches the rest of the stack. None when there is no real cap
    (max == number of options), so the backend then behaves exactly as the convex path."""
    n = len(problem.options)
    k = _opt._parse_constraints(problem).get("cardinality_max", n)
    return int(k) if (k is not None and k < n) else None


def _group_limits(problem: Problem) -> list[tuple[list[int], int, int]]:
    """Per-group bounds from ``group_limit`` constraints → ``[(option-index-list, min, max), …]``.
    Caps drive group-aware support selection (e.g. ≤3 active per region); floors are MILP rows
    on the binary path (the proportional exact gate declines them — a count of active options
    is combinatorial, outside the QP/LP scope)."""
    ix = {o.name: i for i, o in enumerate(problem.options)}
    return [([ix[o] for o in c.options], int(getattr(c, "min", 0) or 0), int(c.max))
            for c in (problem.constraints or []) if getattr(c, "type", "") == "group_limit"]


def _build_milp_data(problem: Problem):
    """Extract MILP ingredients from a binary problem: score matrix, per-objective
    minimize-convention directions, and the combinatorial constraints as index structures."""
    n = len(problem.options)
    names = [o.name for o in problem.options]
    ix = {nm: i for i, nm in enumerate(names)}
    S = _opt._build_score_matrix(problem)
    dirs = np.array([1.0 if o.direction.value == "minimize" else -1.0 for o in problem.objectives])
    ocol = {o.name: j for j, o in enumerate(problem.objectives)}

    def _ref(name, kind, c):
        # A stored constraint can outlive an option/objective rename — decline in words
        # instead of a raw KeyError inside audit/exact consumers.
        table = ix if kind == "option" else ocol
        if name not in table:
            raise ValueError(f"constraint {c.type} references unknown {kind} '{name}' — "
                             "update or remove that constraint (model update), then retry.")
        return table[name]

    mc = {"card": None, "bounds": [], "force_in": [], "force_out": [], "deps": [], "excl": [], "groups": []}
    for c in (problem.constraints or []):
        t = c.type
        if t == "cardinality":
            mc["card"] = (int(c.min), int(c.max))
        elif t == "objective_bound":
            mc["bounds"].append((S[:, _ref(c.objective, "objective", c)].copy(), c.operator, float(c.value)))
        elif t == "force_include":
            mc["force_in"].append(_ref(c.option, "option", c))
        elif t == "force_exclude":
            mc["force_out"].append(_ref(c.option, "option", c))
        elif t == "dependency":
            mc["deps"].append((_ref(c.if_option, "option", c), _ref(c.then_option, "option", c)))
        elif t == "exclusion_pair":
            mc["excl"].append((_ref(c.option_a, "option", c), _ref(c.option_b, "option", c)))
        elif t == "group_limit":
            mc["groups"].append(([_ref(o, "option", c) for o in c.options],
                                 int(getattr(c, "min", 0) or 0), int(c.max)))
    return n, names, S, dirs, mc


# --------------------------------------------------------------------------- #
# Numeric helpers (pure)
# --------------------------------------------------------------------------- #
# _round_weights_to_pct lives in engine.optimizer (shared with the NSGA
# proportional path); re-exported here for the backends.
_round_weights_to_pct = _opt._round_weights_to_pct

def _nearest_psd(M: np.ndarray, rel_floor: float = 1e-8) -> np.ndarray:
    """Project a symmetric matrix onto the PSD cone by clipping eigenvalues up to a small
    positive floor, so a convex QP solver accepts the covariance. Covariance estimates built
    from correlations × volatilities are frequently indefinite; only the inner solve sees
    this projection — reported risk uses the ORIGINAL matrix via the engine's aggregator."""
    A = 0.5 * (M + M.T)
    eigvals, eigvecs = np.linalg.eigh(A)
    floor = rel_floor * max(1.0, float(eigvals.max()))
    eigvals = np.maximum(eigvals, floor)
    A_psd = (eigvecs * eigvals) @ eigvecs.T
    return 0.5 * (A_psd + A_psd.T)  # re-symmetrize away float asymmetry


def _weight_box(n, max_weight, min_weight, support):
    """Per-variable ``(ubs, lbs)`` lists from scalar-or-vector bounds; off-``support`` assets
    pin to a zero box. A floored asset dropped from support makes the box infeasible
    (lb>ub=0) — the inner solver reports infeasible and the EA discards that support choice,
    which is correct. Shared by the HiGHS and cuOpt inner solves."""
    ub_vec = np.broadcast_to(np.asarray(max_weight if max_weight is not None else 1.0,
                                        dtype=float), (n,))
    lb_vec = np.broadcast_to(np.asarray(min_weight if min_weight is not None else 0.0,
                                        dtype=float), (n,))
    if support is None:
        return [float(u) for u in ub_vec], [float(l) for l in lb_vec]
    supp = {int(i) for i in support}
    # Off-support: ub pins to 0; the lb keeps its floor so a floored asset dropped from
    # support is infeasible AT THE SOLVER (lb>ub), not merely rejected by the post-gate.
    return ([float(ub_vec[i]) if i in supp else 0.0 for i in range(n)],
            [float(lb_vec[i]) for i in range(n)])


def _box_infeasible(ubs, lbs, tol: float = 1e-12) -> bool:
    """True when the weight box is empty (some lb > ub) — a floored asset dropped from
    ``support``. The scalarization is infeasible before a solver model exists; callers must
    short-circuit, because highspy raises on ``addVariable(lb > ub)`` (and cuOpt's DataModel
    rejects an empty box) instead of reporting infeasibility."""
    return any(l > u + tol for u, l in zip(ubs, lbs))


def _qp_weights_ok(weights: "np.ndarray | None", ub, lb=None, *, tol: float = 1e-3) -> bool:
    """Feasibility gate on a QP solver's *returned* weights — not just its status. First-order
    QP solvers can terminate 'solved' on a degenerate point whose weights are non-finite or
    violate Σw=1 / the [lb, ub] box; the downstream aggregation then explodes one point and
    blows out the frontier. Reject those here so the scalarization is treated as infeasible.
    ``ub``/``lb`` are a scalar or a per-option vector (allocation_bound constraints)."""
    if weights is None or not np.all(np.isfinite(weights)):
        return False
    if abs(float(weights.sum()) - 1.0) > tol:
        return False
    ub_vec = np.broadcast_to(np.asarray(ub if ub is not None else 1.0, dtype=float), weights.shape)
    lb_vec = np.broadcast_to(np.asarray(lb if lb is not None else 0.0, dtype=float), weights.shape)
    return bool(np.all(weights >= lb_vec - 1e-6) and np.all(weights <= ub_vec + 1e-4))


def _nondominated(solutions: list[Solution], obj_list: list) -> list[Solution]:
    """Keep only the non-dominated front. Marshaled convex-walker points are already
    non-dominated, but integer rounding after the per-individual re-solve can make a few
    cardinality portfolios dominate one another — so re-filter in objective space (minimize
    convention) before pruning, which only down-samples and assumes a clean front."""
    if len(solutions) <= 1:
        return solutions
    F = np.array([
        [(-s.objective_values[o.name] if o.direction.value == "maximize"
          else s.objective_values[o.name]) for o in obj_list]
        for s in solutions
    ])
    keep = NonDominatedSorting().do(F, only_non_dominated_front=True)
    return [solutions[i] for i in keep]


def _seed_cardinality_population(linear_coefs, cov, eps_bounds, k, pop, seed,
                                 linear_maximize=None) -> np.ndarray:
    """Domain-informed initial population for the cardinality EA. The support search is
    combinatorial, so at a small pop/gen the EA can miss the best-primary corner. Seed with
    sensible supports — lowest-volatility K, best-primary K, best primary/vol K — each
    across a span of primary targets, so the inner solver reaches those corners exactly from
    generation 0 and the EA refines around them. Every seeded support is still solved exactly.
    ``linear_maximize`` orients the seeds per objective: the best-primary support flips for a
    minimize primary (e.g. cost), and each extra objective's seed epsilon sits at its LOOSE end
    (floor low for maximize, ceiling high for minimize) so seeded inner solves stay feasible.

    Genome row = ``[eps per linear objective] + [priority vector]``; a support is selected by
    giving its assets the top-K priorities (≥0.7 vs ≤0.3 elsewhere)."""
    if linear_maximize is None:
        linear_maximize = [True] * len(linear_coefs)
    rng = np.random.default_rng(seed)
    n_assets = cov.shape[0]
    vols = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    ret = np.asarray(linear_coefs[0], float) * (1.0 if linear_maximize[0] else -1.0)
    # Goodness-per-volatility must stay volatility-PENALIZING for oriented values of any
    # sign (a raw ratio inverts once oriented values go negative on a minimize primary),
    # so shift goodness to non-negative before dividing.
    goodness = ret - ret.min()
    sharpe = goodness / np.where(vols > 0, vols, 1e-9)
    supports = [np.argsort(vols)[:k], np.argsort(ret)[-k:], np.argsort(sharpe)[-k:]]
    lo0, hi0 = eps_bounds[0]
    loose_rest = [b[0] if mx else b[1]
                  for b, mx in zip(eps_bounds[1:], linear_maximize[1:])]
    n_frac = max(2, pop // (len(supports) * 2))
    rows: list[list[float]] = []
    for supp in supports:
        for frac in np.linspace(0.0, 1.0, n_frac):
            eps = [lo0 + frac * (hi0 - lo0)] + loose_rest
            pri = rng.uniform(0.0, 0.3, n_assets)
            pri[np.asarray(supp)] = rng.uniform(0.7, 1.0, len(supp))
            rows.append(eps + list(pri))
    while len(rows) < pop:                       # fill remainder with random genomes
        eps = [rng.uniform(b[0], b[1]) for b in eps_bounds]
        rows.append(eps + list(rng.uniform(0.0, 1.0, n_assets)))
    return np.array(rows[:pop], dtype=float)


# --------------------------------------------------------------------------- #
# Anchor corners (per-objective extremes)
#
# The EA's epsilon sweep samples the scalarization box stochastically, so it can leave the
# frontier's per-objective extreme corners under-covered — the "exact looks short of NSGA at
# a linear extreme" artifact. These helpers add one anchor scalarization per objective (the
# classic epsilon-constraint payoff-table step), so every exact overlay — full pass or
# progressive certify — samples the true corners regardless of the sweep's budget. Anchors
# flow through the same inner solves and marshaling as every other point (dedup'd by content
# signature, dominance-filtered), so the change is strictly additive.
# --------------------------------------------------------------------------- #
def _box_extreme(coef, maximize, max_weight, min_weight=None) -> float:
    """Feasible extreme of a linear objective over the budget+box region (Σw=1, lo≤w≤cap),
    closed form: satisfy every floor, then fill the best assets to their caps. Unlike
    ``coef.max()`` (the best single asset), this value is reachable under the box, so it
    makes a solvable epsilon target for an anchor corner. ``max_weight``/``min_weight``
    are a scalar or per-option vector."""
    coef = np.asarray(coef, dtype=float)
    n = len(coef)
    cap = np.broadcast_to(np.asarray(max_weight if max_weight is not None else 1.0,
                                     dtype=float), (n,)).copy()
    lo = np.broadcast_to(np.asarray(min_weight if min_weight is not None else 0.0,
                                    dtype=float), (n,)).copy()
    order = np.argsort(coef)
    if maximize:
        order = order[::-1]
    w = lo.copy()                       # floors first — they're spent budget
    remaining = 1.0 - float(lo.sum())
    for i in order:
        take = min(cap[i] - w[i], max(remaining, 0.0))
        w[i] += take
        remaining -= take
        if remaining <= 1e-12:
            break
    return float(coef @ w)


def _allocation_bound_vectors(problem: Problem, cp: dict):
    """Per-option weight-fraction ``(lo, hi)`` vectors from ``allocation_bound`` constraints
    AND the force_include / force_exclude sets, or ``(None, None)`` when none apply. ``hi``
    folds in the global ``max_allocation`` cap (effective cap = min of the two).
    force_exclude pins ``hi`` to 0; force_include lifts ``lo`` to 1% — the engine's activity
    grid (NSGA treats >0.5% as active on the integer-percent representation), so the exact
    paths honor the same membership constraints the EA enforces."""
    ab = cp.get("allocation_bounds") or {}
    forced_in = cp.get("forced_in") or set()
    forced_out = cp.get("forced_out") or set()
    if not ab and not forced_in and not forced_out:
        return None, None
    n = len(problem.options)
    cap = (cp["max_allocation"] / 100.0) if cp.get("max_allocation") else 1.0
    lo, hi = np.zeros(n), np.full(n, cap)
    for i, (l, h) in ab.items():
        lo[i] = l / 100.0
        hi[i] = min(cap, h / 100.0)
    for i in forced_in:
        lo[i] = max(lo[i], 0.01)
    for i in forced_out:
        hi[i] = 0.0
        lo[i] = 0.0
    return lo, hi


def _model_bound_rows(problem: Problem, score_matrix) -> tuple[list, list[str]]:
    """Model-level ``objective_bound`` constraints as permanent linear rows for the proportional
    inner solves — ``(rows, bounded_objective_names)`` with each row ``(coef, target, floor_bool)``
    in the extra_linears/eps_list tuple shape (floor_bool True → coef·w ≥ target). NSGA enforces
    these as G rows and the binary MILP as matrix rows; without this the exact proportional
    overlay could return points outside the model's own bounds. Linear rows are exact for sum
    and avg aggregation alike (Σw=1 makes them equal); bounds on min/max/quadratic objectives
    never reach here — ``exact_solver_fits`` declines those shapes. The names list mirrors row
    order (constraint order), the contract ``_build_solution_sensitivity`` uses to label each
    model-bound dual."""
    ocol = {o.name: j for j, o in enumerate(problem.objectives)}
    agg = {o.name: getattr(o.aggregation, "value", o.aggregation) for o in problem.objectives}
    rows, names = [], []
    for c in (problem.constraints or []):
        if getattr(c, "type", "") == "objective_bound" and agg.get(c.objective) in ("sum", "avg"):
            j = ocol[c.objective]
            rows.append((score_matrix[:, j].astype(float), float(c.value),
                         getattr(c.operator, "value", c.operator) == "min"))
            names.append(c.objective)
    return rows, names


def _prop_bound_context(problem: Problem, cp: dict, score_matrix):
    """The proportional exact paths' shared bound context, built once per path:
    ``(model_rows, bound_names, max_weight, min_weight, bounds_pct, quad_caps)``. One
    construction site keeps the row/name order coupling, the cap folding, and the rounding box
    in lockstep across optimize_qp / optimize_lp / certify_curated_frontier. ``quad_caps`` are
    the model's MAX bounds on quadratic objectives — not encodable as rows; the assemblies
    filter returned points against them (exact, because each inner solve minimizes the
    quadratic: a violating point proves its epsilon-targets infeasible)."""
    model_rows, bound_names = _model_bound_rows(problem, score_matrix)
    max_weight = (cp["max_allocation"] / 100.0) if cp.get("max_allocation") else None
    min_weight, _hi_vec = _allocation_bound_vectors(problem, cp)
    if _hi_vec is not None:
        max_weight = _hi_vec
    bounds_pct = ((np.round(min_weight * 100).astype(int), np.round(_hi_vec * 100).astype(int))
                  if min_weight is not None else None)
    quad = {o.name for o in problem.objectives
            if getattr(o.aggregation, "value", o.aggregation) == "quadratic"}
    quad_caps = [(c.objective, float(c.value)) for c in (problem.constraints or [])
                 if getattr(c, "type", "") == "objective_bound" and c.objective in quad
                 and getattr(c.operator, "value", c.operator) == "max"]
    return model_rows, bound_names, max_weight, min_weight, bounds_pct, quad_caps


def _prop_anchor_rows(linear_coefs, linear_maximize, max_weight, include_primary_eps,
                      min_weight=None) -> list:
    """Anchor epsilon-rows for the proportional exact paths. One all-loose row — every floor
    trivially satisfied, so the inner solve lands on the minimand's own corner (min-variance
    for the QP, best-primary for the LP) — plus one row per epsilon'd objective pinning it at
    its feasible box extreme while the rest stay loose (its lexicographic corner, minimand as
    tiebreak). A loose floor is the objective's guaranteed bound over the simplex: any
    budget-feasible w has ``coef·w ≥ coef.min()`` (maximize floors) and ``≤ coef.max()``
    (minimize ceilings). ``include_primary_eps`` mirrors the genome shape: the QP
    epsilon-constrains every linear objective, the LP all but the optimized primary."""
    coefs = linear_coefs if include_primary_eps else linear_coefs[1:]
    maxs = linear_maximize if include_primary_eps else linear_maximize[1:]
    loose = [float(np.min(c)) if m else float(np.max(c)) for c, m in zip(coefs, maxs)]
    rows = [np.array(loose, dtype=float)]
    for k in range(len(coefs)):
        row = list(loose)
        row[k] = _box_extreme(coefs[k], maxs[k], max_weight, min_weight)
        rows.append(np.array(row, dtype=float))
    return rows


def _rank_priorities(coef, maximize) -> np.ndarray:
    """Priority tail favoring a linear objective's best assets, rank-normalized to [0,1] so
    ``_decode_support`` selects the top-K (or top-per-group) assets by coefficient. For a
    linear objective the top-K support is greedy-optimal — any weight on a lower-coefficient
    asset improves by moving to an unused higher one — so an anchor carrying this tail reaches
    the true capped extreme; and any feasible cap satisfies ``K·cap ≥ 1 ≥ ceil(1/cap)·cap``,
    so ``_box_extreme``'s uncapped greedy value is already attainable on that support."""
    c = np.asarray(coef, dtype=float)
    ranks = np.argsort(np.argsort(c if maximize else -c))
    return ranks / max(len(c) - 1, 1)


def _milp_anchor_sels(S, dirs, mc, n, inner_milp, exact, first_stage=None) -> list:
    """Anchor selections for the binary MILP paths: per objective, the feasible plan
    lexicographically best on it — solve that objective alone, then re-solve the primary with
    the achieved optimum as an epsilon floor (tiebreak), so ties on the anchored objective
    resolve toward the frontier rather than arbitrarily. Infeasible/failed anchors are simply
    skipped (best-effort). ``first_stage`` maps objective index → an already-solved
    best-for-that-objective selection (optimize_milp's eps-bounds loop produces exactly
    these), skipping the duplicate first-stage solve; objectives it omits are solved here."""
    first_stage = first_stage or {}
    sels: list = []
    for j in range(S.shape[1]):
        sel = first_stage.get(j)
        if sel is None:
            sel, ok = inner_milp(dirs[j] * S[:, j], [], mc, n, exact)
            if not ok:
                continue
        if j != 0:  # pin objective j at its optimum, optimize the primary as tiebreak
            vj = float(S[:, j] @ sel)
            eps = [(S[:, j], "ge" if dirs[j] < 0 else "le", vj)]
            sel2, ok2 = inner_milp(dirs[0] * S[:, 0], eps, mc, n, exact)
            if ok2:
                sel = sel2
        sels.append(sel)
    return sels


# --------------------------------------------------------------------------- #
# QP genome (proportional mean-variance)
# --------------------------------------------------------------------------- #
def _solve_individual(cov, linear_coefs, linear_maximize, max_weight, eps, support, inner_qp,
                      min_weight=None, model_rows=()):
    """Inner QP for one EA individual: minimize variance subject to every linear objective k
    meeting its epsilon target ``eps[k]``, restricted to ``support``. Shared by the genome's
    ``_evaluate`` and the marshaling re-solve so the two can never disagree on what an
    individual decodes to."""
    extra = [(linear_coefs[t], float(eps[t]), linear_maximize[t])
             for t in range(1, len(linear_coefs))]
    return inner_qp(cov, linear_coefs[0], float(eps[0]), linear_maximize[0],
                    max_weight, support, extra + list(model_rows), min_weight=min_weight)


def _solve_individual_sensitivity(cov, linear_coefs, linear_maximize, max_weight, eps,
                                  support, inner_qp_sensitivity, min_weight=None,
                                  model_rows=()):
    """Dual-returning sibling of ``_solve_individual`` — same scalarization, but the inner
    solve also returns the exact duals. Returns ``(weights_frac, ok, raw_sensitivity)``."""
    extra = [(linear_coefs[t], float(eps[t]), linear_maximize[t])
             for t in range(1, len(linear_coefs))]
    return inner_qp_sensitivity(cov, linear_coefs[0], float(eps[0]), linear_maximize[0],
                                max_weight, support, extra + list(model_rows),
                                min_weight=min_weight)


def _solve_individual_lp(linear_coefs, linear_maximize, max_weight, eps, support, inner_lp,
                         min_weight=None, model_rows=()):
    """Inner LP for one EA individual (proportional allocation, purely linear objectives): optimize
    the **primary** linear objective (``linear_coefs[0]``) subject to every NON-primary objective
    meeting its epsilon target ``eps[t]``, restricted to ``support``. The continuous-allocation
    analogue of ``_solve_individual`` — but one linear objective is *optimized* rather than the
    quadratic, so the genome carries one fewer target (the primary isn't epsilon-constrained)."""
    eps_list = [(linear_coefs[t + 1], float(eps[t]), linear_maximize[t + 1])
                for t in range(len(eps))]
    return inner_lp(linear_coefs[0], linear_maximize[0], eps_list + list(model_rows),
                    max_weight, support, min_weight=min_weight)


def _solve_individual_lp_sensitivity(linear_coefs, linear_maximize, max_weight, eps,
                                     support, inner_lp_sensitivity, min_weight=None,
                                     model_rows=()):
    """Dual-returning sibling of ``_solve_individual_lp``: ``(weights_frac, ok, raw_sensitivity)``."""
    eps_list = [(linear_coefs[t + 1], float(eps[t]), linear_maximize[t + 1])
                for t in range(len(eps))]
    return inner_lp_sensitivity(linear_coefs[0], linear_maximize[0],
                                eps_list + list(model_rows), max_weight, support,
                                min_weight=min_weight)


def _required_indices(min_weight, n) -> "np.ndarray | None":
    """Indices carrying a positive weight floor (allocation_bound min / force_include) —
    the options every decoded support must admit first. None when there are none."""
    if min_weight is None:
        return None
    lb = np.broadcast_to(np.asarray(min_weight, dtype=float), (n,))
    req = np.where(lb > 0)[0]
    return req if len(req) else None


def _decode_support(pri, cardinality_k, groups, required=None):
    """Decode an asset-selection priority vector → the eligible asset indices (or ``None`` when
    unconstrained). Group-aware greedy: walk options by priority (best first) and admit one only
    while every group containing it has spare cap and the global cardinality cap has room, so the
    decoded support satisfies ALL count caps at once — overlapping groups and a global cap tighter
    than the group caps' sum included — and every plan the inner solves build from it is feasible
    for the model's count constraints. ``required`` indices (options carrying a weight floor —
    a support without them is infeasible at the solver, see ``_weight_box``) are admitted FIRST,
    so deterministic supports (anchors, seeds) stay solvable whenever the caps allow it.
    Shared by the QP and LP genomes so the support search behaves identically on both paths."""
    if cardinality_k is None and not groups:
        return None
    pri = np.asarray(pri, dtype=float)
    n = len(pri)
    req = [int(i) for i in (required if required is not None else [])]
    if groups:
        membership: dict[int, list[int]] = {}
        remaining = []
        for g, (grp, gmax) in enumerate(groups):
            remaining.append(int(gmax))
            for i in grp:
                membership.setdefault(int(i), []).append(g)
        cap = n if cardinality_k is None else int(cardinality_k)
        support: list[int] = []
        taken = set()

        def _admit(i, force=False):
            gs = membership.get(i, [])
            if force or (len(support) < cap and all(remaining[g] > 0 for g in gs)):
                support.append(i)
                taken.add(i)
                for g in gs:
                    remaining[g] -= 1

        for i in req:                       # floors first — even past a cap, the inner
            _admit(i, force=True)           # solve owns the infeasibility verdict then
        for i in np.argsort(-pri):
            i = int(i)
            if len(support) >= cap:
                break
            if i not in taken:
                _admit(i)
        return np.array(sorted(support), dtype=int)
    if req:
        rest = [int(i) for i in np.argsort(-pri) if int(i) not in set(req)]
        support = req + rest[:max(0, int(cardinality_k) - len(req))]
        return np.array(sorted(support), dtype=int)
    return np.asarray(np.argsort(pri)[-cardinality_k:], dtype=int)


def _build_raw_sensitivity(row_dual, col_dual, n, has_return, n_extra, support):
    """Shared dual marshaller for every exact path (HiGHS / cuOpt × QP / LP): role-tag the constraint
    duals by add-order — budget Σw=1 (row 0), then the return floor (QP only) and the linear-objective
    floors — and pair the per-variable reduced costs with an ``eligible`` flag, producing the dict
    shape ``_build_solution_sensitivity`` consumes. ``has_return`` is True on the QP path (its primary
    linear objective is epsilon-constrained as a return floor) and False on the LP path (its primary
    linear objective is *optimized*, so it carries no shadow price). An off-``support`` asset is pinned
    to ub=0 by the cardinality/group search → its reduced cost prices that cap, not a near-miss, so it
    is flagged ineligible. ``ranging`` is None (no solver exposes it on these paths)."""
    def _row(i):
        return float(row_dual[i]) if 0 <= i < len(row_dual) else 0.0

    shadow_prices = [{"role": "budget", "linear_index": None, "value": _row(0)}]
    idx = 1
    if has_return:
        shadow_prices.append({"role": "return_floor", "linear_index": 0, "value": _row(idx)})
        idx += 1
    for t in range(n_extra):
        shadow_prices.append({"role": "linear_floor", "linear_index": t + 1, "value": _row(idx)})
        idx += 1

    if support is None:
        eligible = [True] * n
    else:
        ss = {int(i) for i in support}
        eligible = [i in ss for i in range(n)]

    return {"shadow_prices": shadow_prices, "reduced_costs": [float(x) for x in col_dual],
            "eligible": eligible, "ranging": None}


def _build_solution_sensitivity(raw, opt_names, alloc_row, linear_idxs, obj_list,
                                bound_names=()):
    """Map a backend's raw dual payload onto option/objective names → a
    ``SolutionSensitivity``. Backend-agnostic: ``raw['shadow_prices']`` is a list of
    ``{role, linear_index, value}`` (``linear_index`` indexes ``linear_idxs``; None =
    budget), and ``raw['reduced_costs']`` is one value per option index."""
    shadow = []
    n_model = 0
    for sp in raw["shadow_prices"]:
        li = sp.get("linear_index")
        if li is not None and li >= len(linear_idxs):
            # A model-level objective_bound row appended after the genome's epsilon rows (see
            # ``_model_bound_rows``) — priced, but not one of the walked objectives. Rows keep
            # constraint order, so the lever is named for the objective its bound constrains
            # (the surface convention: levers carry business names, never schema types).
            name = bound_names[n_model] if n_model < len(bound_names) else "objective_bound"
            n_model += 1
            shadow.append(ShadowPrice(name=name, role="model_bound",
                                      shadow_price=round(float(sp["value"]), 6)))
            continue
        name = "budget" if li is None else obj_list[linear_idxs[li]].name
        shadow.append(ShadowPrice(name=name, role=sp["role"],
                                  shadow_price=round(float(sp["value"]), 6)))
    rcs = raw.get("reduced_costs") or []
    elig = raw.get("eligible") or [True] * len(opt_names)
    reduced = [ReducedCost(option=opt_names[i], allocation=int(alloc_row[i]),
                           reduced_cost=round(float(rcs[i]), 6),
                           eligible=bool(elig[i]) if i < len(elig) else True)
               for i in range(len(opt_names)) if i < len(rcs)]
    return SolutionSensitivity(source="solver_exact", shadow_prices=shadow,
                               reduced_costs=reduced, ranging=raw.get("ranging"))


class _QpFrontierProblem(PymooProblem):
    """Epsilon-constraint genome for proportional mean-variance problems.

    Decision variables: one epsilon target per linear objective, plus — when a cardinality
    cap K or group caps apply — an N-length real *priority* vector whose top entries select
    the eligible assets. The plain 2-objective walker is the ``len(linear_coefs)==1`` /
    ``cardinality_k is None`` / no-groups special case. The inner solver solves each QP
    exactly; objective values come back through the engine's own aggregator (apples-to-apples
    with NSGA)."""

    def __init__(self, prop_problem, cov, linear_coefs, linear_maximize, max_weight,
                 eps_bounds, cardinality_k=None, groups=None, *, inner_qp, min_weight=None,
                 model_rows=()):
        self.prop = prop_problem
        self.cov = cov
        self.linear_coefs = linear_coefs
        self.linear_maximize = linear_maximize
        self.max_weight = max_weight
        self.min_weight = min_weight
        self.model_rows = tuple(model_rows)
        self.cardinality_k = cardinality_k
        self.groups = groups or []
        self.inner_qp = inner_qp
        n_assets = cov.shape[0]
        xl = [b[0] for b in eps_bounds]
        xu = [b[1] for b in eps_bounds]
        if cardinality_k is not None or self.groups:    # + per-asset selection priorities
            xl = xl + [0.0] * n_assets
            xu = xu + [1.0] * n_assets
        super().__init__(n_var=len(xl), n_obj=prop_problem.n_obj,
                         n_ieq_constr=1, xl=np.array(xl), xu=np.array(xu))

    def _support_from_row(self, x_row: np.ndarray) -> "np.ndarray | None":
        """Decode the selection-priority tail of one genome row → eligible asset indices (None when
        unconstrained). Delegates to the shared ``_decode_support`` so QP and LP search identically."""
        return _decode_support(np.asarray(x_row[len(self.linear_coefs):], dtype=float),
                               self.cardinality_k, self.groups,
                               required=_required_indices(self.min_weight, self.cov.shape[0]))

    def _evaluate(self, X, out, *args, **kwargs):
        X = np.atleast_2d(X)
        n_pop = X.shape[0]
        n_assets = self.cov.shape[0]
        n_lin = len(self.linear_coefs)
        objectives = self.prop.objectives

        W_pct = np.zeros((n_pop, n_assets))
        feasible = np.ones(n_pop, dtype=bool)
        for k in range(n_pop):
            w_frac, ok = _solve_individual(
                self.cov, self.linear_coefs, self.linear_maximize,
                self.max_weight, X[k, :n_lin], self._support_from_row(X[k]), self.inner_qp,
                min_weight=self.min_weight, model_rows=self.model_rows,
            )
            if ok:
                W_pct[k] = w_frac * 100.0
            else:
                feasible[k] = False

        F = np.zeros((n_pop, len(objectives)))
        for j, obj in enumerate(objectives):
            natural = self.prop._aggregate_objective(W_pct, j)
            F[:, j] = -natural if obj.direction.value == "maximize" else natural

        F[~feasible, :] = _INFEASIBLE_PENALTY
        out["F"] = F
        out["G"] = np.where(feasible, -1.0, 1.0).reshape(-1, 1)


def optimize_qp(problem, mode, *, inner_qp, inner_qp_sensitivity=None, pop, gen,
                max_solutions=None, seed=42, time_limit=None) -> Run:
    """Proportional mean-variance solve: the EA walks an epsilon-constraint target per linear
    objective (and, under a cardinality/group cap, the asset-selection priorities) while
    ``inner_qp`` solves each inner min-variance QP exactly. Returns a ``Run`` in the engine's
    exact shape, so explorer / metrics / store need no changes.

    ``time_limit`` (s) bounds the EA scalarization sweep — its dominant pop×gen inner-solve
    cost — stopping at the generation budget or the wall-clock cap, whichever fires first
    (best-effort: the cheap eps-bound and marshaling solves around the sweep are not counted).
    A capped run returns a sparser best-so-far frontier; each returned point is still optimal
    for its scalarization."""
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

    cov = _nearest_psd(im[risk_idx])
    model_rows, bound_names, max_weight, min_weight, bounds_pct, quad_caps = \
        _prop_bound_context(problem, cp, score_matrix)
    cardinality_k = _cardinality_k(problem)
    # Caps only — the exact gate declines proportional problems with group floors.
    groups = [(g, mx) for g, _mn, mx in _group_limits(problem)]

    prop = _opt._ProportionalProblem(
        n_options=n_options, score_matrix=score_matrix, objectives=obj_list,
        interaction_matrices=im, **cp,
    )

    # Epsilon range per linear objective, DIRECTION-AWARE: the loose end is the objective's
    # value at the global min-variance portfolio (one unconstrained inner solve); the tight end
    # is the best single-asset value in that objective's own direction. A maximize objective
    # sweeps its floor up toward max(coef); a minimize objective sweeps its ceiling down toward
    # min(coef) — the old max(coef)-only upper bound left a minimize ceiling forever slack, so
    # the sweep never traded variance against that objective.
    w_mv, ok_mv = inner_qp(cov, linear_coefs[0], None, linear_maximize[0], max_weight, None,
                           list(model_rows), min_weight=min_weight)
    eps_bounds: list[tuple[float, float]] = []
    for coef, maximize in zip(linear_coefs, linear_maximize):
        # Loose end: the objective's value at the min-variance portfolio; when that probe
        # fails, fall back to the box extreme every feasible portfolio clears (min for a
        # maximize floor, max for a minimize ceiling) so the sweep still spans the range.
        loose_fallback = float(coef.min()) if maximize else float(coef.max())
        at_mv = float(coef @ w_mv) if ok_mv else loose_fallback
        tight = float(coef.max()) if maximize else float(coef.min())
        lo, hi = (at_mv, tight) if maximize else (tight, at_mv)
        if hi <= lo:
            hi = lo + 1e-6  # degenerate guard (all values equal)
        eps_bounds.append((lo, hi))

    pymoo_problem = _QpFrontierProblem(
        prop, cov, linear_coefs, linear_maximize, max_weight, eps_bounds,
        cardinality_k, groups, inner_qp=inner_qp, min_weight=min_weight,
        model_rows=model_rows,
    )
    if cardinality_k is not None:
        seed_X = _seed_cardinality_population(linear_coefs, cov, eps_bounds, cardinality_k, pop, seed,
                                              linear_maximize=list(linear_maximize))
        algorithm = NSGA2(pop_size=pop, sampling=seed_X)
    else:
        algorithm = NSGA2(pop_size=pop)
    _t0 = time.monotonic()
    result = pymoo_minimize(pymoo_problem, algorithm, _opt._build_termination(gen, time_limit),
                            seed=seed, verbose=False)
    _elapsed = time.monotonic() - _t0

    n_lin = len(linear_coefs)
    rows = list(np.atleast_2d(result.X)) if result.X is not None else []
    # Anchor corners: guarantee the per-objective extremes are sampled even when the EA's
    # epsilon sweep under-covered them. Skipped under a cardinality/group support search —
    # an anchor row carries no priority tail, and support=None would sidestep the cap.
    if cardinality_k is None and not groups:
        rows += _prop_anchor_rows(linear_coefs, linear_maximize, max_weight,
                                  include_primary_eps=True, min_weight=min_weight)
    solutions: list[Solution] = []
    seen: set[str] = set()
    if rows:
        for row in rows:
            support = pymoo_problem._support_from_row(row)
            if inner_qp_sensitivity is not None:
                w_frac, ok, raw_sens = _solve_individual_sensitivity(
                    cov, linear_coefs, linear_maximize, max_weight,
                    row[:n_lin], support, inner_qp_sensitivity, min_weight=min_weight,
                    model_rows=model_rows,
                )
            else:
                w_frac, ok = _solve_individual(
                    cov, linear_coefs, linear_maximize, max_weight,
                    row[:n_lin], support, inner_qp, min_weight=min_weight,
                    model_rows=model_rows,
                )
                raw_sens = None
            if not ok:
                continue
            raw = _round_weights_to_pct(w_frac, n_options, cp.get("max_allocation"), bounds_pct)
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
            # Model MAX caps on the quadratic objective: the inner solve minimized it, so a
            # violating point means these epsilon-targets are infeasible under the model.
            if any(obj_values.get(nm, 0.0) > v + 1e-9 for nm, v in quad_caps):
                continue
            sensitivity = (_build_solution_sensitivity(raw_sens, opt_names, raw, linear_idxs,
                                                       obj_list, bound_names=bound_names)
                           if raw_sens else None)
            solutions.append(Solution(
                solution_id=len(solutions), selected_options=selected,
                objective_values=obj_values, allocations=alloc_map,
                sensitivity=sensitivity,
            ))

    solutions = _nondominated(solutions, obj_list)
    max_n = max_solutions or _opt.MAX_PARETO_SOLUTIONS
    solutions, total_found = _opt._prune_pareto(solutions, obj_list, max_n=max_n)
    solutions = _opt._sort_and_reindex(solutions, obj_list)
    return Run(solutions=solutions, total_pareto_found=total_found,
               quality=_opt._compute_quality(result, seed=seed), mode=mode, seed_used=seed,
               time_limit=time_limit, time_limited=_opt._was_time_limited(time_limit, _elapsed))


# --------------------------------------------------------------------------- #
# LP genome (proportional allocation, purely linear objectives)
# --------------------------------------------------------------------------- #
class _LpFrontierProblem(PymooProblem):
    """EA genome for proportional allocation with purely linear objectives: one epsilon target per
    NON-primary objective (plus, under a cardinality/group cap, the asset-selection priorities). The
    inner solver optimizes the primary linear objective exactly subject to those targets + budget /
    box / support; NSGA-II explores the epsilon space. The continuous-allocation twin of
    ``_MilpFrontierProblem`` — an LP inner solve instead of a 0/1 MILP — and the proportional
    aggregator scores the resulting weights apples-to-apples with the NSGA paths."""

    def __init__(self, prop, linear_coefs, linear_maximize, max_weight, eps_bounds,
                 cardinality_k=None, groups=None, *, inner_lp, min_weight=None,
                 model_rows=()):
        self.prop = prop
        self.linear_coefs = linear_coefs
        self.linear_maximize = linear_maximize
        self.max_weight = max_weight
        self.min_weight = min_weight
        self.model_rows = tuple(model_rows)
        self.cardinality_k = cardinality_k
        self.groups = groups or []
        self.inner_lp = inner_lp
        self.n_eps = len(linear_coefs) - 1            # one epsilon target per non-primary objective
        n_assets = len(linear_coefs[0])
        xl = [b[0] for b in eps_bounds]
        xu = [b[1] for b in eps_bounds]
        if cardinality_k is not None or self.groups:
            xl = xl + [0.0] * n_assets
            xu = xu + [1.0] * n_assets
        super().__init__(n_var=len(xl), n_obj=prop.n_obj, n_ieq_constr=1,
                         xl=np.array(xl), xu=np.array(xu))

    def _support_from_row(self, x_row):
        return _decode_support(np.asarray(x_row[self.n_eps:], dtype=float),
                               self.cardinality_k, self.groups,
                               required=_required_indices(self.min_weight, len(self.linear_coefs[0])))

    def _evaluate(self, X, out, *args, **kwargs):
        X = np.atleast_2d(X)
        n_pop = X.shape[0]
        n_assets = len(self.linear_coefs[0])
        objectives = self.prop.objectives
        W_pct = np.zeros((n_pop, n_assets))
        feasible = np.ones(n_pop, dtype=bool)
        for k in range(n_pop):
            w_frac, ok = _solve_individual_lp(
                self.linear_coefs, self.linear_maximize, self.max_weight,
                X[k, :self.n_eps], self._support_from_row(X[k]), self.inner_lp,
                min_weight=self.min_weight, model_rows=self.model_rows,
            )
            if ok:
                W_pct[k] = w_frac * 100.0
            else:
                feasible[k] = False
        F = np.zeros((n_pop, len(objectives)))
        for j, obj in enumerate(objectives):
            natural = self.prop._aggregate_objective(W_pct, j)
            F[:, j] = -natural if obj.direction.value == "maximize" else natural
        F[~feasible, :] = _INFEASIBLE_PENALTY
        out["F"] = F
        out["G"] = np.where(feasible, -1.0, 1.0).reshape(-1, 1)


def optimize_lp(problem, mode, *, inner_lp, inner_lp_sensitivity=None, pop, gen,
                max_solutions=None, seed=42, time_limit=None) -> Run:
    """Proportional allocation with purely linear objectives — an exact multi-objective LP. The EA
    walks an epsilon-constraint target on each non-primary objective while ``inner_lp`` optimizes the
    primary linear objective exactly per individual (continuous weights, Σw=1). The pure-linear
    sibling of ``optimize_qp`` (no covariance / quadratic term); solver-exact shadow prices + reduced
    costs ride the final-frontier re-solve via ``inner_lp_sensitivity``. Returns a Run in the engine's
    exact shape, so explorer / metrics / store need no changes."""
    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    score_matrix = _opt._build_score_matrix(problem)
    cp = _opt._parse_constraints(problem)

    linear_idxs = _resolve_linear_objectives(problem)   # all objectives (no quadratic on this path)
    linear_coefs = [score_matrix[:, j] for j in linear_idxs]
    linear_maximize = [obj_list[j].direction.value == "maximize" for j in linear_idxs]

    model_rows, bound_names, max_weight, min_weight, bounds_pct, _quad_caps = \
        _prop_bound_context(problem, cp, score_matrix)
    cardinality_k = _cardinality_k(problem)
    # Caps only — the exact gate declines proportional problems with group floors.
    groups = [(g, mx) for g, _mn, mx in _group_limits(problem)]

    prop = _opt._ProportionalProblem(
        n_options=n_options, score_matrix=score_matrix, objectives=obj_list,
        interaction_matrices=_opt._build_interaction_matrices(problem), **cp,
    )

    # Epsilon range per NON-primary objective = [min, max] over the budget/box-feasible region, from
    # two LP anchor solves that optimize that objective alone (the primary objective ignored).
    eps_bounds: list[tuple[float, float]] = []
    for t in range(1, len(linear_coefs)):
        coef, maximize = linear_coefs[t], linear_maximize[t]
        w_hi, ok_hi = inner_lp(coef, maximize, list(model_rows), max_weight, None,
                               min_weight=min_weight)      # best for this objective
        w_lo, ok_lo = inner_lp(coef, not maximize, list(model_rows), max_weight, None,
                               min_weight=min_weight)      # worst for this objective
        vals = [float(coef @ w) for w, ok in ((w_hi, ok_hi), (w_lo, ok_lo)) if ok]
        lo, hi = (min(vals), max(vals)) if vals else (float(coef.min()), float(coef.max()))
        eps_bounds.append((lo, hi if hi > lo else lo + 1e-6))

    pymoo_problem = _LpFrontierProblem(
        prop, linear_coefs, linear_maximize, max_weight, eps_bounds,
        cardinality_k, groups, inner_lp=inner_lp, min_weight=min_weight,
        model_rows=model_rows,
    )
    _t0 = time.monotonic()
    result = pymoo_minimize(pymoo_problem, NSGA2(pop_size=pop),
                            _opt._build_termination(gen, time_limit), seed=seed, verbose=False)
    _elapsed = time.monotonic() - _t0

    n_eps = pymoo_problem.n_eps
    rows = list(np.atleast_2d(result.X)) if result.X is not None else []
    # Anchor corners: the best-primary corner (all floors loose) plus each non-primary
    # objective's lexicographic extreme — sampled even when the EA's epsilon sweep
    # under-covered them. Under a cardinality/group cap each anchor row carries a priority
    # tail favoring its objective's best assets (``_rank_priorities``): for a linear
    # objective the top-K support is greedy-optimal, so the decoded support reaches the true
    # capped extreme — exact under a pure cardinality cap; group caps inherit the EA's
    # decode semantics. (Row order: all-loose → objective 0, then pinned rows → 1..n_eps.)
    anchor_rows = _prop_anchor_rows(linear_coefs, linear_maximize, max_weight,
                                    include_primary_eps=False, min_weight=min_weight)
    if cardinality_k is not None or groups:
        anchor_rows = [np.concatenate([row, _rank_priorities(linear_coefs[j], linear_maximize[j])])
                       for j, row in enumerate(anchor_rows)]
    rows += anchor_rows
    solutions: list[Solution] = []
    seen: set[str] = set()
    if rows:
        for row in rows:
            support = pymoo_problem._support_from_row(row)
            if inner_lp_sensitivity is not None:
                w_frac, ok, raw_sens = _solve_individual_lp_sensitivity(
                    linear_coefs, linear_maximize, max_weight, row[:n_eps], support,
                    inner_lp_sensitivity, min_weight=min_weight, model_rows=model_rows)
            else:
                w_frac, ok = _solve_individual_lp(
                    linear_coefs, linear_maximize, max_weight, row[:n_eps], support, inner_lp,
                    min_weight=min_weight, model_rows=model_rows)
                raw_sens = None
            if not ok:
                continue
            raw = _round_weights_to_pct(w_frac, n_options, cp.get("max_allocation"), bounds_pct)
            selected = [opt_names[i] for i in range(n_options) if raw[i] > 0]
            alloc_map = {opt_names[i]: int(raw[i]) for i in range(n_options)}
            sig = _content_signature(selected, alloc_map)
            if sig in seen:
                continue
            seen.add(sig)
            W_pct = raw.astype(float).reshape(1, -1)
            obj_values = {obj.name: round(float(prop._aggregate_objective(W_pct, j)[0]), 4)
                          for j, obj in enumerate(obj_list)}
            sensitivity = (_build_solution_sensitivity(raw_sens, opt_names, raw, linear_idxs,
                                                       obj_list, bound_names=bound_names)
                           if raw_sens else None)
            solutions.append(Solution(
                solution_id=len(solutions), selected_options=selected,
                objective_values=obj_values, allocations=alloc_map, sensitivity=sensitivity))

    solutions = _nondominated(solutions, obj_list)
    max_n = max_solutions or _opt.MAX_PARETO_SOLUTIONS
    solutions, total_found = _opt._prune_pareto(solutions, obj_list, max_n=max_n)
    solutions = _opt._sort_and_reindex(solutions, obj_list)
    return Run(solutions=solutions, total_pareto_found=total_found,
               quality=_opt._compute_quality(result, seed=seed), mode=mode, seed_used=seed,
               time_limit=time_limit, time_limited=_opt._was_time_limited(time_limit, _elapsed))


# --------------------------------------------------------------------------- #
# Progressive certify (exact-solve only an existing run's frontier points)
# --------------------------------------------------------------------------- #
def certify_curated_frontier(problem, source_run, *, inner=None, inner_sensitivity=None,
                             inner_milp=None, exact=False, mode=None, max_solutions=None) -> Run:
    """Exact-solve **only the points of an existing run** (typically the exploratory NSGA frontier),
    re-solving each for its own scalarization (support + epsilon targets), and assemble them into an
    exact ``Run`` — non-dominated-filtered, pruned, and re-indexed exactly like a full scalarization.

    This is the lean *explore-then-certify* overlay: where ``optimize_{qp,lp,milp}`` run the inner solver
    on every one of ~pop×gen NSGA *evaluations* (the inner solve **is** NSGA's fitness), this runs it once
    per *curated frontier point* (~dozens). The heuristic explores; the exact solver certifies only what
    it kept. Covers all three shapes (inner shape-matched by the caller): binary 0/1 **MILP** via
    ``inner_milp``, proportional **QP**/**LP** via ``inner`` (+ ``inner_sensitivity`` for solver duals).
    Each returned point is optimal for its scalarization, so the overlay can only confirm or sharpen the
    source frontier — the same auditor guarantee as the full exact pass, at a fraction of the cost.
    Like the full pass, the overlay also carries per-objective **anchor corners** (the epsilon-constraint
    payoff-table step), so it samples the frontier's extremes even when the source run missed them."""
    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    opt_index = {n: i for i, n in enumerate(opt_names)}
    obj_list = problem.objectives

    solutions: list[Solution] = []
    seen: set = set()

    if getattr(problem.approach, "value", problem.approach) == "binary":
        # Binary MILP: re-solve each source point's scalarization — minimize the primary objective
        # subject to the source point's non-primary values as epsilon targets + the combinatorial
        # constraints. Mirrors optimize_milp's inner solve, once per curated point instead of pop×gen.
        n, names, S, dirs, mc = _build_milp_data(problem)
        primary, nonprimary = 0, [j for j in range(len(obj_list)) if j != 0]
        cand_sels: list = []
        for src in source_run.solutions:
            eps_list = [(S[:, j], "ge" if dirs[j] < 0 else "le",
                         float(src.objective_values.get(obj_list[j].name, 0.0))) for j in nonprimary]
            sel, ok = inner_milp(dirs[primary] * S[:, primary], eps_list, mc, n, exact)
            if ok:
                cand_sels.append(sel)
        # Anchor corners: the overlay samples every per-objective extreme even when the
        # source run missed one — the certify-path half of the "short at a linear extreme" fix.
        cand_sels += _milp_anchor_sels(S, dirs, mc, n, inner_milp, exact)
        for sel in cand_sels:
            selected = [names[i] for i in range(n) if sel[i] > 0.5]
            key = tuple(sorted(selected))
            if key in seen:
                continue
            seen.add(key)
            obj_values = {o.name: round(float(S[:, j] @ sel), 4) for j, o in enumerate(obj_list)}
            solutions.append(Solution(solution_id=len(solutions), selected_options=selected,
                                      objective_values=obj_values))
    else:
        score_matrix = _opt._build_score_matrix(problem)
        cp = _opt._parse_constraints(problem)
        im = _opt._build_interaction_matrices(problem)
        linear_idxs = _resolve_linear_objectives(problem)
        linear_coefs = [score_matrix[:, j] for j in linear_idxs]
        linear_maximize = [obj_list[j].direction.value == "maximize" for j in linear_idxs]
        model_rows, bound_names, max_weight, min_weight, bounds_pct, quad_caps = \
            _prop_bound_context(problem, cp, score_matrix)
        prop = _opt._ProportionalProblem(n_options=n_options, score_matrix=score_matrix,
                                         objectives=obj_list, interaction_matrices=im, **cp)
        is_qp = bool(im)
        cov = _nearest_psd(im[_resolve_objective_roles(problem)[0]]) if is_qp else None
        # Each source point's reported objective values become its epsilon targets: QP epsilon-
        # constrains every linear objective (variance minimized); LP optimizes the primary and
        # epsilon-constrains the rest, so it carries one fewer target.
        idxs = linear_idxs if is_qp else linear_idxs[1:]
        targets = [
            (np.array([src.objective_values.get(obj_list[j].name, 0.0) for j in idxs], dtype=float),
             [opt_index[nm] for nm in src.selected_options if nm in opt_index])
            for src in source_run.solutions
        ]
        # Anchor corners: the overlay samples each per-objective extreme even when the source
        # run missed one. Uncapped: support=None (every asset eligible). Under a cardinality/
        # group cap, LP anchors pair each row with the decoded top-K support for its objective
        # (greedy-optimal for a linear objective — see ``_rank_priorities``); QP anchors are
        # skipped there — the min-variance corner has no greedy-derivable support, and the
        # capped QP path's seeded population owns corner coverage.
        k_cap, glims = _cardinality_k(problem), [(g, mx) for g, _mn, mx in _group_limits(problem)]
        anchor_rows = _prop_anchor_rows(linear_coefs, linear_maximize, max_weight,
                                        include_primary_eps=is_qp, min_weight=min_weight)
        if k_cap is None and not glims:
            targets += [(row, None) for row in anchor_rows]
        elif not is_qp:
            req = _required_indices(min_weight, len(linear_coefs[0]))
            targets += [(row, _decode_support(_rank_priorities(linear_coefs[j], linear_maximize[j]),
                                              k_cap, glims, required=req))
                        for j, row in enumerate(anchor_rows)]
        for eps, support in targets:
            if is_qp and inner_sensitivity is not None:
                w_frac, ok, raw_sens = _solve_individual_sensitivity(
                    cov, linear_coefs, linear_maximize, max_weight, eps, support, inner_sensitivity,
                    min_weight=min_weight, model_rows=model_rows)
            elif is_qp:
                w_frac, ok = _solve_individual(cov, linear_coefs, linear_maximize, max_weight,
                                               eps, support, inner, min_weight=min_weight,
                                               model_rows=model_rows)
                raw_sens = None
            elif inner_sensitivity is not None:
                w_frac, ok, raw_sens = _solve_individual_lp_sensitivity(
                    linear_coefs, linear_maximize, max_weight, eps, support, inner_sensitivity,
                    min_weight=min_weight, model_rows=model_rows)
            else:
                w_frac, ok = _solve_individual_lp(linear_coefs, linear_maximize, max_weight,
                                                  eps, support, inner, min_weight=min_weight,
                                                  model_rows=model_rows)
                raw_sens = None
            if not ok:
                continue
            raw = _round_weights_to_pct(w_frac, n_options, cp.get("max_allocation"), bounds_pct)
            selected = [opt_names[i] for i in range(n_options) if raw[i] > 0]
            alloc_map = {opt_names[i]: int(raw[i]) for i in range(n_options)}
            sig = _content_signature(selected, alloc_map)
            if sig in seen:
                continue
            seen.add(sig)
            W_pct = raw.astype(float).reshape(1, -1)
            obj_values = {obj.name: round(float(prop._aggregate_objective(W_pct, j)[0]), 4)
                          for j, obj in enumerate(obj_list)}
            if is_qp and any(obj_values.get(nm, 0.0) > v + 1e-9 for nm, v in quad_caps):
                continue
            sensitivity = (_build_solution_sensitivity(raw_sens, opt_names, raw, linear_idxs,
                                                       obj_list, bound_names=bound_names)
                           if raw_sens else None)
            solutions.append(Solution(solution_id=len(solutions), selected_options=selected,
                                      objective_values=obj_values, allocations=alloc_map, sensitivity=sensitivity))

    solutions = _nondominated(solutions, obj_list)
    max_n = max_solutions or _opt.MAX_PARETO_SOLUTIONS
    solutions, total_found = _opt._prune_pareto(solutions, obj_list, max_n=max_n)
    solutions = _opt._sort_and_reindex(solutions, obj_list)
    return Run(solutions=solutions, total_pareto_found=total_found,
               quality=source_run.quality, mode=mode or source_run.mode, seed_used=source_run.seed_used)


# --------------------------------------------------------------------------- #
# MILP genome (binary selection)
# --------------------------------------------------------------------------- #
class _MilpFrontierProblem(PymooProblem):
    """EA genome for binary selection: one epsilon target per non-primary objective. The
    inner solver minimizes the primary objective exactly subject to those targets + the
    combinatorial constraints; the EA (NSGA-II) explores the epsilon space."""

    def __init__(self, S, dirs, primary, nonprimary, mc, n, objectives, eps_bounds,
                 exact=False, *, inner_milp):
        self.S, self.dirs, self.primary, self.nonprimary = S, dirs, primary, nonprimary
        self.mc, self.n, self.objectives, self.exact = mc, n, objectives, exact
        self.inner_milp = inner_milp
        super().__init__(n_var=len(nonprimary), n_obj=len(objectives), n_ieq_constr=1,
                         xl=np.array([b[0] for b in eps_bounds]),
                         xu=np.array([b[1] for b in eps_bounds]))

    def _solve_row(self, row):
        eps_list = [(self.S[:, j], "ge" if self.dirs[j] < 0 else "le", float(row[k]))
                    for k, j in enumerate(self.nonprimary)]
        return self.inner_milp(self.dirs[self.primary] * self.S[:, self.primary], eps_list,
                               self.mc, self.n, self.exact)

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


def audit_milp(problem, negated_disjuncts, *, inner_audit):
    """Backend-agnostic witness / feasibility audit over a binary problem's feasible region.

    The feasible region is the problem's own hard constraints (``_build_milp_data``'s ``mc``).
    Each entry of ``negated_disjuncts`` is a set of extra linear rows ``(coef, op, rhs)`` encoding
    ONE way to violate the audited property — a *disjunction*, because some properties negate to an
    OR (cardinality → count≤min-1 OR count≥max+1). The property holds iff EVERY disjunct is
    infeasible against the feasible region; the first feasible disjunct is a counterexample witness.

    ``inner_audit(eps_list, mc, n) -> (status, sel)`` is the injected feasibility solve (HiGHS
    today; a cuOpt sibling can drop in later — same split as ``optimize_milp``'s ``inner_milp``).
    Returns ``{feasible, witness_options, statuses}``; the engine maps that — with the property /
    probe context — to a verdict."""
    n, names, _, _, mc = _build_milp_data(problem)   # score matrix / directions unused for feasibility
    statuses: list[str] = []
    for rows in negated_disjuncts:
        status, sel = inner_audit(rows, mc, n)
        statuses.append(status)
        if status == "Optimal":   # a feasible witness violating the property
            witness = [names[i] for i in range(n) if sel[i] > 0.5]
            return {"feasible": True, "witness_options": witness, "statuses": statuses}
    return {"feasible": False, "witness_options": None, "statuses": statuses}


def optimize_milp(problem, mode, *, inner_milp, max_solutions=None,
                  seed=42, exact=False, time_limit=None) -> Run:
    """Binary selection solve: the EA evolves epsilon targets on the non-primary objectives
    while ``inner_milp`` solves the scalarized 0/1 MILP (minimizing objective 0) exactly per
    individual. The EA budget auto-scales with the option count (``_milp_budget``). Same
    Run/Solution shape as the NSGA binary path. ``exact`` certifies each inner solve.

    ``time_limit`` (s) bounds the EA sweep (generation budget or wall clock, whichever first);
    a capped run returns a sparser best-so-far frontier, each point still exact for its
    scalarization. Best-effort — the eps-bound and marshaling solves around the sweep are not
    counted."""
    n, names, S, dirs, mc = _build_milp_data(problem)
    pop, gen = _milp_budget(n)
    objs = problem.objectives
    primary = 0
    nonprimary = [j for j in range(len(objs)) if j != primary]

    # epsilon range per non-primary objective = [min, max] over the feasible set. The
    # best-for-j selection each pair of solves discovers doubles as the anchor helper's
    # first stage, so the anchor pass never repeats these exact solves.
    eps_bounds = []
    anchor_first_stage: dict = {}
    for j in nonprimary:
        smin, ok1 = inner_milp(S[:, j], [], mc, n, exact)
        smax, ok2 = inner_milp(-S[:, j], [], mc, n, exact)
        lo = float(S[:, j] @ smin) if ok1 else float(S[:, j].min())
        hi = float(S[:, j] @ smax) if ok2 else float(S[:, j].sum())
        eps_bounds.append((lo, hi if hi > lo else lo + 1e-6))
        best, ok_best = (smax, ok2) if dirs[j] < 0 else (smin, ok1)
        if ok_best:
            anchor_first_stage[j] = best

    pp = _MilpFrontierProblem(S, dirs, primary, nonprimary, mc, n, objs, eps_bounds,
                              exact=exact, inner_milp=inner_milp)
    _t0 = time.monotonic()
    result = pymoo_minimize(pp, NSGA2(pop_size=pop), _opt._build_termination(gen, time_limit),
                            seed=seed, verbose=False)
    _elapsed = time.monotonic() - _t0

    sels: list = []
    if result.X is not None and len(np.atleast_2d(result.X)) > 0:
        for row in np.atleast_2d(result.X):
            sel, ok = pp._solve_row(row)
            if ok:
                sels.append(sel)
    # Anchor corners: one lexicographically-best plan per objective, so the frontier's
    # extremes are present regardless of the EA sweep's coverage. mc carries the
    # combinatorial constraints, so anchors are feasible by construction; the eps-bounds
    # selections serve as the first stage, so only the tiebreak solves are new work.
    sels += _milp_anchor_sels(S, dirs, mc, n, inner_milp, exact,
                              first_stage=anchor_first_stage)

    solutions: list[Solution] = []
    seen: set = set()
    for sel in sels:
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
               quality=_opt._compute_quality(result, seed=seed), mode=mode, seed_used=seed,
               time_limit=time_limit, time_limited=_opt._was_time_limited(time_limit, _elapsed))

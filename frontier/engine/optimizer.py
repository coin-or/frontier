"""Optimizer: validate problem and run NSGA-II via pymoo."""

from __future__ import annotations

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem as PymooProblem
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.bitflip import BitflipMutation
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import BinaryRandomSampling, FloatRandomSampling
from pymoo.optimize import minimize as pymoo_minimize

from .models import (
    Aggregation,
    Approach,
    BoundOperator,
    Problem,
    QualityIndicators,
    Run,
    Solution,
    ValidationIssue,
    ValidationResult,
)


def validate(problem: Problem) -> ValidationResult:
    """Check if a problem is ready to optimize."""
    issues: list[ValidationIssue] = []
    missing_scores: list[dict[str, str]] = []

    # Duplicate objective names
    obj_name_list = [o.name for o in problem.objectives]
    obj_name_dupes = {n for n in obj_name_list if obj_name_list.count(n) > 1}
    if obj_name_dupes:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Duplicate objective names: {obj_name_dupes}.",
        ))

    # Duplicate option names
    opt_name_list = [o.name for o in problem.options]
    opt_name_dupes = {n for n in opt_name_list if opt_name_list.count(n) > 1}
    if opt_name_dupes:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Duplicate option names: {opt_name_dupes}.",
        ))

    # Need >= 2 objectives
    if len(problem.objectives) < 2:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Need at least 2 objectives, have {len(problem.objectives)}.",
        ))

    # Need >= 3 options
    if len(problem.options) < 3:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Need at least 3 options, have {len(problem.options)}.",
        ))

    # Score matrix completeness
    obj_names = {o.name for o in problem.objectives}
    opt_names = {o.name for o in problem.options}
    scored = {(s.option, s.objective) for s in problem.scores}

    for opt in opt_names:
        for obj in obj_names:
            if (opt, obj) not in scored:
                missing_scores.append({"option": opt, "objective": obj})

    if missing_scores:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Score matrix incomplete: {len(missing_scores)} missing scores.",
        ))

    # Constraint feasibility checks
    for c in problem.constraints:
        if c.type == "force_include" and c.option not in opt_names:
            issues.append(ValidationIssue(
                severity="error",
                message=f"force_include references unknown option '{c.option}'.",
            ))
        elif c.type == "force_exclude" and c.option not in opt_names:
            issues.append(ValidationIssue(
                severity="error",
                message=f"force_exclude references unknown option '{c.option}'.",
            ))
        elif c.type == "objective_bound" and c.objective not in obj_names:
            issues.append(ValidationIssue(
                severity="error",
                message=f"objective_bound references unknown objective '{c.objective}'.",
            ))

    # Check force_include + force_exclude conflict
    forced_in = {c.option for c in problem.constraints if c.type == "force_include"}
    forced_out = {c.option for c in problem.constraints if c.type == "force_exclude"}
    conflict = forced_in & forced_out
    if conflict:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Options both force_include and force_exclude: {conflict}.",
        ))

    # Check cardinality feasibility
    available = len(opt_names - forced_out)
    for c in problem.constraints:
        if c.type == "cardinality":
            if c.min > available:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"Cardinality min ({c.min}) exceeds available options ({available}).",
                ))
            if c.min > c.max:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"Cardinality min ({c.min}) > max ({c.max}).",
                ))
            if len(forced_in) > c.max:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"force_include count ({len(forced_in)}) exceeds cardinality max ({c.max}).",
                ))

    ready = all(i.severity != "error" for i in issues)
    return ValidationResult(ready=ready, issues=issues, missing_scores=missing_scores)


def _parse_constraints(problem: Problem) -> tuple:
    """Extract constraint parameters from problem. Shared by binary and proportional."""
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    opt_index = {name: i for i, name in enumerate(opt_names)}

    forced_in_idx = set()
    forced_out_idx = set()
    cardinality_min = 1
    cardinality_max = len(opt_names)
    obj_bounds: list[tuple[int, BoundOperator, float]] = []

    for c in problem.constraints:
        if c.type == "force_include":
            forced_in_idx.add(opt_index[c.option])
        elif c.type == "force_exclude":
            forced_out_idx.add(opt_index[c.option])
        elif c.type == "cardinality":
            cardinality_min = c.min
            cardinality_max = c.max
        elif c.type == "objective_bound":
            obj_idx = next(j for j, o in enumerate(obj_list) if o.name == c.objective)
            obj_bounds.append((obj_idx, c.operator, c.value))

    return forced_in_idx, forced_out_idx, cardinality_min, cardinality_max, obj_bounds


def _build_score_matrix(problem: Problem) -> np.ndarray:
    """Build score_matrix[opt_idx][obj_idx] from problem scores."""
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    score_map = {(s.option, s.objective): s.value for s in problem.scores}
    matrix = np.zeros((len(opt_names), len(obj_list)))
    for i, opt in enumerate(opt_names):
        for j, obj in enumerate(obj_list):
            matrix[i, j] = score_map[(opt, obj.name)]
    return matrix


def optimize(problem: Problem) -> Run:
    """Validate and run NSGA-II. Returns a Run with solutions."""
    vr = validate(problem)
    if not vr.ready:
        raise ValueError(f"Problem not ready: {[i.message for i in vr.issues]}")

    if problem.approach == Approach.proportional:
        return _optimize_proportional(problem)
    return _optimize_binary(problem)


def _optimize_binary(problem: Problem) -> Run:
    """Binary mode: pick K of N options."""
    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    score_matrix = _build_score_matrix(problem)
    forced_in, forced_out, card_min, card_max, obj_bounds = _parse_constraints(problem)

    pymoo_problem = _FrontierProblem(
        n_options=n_options,
        score_matrix=score_matrix,
        objectives=obj_list,
        forced_in=forced_in,
        forced_out=forced_out,
        cardinality_min=card_min,
        cardinality_max=card_max,
        obj_bounds=obj_bounds,
    )

    if n_options <= 20:
        pop_size, n_gen = 100, 200
    else:
        pop_size, n_gen = n_options * 5, n_options * 10

    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=BinaryRandomSampling(),
        crossover=TwoPointCrossover(prob=0.9),
        mutation=BitflipMutation(prob=1.0 / n_options),
        eliminate_duplicates=True,
    )

    result = pymoo_minimize(
        pymoo_problem, algorithm, ("n_gen", n_gen), seed=42, verbose=False,
    )

    solutions: list[Solution] = []
    if result.F is not None and len(result.F) > 0:
        for idx, (x, f) in enumerate(zip(result.X, result.F)):
            selected = [opt_names[i] for i in range(n_options) if x[i] > 0.5]
            obj_values = {}
            for j, obj in enumerate(obj_list):
                val = -f[j] if obj.direction.value == "maximize" else f[j]
                obj_values[obj.name] = round(float(val), 4)
            solutions.append(Solution(
                solution_id=idx, selected_options=selected, objective_values=obj_values,
            ))

    solutions = _sort_and_reindex(solutions, obj_list)
    return Run(solutions=solutions, quality=_compute_quality(result))


def _optimize_proportional(problem: Problem) -> Run:
    """Proportional mode: allocate integer percentages (0-100, sum to 100)."""
    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    score_matrix = _build_score_matrix(problem)
    forced_in, forced_out, card_min, card_max, obj_bounds = _parse_constraints(problem)

    pymoo_problem = _ProportionalProblem(
        n_options=n_options,
        score_matrix=score_matrix,
        objectives=obj_list,
        forced_in=forced_in,
        forced_out=forced_out,
        cardinality_min=card_min,
        cardinality_max=card_max,
        obj_bounds=obj_bounds,
    )

    if n_options <= 20:
        pop_size, n_gen = 150, 300
    else:
        pop_size, n_gen = n_options * 8, n_options * 15

    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True,
    )

    result = pymoo_minimize(
        pymoo_problem, algorithm, ("n_gen", n_gen), seed=42, verbose=False,
    )

    solutions: list[Solution] = []
    if result.F is not None and len(result.F) > 0:
        for idx, (x, f) in enumerate(zip(result.X, result.F)):
            # Round to integers and normalize to sum to 100
            raw = np.maximum(np.round(x), 0).astype(int)
            # Redistribute rounding error to largest allocation
            diff = 100 - raw.sum()
            if diff != 0 and raw.max() > 0:
                raw[np.argmax(raw)] += diff

            allocs = {opt_names[i]: int(raw[i]) for i in range(n_options)}
            selected = [opt_names[i] for i in range(n_options) if raw[i] > 0]

            obj_values = {}
            for j, obj in enumerate(obj_list):
                val = -f[j] if obj.direction.value == "maximize" else f[j]
                obj_values[obj.name] = round(float(val), 4)

            solutions.append(Solution(
                solution_id=idx,
                selected_options=selected,
                objective_values=obj_values,
                allocations=allocs,
            ))

    solutions = _sort_and_reindex(solutions, obj_list)
    return Run(solutions=solutions, quality=_compute_quality(result))


def _sort_and_reindex(solutions: list[Solution], obj_list: list) -> list[Solution]:
    """Sort solutions by first objective and reindex."""
    if solutions and obj_list:
        first_obj = obj_list[0].name
        reverse = obj_list[0].direction.value == "maximize"
        solutions.sort(key=lambda s: s.objective_values.get(first_obj, 0), reverse=reverse)
        for i, s in enumerate(solutions):
            s.solution_id = i
    return solutions
    return run


class _FrontierProblem(PymooProblem):
    """pymoo problem wrapper for binary portfolio selection."""

    def __init__(
        self,
        n_options: int,
        score_matrix: np.ndarray,
        objectives: list,
        forced_in: set[int],
        forced_out: set[int],
        cardinality_min: int,
        cardinality_max: int,
        obj_bounds: list[tuple[int, BoundOperator, float]],
    ):
        # Count inequality constraints
        n_ieq = 0
        n_ieq += 2  # cardinality min and max
        n_ieq += len(forced_in)  # each forced in
        n_ieq += len(forced_out)  # each forced out
        n_ieq += len(obj_bounds)  # each objective bound

        super().__init__(
            n_var=n_options,
            n_obj=len(objectives),
            n_ieq_constr=n_ieq,
            xl=0,
            xu=1,
        )
        self.score_matrix = score_matrix
        self.objectives = objectives
        self.forced_in = forced_in
        self.forced_out = forced_out
        self.cardinality_min = cardinality_min
        self.cardinality_max = cardinality_max
        self.obj_bounds = obj_bounds

    def _aggregate_objective(self, X_bin: np.ndarray, j: int) -> np.ndarray:
        """Compute objective j values for all population members using the correct aggregation."""
        agg = self.objectives[j].aggregation
        n_pop = X_bin.shape[0]

        if agg == Aggregation.sum:
            return X_bin @ self.score_matrix[:, j]
        elif agg == Aggregation.avg:
            sums = X_bin @ self.score_matrix[:, j]
            counts = np.maximum(X_bin.sum(axis=1), 1.0)  # avoid div by zero
            return sums / counts
        elif agg == Aggregation.min:
            vals = np.full(n_pop, np.inf)
            for i in range(n_pop):
                selected = X_bin[i] > 0.5
                if selected.any():
                    vals[i] = self.score_matrix[selected, j].min()
                else:
                    vals[i] = 0.0
            return vals
        elif agg == Aggregation.max:
            vals = np.full(n_pop, -np.inf)
            for i in range(n_pop):
                selected = X_bin[i] > 0.5
                if selected.any():
                    vals[i] = self.score_matrix[selected, j].max()
                else:
                    vals[i] = 0.0
            return vals
        else:
            return X_bin @ self.score_matrix[:, j]  # fallback to sum

    def _evaluate(self, X, out, *args, **kwargs):
        # Round to binary
        X_bin = (X > 0.5).astype(float)
        n_pop = X_bin.shape[0]
        n_obj = len(self.objectives)

        # Objectives: compute per-objective using aggregation method
        F = np.zeros((n_pop, n_obj))
        for j in range(n_obj):
            F[:, j] = self._aggregate_objective(X_bin, j)

        # pymoo minimizes — negate maximize objectives
        for j, obj in enumerate(self.objectives):
            if obj.direction.value == "maximize":
                F[:, j] = -F[:, j]

        out["F"] = F

        # Constraints: g(x) <= 0 means feasible
        G = []

        # Cardinality: min <= sum(x) <= max
        counts = X_bin.sum(axis=1)
        G.append(self.cardinality_min - counts)  # min - count <= 0
        G.append(counts - self.cardinality_max)  # count - max <= 0

        # Force include: x[i] >= 1 → 1 - x[i] <= 0
        for i in self.forced_in:
            G.append(1.0 - X_bin[:, i])

        # Force exclude: x[i] <= 0 → x[i] <= 0
        for i in self.forced_out:
            G.append(X_bin[:, i])

        # Objective bounds — use same aggregation as the objective
        for obj_idx, operator, value in self.obj_bounds:
            obj_vals = self._aggregate_objective(X_bin, obj_idx)
            if operator == BoundOperator.max:
                G.append(obj_vals - value)  # val <= max → val - max <= 0
            else:  # min
                G.append(value - obj_vals)  # val >= min → min - val <= 0

        out["G"] = np.column_stack(G) if G else np.zeros((n_pop, 0))


class _ProportionalProblem(PymooProblem):
    """pymoo problem wrapper for proportional allocation (0-100 percentages)."""

    def __init__(
        self,
        n_options: int,
        score_matrix: np.ndarray,
        objectives: list,
        forced_in: set[int],
        forced_out: set[int],
        cardinality_min: int,
        cardinality_max: int,
        obj_bounds: list[tuple[int, BoundOperator, float]],
    ):
        # Constraints: sum=100 (2 ineq), cardinality (2), forced in/out, obj bounds
        n_ieq = 2 + 2 + len(forced_in) + len(forced_out) + len(obj_bounds)

        super().__init__(
            n_var=n_options,
            n_obj=len(objectives),
            n_ieq_constr=n_ieq,
            xl=0,
            xu=100,
        )
        self.score_matrix = score_matrix
        self.objectives = objectives
        self.forced_in = forced_in
        self.forced_out = forced_out
        self.cardinality_min = cardinality_min
        self.cardinality_max = cardinality_max
        self.obj_bounds = obj_bounds

    def _aggregate_objective(self, X: np.ndarray, j: int) -> np.ndarray:
        """Compute objective j for proportional allocations."""
        agg = self.objectives[j].aggregation
        n_pop = X.shape[0]
        # Fractions: allocation / 100
        fracs = X / 100.0

        if agg == Aggregation.sum:
            # Weighted sum: sum(frac_k * score_k)
            return fracs @ self.score_matrix[:, j]
        elif agg == Aggregation.avg:
            # Weighted average: sum(frac_k * score_k) / sum(frac_k) where frac_k > 0
            weighted_sums = fracs @ self.score_matrix[:, j]
            total_fracs = np.maximum(fracs.sum(axis=1), 0.01)  # avoid div by zero
            return weighted_sums / total_fracs
        elif agg == Aggregation.min:
            vals = np.full(n_pop, np.inf)
            for i in range(n_pop):
                selected = X[i] > 0.5
                if selected.any():
                    vals[i] = self.score_matrix[selected, j].min()
                else:
                    vals[i] = 0.0
            return vals
        elif agg == Aggregation.max:
            vals = np.full(n_pop, -np.inf)
            for i in range(n_pop):
                selected = X[i] > 0.5
                if selected.any():
                    vals[i] = self.score_matrix[selected, j].max()
                else:
                    vals[i] = 0.0
            return vals
        else:
            return fracs @ self.score_matrix[:, j]

    def _evaluate(self, X, out, *args, **kwargs):
        n_pop = X.shape[0]
        n_obj = len(self.objectives)

        # Objectives
        F = np.zeros((n_pop, n_obj))
        for j in range(n_obj):
            F[:, j] = self._aggregate_objective(X, j)

        for j, obj in enumerate(self.objectives):
            if obj.direction.value == "maximize":
                F[:, j] = -F[:, j]

        out["F"] = F

        # Constraints
        G = []

        # Sum to 100: |sum - 100| <= 0 via two inequalities
        sums = X.sum(axis=1)
        G.append(sums - 100.0)   # sum <= 100
        G.append(100.0 - sums)   # sum >= 100

        # Cardinality: count of non-zero allocations
        allocated_count = (X > 0.5).sum(axis=1).astype(float)
        G.append(self.cardinality_min - allocated_count)
        G.append(allocated_count - self.cardinality_max)

        # Force include: allocation must be > 0 (use threshold 0.5)
        for i in self.forced_in:
            G.append(0.5 - X[:, i])

        # Force exclude: allocation must be 0 (use threshold 0.5)
        for i in self.forced_out:
            G.append(X[:, i] - 0.5)

        # Objective bounds
        for obj_idx, operator, value in self.obj_bounds:
            obj_vals = self._aggregate_objective(X, obj_idx)
            if operator == BoundOperator.max:
                G.append(obj_vals - value)
            else:
                G.append(value - obj_vals)

        out["G"] = np.column_stack(G) if G else np.zeros((n_pop, 0))


def analyze_infeasibility(problem: Problem) -> dict:
    """Diagnose which constraints are most likely causing infeasibility.

    Tests each constraint by relaxing it individually and checking if
    feasible solutions exist via brute-force enumeration of small subsets.
    """
    from itertools import combinations

    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    n_options = len(opt_names)

    # Build score lookup
    score_map: dict[tuple[str, str], float] = {}
    for s in problem.scores:
        score_map[(s.option, s.objective)] = s.value

    # Build aggregation map from objectives
    agg_map = {o.name: o.aggregation for o in problem.objectives}

    # Parse constraints
    forced_in = {c.option for c in problem.constraints if c.type == "force_include"}
    forced_out = {c.option for c in problem.constraints if c.type == "force_exclude"}
    card_min, card_max = 1, n_options
    obj_bounds = []
    for c in problem.constraints:
        if c.type == "cardinality":
            card_min, card_max = c.min, c.max
        elif c.type == "objective_bound":
            obj_bounds.append((c.objective, c.operator, c.value))

    def _aggregate_for_portfolio(selected: set[str], obj_name: str) -> float:
        """Compute aggregated objective value for a portfolio, respecting aggregation mode."""
        scores = [score_map.get((o, obj_name), 0) for o in selected]
        if not scores:
            return 0.0
        agg = agg_map.get(obj_name, Aggregation.sum)
        if agg == Aggregation.sum:
            return sum(scores)
        elif agg == Aggregation.avg:
            return sum(scores) / len(scores)
        elif agg == Aggregation.min:
            return min(scores)
        elif agg == Aggregation.max:
            return max(scores)
        return sum(scores)

    def portfolio_feasible(selected: set[str], skip_constraint=None) -> bool:
        """Check if a portfolio satisfies all constraints except skip_constraint."""
        # Cardinality
        if skip_constraint != "cardinality":
            if not (card_min <= len(selected) <= card_max):
                return False
        # Force include
        for opt in forced_in:
            if skip_constraint == f"force_include:{opt}":
                continue
            if opt not in selected:
                return False
        # Force exclude
        for opt in forced_out:
            if skip_constraint == f"force_exclude:{opt}":
                continue
            if opt in selected:
                return False
        # Objective bounds
        for obj_name, operator, value in obj_bounds:
            if skip_constraint == f"objective_bound:{obj_name}:{operator}:{value}":
                continue
            agg_val = _aggregate_for_portfolio(selected, obj_name)
            if operator.value == "max" and agg_val > value:
                return False
            if operator.value == "min" and agg_val < value:
                return False
        return True

    # Available options (respecting force_exclude for enumeration)
    available = [o for o in opt_names if o not in forced_out]

    # Try to find any feasible portfolio (brute force for small problems)
    # Limit enumeration to avoid combinatorial explosion
    max_combos = 50000

    def has_feasible(skip_constraint=None) -> bool:
        pool = available if skip_constraint is None or not skip_constraint.startswith("force_exclude:") else opt_names
        for k in range(max(1, card_min), min(len(pool), card_max) + 1):
            count = 0
            for combo in combinations(pool, k):
                if portfolio_feasible(set(combo), skip_constraint):
                    return True
                count += 1
                if count >= max_combos:
                    return False  # can't tell, assume not
        return False

    # Build constraint labels for testing
    constraint_labels = []
    for c in problem.constraints:
        if c.type == "cardinality":
            constraint_labels.append(("cardinality", c.model_dump()))
        elif c.type == "force_include":
            constraint_labels.append((f"force_include:{c.option}", c.model_dump()))
        elif c.type == "force_exclude":
            constraint_labels.append((f"force_exclude:{c.option}", c.model_dump()))
        elif c.type == "objective_bound":
            constraint_labels.append(
                (f"objective_bound:{c.objective}:{c.operator}:{c.value}", c.model_dump())
            )

    # Test each constraint: does removing it make the problem feasible?
    binding = []
    suggestions = []
    for label, constraint_dict in constraint_labels:
        if has_feasible(skip_constraint=label):
            binding.append(constraint_dict)
            if label == "cardinality":
                suggestions.append(f"Relaxing cardinality ({card_min}-{card_max}) may help.")
            elif label.startswith("force_include:"):
                opt = label.split(":", 1)[1]
                suggestions.append(f"Removing force_include on '{opt}' may help.")
            elif label.startswith("force_exclude:"):
                opt = label.split(":", 1)[1]
                suggestions.append(f"Removing force_exclude on '{opt}' may help.")
            elif label.startswith("objective_bound:"):
                parts = label.split(":")
                suggestions.append(f"Relaxing {parts[2]} bound on '{parts[1]}' ({parts[3]}) may help.")

    if not binding:
        binding = [c.model_dump() for c in problem.constraints]
        suggestions = ["Constraints may be jointly infeasible. Try relaxing multiple constraints."]

    return {"binding_constraints": binding, "suggestions": suggestions}


def _compute_quality(result) -> QualityIndicators:
    """Compute quality indicators from pymoo result."""
    if result.F is None or len(result.F) < 2:
        return QualityIndicators()

    F = result.F

    # Normalized hypervolume (approximate): fraction of bounding box dominated
    f_min = F.min(axis=0)
    f_max = F.max(axis=0)
    spread = f_max - f_min
    if np.all(spread > 0):
        F_norm = (F - f_min) / spread
        # Simple hypervolume approximation using reference point at (1.1, ..., 1.1)
        ref = np.ones(F.shape[1]) * 1.1
        hv = _approx_hypervolume(F_norm, ref)
        hv_max = np.prod(ref)
        hv_normalized = round(float(hv / hv_max), 4) if hv_max > 0 else None
    else:
        hv_normalized = None

    # Spacing CV: coefficient of variation of nearest-neighbor distances
    if len(F) >= 3:
        from scipy.spatial.distance import cdist
        dists = cdist(F, F)
        np.fill_diagonal(dists, np.inf)
        nn_dists = dists.min(axis=1)
        mean_d = nn_dists.mean()
        spacing_cv = round(float(nn_dists.std() / mean_d), 4) if mean_d > 0 else None
    else:
        spacing_cv = None

    return QualityIndicators(
        hypervolume_normalized=hv_normalized,
        spacing_cv=spacing_cv,
    )


def _approx_hypervolume(F: np.ndarray, ref: np.ndarray) -> float:
    """Monte Carlo hypervolume approximation for small dimensions."""
    n_samples = 10000
    n_obj = F.shape[1]
    rng = np.random.default_rng(42)

    # Sample random points in the bounding box [0, ref]
    samples = rng.uniform(0, ref, size=(n_samples, n_obj))

    # A sample is dominated if any Pareto point dominates it
    dominated = np.zeros(n_samples, dtype=bool)
    for f in F:
        dominated |= np.all(samples >= f, axis=1)

    vol_box = np.prod(ref)
    return float(dominated.sum() / n_samples * vol_box)

"""Optimizer: validate problem and run NSGA-II via pymoo."""

from __future__ import annotations

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem as PymooProblem
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.mutation.bitflip import BitflipMutation
from pymoo.operators.sampling.rnd import BinaryRandomSampling
from pymoo.optimize import minimize as pymoo_minimize

from .models import (
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


def optimize(problem: Problem) -> Run:
    """Validate and run NSGA-II. Returns a Run with solutions."""
    vr = validate(problem)
    if not vr.ready:
        raise ValueError(f"Problem not ready: {[i.message for i in vr.issues]}")

    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives

    # Build score lookup: score_matrix[opt_idx][obj_idx] = value
    score_map: dict[tuple[str, str], float] = {}
    for s in problem.scores:
        score_map[(s.option, s.objective)] = s.value

    score_matrix = np.zeros((n_options, len(obj_list)))
    for i, opt in enumerate(opt_names):
        for j, obj in enumerate(obj_list):
            score_matrix[i, j] = score_map[(opt, obj.name)]

    # Parse constraints
    forced_in_idx = set()
    forced_out_idx = set()
    cardinality_min = 1
    cardinality_max = n_options
    obj_bounds: list[tuple[int, BoundOperator, float]] = []

    opt_index = {name: i for i, name in enumerate(opt_names)}

    for c in problem.constraints:
        if c.type == "force_include":
            forced_in_idx.add(opt_index[c.option])
        elif c.type == "force_exclude":
            forced_out_idx.add(opt_index[c.option])
        elif c.type == "cardinality":
            cardinality_min = c.min
            cardinality_max = c.max
        elif c.type == "objective_bound":
            obj_idx = next(
                j for j, o in enumerate(obj_list) if o.name == c.objective
            )
            obj_bounds.append((obj_idx, c.operator, c.value))

    # Build pymoo problem
    pymoo_problem = _FrontierProblem(
        n_options=n_options,
        score_matrix=score_matrix,
        objectives=obj_list,
        forced_in=forced_in_idx,
        forced_out=forced_out_idx,
        cardinality_min=cardinality_min,
        cardinality_max=cardinality_max,
        obj_bounds=obj_bounds,
    )

    # Scale parameters based on problem size
    pop_size = max(100, n_options * 10)
    n_gen = max(200, n_options * 20)

    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=BinaryRandomSampling(),
        crossover=TwoPointCrossover(prob=0.9),
        mutation=BitflipMutation(prob=1.0 / n_options),
        eliminate_duplicates=True,
    )

    result = pymoo_minimize(
        pymoo_problem,
        algorithm,
        ("n_gen", n_gen),
        seed=42,
        verbose=False,
    )

    # Extract solutions
    solutions: list[Solution] = []
    if result.F is not None and len(result.F) > 0:
        for idx, (x, f) in enumerate(zip(result.X, result.F)):
            selected = [opt_names[i] for i in range(n_options) if x[i] > 0.5]
            obj_values = {}
            for j, obj in enumerate(obj_list):
                # pymoo minimizes, so we negated maximize objectives — reverse it
                val = -f[j] if obj.direction.value == "maximize" else f[j]
                obj_values[obj.name] = round(float(val), 4)
            solutions.append(Solution(
                solution_id=idx,
                selected_options=selected,
                objective_values=obj_values,
            ))

    # Sort by first objective value
    if solutions and obj_list:
        first_obj = obj_list[0].name
        reverse = obj_list[0].direction.value == "maximize"
        solutions.sort(key=lambda s: s.objective_values.get(first_obj, 0), reverse=reverse)
        # Re-index after sort
        for i, s in enumerate(solutions):
            s.solution_id = i

    run = Run(solutions=solutions, quality=_compute_quality(result))
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

    def _evaluate(self, X, out, *args, **kwargs):
        # Round to binary
        X_bin = (X > 0.5).astype(float)
        n_pop = X_bin.shape[0]

        # Objectives: portfolio score for each objective
        # F[i, j] = sum of score_matrix[k, j] for selected options k
        F = X_bin @ self.score_matrix  # (n_pop, n_obj)

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

        # Objective bounds
        for obj_idx, operator, value in self.obj_bounds:
            obj_vals = X_bin @ self.score_matrix[:, obj_idx]
            if operator == BoundOperator.max:
                G.append(obj_vals - value)  # val <= max → val - max <= 0
            else:  # min
                G.append(value - obj_vals)  # val >= min → min - val <= 0

        out["G"] = np.column_stack(G) if G else np.zeros((n_pop, 0))


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

"""Optimizer: validate problem and run NSGA-II/NSGA-III via pymoo."""

from __future__ import annotations

import math

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.core.problem import Problem as PymooProblem
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.bitflip import BitflipMutation
from pymoo.operators.mutation.pm import PM
from pymoo.core.repair import Repair
from pymoo.core.sampling import Sampling
from pymoo.operators.sampling.rnd import BinaryRandomSampling, FloatRandomSampling
from pymoo.optimize import minimize as pymoo_minimize
from pymoo.util.ref_dirs import get_reference_directions


class _SimplexSampling(Sampling):
    """Sample initial populations on the simplex (allocations sum to 100)."""

    def _do(self, problem, n_samples, **kwargs):
        n_var = problem.n_var
        # Dirichlet(alpha=1) generates uniform random points on the simplex
        raw = np.random.dirichlet(np.ones(n_var), size=n_samples) * 100.0
        # Round to integers while preserving sum = 100
        X = np.floor(raw).astype(float)
        remainders = raw - X
        for i in range(n_samples):
            diff = int(100 - X[i].sum())
            if diff > 0:
                # Distribute remaining units to largest remainders
                indices = np.argsort(remainders[i])[::-1][:diff]
                X[i, indices] += 1.0
        return X


class _SimplexRepair(Repair):
    """After crossover/mutation, project solutions back onto the simplex (sum=100, non-negative)."""

    def _do(self, problem, X, **kwargs):
        # Clamp to non-negative
        X = np.maximum(X, 0.0)
        # Normalize each row to sum to 100
        row_sums = X.sum(axis=1, keepdims=True)
        row_sums = np.maximum(row_sums, 1e-9)  # avoid div by zero
        X = X / row_sums * 100.0
        return X

from .models import (
    Aggregation,
    Approach,
    BoundOperator,
    OptimizeMode,
    Problem,
    QualityIndicators,
    Run,
    Solution,
    ValidationIssue,
    ValidationResult,
    _content_signature,
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
        elif c.type == "exclusion_pair":
            for opt in (c.option_a, c.option_b):
                if opt not in opt_names:
                    issues.append(ValidationIssue(
                        severity="error",
                        message=f"exclusion_pair references unknown option '{opt}'.",
                    ))
            if c.option_a == c.option_b:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"exclusion_pair has same option for both: '{c.option_a}'.",
                ))
        elif c.type == "dependency":
            for opt in (c.if_option, c.then_option):
                if opt not in opt_names:
                    issues.append(ValidationIssue(
                        severity="error",
                        message=f"dependency references unknown option '{opt}'.",
                    ))
        elif c.type == "group_limit":
            for opt in c.options:
                if opt not in opt_names:
                    issues.append(ValidationIssue(
                        severity="error",
                        message=f"group_limit references unknown option '{opt}'.",
                    ))
            if c.max < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"group_limit max ({c.max}) must be non-negative.",
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


def _parse_constraints(problem: Problem) -> dict:
    """Extract constraint parameters from problem. Shared by binary and proportional."""
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    opt_index = {name: i for i, name in enumerate(opt_names)}

    forced_in_idx = set()
    forced_out_idx = set()
    cardinality_min = 1
    cardinality_max = len(opt_names)
    obj_bounds: list[tuple[int, BoundOperator, float]] = []
    exclusion_pairs: list[tuple[int, int]] = []
    dependencies: list[tuple[int, int]] = []  # (if_idx, then_idx)
    group_limits: list[tuple[list[int], int]] = []  # (group_indices, max)

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
        elif c.type == "exclusion_pair":
            exclusion_pairs.append((opt_index[c.option_a], opt_index[c.option_b]))
        elif c.type == "dependency":
            dependencies.append((opt_index[c.if_option], opt_index[c.then_option]))
        elif c.type == "group_limit":
            group_indices = [opt_index[o] for o in c.options]
            group_limits.append((group_indices, c.max))

    return {
        "forced_in": forced_in_idx,
        "forced_out": forced_out_idx,
        "cardinality_min": cardinality_min,
        "cardinality_max": cardinality_max,
        "obj_bounds": obj_bounds,
        "exclusion_pairs": exclusion_pairs,
        "dependencies": dependencies,
        "group_limits": group_limits,
    }


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


def _tune_parameters(problem: Problem, mode: OptimizeMode) -> tuple:
    """Return (algorithm, n_gen) adapted to problem size and mode.

    Scales directly from the two independent dimensions that matter:
      1. Solution space size — driven by n_options and approach type.
         Binary: 2^n values. Proportional: ~100^n (continuous, much larger).
         We use log2 of the space to set pop/gen multipliers.
      2. Objective count — independently drives algorithm selection and
         population needs (more objectives need more population for coverage).

    Mode controls the budget: fast for exploration, thorough for convergence.
    """
    n = len(problem.options)
    n_obj = len(problem.objectives)
    is_binary = problem.approach == Approach.binary
    is_fast = mode == OptimizeMode.fast
    use_nsga3 = n_obj >= 4

    # --- Solution space drives pop_size and n_gen ---
    # Binary space: 2^n. Proportional space: effectively continuous (~100^n).
    # Use log2 of space as a scaling factor, capped to keep things sane.
    # Binary: log2(2^n) = n. Proportional: log2(100^n) ≈ 6.6n.
    if is_binary:
        space_factor = n
    else:
        space_factor = 6.6 * n

    # Population: scales with sqrt of space_factor (diminishing returns).
    # More objectives need more population to cover the Pareto surface.
    obj_multiplier = 1.0 + 0.3 * (n_obj - 2)  # 1.0 at 2 obj, 2.8 at 8 obj
    mode_pop = 1.0 if is_fast else 1.8
    pop_size = int(math.sqrt(space_factor) * 10 * obj_multiplier * mode_pop)

    # Generations: scales with space_factor more aggressively than pop.
    # Thorough mode gets substantially more generations for convergence.
    mode_gen = 1.0 if is_fast else 2.5
    gen_base = max(8, int(space_factor * 0.5))
    n_gen = int(gen_base * obj_multiplier * mode_gen)

    # Floors and caps
    pop_size = max(50, min(pop_size, 2000))
    n_gen = max(50, min(n_gen, 3000))

    # --- Algorithm selection (objective count only) ---
    if use_nsga3:
        n_partitions = max(3, 12 - n_obj)
        ref_dirs = get_reference_directions("das-dennis", n_obj, n_partitions=n_partitions)
        pop_size = len(ref_dirs)  # pymoo requires pop_size == len(ref_dirs)
        AlgClass = NSGA3
        alg_kwargs: dict = {"ref_dirs": ref_dirs, "pop_size": pop_size}
    else:
        AlgClass = NSGA2
        alg_kwargs = {"pop_size": pop_size}

    # --- Operator adaptation (approach type only) ---
    if is_binary:
        # Mutation prob: ~1 bit flip per individual on average, bounded
        mut_prob = max(0.01, min(0.25, 1.0 / n))
        alg_kwargs.update(
            sampling=BinaryRandomSampling(),
            crossover=TwoPointCrossover(prob=0.9),
            mutation=BitflipMutation(prob=mut_prob),
            eliminate_duplicates=True,
        )
    else:
        # Larger search spaces benefit from higher eta (more exploitation)
        eta_scale = min(1.0, math.log2(max(n, 3)) / math.log2(200))
        sbx_eta = int(10 + eta_scale * 20)   # 10-30
        pm_eta = int(15 + eta_scale * 25)     # 15-40
        alg_kwargs.update(
            sampling=_SimplexSampling(),
            crossover=SBX(prob=0.9, eta=sbx_eta),
            mutation=PM(eta=pm_eta),
            repair=_SimplexRepair(),
            eliminate_duplicates=True,
        )

    return AlgClass(**alg_kwargs), n_gen


def optimize(problem: Problem, mode: OptimizeMode | None = None) -> Run:
    """Validate and run multi-objective optimization. Returns a Run with solutions."""
    if mode is None:
        mode = OptimizeMode.fast
    vr = validate(problem)
    if not vr.ready:
        raise ValueError(f"Problem not ready: {[i.message for i in vr.issues]}")

    if problem.approach == Approach.proportional:
        return _optimize_proportional(problem, mode)
    return _optimize_binary(problem, mode)


def optimize_scenarios(problem: Problem, mode: OptimizeMode | None = None) -> dict[str, Run]:
    """Run optimization independently per scenario. Returns {scenario_name: Run}.

    Each scenario is solved as a fully independent optimization — no probability
    weighting required. Probabilities are optional and only used downstream in
    explorer for expected-value analysis.

    Scenarios run in parallel to stay within MCP tool-call timeouts.
    """
    from concurrent.futures import ThreadPoolExecutor

    if not problem.scenario_config or not problem.scenario_config.enabled:
        raise ValueError("Scenario config not enabled.")
    if not problem.scenario_config.scenarios:
        raise ValueError("No scenarios defined.")

    def _build_and_solve(scenario: "Scenario") -> tuple[str, Run]:
        scenario_problem = problem.model_copy(deep=True)

        # 1) Apply bulk score_adjustments (multiply/add) by objective
        if scenario.score_adjustments:
            adj_map = {a.objective: a for a in scenario.score_adjustments}
            for score in scenario_problem.scores:
                if score.objective in adj_map:
                    adj = adj_map[score.objective]
                    if adj.multiply is not None:
                        score.value *= adj.multiply
                    if adj.add is not None:
                        score.value += adj.add

        # 2) Apply explicit score_overrides (takes precedence)
        if scenario.score_overrides:
            override_map = {(s.option, s.objective): s.value for s in scenario.score_overrides}
            for score in scenario_problem.scores:
                key = (score.option, score.objective)
                if key in override_map:
                    score.value = override_map[key]

        # 3) Apply constraint overrides (full replacement when provided)
        if scenario.constraint_overrides:
            scenario_problem.constraints = list(scenario.constraint_overrides)

        scenario_problem.scenario_config = None
        return scenario.name, optimize(scenario_problem, mode=mode)

    with ThreadPoolExecutor(max_workers=len(problem.scenario_config.scenarios)) as pool:
        futures = [pool.submit(_build_and_solve, s) for s in problem.scenario_config.scenarios]
        results = dict(f.result() for f in futures)

    return results


def _optimize_binary(problem: Problem, mode: OptimizeMode) -> Run:
    """Binary mode: pick K of N options."""
    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    score_matrix = _build_score_matrix(problem)
    cp = _parse_constraints(problem)

    pymoo_problem = _FrontierProblem(
        n_options=n_options, score_matrix=score_matrix, objectives=obj_list, **cp,
    )

    algorithm, n_gen = _tune_parameters(problem, mode)

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


def _optimize_proportional(problem: Problem, mode: OptimizeMode) -> Run:
    """Proportional mode: allocate integer percentages (0-100, sum to 100)."""
    n_options = len(problem.options)
    opt_names = [o.name for o in problem.options]
    obj_list = problem.objectives
    score_matrix = _build_score_matrix(problem)
    cp = _parse_constraints(problem)

    pymoo_problem = _ProportionalProblem(
        n_options=n_options, score_matrix=score_matrix, objectives=obj_list, **cp,
    )

    algorithm, n_gen = _tune_parameters(problem, mode)

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
    """Sort solutions by first objective, reindex, and stamp content signatures."""
    if solutions and obj_list:
        first_obj = obj_list[0].name
        reverse = obj_list[0].direction.value == "maximize"
        solutions.sort(key=lambda s: s.objective_values.get(first_obj, 0), reverse=reverse)
        for i, s in enumerate(solutions, start=1):
            s.solution_id = i
            s.content_signature = _content_signature(s.selected_options, s.allocations)
    return solutions


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
        exclusion_pairs: list[tuple[int, int]] | None = None,
        dependencies: list[tuple[int, int]] | None = None,
        group_limits: list[tuple[list[int], int]] | None = None,
    ):
        exclusion_pairs = exclusion_pairs or []
        dependencies = dependencies or []
        group_limits = group_limits or []

        n_ieq = 0
        n_ieq += 2  # cardinality min and max
        n_ieq += len(forced_in)
        n_ieq += len(forced_out)
        n_ieq += len(obj_bounds)
        n_ieq += len(exclusion_pairs)  # x[a] + x[b] <= 1
        n_ieq += len(dependencies)     # x[a] - x[b] <= 0
        n_ieq += len(group_limits)     # sum(group) <= max

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
        self.exclusion_pairs = exclusion_pairs
        self.dependencies = dependencies
        self.group_limits = group_limits

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
                G.append(obj_vals - value)
            else:
                G.append(value - obj_vals)

        # Exclusion pairs: x[a] + x[b] <= 1
        for a, b in self.exclusion_pairs:
            G.append(X_bin[:, a] + X_bin[:, b] - 1.0)

        # Dependencies: if x[a] then x[b] → x[a] - x[b] <= 0
        for if_idx, then_idx in self.dependencies:
            G.append(X_bin[:, if_idx] - X_bin[:, then_idx])

        # Group limits: sum(x[i] for i in group) <= max
        for group_indices, max_count in self.group_limits:
            group_sum = sum(X_bin[:, i] for i in group_indices)
            G.append(group_sum - max_count)

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
        exclusion_pairs: list[tuple[int, int]] | None = None,
        dependencies: list[tuple[int, int]] | None = None,
        group_limits: list[tuple[list[int], int]] | None = None,
    ):
        exclusion_pairs = exclusion_pairs or []
        dependencies = dependencies or []
        group_limits = group_limits or []

        n_ieq = 2 + 2 + len(forced_in) + len(forced_out) + len(obj_bounds)
        n_ieq += len(exclusion_pairs) + len(dependencies) + len(group_limits)

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
        self.exclusion_pairs = exclusion_pairs
        self.dependencies = dependencies
        self.group_limits = group_limits

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

        # Exclusion pairs: can't allocate to both (both > 0.5)
        allocated = (X > 0.5).astype(float)
        for a, b in self.exclusion_pairs:
            G.append(allocated[:, a] + allocated[:, b] - 1.0)

        # Dependencies: if allocated to a, must allocate to b
        for if_idx, then_idx in self.dependencies:
            G.append(allocated[:, if_idx] - allocated[:, then_idx])

        # Group limits: count of allocated in group <= max
        for group_indices, max_count in self.group_limits:
            group_sum = sum(allocated[:, i] for i in group_indices)
            G.append(group_sum - max_count)

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
    exclusion_pairs = [(c.option_a, c.option_b) for c in problem.constraints if c.type == "exclusion_pair"]
    dependencies = [(c.if_option, c.then_option) for c in problem.constraints if c.type == "dependency"]
    group_limits = [(c.options, c.max) for c in problem.constraints if c.type == "group_limit"]
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
        # Exclusion pairs
        for opt_a, opt_b in exclusion_pairs:
            if skip_constraint == f"exclusion_pair:{opt_a}:{opt_b}":
                continue
            if opt_a in selected and opt_b in selected:
                return False
        # Dependencies
        for if_opt, then_opt in dependencies:
            if skip_constraint == f"dependency:{if_opt}:{then_opt}":
                continue
            if if_opt in selected and then_opt not in selected:
                return False
        # Group limits
        for group_opts, max_count in group_limits:
            if skip_constraint == f"group_limit:{','.join(group_opts)}:{max_count}":
                continue
            if sum(1 for o in group_opts if o in selected) > max_count:
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
        elif c.type == "exclusion_pair":
            constraint_labels.append(
                (f"exclusion_pair:{c.option_a}:{c.option_b}", c.model_dump())
            )
        elif c.type == "dependency":
            constraint_labels.append(
                (f"dependency:{c.if_option}:{c.then_option}", c.model_dump())
            )
        elif c.type == "group_limit":
            constraint_labels.append(
                (f"group_limit:{','.join(c.options)}:{c.max}", c.model_dump())
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
            elif label.startswith("exclusion_pair:"):
                parts = label.split(":")
                suggestions.append(f"Removing exclusion between '{parts[1]}' and '{parts[2]}' may help.")
            elif label.startswith("dependency:"):
                parts = label.split(":")
                suggestions.append(f"Removing dependency '{parts[1]}' → '{parts[2]}' may help.")
            elif label.startswith("group_limit:"):
                suggestions.append(f"Relaxing group limit may help.")

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

"""Lightweight eval metrics for Frontier Phase 0.

Two layers:
  1. Automated checkpoints — deterministic signals from problem state
  2. Diagnostics — patterns that suggest structural issues

These are computed from Problem state, not LLM-generated.
The MCP server includes them in tool responses at natural checkpoints.
"""

from __future__ import annotations

from statistics import mean, variance

from .models import (
    BoundOperator,
    Direction,
    Problem,
)


def compute_metrics(problem: Problem) -> dict:
    """Compute all workflow health metrics from current problem state."""
    return {
        "framing": framing_metrics(problem),
        "data": data_metrics(problem),
        "solve": solve_metrics(problem),
        "outcome": outcome_metrics(problem),
        "diagnostics": diagnostics(problem),
    }


# --- Layer 1: Automated checkpoints ---


def framing_metrics(problem: Problem) -> dict:
    """Metrics about problem structure (objectives, options, constraints)."""
    return {
        "objective_count": len(problem.objectives),
        "option_count": len(problem.options),
        "has_constraints": len(problem.constraints) > 0,
        "constraint_count": len(problem.constraints),
        "directions_set": all(
            obj.direction is not None for obj in problem.objectives
        ),
    }


def data_metrics(problem: Problem) -> dict:
    """Metrics about score matrix completeness and quality."""
    obj_names = {o.name for o in problem.objectives}
    opt_names = {o.name for o in problem.options}
    max_scores = len(obj_names) * len(opt_names)

    if max_scores == 0:
        return {
            "score_completeness": 0.0,
            "missing_scores": [],
            "score_variance_by_objective": {},
            "dominated_options": [],
        }

    # Completeness
    filled = {(s.option, s.objective) for s in problem.scores}
    missing = []
    for opt in opt_names:
        for obj in obj_names:
            if (opt, obj) not in filled:
                missing.append({"option": opt, "objective": obj})

    completeness = len(filled) / max_scores

    # Per-objective variance (do scores actually differentiate options?)
    scores_by_obj: dict[str, list[float]] = {}
    for s in problem.scores:
        if s.objective in obj_names:
            scores_by_obj.setdefault(s.objective, []).append(s.value)

    variance_by_obj = {}
    for obj_name, values in scores_by_obj.items():
        if len(values) >= 2:
            variance_by_obj[obj_name] = round(variance(values), 4)

    # Dominated options (worse than another option on ALL objectives)
    dominated = _find_dominated_options(problem)

    return {
        "score_completeness": round(completeness, 4),
        "missing_scores": missing,
        "score_variance_by_objective": variance_by_obj,
        "dominated_options": dominated,
    }


def solve_metrics(problem: Problem) -> dict:
    """Metrics about optimization results."""
    if problem.run is None:
        return {
            "solve_success": False,
            "solution_count": 0,
            "feasibility": None,
            "hypervolume": None,
            "spacing_cv": None,
            "objective_variation": {},
            "option_coverage": {},
        }

    run = problem.run
    solutions = run.solutions

    # Objective variation across solutions
    obj_variation = {}
    for obj in problem.objectives:
        values = [s.objective_values.get(obj.name, 0) for s in solutions]
        if values:
            obj_variation[obj.name] = {
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "range": round(max(values) - min(values), 4),
            }

    # Option coverage: how many solutions include each option?
    opt_names = [o.name for o in problem.options]
    coverage = {name: 0 for name in opt_names}
    for sol in solutions:
        for opt in sol.selected_options:
            if opt in coverage:
                coverage[opt] += 1

    return {
        "solve_success": len(solutions) > 0,
        "solution_count": len(solutions),
        "feasibility": len(solutions) > 0,
        "hypervolume": run.quality.hypervolume_normalized,
        "spacing_cv": run.quality.spacing_cv,
        "objective_variation": obj_variation,
        "option_coverage": coverage,
    }


def outcome_metrics(problem: Problem) -> dict:
    """Metrics about user engagement and decision progress."""
    feedback_list = problem.feedback

    selected = None
    rating = None
    for fb in feedback_list:
        if fb.solution_id is not None:
            selected = fb.solution_id
        if fb.rating is not None:
            rating = fb.rating

    return {
        "user_selected_solution": selected,
        "user_rating": rating,
        "feedback_count": len(feedback_list),
    }


# --- Diagnostics ---


def diagnostics(problem: Problem) -> list[dict]:
    """Detect structural patterns that suggest issues or opportunities.

    Returns a list of diagnostic dicts with 'pattern', 'message', and 'severity'.
    """
    results = []

    if problem.run is None or not problem.run.solutions:
        if problem.run is not None:
            results.append({
                "pattern": "zero_solutions",
                "severity": "error",
                "message": (
                    "Optimization returned no solutions. "
                    "The problem is likely over-constrained."
                ),
            })
        return results

    solutions = problem.run.solutions

    # 1. Clustered solutions: all solutions within 5% of each other
    if len(solutions) >= 3:
        _check_clustering(problem, solutions, results)

    # 2. One objective dominates: <10% variation
    _check_objective_dominance(problem, solutions, results)

    # 3. Option never selected
    _check_option_coverage(problem, solutions, results)

    # 4. Binding constraints + low diversity
    _check_binding_constraints(problem, solutions, results)

    return results


def _check_clustering(problem, solutions, results):
    """Detect if solutions are highly clustered (within 5% on all objectives)."""
    for obj in problem.objectives:
        values = [s.objective_values.get(obj.name, 0) for s in solutions]
        if not values:
            continue
        obj_range = max(values) - min(values)
        obj_mean = mean(values) if values else 1
        # Avoid division by zero
        if obj_mean == 0:
            continue
        relative_range = obj_range / abs(obj_mean)
        if relative_range > 0.05:
            return  # At least one objective has spread — not clustered

    results.append({
        "pattern": "clustered_solutions",
        "severity": "warning",
        "message": (
            "Solutions are very similar across all objectives. "
            "Objectives may be correlated or the problem may be effectively "
            "single-objective."
        ),
    })


def _check_objective_dominance(problem, solutions, results):
    """Detect objectives with <10% variation across solutions."""
    for obj in problem.objectives:
        values = [s.objective_values.get(obj.name, 0) for s in solutions]
        if len(values) < 2:
            continue
        obj_range = max(values) - min(values)
        obj_mean = mean(values) if values else 1
        if obj_mean == 0:
            continue
        relative_range = obj_range / abs(obj_mean)
        if relative_range < 0.10:
            results.append({
                "pattern": "low_variation_objective",
                "severity": "info",
                "message": (
                    f"Objective '{obj.name}' shows <10% variation across "
                    f"solutions (range: {obj_range:.2f}). It may not "
                    f"genuinely conflict with other objectives."
                ),
            })


def _check_option_coverage(problem, solutions, results):
    """Detect options that never appear in any solution."""
    opt_names = {o.name for o in problem.options}
    # Exclude force-excluded options
    for c in problem.constraints:
        if hasattr(c, "type") and c.type == "force_exclude":
            opt_names.discard(c.option)

    selected_ever = set()
    for sol in solutions:
        selected_ever.update(sol.selected_options)

    never_selected = opt_names - selected_ever
    for opt in never_selected:
        results.append({
            "pattern": "option_never_selected",
            "severity": "info",
            "message": (
                f"Option '{opt}' does not appear in any Pareto solution. "
                f"It may be dominated — check if its scores are competitive."
            ),
        })


def _check_binding_constraints(problem, solutions, results):
    """Detect constraints that are binding on all solutions."""
    for constraint in problem.constraints:
        if constraint.type == "objective_bound":
            obj_name = constraint.objective
            bound_val = constraint.value
            op = constraint.operator

            values = [
                s.objective_values.get(obj_name, 0) for s in solutions
            ]
            if not values:
                continue

            # Check if constraint is binding (all solutions at the boundary)
            if op == BoundOperator.max:
                max_val = max(values)
                if max_val >= bound_val * 0.95:  # within 5% of bound
                    results.append({
                        "pattern": "binding_constraint",
                        "severity": "info",
                        "message": (
                            f"Constraint '{obj_name} ≤ {bound_val}' is "
                            f"binding (max across solutions: {max_val:.2f}). "
                            f"Relaxing it could expand the solution space."
                        ),
                    })
            elif op == BoundOperator.min:
                min_val = min(values)
                if min_val <= bound_val * 1.05:  # within 5% of bound
                    results.append({
                        "pattern": "binding_constraint",
                        "severity": "info",
                        "message": (
                            f"Constraint '{obj_name} ≥ {bound_val}' is "
                            f"binding (min across solutions: {min_val:.2f}). "
                            f"Relaxing it could expand the solution space."
                        ),
                    })


# --- Helpers ---


def _find_dominated_options(problem: Problem) -> list[str]:
    """Find options dominated on all objectives by at least one other option."""
    obj_names = [o.name for o in problem.objectives]
    opt_names = [o.name for o in problem.options]
    directions = {o.name: o.direction for o in problem.objectives}

    if not obj_names or not opt_names:
        return []

    # Build score lookup: option -> objective -> value
    score_map: dict[str, dict[str, float]] = {}
    for s in problem.scores:
        score_map.setdefault(s.option, {})[s.objective] = s.value

    # Only consider options with complete scores
    complete_opts = [
        opt for opt in opt_names
        if all(obj in score_map.get(opt, {}) for obj in obj_names)
    ]

    dominated = []
    for opt_a in complete_opts:
        for opt_b in complete_opts:
            if opt_a == opt_b:
                continue
            # Check if opt_b dominates opt_a
            b_dominates = True
            b_strictly_better = False
            for obj in obj_names:
                a_val = score_map[opt_a][obj]
                b_val = score_map[opt_b][obj]
                if directions[obj] == Direction.maximize:
                    if b_val < a_val:
                        b_dominates = False
                        break
                    if b_val > a_val:
                        b_strictly_better = True
                else:  # minimize
                    if b_val > a_val:
                        b_dominates = False
                        break
                    if b_val < a_val:
                        b_strictly_better = True
            if b_dominates and b_strictly_better:
                dominated.append(opt_a)
                break  # No need to check more — opt_a is dominated

    return dominated

"""Lightweight eval metrics for Frontier Phase 0.

Two layers:
  1. Automated checkpoints — deterministic signals from problem state
  2. Diagnostics — patterns that suggest structural issues

These are computed from Problem state, not LLM-generated.
The MCP server includes them in tool responses at natural checkpoints.
"""

from __future__ import annotations

from statistics import variance

from .models import (
    BoundOperator,
    CardinalityConstraint,
    Direction,
    ForceExcludeConstraint,
    GroupLimitConstraint,
    ObjectiveBoundConstraint,
    Problem,
    Solution,
)

_MAX_MISSING_SCORES_RETURNED = 20


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

    # Single pass over scores: build filled set, per-objective values, and score map
    filled: set[tuple[str, str]] = set()
    scores_by_obj: dict[str, list[float]] = {}
    score_map: dict[str, dict[str, float]] = {}
    for s in problem.scores:
        filled.add((s.option, s.objective))
        if s.objective in obj_names:
            scores_by_obj.setdefault(s.objective, []).append(s.value)
        score_map.setdefault(s.option, {})[s.objective] = s.value

    # Missing scores (capped to avoid bloating tool responses)
    missing = []
    for opt in opt_names:
        for obj in obj_names:
            if (opt, obj) not in filled:
                missing.append({"option": opt, "objective": obj})
                if len(missing) >= _MAX_MISSING_SCORES_RETURNED:
                    break
        if len(missing) >= _MAX_MISSING_SCORES_RETURNED:
            break

    completeness = len(filled) / max_scores

    # Per-objective variance
    variance_by_obj = {}
    for obj_name, values in scores_by_obj.items():
        if len(values) >= 2:
            variance_by_obj[obj_name] = round(variance(values), 4)

    # Dominated options (reuse score_map built above)
    dominated = _find_dominated_options(problem, score_map)

    missing_total = max_scores - len(filled)
    result = {
        "score_completeness": round(completeness, 4),
        "missing_scores": missing,
        "score_variance_by_objective": variance_by_obj,
        "dominated_options": dominated,
    }
    if missing_total > _MAX_MISSING_SCORES_RETURNED:
        result["missing_scores_total"] = missing_total

    return result


def solve_metrics(problem: Problem) -> dict:
    """Metrics about optimization results."""
    if problem.run is None:
        return {
            "solve_success": False,
            "solution_count": 0,
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
        values = _obj_values(solutions, obj.name)
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
        "hypervolume": run.quality.hypervolume_normalized,
        "spacing_cv": run.quality.spacing_cv,
        "objective_variation": obj_variation,
        "option_coverage": coverage,
    }


def outcome_metrics(problem: Problem) -> dict:
    """Metrics about user engagement and decision progress.

    Uses the latest feedback entry that has both solution_id and rating,
    falling back to the latest of each independently.
    """
    feedback_list = problem.feedback

    # Prefer the latest feedback that has both fields paired
    selected = None
    rating = None
    for fb in reversed(feedback_list):
        if fb.solution_id is not None and fb.rating is not None:
            selected = fb.solution_id
            rating = fb.rating
            break

    # Fall back to latest of each if no paired entry exists
    if selected is None:
        for fb in reversed(feedback_list):
            if fb.solution_id is not None:
                selected = fb.solution_id
                break
    if rating is None:
        for fb in reversed(feedback_list):
            if fb.rating is not None:
                rating = fb.rating
                break

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
    results: list[dict] = []

    if problem.run is None or not problem.run.solutions:
        if problem.run is not None:
            results.append({
                "pattern": "zero_solutions",
                "severity": "error",
            })
        return results

    solutions = problem.run.solutions

    # Pre-compute per-objective stats (single pass, shared by clustering + dominance checks)
    obj_stats = _compute_obj_stats(problem, solutions)

    # 1. Clustered solutions: all solutions within 5% of each other
    if len(solutions) >= 3:
        _check_clustering(obj_stats, results)

    # 2. One objective dominates: <10% variation
    _check_low_variation(obj_stats, results)

    # 3. Option never selected
    _check_option_coverage(problem, solutions, results)

    # 4. Binding constraints + low diversity
    _check_binding_constraints(problem, solutions, results)

    return results


# --- Diagnostic helpers ---


def _compute_obj_stats(
    problem: Problem, solutions: list[Solution],
) -> dict[str, dict]:
    """Compute per-objective stats once for use by multiple diagnostic checks."""
    stats = {}
    for obj in problem.objectives:
        values = _obj_values(solutions, obj.name)
        if len(values) < 2:
            continue
        val_min = min(values)
        val_max = max(values)
        val_range = val_max - val_min
        val_mean = sum(values) / len(values)
        rel_range = (val_range / abs(val_mean)) if val_mean != 0 else 0.0
        stats[obj.name] = {
            "min": val_min,
            "max": val_max,
            "range": val_range,
            "mean": val_mean,
            "relative_range": rel_range,
        }
    return stats


def _check_clustering(obj_stats: dict, results: list[dict]):
    """Detect if solutions are highly clustered (within 5% on all objectives)."""
    if not obj_stats:
        return
    for stat in obj_stats.values():
        if stat["relative_range"] > 0.05:
            return  # At least one objective has spread — not clustered

    results.append({
        "pattern": "clustered_solutions",
        "severity": "warning",
    })


def _check_low_variation(obj_stats: dict, results: list[dict]):
    """Detect objectives with <10% variation across solutions."""
    for obj_name, stat in obj_stats.items():
        if stat["relative_range"] < 0.10:
            results.append({
                "pattern": "low_variation_objective",
                "severity": "info",
                "objective": obj_name,
                "relative_range": round(stat["relative_range"], 4),
            })


def _check_option_coverage(problem, solutions, results):
    """Detect options that never appear in any solution."""
    opt_names = {o.name for o in problem.options}
    for c in problem.constraints:
        if isinstance(c, ForceExcludeConstraint):
            opt_names.discard(c.option)

    selected_ever = set()
    for sol in solutions:
        selected_ever.update(sol.selected_options)

    never_selected = opt_names - selected_ever
    for opt in never_selected:
        results.append({
            "pattern": "option_never_selected",
            "severity": "info",
            "option": opt,
        })


def _check_binding_constraints(problem, solutions, results):
    """Detect constraints that are binding on any solution."""
    for constraint in problem.constraints:
        if isinstance(constraint, ObjectiveBoundConstraint):
            _check_binding_objective_bound(constraint, solutions, results)
        elif isinstance(constraint, CardinalityConstraint):
            _check_binding_cardinality(constraint, solutions, results)
        elif isinstance(constraint, GroupLimitConstraint):
            _check_binding_group_limit(constraint, solutions, results)


def _check_binding_objective_bound(constraint, solutions, results):
    obj_name = constraint.objective
    bound_val = constraint.value
    values = _obj_values(solutions, obj_name)
    if not values:
        return

    if constraint.operator == BoundOperator.max:
        extreme = max(values)
        if extreme >= bound_val * 0.95:
            results.append({
                "pattern": "binding_constraint",
                "severity": "info",
                "constraint": f"{obj_name} ≤ {bound_val}",
                "extreme_value": round(extreme, 2),
            })
    elif constraint.operator == BoundOperator.min:
        extreme = min(values)
        if extreme <= bound_val * 1.05:
            results.append({
                "pattern": "binding_constraint",
                "severity": "info",
                "constraint": f"{obj_name} ≥ {bound_val}",
                "extreme_value": round(extreme, 2),
            })


def _check_binding_cardinality(constraint, solutions, results):
    for sol in solutions:
        count = len(sol.selected_options)
        if count == constraint.max:
            results.append({
                "pattern": "binding_constraint",
                "severity": "info",
                "constraint": f"cardinality ≤ {constraint.max}",
                "actual_value": count,
            })
            return
        if count == constraint.min and constraint.min > 1:
            results.append({
                "pattern": "binding_constraint",
                "severity": "info",
                "constraint": f"cardinality ≥ {constraint.min}",
                "actual_value": count,
            })
            return


def _check_binding_group_limit(constraint, solutions, results):
    group_set = set(constraint.options)
    for sol in solutions:
        count = len(group_set.intersection(sol.selected_options))
        if count == constraint.max:
            results.append({
                "pattern": "binding_constraint",
                "severity": "info",
                "constraint": f"group_limit({', '.join(constraint.options)}) ≤ {constraint.max}",
                "actual_value": count,
            })
            return


# --- Shared helpers ---


def _obj_values(solutions: list[Solution], obj_name: str) -> list[float]:
    """Extract values for a single objective across all solutions."""
    return [s.objective_values.get(obj_name, 0) for s in solutions]


def _find_dominated_options(
    problem: Problem,
    score_map: dict[str, dict[str, float]] | None = None,
) -> list[str]:
    """Find options dominated on all objectives by at least one other option."""
    obj_names = [o.name for o in problem.objectives]
    opt_names = [o.name for o in problem.options]
    directions = {o.name: o.direction for o in problem.objectives}

    if not obj_names or not opt_names:
        return []

    if score_map is None:
        score_map = {}
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
                else:
                    if b_val > a_val:
                        b_dominates = False
                        break
                    if b_val < a_val:
                        b_strictly_better = True
            if b_dominates and b_strictly_better:
                dominated.append(opt_a)
                break

    return dominated

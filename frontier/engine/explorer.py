"""Explorer: navigate the Pareto frontier after solving."""

from __future__ import annotations

import numpy as np

from .models import Problem, Run


def get_tradeoffs(problem: Problem) -> dict:
    """Frontier overview: ranges, correlations, extremes, balanced solution."""
    run = _require_run(problem)
    solutions = run.solutions
    obj_names = [o.name for o in problem.objectives]

    # Objective ranges
    obj_ranges = {}
    for name in obj_names:
        vals = [s.objective_values[name] for s in solutions]
        obj_ranges[name] = {"min": min(vals), "max": max(vals)}

    # Key tradeoffs: pairwise correlation between objectives
    if len(solutions) >= 3 and len(obj_names) >= 2:
        matrix = np.array([
            [s.objective_values[name] for name in obj_names]
            for s in solutions
        ])
        corr = np.corrcoef(matrix.T)
        key_tradeoffs = []
        for i in range(len(obj_names)):
            for j in range(i + 1, len(obj_names)):
                key_tradeoffs.append({
                    "objectives": [obj_names[i], obj_names[j]],
                    "correlation": round(float(corr[i, j]), 2),
                })
    else:
        key_tradeoffs = []

    # Extreme solutions: best per objective
    extreme_solutions = {}
    for obj in problem.objectives:
        name = obj.name
        reverse = obj.direction.value == "maximize"
        best = max(solutions, key=lambda s: s.objective_values[name]) if reverse else min(solutions, key=lambda s: s.objective_values[name])
        extreme_solutions[f"best_{name}"] = {
            "solution_id": best.solution_id,
            "value": best.objective_values[name],
            "selected_options": best.selected_options,
        }

    # Balanced solution: min normalized distance to ideal point
    balanced = _find_balanced(solutions, problem.objectives)

    return {
        "total_solutions": len(solutions),
        "objective_ranges": obj_ranges,
        "key_tradeoffs": key_tradeoffs,
        "extreme_solutions": extreme_solutions,
        "balanced_solution": {
            "solution_id": balanced.solution_id,
            "objective_values": balanced.objective_values,
            "selected_options": balanced.selected_options,
        },
    }


def compare_solutions(problem: Problem, solution_ids: list[int]) -> dict:
    """Side-by-side comparison of specific solutions."""
    run = _require_run(problem)
    sol_map = {s.solution_id: s for s in run.solutions}

    selected = []
    for sid in solution_ids:
        if sid not in sol_map:
            raise ValueError(f"Solution {sid} not found in current run.")
        selected.append(sol_map[sid])

    # Shared and differentiating options
    option_sets = [set(s.selected_options) for s in selected]
    shared = set.intersection(*option_sets) if option_sets else set()
    all_options = set.union(*option_sets) if option_sets else set()
    differentiating = all_options - shared

    # Tradeoff summary per objective
    tradeoff_summary = {}
    for obj in problem.objectives:
        name = obj.name
        vals = {s.solution_id: s.objective_values[name] for s in selected}
        best_id = max(vals, key=vals.get) if obj.direction.value == "maximize" else min(vals, key=vals.get)
        worst_id = min(vals, key=vals.get) if obj.direction.value == "maximize" else max(vals, key=vals.get)
        all_vals = list(vals.values())
        tradeoff_summary[name] = {
            "best": best_id,
            "worst": worst_id,
            "range": [min(all_vals), max(all_vals)],
        }

    return {
        "solutions": [s.model_dump() for s in selected],
        "shared_options": sorted(shared),
        "differentiating_options": sorted(differentiating),
        "tradeoff_summary": tradeoff_summary,
    }


def _require_run(problem: Problem) -> Run:
    if problem.run is None:
        raise ValueError("No run found. Use solve first.")
    if not problem.run.solutions:
        raise ValueError("Run has no solutions.")
    return problem.run


def _find_balanced(solutions, objectives) -> object:
    """Find the solution with minimum normalized Euclidean distance to ideal."""
    obj_names = [o.name for o in objectives]
    directions = [o.direction.value for o in objectives]

    # Build matrix
    matrix = np.array([
        [s.objective_values[name] for name in obj_names]
        for s in solutions
    ])

    # Ideal point: best value per objective
    ideal = np.zeros(len(obj_names))
    for j, d in enumerate(directions):
        ideal[j] = matrix[:, j].max() if d == "maximize" else matrix[:, j].min()

    # Normalize
    col_min = matrix.min(axis=0)
    col_max = matrix.max(axis=0)
    spread = col_max - col_min
    spread[spread == 0] = 1.0  # avoid division by zero

    norm_matrix = (matrix - col_min) / spread
    norm_ideal = (ideal - col_min) / spread

    # For maximize objectives, distance = (ideal - actual); for minimize, (actual - ideal)
    # After normalization, ideal for maximize = 1.0, for minimize = 0.0
    distances = np.zeros(len(solutions))
    for j, d in enumerate(directions):
        if d == "maximize":
            distances += (norm_ideal[j] - norm_matrix[:, j]) ** 2
        else:
            distances += (norm_matrix[:, j] - norm_ideal[j]) ** 2

    distances = np.sqrt(distances)
    best_idx = int(np.argmin(distances))
    return solutions[best_idx]

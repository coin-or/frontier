"""Explorer: navigate the Pareto frontier after solving."""

from __future__ import annotations

import numpy as np

from .models import CuratedSolution, Problem, Run, _content_signature


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

    result = {
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

    if problem.reference_points:
        result["balanced_vs_references"] = _compute_reference_analysis(
            balanced.objective_values, problem.reference_points, problem.objectives,
        )

    return result


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

    result = {
        "solutions": [s.model_dump() for s in selected],
        "shared_options": sorted(shared),
        "differentiating_options": sorted(differentiating),
        "tradeoff_summary": tradeoff_summary,
    }

    # Allocation comparison for proportional mode
    if any(s.allocations for s in selected):
        alloc_comparison = {}
        for opt in sorted(all_options):
            alloc_comparison[opt] = {
                f"solution_{s.solution_id}": (s.allocations or {}).get(opt, 0)
                for s in selected
            }
        result["allocation_comparison"] = alloc_comparison

    return result


def get_solutions(problem: Problem) -> dict:
    """Full Pareto frontier, sorted by first objective."""
    run = _require_run(problem)
    return {
        "run_id": run.run_id,
        "total_solutions": len(run.solutions),
        "solutions": [s.model_dump() for s in run.solutions],
    }


def get_solution(problem: Problem, solution_id: int) -> dict:
    """Single solution detail by ID."""
    run = _require_run(problem)
    for s in run.solutions:
        if s.solution_id == solution_id:
            result = s.model_dump()
            if problem.reference_points:
                result["vs_references"] = _compute_reference_analysis(
                    s.objective_values, problem.reference_points, problem.objectives,
                )
            return result
    raise ValueError(f"Solution {solution_id} not found in current run.")


def _compute_reference_analysis(solution_obj_values: dict, reference_points: list, objectives: list) -> list[dict]:
    """Compute distance from a solution to each reference point, per objective."""
    if not reference_points:
        return []

    obj_dirs = {o.name: o.direction.value for o in objectives}
    results = []
    for rp in reference_points:
        per_obj = {}
        for obj_name, ref_val in rp.objective_values.items():
            if obj_name not in solution_obj_values:
                continue
            sol_val = solution_obj_values[obj_name]
            diff = sol_val - ref_val
            direction = obj_dirs.get(obj_name, "maximize")
            # Positive = better than reference for maximize, worse for minimize
            if direction == "minimize":
                diff = -diff
            pct = round(diff / abs(ref_val) * 100, 1) if ref_val != 0 else 0.0
            per_obj[obj_name] = {
                "solution_value": sol_val,
                "reference_value": ref_val,
                "difference": round(diff, 4),
                "percent_vs_reference": pct,
                "better": diff > 0,
            }
        results.append({
            "reference": rp.name or rp.type,
            "type": rp.type,
            "objectives": per_obj,
        })
    return results


def compare_runs(problem: Problem, run_ids: list[str]) -> dict:
    """Compare two or more runs: constraint diffs, frontier diffs, option coverage."""
    all_runs = {r.run_id: r for r in problem.runs}
    if problem.run:
        all_runs[problem.run.run_id] = problem.run

    selected_runs = []
    for rid in run_ids:
        if rid not in all_runs:
            raise ValueError(f"Run {rid} not found. Available: {list(all_runs.keys())}")
        selected_runs.append(all_runs[rid])

    obj_names = [o.name for o in problem.objectives]

    # Criteria diff: compare constraint snapshots between runs
    criteria_diffs = []
    for i in range(1, len(selected_runs)):
        prev_snap = selected_runs[i - 1].constraints_snapshot
        curr_snap = selected_runs[i].constraints_snapshot
        prev_set = {_constraint_key(c) for c in prev_snap}
        curr_set = {_constraint_key(c) for c in curr_snap}
        added = [c for c in curr_snap if _constraint_key(c) not in prev_set]
        removed = [c for c in prev_snap if _constraint_key(c) not in curr_set]
        criteria_diffs.append({
            "from_run": selected_runs[i - 1].run_id,
            "to_run": selected_runs[i].run_id,
            "added": added,
            "removed": removed,
        })

    # Frontier diff: solution count and objective range changes
    frontier_diffs = []
    for run in selected_runs:
        ranges = {}
        for name in obj_names:
            vals = [s.objective_values.get(name, 0) for s in run.solutions]
            if vals:
                ranges[name] = {"min": min(vals), "max": max(vals)}
            else:
                ranges[name] = {"min": None, "max": None}
        frontier_diffs.append({
            "run_id": run.run_id,
            "solution_count": len(run.solutions),
            "objective_ranges": ranges,
            "created_at": run.created_at.isoformat(),
        })

    # Option coverage diff: how many solutions include each option per run
    option_coverage = {}
    opt_names = [o.name for o in problem.options]
    for run in selected_runs:
        coverage = {}
        for opt in opt_names:
            coverage[opt] = sum(1 for s in run.solutions if opt in s.selected_options)
        option_coverage[run.run_id] = coverage

    return {
        "runs_compared": [r.run_id for r in selected_runs],
        "criteria_diffs": criteria_diffs,
        "frontier_diffs": frontier_diffs,
        "option_coverage": option_coverage,
    }


def _constraint_key(c: dict) -> str:
    """Stable string key for a constraint dict, for comparison."""
    ctype = c.get("type", "")
    if ctype == "cardinality":
        return f"cardinality:{c.get('min')}:{c.get('max')}"
    elif ctype in ("force_include", "force_exclude"):
        return f"{ctype}:{c.get('option')}"
    elif ctype == "objective_bound":
        return f"objective_bound:{c.get('objective')}:{c.get('operator')}:{c.get('value')}"
    elif ctype == "exclusion_pair":
        return f"exclusion_pair:{c.get('option_a')}:{c.get('option_b')}"
    elif ctype == "dependency":
        return f"dependency:{c.get('if_option')}:{c.get('then_option')}"
    elif ctype == "group_limit":
        return f"group_limit:{','.join(c.get('options', []))}:{c.get('max')}"
    return str(c)


def curate_solution(problem: Problem, solution_id: int, custom_name: str = "", notes: str = "") -> dict:
    """Add a solution from the current frontier to the curated set."""
    run = _require_run(problem)
    sol = None
    for s in run.solutions:
        if s.solution_id == solution_id:
            sol = s
            break
    if sol is None:
        raise ValueError(f"Solution {solution_id} not found in current run.")

    sig = sol.content_signature or _content_signature(sol.selected_options, sol.allocations)

    # Duplicate check
    for cs in problem.curated_solutions:
        if cs.content_signature == sig:
            return {"error": f"Solution already curated as '{cs.custom_name or sig}'."}

    # Pull in any existing feedback matching this signature
    existing_feedback = [
        fb for fb in problem.feedback if fb.content_signature == sig
    ]

    curated = CuratedSolution(
        content_signature=sig,
        custom_name=custom_name,
        selected_options=sol.selected_options,
        allocations=sol.allocations,
        objective_values=sol.objective_values,
        source_run_id=run.run_id,
        notes=notes,
        feedback=existing_feedback,
    )
    problem.curated_solutions.append(curated)
    return {
        "curated": True,
        "content_signature": sig,
        "custom_name": custom_name,
        "total_curated": len(problem.curated_solutions),
    }


def uncurate_solution(problem: Problem, content_signature: str) -> dict:
    """Remove a solution from the curated set."""
    before = len(problem.curated_solutions)
    problem.curated_solutions = [
        cs for cs in problem.curated_solutions if cs.content_signature != content_signature
    ]
    if len(problem.curated_solutions) == before:
        raise ValueError(f"No curated solution with signature '{content_signature}'.")
    return {"removed": content_signature, "total_curated": len(problem.curated_solutions)}


def rename_curated(problem: Problem, content_signature: str, custom_name: str) -> dict:
    """Update the name of a curated solution."""
    for cs in problem.curated_solutions:
        if cs.content_signature == content_signature:
            cs.custom_name = custom_name
            return {"renamed": content_signature, "custom_name": custom_name}
    raise ValueError(f"No curated solution with signature '{content_signature}'.")


def list_curated(problem: Problem) -> dict:
    """List all curated solutions with survival status against current run."""
    current_sigs = set()
    if problem.run:
        for s in problem.run.solutions:
            sig = s.content_signature or _content_signature(s.selected_options, s.allocations)
            current_sigs.add(sig)

    curated = []
    for cs in problem.curated_solutions:
        entry = cs.model_dump()
        entry["in_current_frontier"] = cs.content_signature in current_sigs
        entry["feedback_count"] = len(cs.feedback)
        if cs.feedback:
            ratings = [fb.rating for fb in cs.feedback if fb.rating is not None]
            entry["avg_rating"] = round(sum(ratings) / len(ratings), 1) if ratings else None
        else:
            entry["avg_rating"] = None
        curated.append(entry)

    return {
        "total_curated": len(curated),
        "curated_solutions": curated,
    }


def compare_curated(problem: Problem, signatures: list[str]) -> dict:
    """Side-by-side comparison of curated solutions."""
    sig_map = {cs.content_signature: cs for cs in problem.curated_solutions}

    selected = []
    for sig in signatures:
        if sig not in sig_map:
            raise ValueError(f"No curated solution with signature '{sig}'.")
        selected.append(sig_map[sig])

    # Shared and differentiating options
    option_sets = [set(cs.selected_options) for cs in selected]
    shared = set.intersection(*option_sets) if option_sets else set()
    all_options = set.union(*option_sets) if option_sets else set()
    differentiating = all_options - shared

    # Tradeoff summary per objective
    tradeoff_summary = {}
    for obj in problem.objectives:
        name = obj.name
        vals = {cs.content_signature: cs.objective_values.get(name, 0) for cs in selected}
        if not vals:
            continue
        best_sig = max(vals, key=vals.get) if obj.direction.value == "maximize" else min(vals, key=vals.get)
        worst_sig = min(vals, key=vals.get) if obj.direction.value == "maximize" else max(vals, key=vals.get)
        all_vals = list(vals.values())
        tradeoff_summary[name] = {
            "best": best_sig,
            "worst": worst_sig,
            "range": [min(all_vals), max(all_vals)],
        }

    result = {
        "solutions": [
            {
                "content_signature": cs.content_signature,
                "custom_name": cs.custom_name,
                "selected_options": cs.selected_options,
                "objective_values": cs.objective_values,
                "allocations": cs.allocations,
            }
            for cs in selected
        ],
        "shared_options": sorted(shared),
        "differentiating_options": sorted(differentiating),
        "tradeoff_summary": tradeoff_summary,
    }

    if problem.reference_points:
        for sol_dict in result["solutions"]:
            sol_dict["vs_references"] = _compute_reference_analysis(
                sol_dict["objective_values"], problem.reference_points, problem.objectives,
            )

    return result


def get_scenario_results(problem: Problem) -> dict:
    """Analyze per-scenario results: robust options, scenario-specific options, expected value."""
    if not problem.scenario_run or not problem.scenario_run.scenario_runs:
        raise ValueError("No scenario runs found. Use solve run_scenarios first.")
    if not problem.scenario_config or not problem.scenario_config.scenarios:
        raise ValueError("No scenario config found.")

    scenario_runs = problem.scenario_run.scenario_runs
    scenarios = {s.name: s for s in problem.scenario_config.scenarios}
    opt_names = [o.name for o in problem.options]
    obj_names = [o.name for o in problem.objectives]

    # Per-scenario summaries
    per_scenario = {}
    for name, run in scenario_runs.items():
        ranges = {}
        for obj in obj_names:
            vals = [s.objective_values.get(obj, 0) for s in run.solutions]
            if vals:
                ranges[obj] = {"min": min(vals), "max": max(vals)}
        per_scenario[name] = {
            "solution_count": len(run.solutions),
            "objective_ranges": ranges,
        }

    # Robust options: appear in at least one Pareto solution in ALL scenarios
    option_in_scenario = {}
    for name, run in scenario_runs.items():
        opts_in_any = set()
        for sol in run.solutions:
            opts_in_any.update(sol.selected_options)
        option_in_scenario[name] = opts_in_any

    all_scenario_names = list(scenario_runs.keys())
    robust_options = []
    scenario_specific = {}
    for opt in opt_names:
        present_in = [name for name in all_scenario_names if opt in option_in_scenario.get(name, set())]
        if len(present_in) == len(all_scenario_names):
            robust_options.append(opt)
        elif len(present_in) > 0:
            scenario_specific[opt] = present_in

    # Expected value: probability-weighted if probabilities provided, else equal-weight
    has_probabilities = all(
        scenarios[name].probability is not None for name in scenario_runs
    )
    n_scenarios = len(scenario_runs)

    expected_values = {}
    for obj in obj_names:
        ev = 0.0
        for name, run in scenario_runs.items():
            if has_probabilities:
                weight = scenarios[name].probability
            else:
                weight = 1.0 / n_scenarios  # equal weight
            vals = [s.objective_values.get(obj, 0) for s in run.solutions]
            if vals:
                direction = next(o.direction.value for o in problem.objectives if o.name == obj)
                best = max(vals) if direction == "maximize" else min(vals)
                ev += weight * best
        expected_values[obj] = round(ev, 4)

    return {
        "per_scenario": per_scenario,
        "robust_options": sorted(robust_options),
        "scenario_specific_options": scenario_specific,
        "expected_values": expected_values,
        "weighting": "probability" if has_probabilities else "equal",
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

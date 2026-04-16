"""Explorer: navigate the Pareto frontier after solving."""

from __future__ import annotations

import numpy as np

from .models import CuratedSolution, Problem, Run, _content_signature


def get_tradeoffs(problem: Problem, scenario: str | None = None) -> dict:
    """Frontier overview: ranges, correlations, extremes, balanced solution."""
    run = _require_run(problem, scenario)
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

    # Extreme solutions: top performer per objective
    extreme_solutions = {}
    for obj in problem.objectives:
        name = obj.name
        reverse = obj.direction.value == "maximize"
        best = max(solutions, key=lambda s: s.objective_values[name]) if reverse else min(solutions, key=lambda s: s.objective_values[name])
        extreme_solutions[f"extreme_{name}"] = {
            "solution_id": best.solution_id,
            "value": best.objective_values[name],
            "selected_options": best.selected_options,
        }

    # Balanced solution: min normalized distance to ideal point
    balanced = _find_balanced(solutions, problem.objectives)

    # Inflection-point candidates: solutions where marginal tradeoff cost jumps
    inflection_candidates = []
    for inf in _find_inflection_solutions(solutions, problem.objectives):
        s = inf["solution"]
        if s.solution_id != balanced.solution_id:  # Don't duplicate balanced
            inflection_candidates.append({
                "solution_id": s.solution_id,
                "objective_values": s.objective_values,
                "selected_options": s.selected_options,
                "inflection_pair": inf["pair"],
                "jump_factor": inf["jump_factor"],
            })

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
        "inflection_point_candidates": inflection_candidates,
    }

    if problem.reference_points:
        result["balanced_vs_references"] = _compute_reference_analysis(
            balanced.objective_values, problem.reference_points, problem.objectives,
        )

    # Frontier shape classification per conflicting objective pair
    result["frontier_shape"] = _classify_frontier_shapes(solutions, problem.objectives)

    result["visualization"] = _render_tradeoffs_viz(result, problem.objectives, solutions)
    return result


def compare_solutions(problem: Problem, solution_ids: list[int], scenario: str | None = None) -> dict:
    """Side-by-side comparison of specific solutions."""
    run = _require_run(problem, scenario)
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
            "leads": best_id,
            "trails": worst_id,
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

    # Parallel coordinates visualization
    sol_dicts = [{"solution_id": s.solution_id, "objective_values": s.objective_values}
                 for s in selected]
    labels = {s.solution_id: f"[{s.solution_id}]" for s in selected}
    result["visualization"] = _render_parallel_coords(sol_dicts, problem.objectives, labels)

    return result


def get_solutions(problem: Problem, scenario: str | None = None, detail: bool = False) -> dict:
    """Pareto frontier, sorted by first objective.

    Default (detail=False): compact — `{solution_id, objective_values, content_signature}` per solution.
    detail=True: full dump including `selected_options` and `allocations`.

    For full single-solution detail prefer `get_solution(problem, solution_id)`.
    """
    run = _require_run(problem, scenario)
    if detail:
        sols = [s.model_dump() for s in run.solutions]
    else:
        sols = [
            {
                "solution_id": s.solution_id,
                "objective_values": s.objective_values,
                "content_signature": s.content_signature,
            }
            for s in run.solutions
        ]
    return {
        "run_id": run.run_id,
        "total_solutions": len(run.solutions),
        "detail": detail,
        "solutions": sols,
    }


def get_solution(problem: Problem, solution_id: int, scenario: str | None = None) -> dict:
    """Single solution detail by ID."""
    run = _require_run(problem, scenario)
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
            "mode": run.mode.value,
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


def curate_solution(problem: Problem, solution_id: int, custom_name: str = "", notes: str = "", scenario: str | None = None) -> dict:
    """Add a solution from the current frontier to the curated set."""
    run = _require_run(problem, scenario)
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


def compare_curated(problem: Problem, signatures: list[str], detail: bool = False) -> dict:
    """Side-by-side comparison of curated solutions.

    Default (detail=False): compact — omits per-solution `selected_options` and
    `allocations`. The `shared_options` and `differentiating_options` summary
    fields already convey the structural differences.

    detail=True: include full `selected_options` and `allocations` per solution.
    Use for artifact assembly or deep dives; for large proportional problems,
    pair with the `full_result_path` file written by solve instead.
    """
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
            "leads": best_sig,
            "trails": worst_sig,
            "range": [min(all_vals), max(all_vals)],
        }

    def _sol_entry(cs):
        entry = {
            "content_signature": cs.content_signature,
            "custom_name": cs.custom_name,
            "objective_values": cs.objective_values,
        }
        if detail:
            entry["selected_options"] = cs.selected_options
            entry["allocations"] = cs.allocations
        return entry

    result = {
        "solutions": [_sol_entry(cs) for cs in selected],
        "shared_options": sorted(shared),
        "differentiating_options": sorted(differentiating),
        "tradeoff_summary": tradeoff_summary,
        "detail": detail,
    }

    if problem.reference_points:
        for sol_dict in result["solutions"]:
            sol_dict["vs_references"] = _compute_reference_analysis(
                sol_dict["objective_values"], problem.reference_points, problem.objectives,
            )

    # Parallel coordinates visualization
    sol_dicts = [{"content_signature": cs.content_signature, "objective_values": cs.objective_values}
                 for cs in selected]
    labels = {cs.content_signature: (cs.custom_name or cs.content_signature[:8]) for cs in selected}
    result["visualization"] = _render_parallel_coords(sol_dicts, problem.objectives, labels)

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

    # Robust options: frequency + allocation-weighted across scenarios
    from collections import Counter

    all_scenario_names = list(scenario_runs.keys())
    # Per-scenario: count how often each option appears + total allocation weight
    per_scenario_freq = {}  # {scenario: {opt: frequency 0-1}}
    per_scenario_avg_weight = {}  # {scenario: {opt: avg_weight when present}}
    for name, run in scenario_runs.items():
        n_sols = len(run.solutions)
        opt_count: Counter = Counter()
        opt_weight_sum: Counter = Counter()
        for sol in run.solutions:
            for opt in sol.selected_options:
                opt_count[opt] += 1
                if sol.allocations:
                    opt_weight_sum[opt] += sol.allocations.get(opt, 0)
        per_scenario_freq[name] = {
            opt: opt_count[opt] / n_sols if n_sols else 0 for opt in opt_count
        }
        per_scenario_avg_weight[name] = {
            opt: opt_weight_sum[opt] / opt_count[opt] if opt_count[opt] else 0
            for opt in opt_count
        }

    # Aggregate across scenarios: avg frequency, avg weight, importance score
    option_robustness = []
    scenario_specific = {}
    for opt in opt_names:
        freqs = [per_scenario_freq[s].get(opt, 0) for s in all_scenario_names]
        weights = [per_scenario_avg_weight[s].get(opt, 0) for s in all_scenario_names]
        present_in = [s for s in all_scenario_names if per_scenario_freq[s].get(opt, 0) > 0]
        avg_freq = sum(freqs) / len(freqs) if freqs else 0
        avg_weight = sum(w for w in weights if w > 0) / max(len([w for w in weights if w > 0]), 1)
        importance = round(avg_freq * avg_weight, 2)

        if avg_freq > 0:
            # Tier: core (>50% freq in all scenarios), common (>25% or in all),
            # marginal (<25% or missing from some)
            min_freq = min(freqs)
            if min_freq > 0.5:
                tier = "core"
            elif min_freq > 0.25 or len(present_in) == len(all_scenario_names):
                tier = "common"
            else:
                tier = "marginal"

            option_robustness.append({
                "option": opt,
                "avg_frequency": round(avg_freq, 3),
                "avg_weight": round(avg_weight, 1),
                "importance": importance,
                "tier": tier,
                "scenarios_present": len(present_in),
            })

        if 0 < len(present_in) < len(all_scenario_names):
            scenario_specific[opt] = present_in

    # Sort by importance descending
    option_robustness.sort(key=lambda x: x["importance"], reverse=True)
    robust_options = [r["option"] for r in option_robustness if r["tier"] == "core"]

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

    result = {
        "per_scenario": per_scenario,
        "robust_options": sorted(robust_options),
        "option_robustness": option_robustness,
        "scenario_specific_options": scenario_specific,
        "expected_values": expected_values,
        "weighting": "probability" if has_probabilities else "equal",
    }
    result["visualization"] = _render_scenario_viz(result)
    return result


def marginal_analysis(problem: Problem, scenario: str | None = None, detail: bool = False) -> dict:
    """Marginal rate analysis: cost-per-unit improvement between adjacent Pareto solutions.

    For each negatively-correlated objective pair, sorts solutions by one objective
    and computes the marginal rate of exchange. Detects inflection points where the rate
    jumps sharply — the point of diminishing returns.

    Default (detail=False): summary per pair — inflection, stats, top-5 steepest rates.
    detail=True: includes full rates array and untruncated visualization.
    """
    run = _require_run(problem, scenario)
    solutions = run.solutions
    objectives = problem.objectives
    obj_names = [o.name for o in objectives]

    if len(solutions) < 3:
        return {"pairs": [], "note": "Need at least 3 solutions for marginal analysis."}

    pairs = []
    for i, j, r in _conflicting_pair_indices(solutions, objectives):
        obj_a = objectives[i]
        obj_b = objectives[j]

        # Sort solutions by objective A (in "better" direction)
        reverse_a = obj_a.direction.value == "maximize"
        sorted_sols = sorted(
            solutions,
            key=lambda s: s.objective_values[obj_a.name],
            reverse=reverse_a,
        )

        # Compute marginal rates between adjacent solutions
        raw_rates = _compute_pair_rates(sorted_sols, obj_a, obj_b)
        rates = [
            {
                "from_id": rr["from_sol"].solution_id,
                "to_id": rr["to_sol"].solution_id,
                f"delta_{obj_a.name}": round(rr["delta_a"], 4),
                f"delta_{obj_b.name}": round(rr["delta_b"], 4),
                "rate": round(rr["rate"], 4),
            }
            for rr in raw_rates
        ]

        # Detect inflection: largest jump in marginal rate
        detected = _detect_inflection([rr["rate"] for rr in raw_rates])
        if detected is None:
            inflection = None
        else:
            inflection = {
                "solution_id": raw_rates[detected["position"]]["from_sol"].solution_id,
                "position": detected["position"],
                "jump_factor": detected["jump_factor"],
            }

        pair_result = {
            "objectives": [obj_a.name, obj_b.name],
            "correlation": round(r, 2),
            "inflection": inflection,
        }

        if detail:
            # Full output: all rates + untruncated viz
            pair_result["rates"] = rates
            pair_result["visualization"] = _render_marginal_rates(
                rates, obj_a, obj_b, inflection,
            )
        else:
            # Summary: stats + top-5 steepest + truncated viz
            rate_values = [r["rate"] for r in rates]
            pair_result["summary"] = {
                "total_transitions": len(rates),
                "rate_min": round(min(rate_values), 4) if rate_values else 0,
                "rate_max": round(max(rate_values), 4) if rate_values else 0,
                "rate_median": round(float(np.median(rate_values)), 4) if rate_values else 0,
            }
            # Top-5 steepest transitions (most expensive tradeoff steps)
            top_rates = sorted(rates, key=lambda r: r["rate"], reverse=True)[:5]
            pair_result["steepest_transitions"] = top_rates
            # Truncated viz: ~20 rows around inflection
            pair_result["visualization"] = _render_marginal_rates(
                rates, obj_a, obj_b, inflection, max_rows=20,
            )

        pairs.append(pair_result)

    return {"pairs": pairs}


def _render_marginal_rates(rates: list[dict], obj_a, obj_b, inflection: dict | None,
                           max_rows: int | None = None) -> str:
    """ASCII bar chart of marginal rates between adjacent solutions.

    max_rows: if set, truncate to max_rows centered on inflection point.
    """
    if not rates:
        return ""

    lines = []
    lines.append(f"─── Marginal Rates: {obj_b.name} cost per unit {obj_a.name} ───")
    lines.append("")

    rate_values = [r["rate"] for r in rates]
    max_rate = max(rate_values) if rate_values else 1.0
    if max_rate == 0:
        max_rate = 1.0

    # Determine which rows to show
    if max_rows and len(rates) > max_rows:
        # Center window on inflection point if available, else on middle
        center = inflection["position"] if inflection else len(rates) // 2
        half = max_rows // 2
        start = max(0, center - half)
        end = min(len(rates), start + max_rows)
        start = max(0, end - max_rows)  # Adjust if near end
        show_range = range(start, end)
        truncated = True
    else:
        show_range = range(len(rates))
        truncated = False

    BAR_W = 30
    if truncated and show_range.start > 0:
        lines.append(f"  ... {show_range.start} earlier transitions omitted")
    for idx in show_range:
        r = rates[idx]
        from_id = r["from_id"]
        to_id = r["to_id"]
        rate = r["rate"]
        filled = max(0, min(BAR_W, round(rate / max_rate * BAR_W)))
        bar = "█" * filled + "░" * (BAR_W - filled)
        marker = " ◀ INFLECTION" if inflection and idx == inflection["position"] else ""
        lines.append(f"  [{from_id}]→[{to_id}]  |{bar}| {_fmt(rate)}{marker}")
    if truncated and show_range.stop < len(rates):
        lines.append(f"  ... {len(rates) - show_range.stop} later transitions omitted")

    lines.append("")
    if inflection:
        lines.append(f"  ◀ Inflection: marginal cost jumps {inflection['jump_factor']:.1f}x at solution {inflection['solution_id']}")
    else:
        lines.append("  No significant inflection detected — marginal costs change gradually.")

    return "\n".join(lines)


# ─── ASCII Visualization Helpers ───


def _normalize(value: float, lo: float, hi: float, direction: str) -> float:
    """Normalize to 0.0–1.0 where 1.0 is 'better'.

    For maximize: higher raw value → higher normalized.
    For minimize: lower raw value → higher normalized (flipped).
    """
    if hi == lo:
        return 0.5
    raw = (value - lo) / (hi - lo)
    return (1.0 - raw) if direction == "minimize" else raw


def _bar(value: float, lo: float, hi: float, width: int = 30) -> str:
    """Render a single normalized bar."""
    if hi == lo:
        filled = width // 2
    else:
        filled = max(0, min(width, round((value - lo) / (hi - lo) * width)))
    return "█" * filled + "░" * (width - filled)


def _fmt(v: float) -> str:
    """Format a number compactly."""
    if abs(v) >= 100:
        return f"{v:.0f}"
    if abs(v) >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def _render_scatter(solutions, objectives, key_tradeoffs, extreme_solutions,
                    balanced_solution, inflection_candidates=None) -> str:
    """2D ASCII scatter plot of the most conflicting objective pair.

    Grid-bins all solutions as · then overlays labeled points for extremes (●),
    balanced (⚖), and inflection points (◆). Shows frontier shape and clustering.
    """
    WIDTH, HEIGHT = 50, 16

    # Find most negatively correlated pair
    if not key_tradeoffs:
        return "  (scatter requires 2+ objectives with correlation data)"
    best_pair = min(key_tradeoffs, key=lambda t: t["correlation"])
    x_name, y_name = best_pair["objectives"]
    r_val = best_pair["correlation"]

    obj_map = {o.name: o for o in objectives}
    x_obj, y_obj = obj_map[x_name], obj_map[y_name]
    x_dir, y_dir = x_obj.direction.value, y_obj.direction.value
    x_unit = f" ({x_obj.unit})" if x_obj.unit else ""
    y_unit = f" ({y_obj.unit})" if y_obj.unit else ""

    # Compute ranges
    x_vals = [s.objective_values[x_name] for s in solutions]
    y_vals = [s.objective_values[y_name] for s in solutions]
    x_lo, x_hi = min(x_vals), max(x_vals)
    y_lo, y_hi = min(y_vals), max(y_vals)

    # Build grid (row 0 = top = high normalized y)
    grid = [[" "] * WIDTH for _ in range(HEIGHT)]

    def _to_grid(xv, yv):
        nx = _normalize(xv, x_lo, x_hi, x_dir)
        ny = _normalize(yv, y_lo, y_hi, y_dir)
        col = max(0, min(WIDTH - 1, int(nx * (WIDTH - 1))))
        row = max(0, min(HEIGHT - 1, HEIGHT - 1 - int(ny * (HEIGHT - 1))))
        return row, col

    # Plot all solutions as dots
    for s in solutions:
        r, c = _to_grid(s.objective_values[x_name], s.objective_values[y_name])
        if grid[r][c] == " ":
            grid[r][c] = "·"

    # Collect labeled points
    labels_right = []  # (row, col, label)

    # Extremes for the plotted pair
    x_ext_key = f"extreme_{x_name}"
    y_ext_key = f"extreme_{y_name}"
    bal_id = balanced_solution["solution_id"]
    bal_vals = balanced_solution["objective_values"]

    inflection_ids = {k["solution_id"] for k in (inflection_candidates or [])}

    for s in solutions:
        sid = s.solution_id
        xv, yv = s.objective_values[x_name], s.objective_values[y_name]
        r, c = _to_grid(xv, yv)
        if x_ext_key in extreme_solutions and sid == extreme_solutions[x_ext_key]["solution_id"]:
            grid[r][c] = "●"
            labels_right.append((r, c, f"[{sid}] Top {x_name[:12]}"))
        elif y_ext_key in extreme_solutions and sid == extreme_solutions[y_ext_key]["solution_id"]:
            grid[r][c] = "●"
            labels_right.append((r, c, f"[{sid}] Top {y_name[:12]}"))
        elif sid == bal_id:
            grid[r][c] = "⚖"
            labels_right.append((r, c, f"[{sid}] Balanced"))
        elif sid in inflection_ids:
            grid[r][c] = "◆"
            labels_right.append((r, c, f"[{sid}] Inflection"))

    # Render
    lines = []
    lines.append(f"─── Frontier Scatter: {x_name} vs {y_name} (r={r_val:+.2f}) ───")
    lines.append("")

    # Y-axis label
    y_better = "↑ better" if y_dir == "maximize" else "↑ better (lower)"
    y_top = _fmt(y_hi if y_dir == "maximize" else y_lo)
    y_bot = _fmt(y_lo if y_dir == "maximize" else y_hi)
    y_label = f"{y_name}{y_unit}"
    lines.append(f"  {y_label} {y_better}")

    # Build label lookup by row for right-side labels
    row_labels = {}
    for r, c, lbl in labels_right:
        row_labels[r] = lbl

    for r in range(HEIGHT):
        row_str = "".join(grid[r])
        y_tick = ""
        if r == 0:
            y_tick = f"{y_top:>6s}"
        elif r == HEIGHT - 1:
            y_tick = f"{y_bot:>6s}"
        else:
            y_tick = "      "
        label = f"  {row_labels[r]}" if r in row_labels else ""
        lines.append(f"  {y_tick} |{row_str}|{label}")

    # X-axis
    x_better = "→ better" if x_dir == "maximize" else "→ better (lower)"
    x_left = _fmt(x_lo if x_dir == "maximize" else x_hi)
    x_right = _fmt(x_hi if x_dir == "maximize" else x_lo)
    lines.append(f"         +{'─' * WIDTH}+ {x_better}")
    lines.append(f"         {x_left}{' ' * (WIDTH - len(x_left) - len(x_right))}{x_right}")
    x_label = f"{x_name}{x_unit}"
    pad = (WIDTH - len(x_label)) // 2
    lines.append(f"         {' ' * pad}{x_label}")
    lines.append("")
    lines.append("  ● extreme  ⚖ balanced  ◆ inflection  · frontier")

    return "\n".join(lines)


def _render_tradeoffs_viz(result: dict, objectives: list, solutions=None) -> str:
    """Scatter plot of most conflicting pair + correlation summary."""
    parts = []

    # Scatter plot (needs full solutions list)
    if solutions and len(objectives) >= 2 and result.get("key_tradeoffs"):
        parts.append(_render_scatter(
            solutions, objectives,
            result["key_tradeoffs"],
            result["extreme_solutions"],
            result["balanced_solution"],
            inflection_candidates=result.get("inflection_point_candidates"),
        ))

    # Correlation summary — raw values, LLM interprets via solution_interpreter skill
    if result.get("key_tradeoffs"):
        lines = ["", "─── Correlations ───", ""]
        for t in result["key_tradeoffs"]:
            r = t["correlation"]
            if abs(r) < 0.3:
                continue
            o1, o2 = t["objectives"]
            lines.append(f"  {o1} vs {o2}: r={r:+.2f}")
        parts.append("\n".join(lines))

    return "\n".join(parts)


def _render_parallel_coords(solutions_data: list[dict], objectives: list,
                            labels: dict | None = None) -> str:
    """Parallel coordinates: one row per solution, one column per objective.

    Each objective gets a 12-char bar with a 2-char marker showing the
    solution's normalized position. Direction-aware: right = better.

    solutions_data: list of dicts with at least 'objective_values' key.
    labels: maps an identifier to a display label (e.g. {0: "[0] Best Ret"}).
    """
    if not solutions_data or not objectives:
        return ""

    BAR_W = 12
    labels = labels or {}

    # Determine which objectives to show (cap at 6 most differentiating)
    obj_list = list(objectives)
    if len(obj_list) > 6:
        # Pick 6 with highest variance across compared solutions
        variances = []
        for obj in obj_list:
            vals = [sd["objective_values"].get(obj.name, 0) for sd in solutions_data]
            v = max(vals) - min(vals) if vals else 0
            variances.append((v, obj))
        variances.sort(reverse=True)
        obj_list = [o for _, o in variances[:6]]
        omitted = len(objectives) - 6
    else:
        omitted = 0

    # Compute ranges across compared solutions
    ranges = {}
    for obj in obj_list:
        vals = [sd["objective_values"].get(obj.name, 0) for sd in solutions_data]
        ranges[obj.name] = (min(vals), max(vals))

    # Build header
    lines = []
    n_sols = len(solutions_data)
    n_objs = len(obj_list)
    lines.append(f"─── Parallel Coordinates: {n_sols} solutions x {n_objs} objectives ───")
    lines.append("")

    # Objective names row
    name_row = f"  {'Solution':<18s}"
    for obj in obj_list:
        arrow = "→" if obj.direction.value == "maximize" else "←"
        name = obj.name[:10]
        name_row += f"  {name}{arrow:>{BAR_W - len(name)}s}"
    lines.append(name_row)

    # Scale row
    scale_row = f"  {'':<18s}"
    for obj in obj_list:
        lo, hi = ranges[obj.name]
        if obj.direction.value == "minimize":
            scale_row += f"  {_fmt(hi):>{BAR_W // 2}s}─{_fmt(lo):<{BAR_W // 2}s}"
        else:
            scale_row += f"  {_fmt(lo):>{BAR_W // 2}s}─{_fmt(hi):<{BAR_W // 2}s}"
    lines.append(scale_row)

    lines.append(f"  {'─' * 18}{'─' * ((BAR_W + 2) * n_objs)}")

    # Solution rows
    for sd in solutions_data:
        # Determine label
        sid = sd.get("solution_id", sd.get("content_signature", ""))
        label = labels.get(sid, str(sid)[:15])
        label = label[:18]

        row = f"  {label:<18s}"
        for obj in obj_list:
            lo, hi = ranges[obj.name]
            val = sd["objective_values"].get(obj.name, 0)
            n = _normalize(val, lo, hi, obj.direction.value)
            pos = max(0, min(BAR_W - 2, int(n * (BAR_W - 2))))
            bar = list("·" * BAR_W)
            bar[pos] = "█"
            bar[min(pos + 1, BAR_W - 1)] = "█"
            row += f"  {''.join(bar)}"
        lines.append(row)

    if omitted:
        lines.append(f"  ({omitted} more objectives omitted)")

    return "\n".join(lines)


def _render_scenario_viz(result: dict) -> str:
    """ASCII side-by-side range comparison per scenario."""
    lines = []
    per_scenario = result["per_scenario"]
    scenario_names = list(per_scenario.keys())
    if not scenario_names:
        return ""

    # Get all objectives
    obj_names = list(per_scenario[scenario_names[0]]["objective_ranges"].keys())

    # Global min/max per objective across scenarios
    global_ranges = {}
    for obj in obj_names:
        all_lo = min(per_scenario[s]["objective_ranges"][obj]["min"] for s in scenario_names)
        all_hi = max(per_scenario[s]["objective_ranges"][obj]["max"] for s in scenario_names)
        global_ranges[obj] = (all_lo, all_hi)

    lines.append("─── Scenario Range Comparison ───")
    lines.append("")

    for obj in obj_names:
        lo, hi = global_ranges[obj]
        lines.append(f"  {obj}  [{lo:.2f} — {hi:.2f}]")
        for s_name in scenario_names:
            s_lo = per_scenario[s_name]["objective_ranges"][obj]["min"]
            s_hi = per_scenario[s_name]["objective_ranges"][obj]["max"]
            bar_lo = _bar(s_lo, lo, hi, width=30)
            bar_hi = _bar(s_hi, lo, hi, width=30)
            # Show range as a bracket
            if hi == lo:
                pos_lo, pos_hi = 15, 15
            else:
                pos_lo = max(0, min(30, round((s_lo - lo) / (hi - lo) * 30)))
                pos_hi = max(0, min(30, round((s_hi - lo) / (hi - lo) * 30)))
            range_bar = "·" * pos_lo + "█" * max(1, pos_hi - pos_lo) + "·" * (30 - pos_hi)
            lines.append(f"    {s_name:30s} |{range_bar}| {s_lo:.2f}–{s_hi:.2f}")
        lines.append("")

    # Option robustness (frequency + allocation-weighted)
    robustness = result.get("option_robustness", [])
    lines.append("─── Option Robustness (frequency × avg weight) ───")
    if robustness:
        lines.append(f"  {'Option':20s} {'Tier':10s} {'Freq':>6s} {'Wt%':>6s} {'Score':>7s} {'In':>4s}")
        lines.append(f"  {'─'*20} {'─'*10} {'─'*6} {'─'*6} {'─'*7} {'─'*4}")
        for r in robustness[:15]:  # Top 15
            lines.append(
                f"  {r['option']:20s} {r['tier']:10s} "
                f"{r['avg_frequency']:6.1%} {r['avg_weight']:5.1f}% "
                f"{r['importance']:7.1f} {r['scenarios_present']:3d}/{len(per_scenario)}"
            )
        if len(robustness) > 15:
            lines.append(f"  ... and {len(robustness) - 15} more")
    else:
        lines.append("  No options found in solutions.")
    lines.append("")

    specific = result.get("scenario_specific_options", {})
    if specific:
        lines.append(f"  Scenario-specific: {len(specific)} options (appear in some but not all)")
        for opt, scenarios in sorted(specific.items()):
            lines.append(f"    {opt}: {', '.join(scenarios)}")
        lines.append("")

    # Expected values
    ev = result.get("expected_values", {})
    if ev:
        lines.append("─── Expected Values (probability-weighted best-per-scenario) ───")
        lines.append("  ⚠ These are ideal-point values — no single solution achieves all simultaneously.")
        for obj, val in ev.items():
            lines.append(f"  {obj:25s} {val:.2f}")

    return "\n".join(lines)


def _require_run(problem: Problem, scenario: str | None = None) -> Run:
    if scenario:
        if not problem.scenario_run or not problem.scenario_run.scenario_runs:
            raise ValueError("No scenario runs found. Use solve run_scenarios first.")
        if scenario not in problem.scenario_run.scenario_runs:
            available = list(problem.scenario_run.scenario_runs.keys())
            raise ValueError(f"Scenario '{scenario}' not found. Available: {available}")
        run = problem.scenario_run.scenario_runs[scenario]
        if not run.solutions:
            raise ValueError(f"Scenario '{scenario}' has no solutions.")
        return run
    if problem.run is None:
        raise ValueError("No run found. Use solve first.")
    if not problem.run.solutions:
        raise ValueError("Run has no solutions.")
    return problem.run


def _classify_frontier_shapes(solutions, objectives) -> list[dict]:
    """Classify tradeoff shape (linear/concave/convex/discontinuous) per conflicting pair.

    Only analyzes pairs with negative correlation and >= 5 solutions.
    """
    from scipy.stats import spearmanr

    obj_names = [o.name for o in objectives]
    if len(solutions) < 5 or len(obj_names) < 2:
        return []

    matrix = np.array([
        [s.objective_values[name] for name in obj_names]
        for s in solutions
    ])
    dir_signs = np.array([
        -1.0 if o.direction.value == "minimize" else 1.0
        for o in objectives
    ])
    norm_matrix = matrix * dir_signs
    corr = np.corrcoef(norm_matrix.T)

    shapes = []
    for i in range(len(obj_names)):
        for j in range(i + 1, len(obj_names)):
            r = float(corr[i, j])
            if r >= -0.2:
                continue  # Only conflicting pairs

            obj_a, obj_b = objectives[i], objectives[j]
            reverse_a = obj_a.direction.value == "maximize"
            sorted_sols = sorted(
                solutions,
                key=lambda s: s.objective_values[obj_a.name],
                reverse=reverse_a,
            )

            # Compute marginal rates between adjacent solutions
            rates = []
            spacings = []
            for k in range(len(sorted_sols) - 1):
                s1, s2 = sorted_sols[k], sorted_sols[k + 1]
                delta_a = s2.objective_values[obj_a.name] - s1.objective_values[obj_a.name]
                delta_b = s2.objective_values[obj_b.name] - s1.objective_values[obj_b.name]
                if obj_a.direction.value == "minimize":
                    delta_a = -delta_a
                if obj_b.direction.value == "minimize":
                    delta_b = -delta_b
                rate = abs(delta_b / delta_a) if abs(delta_a) > 1e-9 else 0.0
                rates.append(rate)
                spacing = abs(delta_a)
                spacings.append(spacing)

            if len(rates) < 3:
                continue

            rates_arr = np.array(rates)
            spacings_arr = np.array(spacings)

            # Check for discontinuous: large gaps in objective space (> 3× median spacing)
            median_spacing = np.median(spacings_arr)
            if median_spacing > 1e-9:
                max_gap = spacings_arr.max()
                if max_gap > 3.0 * median_spacing:
                    shapes.append({
                        "objectives": [obj_a.name, obj_b.name],
                        "shape": "discontinuous",
                        "confidence": round(min(float(max_gap / median_spacing) / 10.0, 1.0), 2),
                    })
                    continue

            # Rate trend: Spearman correlation of rate vs position
            positions = np.arange(len(rates_arr))
            rho, _ = spearmanr(positions, rates_arr)

            # Rate stability: coefficient of variation
            rate_mean = rates_arr.mean()
            rate_cv = float(rates_arr.std() / rate_mean) if rate_mean > 1e-9 else 0.0

            if rate_cv < 0.3:
                shape = "linear"
                confidence = round(1.0 - rate_cv, 2)
            elif rho > 0.3:
                shape = "concave"  # rates increasing → diminishing returns
                confidence = round(min(abs(rho), 1.0), 2)
            elif rho < -0.3:
                shape = "convex"  # rates decreasing → diminishing sacrifice
                confidence = round(min(abs(rho), 1.0), 2)
            else:
                shape = "linear"
                confidence = round(max(0.3, 1.0 - rate_cv), 2)

            shapes.append({
                "objectives": [obj_a.name, obj_b.name],
                "shape": shape,
                "confidence": confidence,
            })

    return shapes


def _compute_pair_rates(sorted_sols, obj_a, obj_b) -> list[dict]:
    """Compute direction-normalized marginal rates between adjacent sorted solutions.

    Returns list of dicts with from_sol, to_sol, delta_a, delta_b, rate — rich
    enough for both marginal_analysis display and inflection detection.
    """
    rates = []
    for k in range(len(sorted_sols) - 1):
        s1, s2 = sorted_sols[k], sorted_sols[k + 1]
        delta_a = s2.objective_values[obj_a.name] - s1.objective_values[obj_a.name]
        delta_b = s2.objective_values[obj_b.name] - s1.objective_values[obj_b.name]
        if obj_a.direction.value == "minimize":
            delta_a = -delta_a
        if obj_b.direction.value == "minimize":
            delta_b = -delta_b
        rate = abs(delta_b / delta_a) if abs(delta_a) > 1e-9 else 0.0
        rates.append({
            "from_sol": s1,
            "to_sol": s2,
            "delta_a": delta_a,
            "delta_b": delta_b,
            "rate": rate,
        })
    return rates


def _detect_inflection(rate_values: list[float], threshold: float = 2.0) -> dict | None:
    """Find the largest jump in marginal rate across adjacent rates.

    Returns {position, jump_factor} if max jump >= threshold, else None.
    Position is the index into the rate list where the jump lands (i.e. k+1).
    """
    if len(rate_values) < 2:
        return None
    max_jump, inflection_idx = 0.0, 0
    for k in range(len(rate_values) - 1):
        prev_rate = rate_values[k]
        next_rate = rate_values[k + 1]
        if prev_rate > 1e-9:
            jump = next_rate / prev_rate
        else:
            jump = next_rate if next_rate > 0 else 0.0
        if jump > max_jump:
            max_jump = jump
            inflection_idx = k + 1
    if max_jump >= threshold:
        return {"position": inflection_idx, "jump_factor": round(max_jump, 1)}
    return None


def _conflicting_pair_indices(solutions, objectives) -> list[tuple[int, int, float]]:
    """Return (i, j, correlation) for each conflicting objective pair.

    Direction-normalized: flips minimize objectives so higher = better before
    computing correlation. Only pairs with negative correlation are returned.
    """
    obj_names = [o.name for o in objectives]
    if len(solutions) < 3 or len(obj_names) < 2:
        return []
    matrix = np.array([
        [s.objective_values[name] for name in obj_names]
        for s in solutions
    ])
    dir_signs = np.array([
        -1.0 if o.direction.value == "minimize" else 1.0
        for o in objectives
    ])
    norm_matrix = matrix * dir_signs
    corr = np.corrcoef(norm_matrix.T)
    pairs = []
    for i in range(len(obj_names)):
        for j in range(i + 1, len(obj_names)):
            r = float(corr[i, j])
            if r < 0:
                pairs.append((i, j, r))
    return pairs


def _find_inflection_solutions(solutions, objectives) -> list[dict]:
    """Find inflection-point solutions from marginal rate analysis.

    Returns a list of {solution, pair, jump_factor} for each conflicting
    objective pair that has a detected inflection. Shares rate computation
    and inflection detection with marginal_analysis.
    """
    knees = []
    seen_ids = set()
    for i, j, _r in _conflicting_pair_indices(solutions, objectives):
        obj_a, obj_b = objectives[i], objectives[j]
        reverse_a = obj_a.direction.value == "maximize"
        sorted_sols = sorted(
            solutions,
            key=lambda s: s.objective_values[obj_a.name],
            reverse=reverse_a,
        )
        rates = _compute_pair_rates(sorted_sols, obj_a, obj_b)
        inflection = _detect_inflection([r["rate"] for r in rates])
        if inflection is None:
            continue
        inflection_sol = rates[inflection["position"]]["from_sol"]
        if inflection_sol.solution_id in seen_ids:
            continue
        seen_ids.add(inflection_sol.solution_id)
        knees.append({
            "solution": inflection_sol,
            "pair": f"{obj_a.name} vs {obj_b.name}",
            "jump_factor": inflection["jump_factor"],
        })
    return knees


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

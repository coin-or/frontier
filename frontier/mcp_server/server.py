"""Frontier MCP server: 3 tools (model, solve, explore) + 4 skills."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from frontier.engine import explorer, metrics, optimizer
from frontier.engine.models import (
    Approach,
    Constraint,
    CardinalityConstraint,
    DependencyConstraint,
    ExclusionPairConstraint,
    Feedback,
    ForceExcludeConstraint,
    _content_signature,
    ForceIncludeConstraint,
    GroupLimitConstraint,
    Objective,
    ObjectiveBoundConstraint,
    OptimizeMode,
    Option,
    Problem,
    ReferencePoint,
    Scenario,
    ScoreAdjustment,
    ScenarioConfig,
    ScenarioRun,
    Score,
)
from frontier.engine.store import Store

mcp = FastMCP(
    "Frontier",
    instructions=(
        "Multi-objective portfolio optimization engine.\n\n"
        "BEFORE using any tools, read the skill resources for guidance:\n"
        "- frontier://skills/problem_framing — read before model/create\n"
        "- frontier://skills/data_collection — read before entering scores\n"
        "- frontier://skills/optimization_strategy — read before solve/run\n"
        "- frontier://skills/solution_interpreter — read before explore/tradeoffs\n\n"
        "Workflow: model → solve → explore. Skills tell you HOW to do each step well."
    ),
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("PORT", "8000")),
)
store = Store()

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


# ─── Skills as resources ───


@mcp.resource("frontier://skills/problem_framing")
def skill_problem_framing() -> str:
    return (SKILLS_DIR / "problem_framing.md").read_text()


@mcp.resource("frontier://skills/data_collection")
def skill_data_collection() -> str:
    return (SKILLS_DIR / "data_collection.md").read_text()


@mcp.resource("frontier://skills/optimization_strategy")
def skill_optimization_strategy() -> str:
    return (SKILLS_DIR / "optimization_strategy.md").read_text()


@mcp.resource("frontier://skills/solution_interpreter")
def skill_solution_interpreter() -> str:
    return (SKILLS_DIR / "solution_interpreter.md").read_text()


# ─── Tool 1: model ───


@mcp.tool()
def model(
    action: str,
    problem_id: str | None = None,
    name: str | None = None,
    domain: str | None = None,
    context: str | None = None,
    objectives: list[dict] | None = None,
    options: list[dict] | None = None,
    scores: list[dict] | None = None,
    constraints: list[dict] | None = None,
    approach: str | None = None,
    reference_points: list[dict] | None = None,
    scenario_config: dict | None = None,
) -> dict:
    """Build and modify the optimization problem.

    Read frontier://skills/problem_framing before creating a problem.
    Read frontier://skills/data_collection before entering scores.

    Actions:
      create  — Start a new problem. Params: name?, domain?, context?, approach?
      update  — Modify problem. Params: problem_id (required), plus any of:
                name, domain, context, objectives, options, scores, constraints,
                approach ("binary" or "proportional"),
                reference_points (list of {type, name?, objective_values, selected_options?}).
                Scores use merge semantics; everything else is full replacement.
      get     — Full problem state. Params: problem_id
      list    — All problems. No params.
      delete  — Remove problem. Params: problem_id
    """
    params = {
        k: v for k, v in {
            "problem_id": problem_id, "name": name, "domain": domain,
            "context": context, "objectives": objectives, "options": options,
            "scores": scores, "constraints": constraints, "approach": approach,
            "reference_points": reference_points, "scenario_config": scenario_config,
        }.items() if v is not None
    }
    match action:
        case "create":
            return _model_create(params)
        case "update":
            return _model_update(params)
        case "get":
            return _model_get(params)
        case "list":
            return _model_list()
        case "delete":
            return _model_delete(params)
        case _:
            return {"error": f"Unknown action: {action}. Use create/update/get/list/delete."}


def _model_create(params: dict) -> dict:
    kwargs = dict(
        name=params.get("name", ""),
        domain=params.get("domain", ""),
        context=params.get("context", ""),
    )
    if "approach" in params:
        kwargs["approach"] = Approach(params["approach"])
    p = Problem(**kwargs)
    store.save(p)
    return {
        "problem_id": p.problem_id,
        "name": p.name,
        "domain": p.domain,
        "created_at": p.created_at.isoformat(),
    }


def _model_update(params: dict) -> dict:
    pid = params.get("problem_id")
    if not pid:
        return {"error": "problem_id is required."}

    try:
        p = store.load(pid)
    except FileNotFoundError:
        return {"error": f"Problem {pid} not found."}

    structural_change = False

    # Metadata updates
    if "name" in params:
        p.name = params["name"]
    if "domain" in params:
        p.domain = params["domain"]
    if "context" in params:
        p.context = params["context"]

    # Objectives — full replacement
    if "objectives" in params:
        old_names = {o.name for o in p.objectives}
        p.objectives = [Objective(**o) if isinstance(o, dict) else o for o in params["objectives"]]
        new_names = {o.name for o in p.objectives}
        # Drop scores and constraints referencing removed objectives
        removed = old_names - new_names
        if removed:
            p.scores = [s for s in p.scores if s.objective not in removed]
            p.constraints = [
                c for c in p.constraints
                if not (c.type == "objective_bound" and c.objective in removed)
            ]
        structural_change = True

    # Options — full replacement
    if "options" in params:
        old_names = {o.name for o in p.options}
        p.options = [Option(**o) if isinstance(o, dict) else o for o in params["options"]]
        new_names = {o.name for o in p.options}
        # Drop scores and constraints referencing removed options
        removed = old_names - new_names
        if removed:
            p.scores = [s for s in p.scores if s.option not in removed]

            def _constraint_references_removed(c, removed_opts):
                if c.type in ("force_include", "force_exclude") and c.option in removed_opts:
                    return True
                if c.type == "exclusion_pair" and (c.option_a in removed_opts or c.option_b in removed_opts):
                    return True
                if c.type == "dependency" and (c.if_option in removed_opts or c.then_option in removed_opts):
                    return True
                if c.type == "group_limit" and any(o in removed_opts for o in c.options):
                    return True
                return False

            p.constraints = [c for c in p.constraints if not _constraint_references_removed(c, removed)]
        structural_change = True

    # Scores — merge semantics (upsert by option+objective)
    if "scores" in params:
        new_scores = [Score(**s) if isinstance(s, dict) else s for s in params["scores"]]
        valid_opts = {o.name for o in p.options}
        valid_objs = {o.name for o in p.objectives}
        invalid = [
            s for s in new_scores
            if s.option not in valid_opts or s.objective not in valid_objs
        ]
        if invalid:
            bad_refs = [
                f"{s.option}/{s.objective}" for s in invalid
            ]
            return {"error": f"Scores reference unknown options/objectives: {bad_refs}"}
        score_map = {(s.option, s.objective): s for s in p.scores}
        for s in new_scores:
            score_map[(s.option, s.objective)] = s
        p.scores = list(score_map.values())
        structural_change = True

    # Constraints — full replacement
    if "constraints" in params:
        p.constraints = [_parse_constraint(c) for c in params["constraints"]]
        structural_change = True

    # Approach
    if "approach" in params:
        p.approach = Approach(params["approach"])
        structural_change = True

    # Scenario config
    if "scenario_config" in params:
        sc = params["scenario_config"]
        if isinstance(sc, dict):
            # Parse nested scenarios with score overrides and adjustments
            scenarios = []
            for s in sc.get("scenarios", []):
                overrides = [Score(**o) if isinstance(o, dict) else o for o in s.get("score_overrides", [])]
                adjustments = [
                    ScoreAdjustment(**a) if isinstance(a, dict) else a
                    for a in s.get("score_adjustments", [])
                ]
                constraint_ov = [
                    _parse_constraint(c) for c in s.get("constraint_overrides", [])
                ]
                scenarios.append(Scenario(
                    name=s["name"],
                    probability=s.get("probability"),  # optional
                    description=s.get("description", ""),
                    score_overrides=overrides,
                    score_adjustments=adjustments,
                    constraint_overrides=constraint_ov,
                ))
            p.scenario_config = ScenarioConfig(enabled=sc.get("enabled", True), scenarios=scenarios)
        structural_change = True

    # Reference points — full replacement (interpretive, no structural impact)
    if "reference_points" in params:
        p.reference_points = [
            ReferencePoint(**rp) if isinstance(rp, dict) else rp
            for rp in params["reference_points"]
        ]

    # Mark results stale on structural change (preserve run for comparison)
    if structural_change:
        p.results_stale = True

    p.updated_at = datetime.now(timezone.utc)
    store.save(p)

    total_possible = len(p.objectives) * len(p.options)
    result = {
        "problem_id": p.problem_id,
        "updated_at": p.updated_at.isoformat(),
        "status": {
            "objectives": len(p.objectives),
            "options": len(p.options),
            "scores_complete": round(len(p.scores) / total_possible, 2) if total_possible > 0 else 0.0,
            "has_run": p.run is not None,
            "results_stale": p.results_stale,
            "total_runs": len(p.runs) + (1 if p.run else 0),
        },
    }

    # Include metrics on structural changes so the LLM can coach the user
    if structural_change:
        result["metrics"] = {
            "framing": metrics.framing_metrics(p),
            "data": metrics.data_metrics(p),
        }

    return result


def _model_get(params: dict) -> dict:
    pid = params.get("problem_id")
    if not pid:
        return {"error": "problem_id is required."}
    try:
        p = store.load(pid)
    except FileNotFoundError:
        return {"error": f"Problem {pid} not found."}
    return json.loads(p.model_dump_json())


def _model_list() -> list:
    return store.list()


def _model_delete(params: dict) -> dict:
    pid = params.get("problem_id")
    if not pid:
        return {"error": "problem_id is required."}
    try:
        store.delete(pid)
    except FileNotFoundError:
        return {"error": f"Problem {pid} not found."}
    return {"deleted": pid}


def _parse_constraint(c: dict | Constraint) -> Constraint:
    if not isinstance(c, dict):
        return c
    ctype = c.get("type")
    match ctype:
        case "cardinality":
            return CardinalityConstraint(**c)
        case "force_include":
            return ForceIncludeConstraint(**c)
        case "force_exclude":
            return ForceExcludeConstraint(**c)
        case "objective_bound":
            return ObjectiveBoundConstraint(**c)
        case "exclusion_pair":
            return ExclusionPairConstraint(**c)
        case "dependency":
            return DependencyConstraint(**c)
        case "group_limit":
            return GroupLimitConstraint(**c)
        case _:
            raise ValueError(f"Unknown constraint type: {ctype}")


# ─── Tool 2: solve ───


@mcp.tool()
def solve(action: str, problem_id: str, mode: str | None = None) -> dict:
    """Validate and run the optimizer.

    Read frontier://skills/optimization_strategy before running.

    Actions:
      validate       — Check if problem is ready. Returns issues and missing scores.
      run            — Validate, then optimize. Returns full Pareto frontier inline.
      run_scenarios  — Run optimization independently per scenario. Requires scenario_config.

    Args:
      mode: "fast" (default) for quick exploration iterations, "thorough" for
            final convergence when the problem is refined. Adapts population size,
            generations, and operator parameters to problem complexity. Also selects
            NSGA-III for 4+ objectives.
    """
    try:
        p = store.load(problem_id)
    except FileNotFoundError:
        return {"error": f"Problem {problem_id} not found."}

    opt_mode = None
    if mode is not None:
        try:
            opt_mode = OptimizeMode(mode)
        except ValueError:
            return {"error": f"Invalid mode '{mode}'. Use 'fast' or 'thorough'."}

    match action:
        case "validate":
            vr = optimizer.validate(p)
            return json.loads(vr.model_dump_json())
        case "run":
            return _solve_run(p, opt_mode)
        case "run_scenarios":
            return _solve_run_scenarios(p, opt_mode)
        case _:
            return {"error": f"Unknown action: {action}. Use validate/run/run_scenarios."}


def _solve_run(p: Problem, mode: OptimizeMode | None = None) -> dict:
    vr = optimizer.validate(p)
    if not vr.ready:
        vr_data = json.loads(vr.model_dump_json())
        return {"ready": False, "issues": vr_data["issues"], "missing_scores": vr_data["missing_scores"]}

    try:
        run = optimizer.optimize(p, mode=mode)
    except Exception as e:
        return {"feasible": False, "error": str(e)}

    if not run.solutions:
        analysis = optimizer.analyze_infeasibility(p)
        return {
            "feasible": False,
            **analysis,
        }

    # Snapshot constraints on the run
    run.constraints_snapshot = [c.model_dump() for c in p.constraints]

    # Archive previous run before replacing
    if p.run is not None:
        p.runs.append(p.run)

    p.run = run
    p.results_stale = False
    store.save(p)

    return {
        "run_id": run.run_id,
        "solutions_found": len(run.solutions),
        "solutions": [json.loads(s.model_dump_json()) for s in run.solutions],
        "quality": json.loads(run.quality.model_dump_json()),
        "metrics": {
            "solve": metrics.solve_metrics(p),
            "diagnostics": metrics.diagnostics(p),
        },
    }


def _solve_run_scenarios(p: Problem, mode: OptimizeMode | None = None) -> dict:
    vr = optimizer.validate(p)
    if not vr.ready:
        vr_data = json.loads(vr.model_dump_json())
        return {"ready": False, "issues": vr_data["issues"]}

    try:
        scenario_results = optimizer.optimize_scenarios(p, mode=mode)
    except ValueError as e:
        return {"error": str(e)}

    p.scenario_run = ScenarioRun(scenario_runs=scenario_results)
    p.results_stale = False
    store.save(p)

    summary = {}
    for name, run in scenario_results.items():
        summary[name] = {
            "solutions_found": len(run.solutions),
            "quality": json.loads(run.quality.model_dump_json()),
        }

    return {
        "scenarios_optimized": len(scenario_results),
        "results": summary,
    }


# ─── Tool 3: explore ───


@mcp.tool()
def explore(
    action: str,
    problem_id: str,
    solution_ids: list[int] | None = None,
    solution_id: int | None = None,
    rating: int | None = None,
    notes: str | None = None,
    stage: str | None = None,
    run_ids: list[str] | None = None,
    custom_name: str | None = None,
    content_signature: str | None = None,
    signatures: list[str] | None = None,
) -> dict:
    """Navigate results after solving.

    Read frontier://skills/solution_interpreter before presenting results.

    Actions:
      tradeoffs  — Frontier overview: ranges, correlations, extremes, balanced solution.
      compare    — Side-by-side comparison. Requires solution_ids (list of 2+ ints).
      solutions  — Full Pareto frontier listing.
      solution   — Single solution detail. Requires solution_id (int).
      feedback   — Record user feedback. Params: solution_id? or content_signature?, rating? (1-5), notes?, stage? Feedback links to content_signature (stable across runs) and attaches to curated solutions.
      compare_runs — Compare run history. Requires run_ids (list of 2+ run ID strings).
      scenario_results — Per-scenario analysis: robust options, scenario-specific options, expected values.
      curate     — Add solution to curated set. Params: solution_id, custom_name?, notes?
      uncurate   — Remove from curated set. Params: content_signature.
      rename_curated — Update name. Params: content_signature, custom_name.
      curated    — List all curated solutions with survival status.
      compare_curated — Compare curated solutions. Params: signatures (list of 2+ content_signature strings).
    """
    try:
        p = store.load(problem_id)
    except FileNotFoundError:
        return {"error": f"Problem {problem_id} not found."}

    match action:
        case "tradeoffs":
            try:
                return explorer.get_tradeoffs(p)
            except ValueError as e:
                return {"error": str(e)}
        case "compare":
            if not solution_ids or len(solution_ids) < 2:
                return {"error": "solution_ids must contain at least 2 IDs for compare."}
            try:
                return explorer.compare_solutions(p, solution_ids)
            except ValueError as e:
                return {"error": str(e)}
        case "solutions":
            try:
                return explorer.get_solutions(p)
            except ValueError as e:
                return {"error": str(e)}
        case "solution":
            if solution_id is None:
                return {"error": "solution_id required for solution action."}
            try:
                return explorer.get_solution(p, solution_id)
            except ValueError as e:
                return {"error": str(e)}
        case "feedback":
            return _explore_feedback(p, solution_id, content_signature, rating, notes, stage)
        case "compare_runs":
            if not run_ids or len(run_ids) < 2:
                return {"error": "run_ids must contain at least 2 run IDs for compare_runs."}
            try:
                return explorer.compare_runs(p, run_ids)
            except ValueError as e:
                return {"error": str(e)}
        case "scenario_results":
            try:
                return explorer.get_scenario_results(p)
            except ValueError as e:
                return {"error": str(e)}
        case "curate":
            if solution_id is None:
                return {"error": "solution_id required for curate action."}
            try:
                result = explorer.curate_solution(p, solution_id, custom_name or "", notes or "")
                store.save(p)
                return result
            except ValueError as e:
                return {"error": str(e)}
        case "uncurate":
            if not content_signature:
                return {"error": "content_signature required for uncurate action."}
            try:
                result = explorer.uncurate_solution(p, content_signature)
                store.save(p)
                return result
            except ValueError as e:
                return {"error": str(e)}
        case "rename_curated":
            if not content_signature or not custom_name:
                return {"error": "content_signature and custom_name required for rename_curated."}
            try:
                result = explorer.rename_curated(p, content_signature, custom_name)
                store.save(p)
                return result
            except ValueError as e:
                return {"error": str(e)}
        case "curated":
            return explorer.list_curated(p)
        case "compare_curated":
            if not signatures or len(signatures) < 2:
                return {"error": "signatures must contain at least 2 content_signature strings."}
            try:
                return explorer.compare_curated(p, signatures)
            except ValueError as e:
                return {"error": str(e)}
        case _:
            return {"error": f"Unknown action: {action}."}


def _explore_feedback(
    p: Problem,
    solution_id: int | None,
    content_signature: str | None,
    rating: int | None,
    notes: str | None,
    stage: str | None,
) -> dict:
    """Record user feedback on solutions or the overall process.

    Feedback is linked to a content_signature (stable across runs). If only
    solution_id is provided, the signature is computed from the current run.
    Feedback is also appended to any curated solution with the same signature.
    """
    if rating is not None and not (1 <= rating <= 5):
        return {"error": "rating must be 1-5."}

    # Resolve content_signature from solution_id if not provided directly
    sig = content_signature
    if sig is None and solution_id is not None and p.run:
        for s in p.run.solutions:
            if s.solution_id == solution_id:
                sig = s.content_signature or _content_signature(
                    s.selected_options, s.allocations
                )
                break

    fb = Feedback(
        content_signature=sig,
        solution_id=solution_id,
        rating=rating,
        notes=notes or "",
        stage=stage or "",
    )

    # Store on problem-level feedback list
    p.feedback.append(fb)

    # Also attach to matching curated solution (preference travels with curation)
    if sig:
        for cs in p.curated_solutions:
            if cs.content_signature == sig:
                cs.feedback.append(fb)
                break

    p.updated_at = datetime.now(timezone.utc)
    store.save(p)

    return {
        "recorded": True,
        "content_signature": sig,
        "feedback_count": len(p.feedback),
        "outcome": metrics.outcome_metrics(p),
    }


# ─── Entry point ───


def main():
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()

"""Frontier MCP server: 3 tools (model, solve, explore) + 4 skills."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from frontier.engine import explorer, metrics, optimizer
from frontier.engine.models import (
    Constraint,
    CardinalityConstraint,
    Feedback,
    ForceExcludeConstraint,
    ForceIncludeConstraint,
    Objective,
    ObjectiveBoundConstraint,
    Option,
    Problem,
    Score,
)
from frontier.engine.store import Store

mcp = FastMCP(
    "Frontier",
    instructions="Multi-objective portfolio optimization engine. Use model → solve → explore workflow.",
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
) -> dict:
    """Build and modify the optimization problem.

    Actions:
      create  — Start a new problem. Params: name?, domain?, context?
      update  — Modify problem. Params: problem_id (required), plus any of:
                name, domain, context, objectives, options, scores, constraints.
                Scores use merge semantics; everything else is full replacement.
      get     — Full problem state. Params: problem_id
      list    — All problems. No params.
      delete  — Remove problem. Params: problem_id
    """
    params = {
        k: v for k, v in {
            "problem_id": problem_id, "name": name, "domain": domain,
            "context": context, "objectives": objectives, "options": options,
            "scores": scores, "constraints": constraints,
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
    p = Problem(
        name=params.get("name", ""),
        domain=params.get("domain", ""),
        context=params.get("context", ""),
    )
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
            p.constraints = [
                c for c in p.constraints
                if not (c.type in ("force_include", "force_exclude") and c.option in removed)
            ]
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

    # Clear run on structural change
    if structural_change:
        p.run = None

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
        case _:
            raise ValueError(f"Unknown constraint type: {ctype}")


# ─── Tool 2: solve ───


@mcp.tool()
def solve(action: str, problem_id: str) -> dict:
    """Validate and run the optimizer.

    Actions:
      validate — Check if problem is ready. Returns issues and missing scores.
      run      — Validate, then optimize. Returns full Pareto frontier inline.
    """
    try:
        p = store.load(problem_id)
    except FileNotFoundError:
        return {"error": f"Problem {problem_id} not found."}

    match action:
        case "validate":
            vr = optimizer.validate(p)
            return json.loads(vr.model_dump_json())
        case "run":
            return _solve_run(p)
        case _:
            return {"error": f"Unknown action: {action}. Use validate/run."}


def _solve_run(p: Problem) -> dict:
    vr = optimizer.validate(p)
    if not vr.ready:
        vr_data = json.loads(vr.model_dump_json())
        return {"ready": False, "issues": vr_data["issues"], "missing_scores": vr_data["missing_scores"]}

    try:
        run = optimizer.optimize(p)
    except Exception as e:
        return {"feasible": False, "error": str(e)}

    if not run.solutions:
        analysis = optimizer.analyze_infeasibility(p)
        return {
            "feasible": False,
            **analysis,
        }

    p.run = run
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
) -> dict:
    """Navigate results after solving.

    Actions:
      tradeoffs  — Frontier overview: ranges, correlations, extremes, balanced solution.
      compare    — Side-by-side comparison. Requires solution_ids (list of 2+ ints).
      solutions  — Full Pareto frontier listing.
      solution   — Single solution detail. Requires solution_id (int).
      feedback   — Record user feedback. Params: solution_id?, rating? (1-5), notes?, stage?
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
            return _explore_feedback(p, solution_id, rating, notes, stage)
        case _:
            return {"error": f"Unknown action: {action}. Use tradeoffs/compare/solutions/solution/feedback."}


def _explore_feedback(
    p: Problem,
    solution_id: int | None,
    rating: int | None,
    notes: str | None,
    stage: str | None,
) -> dict:
    """Record user feedback on solutions or the overall process."""
    if rating is not None and not (1 <= rating <= 5):
        return {"error": "rating must be 1-5."}

    fb = Feedback(
        solution_id=solution_id,
        rating=rating,
        notes=notes or "",
        stage=stage or "",
    )
    p.feedback.append(fb)
    p.updated_at = datetime.now(timezone.utc)
    store.save(p)

    return {
        "recorded": True,
        "feedback_count": len(p.feedback),
        "outcome": metrics.outcome_metrics(p),
    }


# ─── Entry point ───


def main():
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()

"""Frontier MCP server: 3 tools (model, solve, explore) + 4 skills."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from frontier.engine import explorer, optimizer
from frontier.engine.models import (
    Constraint,
    CardinalityConstraint,
    ForceExcludeConstraint,
    ForceIncludeConstraint,
    Objective,
    ObjectiveBoundConstraint,
    Option,
    Problem,
    Score,
)
from frontier.engine.store import Store

mcp = FastMCP("Frontier", instructions="Multi-objective portfolio optimization engine. Use model → solve → explore workflow.")
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
def model(action: str, **kwargs: Any) -> dict:
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
    match action:
        case "create":
            return _model_create(kwargs)
        case "update":
            return _model_update(kwargs)
        case "get":
            return _model_get(kwargs)
        case "list":
            return _model_list()
        case "delete":
            return _model_delete(kwargs)
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
    return {
        "problem_id": p.problem_id,
        "updated_at": p.updated_at.isoformat(),
        "status": {
            "objectives": len(p.objectives),
            "options": len(p.options),
            "scores_complete": round(len(p.scores) / total_possible, 2) if total_possible > 0 else 0.0,
            "has_run": p.run is not None,
        },
    }


def _model_get(params: dict) -> dict:
    pid = params.get("problem_id")
    if not pid:
        return {"error": "problem_id is required."}
    try:
        p = store.load(pid)
    except FileNotFoundError:
        return {"error": f"Problem {pid} not found."}
    return json.loads(p.model_dump_json())


def _model_list() -> dict:
    return {"problems": store.list()}


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
        return {"ready": False, "issues": json.loads(vr.model_dump_json())["issues"]}

    try:
        run = optimizer.optimize(p)
    except Exception as e:
        return {"feasible": False, "error": str(e)}

    if not run.solutions:
        return {
            "feasible": False,
            "binding_constraints": [c.model_dump() for c in p.constraints],
            "suggestions": ["Try relaxing cardinality or objective bound constraints."],
        }

    p.run = run
    store.save(p)

    return {
        "run_id": run.run_id,
        "solutions_found": len(run.solutions),
        "solutions": [json.loads(s.model_dump_json()) for s in run.solutions],
        "quality": json.loads(run.quality.model_dump_json()),
    }


# ─── Tool 3: explore ───


@mcp.tool()
def explore(action: str, problem_id: str, solution_ids: list[int] | None = None) -> dict:
    """Navigate results after solving.

    Actions:
      tradeoffs — Frontier overview: ranges, correlations, extremes, balanced solution.
      compare   — Side-by-side comparison. Requires solution_ids (list of ints).
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
            if not solution_ids:
                return {"error": "solution_ids required for compare."}
            try:
                return explorer.compare_solutions(p, solution_ids)
            except ValueError as e:
                return {"error": str(e)}
        case _:
            return {"error": f"Unknown action: {action}. Use tradeoffs/compare."}


# ─── Entry point ───


def main():
    mcp.run()


if __name__ == "__main__":
    main()

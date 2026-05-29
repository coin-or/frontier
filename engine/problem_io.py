"""Portable problem bundles — save and load problems in the examples format.

A problem persists three ways in Frontier:
  - the live Store (``data/``, UUID-keyed canonical JSON) — full session state;
  - bundled ``examples/`` (tracked, curated) — a read-only showcase;
  - ``saved/`` (gitignored) — the user's own saved problems.

The latter two share one portable on-disk format — the same layout the
examples use — split across up to three files:

  problem.json    definition  — name, domain, context, approach, objectives,
                                constraints, scenarios, reference_points
  scores.json     data        — options, scores, interaction_matrices
  solutions.json  results      — run, runs, scenario_run, curated_solutions,
                                feedback, results_stale (written when solved)

This module is the single (de)serializer between a ``Problem`` and that format.
It is also where the examples' top-level ``scenarios`` list is bridged to the
engine's ``scenario_config``: a naive ``Problem(**problem_json)`` silently drops
scenarios, because the field is named ``scenario_config`` and pydantic ignores
the unknown ``scenarios`` key.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .models import Problem

# Repo root = parent of the engine package dir. Deliberately a single
# parent hop from ``engine/`` — not the three-hop in store.py, which assumes a
# nested ``frontier/engine/`` layout the repo no longer uses.
_REPO_ROOT = Path(__file__).resolve().parent.parent

_PROBLEM_FILE = "problem.json"
_SCORES_FILE = "scores.json"
_SOLUTIONS_FILE = "solutions.json"

# Field partition across the three files. (scores.json — options, scores,
# interaction_matrices — is built inline so empty sections can be omitted.)
_PROBLEM_KEYS = ("name", "domain", "context", "approach", "objectives", "constraints")
_SOLUTION_KEYS = ("run", "runs", "scenario_run", "curated_solutions", "feedback", "results_stale")


def examples_dir() -> Path:
    return Path(os.environ.get("FRONTIER_EXAMPLES_DIR") or _REPO_ROOT / "examples")


def saved_dir() -> Path:
    return Path(os.environ.get("FRONTIER_SAVED_DIR") or _REPO_ROOT / "saved")


_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_name(name: str) -> str:
    """A bundle name must be a bare slug — no path separators or traversal.

    Bundles are addressed by name and resolved under a fixed base dir; without
    this guard a name like ``../../etc`` would escape it. The engine is also
    deployed publicly behind a token, so this is a real read/write vector.
    """
    if not isinstance(name, str) or not _SAFE_NAME.fullmatch(name):
        raise ValueError(
            f"Invalid problem name {name!r}: use letters, digits, '-' or '_' (no path separators)."
        )
    return name


def slugify(text: str) -> str:
    """Filesystem-safe bundle slug from arbitrary text (for default save names).

    Collapses runs of non-alphanumerics to a single underscore — also neutralizes
    path traversal (e.g. ``../x`` -> ``x``), so it doubles as a safety net.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return slug or "problem"


# ─── Problem <-> portable dicts ───


def to_portable(p: Problem) -> tuple[dict, dict, dict | None]:
    """Split a Problem into (problem.json, scores.json, solutions.json | None).

    Mirrors the examples layout: scenarios are emitted as a top-level list
    (unwrapped from ``scenario_config``); empty optional sections are omitted
    to keep files clean. ``solutions`` is ``None`` when the problem has no run.
    """
    full = json.loads(p.model_dump_json())

    problem = {k: full[k] for k in _PROBLEM_KEYS}
    scenarios = (full.get("scenario_config") or {}).get("scenarios") or []
    if scenarios:
        problem["scenarios"] = scenarios
    if full.get("reference_points"):
        problem["reference_points"] = full["reference_points"]

    scores = {"options": full["options"], "scores": full["scores"]}
    if full.get("interaction_matrices"):
        scores["interaction_matrices"] = full["interaction_matrices"]

    solutions = {k: full[k] for k in _SOLUTION_KEYS if full.get(k)}
    # Only a meaningful bundle if there are actual results — a bare
    # results_stale flag with no run is not worth a file.
    if not (solutions.get("run") or solutions.get("scenario_run") or solutions.get("curated_solutions")):
        solutions = None
    return problem, scores, solutions


def from_portable(
    problem: dict,
    scores: dict | None = None,
    solutions: dict | None = None,
    *,
    problem_id: str | None = None,
) -> Problem:
    """Rebuild a Problem from portable dicts — faithful, including scenarios.

    Accepts either the examples' top-level ``scenarios`` list or an explicit
    ``scenario_config``. A scenarios list is wrapped with ``enabled=True`` so
    the loaded scenarios are active for ``solve/run_scenarios`` (the engine
    skips disabled scenario configs). A fresh ``problem_id`` is minted unless
    one is supplied.
    """
    data = {**problem, **(scores or {})}

    if "scenario_config" not in data:
        scenarios = data.pop("scenarios", None)
        if scenarios:
            data["scenario_config"] = {"enabled": True, "scenarios": scenarios}
    else:
        data.pop("scenarios", None)

    if solutions:
        data.update({k: v for k, v in solutions.items() if k in _SOLUTION_KEYS})

    if problem_id:
        data["problem_id"] = problem_id
    else:
        data.pop("problem_id", None)  # let the model mint a fresh id

    return Problem(**data)


# ─── File bundles ───


def write_bundle(p: Problem, dest: Path) -> dict:
    """Write problem.json + scores.json (+ solutions.json) into ``dest``."""
    dest.mkdir(parents=True, exist_ok=True)
    problem, scores, solutions = to_portable(p)
    written: dict[str, str] = {}
    (dest / _PROBLEM_FILE).write_text(json.dumps(problem, indent=2))
    written["problem"] = str(dest / _PROBLEM_FILE)
    (dest / _SCORES_FILE).write_text(json.dumps(scores, indent=2))
    written["scores"] = str(dest / _SCORES_FILE)
    if solutions is not None:
        (dest / _SOLUTIONS_FILE).write_text(json.dumps(solutions, indent=2))
        written["solutions"] = str(dest / _SOLUTIONS_FILE)
    return written


def read_bundle(src: Path, *, problem_id: str | None = None) -> Problem:
    """Read a bundle dir (problem.json [+ scores.json] [+ solutions.json])."""
    problem_file = src / _PROBLEM_FILE
    if not problem_file.exists():
        raise FileNotFoundError(f"No {_PROBLEM_FILE} in {src}")
    problem = json.loads(problem_file.read_text())
    scores_file = src / _SCORES_FILE
    scores = json.loads(scores_file.read_text()) if scores_file.exists() else {}
    solutions_file = src / _SOLUTIONS_FILE
    solutions = json.loads(solutions_file.read_text()) if solutions_file.exists() else None
    return from_portable(problem, scores, solutions, problem_id=problem_id)


def resolve_source(name: str) -> Path:
    """Resolve a bundle name to a dir, searching saved/ first, then examples/.

    A user's saved problem shadows a bundled example of the same name.
    """
    safe = _safe_name(name)
    for base in (saved_dir(), examples_dir()):
        candidate = base / safe
        if (candidate / _PROBLEM_FILE).exists():
            return candidate
    raise FileNotFoundError(
        f"No saved problem or example named {name!r} "
        f"(looked in {saved_dir()} and {examples_dir()})."
    )


def save_problem(p: Problem, name: str) -> dict:
    """Save a problem under saved/<name>/ in the portable format."""
    dest = saved_dir() / _safe_name(name)
    written = write_bundle(p, dest)
    return {"name": name, "dir": str(dest), "files": written}


def load_problem(source: str, *, problem_id: str | None = None) -> Problem:
    """Load a problem by name from saved/ or examples/."""
    return read_bundle(resolve_source(source), problem_id=problem_id)


def list_available() -> dict:
    """Bundle names available to load, split by source — for discovery."""

    def _names(base: Path) -> list[str]:
        if not base.exists():
            return []
        return sorted(
            d.name for d in base.iterdir()
            if d.is_dir() and (d / _PROBLEM_FILE).exists()
        )

    return {"saved": _names(saved_dir()), "examples": _names(examples_dir())}

"""JSON file store for problems. One file per problem in ./data/."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Problem

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class Store:
    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, problem_id: str) -> Path:
        return self.data_dir / f"{problem_id}.json"

    def save(self, problem: Problem) -> None:
        path = self._path(problem.problem_id)
        path.write_text(problem.model_dump_json(indent=2))

    def load(self, problem_id: str) -> Problem:
        path = self._path(problem_id)
        if not path.exists():
            raise FileNotFoundError(f"Problem {problem_id} not found")
        return Problem.model_validate_json(path.read_text())

    def list(self) -> list[dict]:
        problems = []
        for path in sorted(self.data_dir.glob("*.json")):
            try:
                p = Problem.model_validate_json(path.read_text())
                problems.append({
                    "problem_id": p.problem_id,
                    "name": p.name,
                    "domain": p.domain,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                    "status": {
                        "objectives": len(p.objectives),
                        "options": len(p.options),
                        "scores_complete": _scores_completeness(p),
                        "has_run": p.run is not None,
                        "results_stale": p.results_stale,
                        "total_runs": len(p.runs) + (1 if p.run else 0),
                    },
                })
            except Exception:
                continue
        return problems

    def delete(self, problem_id: str) -> None:
        path = self._path(problem_id)
        if not path.exists():
            raise FileNotFoundError(f"Problem {problem_id} not found")
        path.unlink()

    def exists(self, problem_id: str) -> bool:
        return self._path(problem_id).exists()


def _scores_completeness(p: Problem) -> float:
    total = len(p.objectives) * len(p.options)
    if total == 0:
        return 0.0
    return len(p.scores) / total

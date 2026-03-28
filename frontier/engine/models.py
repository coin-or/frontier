"""Pydantic data models for Frontier Phase 0 MVP."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# --- Enums ---


class Direction(str, Enum):
    maximize = "maximize"
    minimize = "minimize"


class ConstraintType(str, Enum):
    cardinality = "cardinality"
    force_include = "force_include"
    force_exclude = "force_exclude"
    objective_bound = "objective_bound"


class Aggregation(str, Enum):
    sum = "sum"
    avg = "avg"
    min = "min"
    max = "max"


class Approach(str, Enum):
    binary = "binary"
    proportional = "proportional"


class BoundOperator(str, Enum):
    min = "min"
    max = "max"


# --- Core models ---


class Objective(BaseModel):
    name: str
    direction: Direction
    unit: str = ""
    aggregation: Aggregation = Aggregation.sum


class Option(BaseModel):
    name: str
    description: str = ""


class Score(BaseModel):
    option: str
    objective: str
    value: float


# --- Constraints ---


class CardinalityConstraint(BaseModel):
    type: Literal["cardinality"] = "cardinality"
    min: int
    max: int


class ForceIncludeConstraint(BaseModel):
    type: Literal["force_include"] = "force_include"
    option: str


class ForceExcludeConstraint(BaseModel):
    type: Literal["force_exclude"] = "force_exclude"
    option: str


class ObjectiveBoundConstraint(BaseModel):
    type: Literal["objective_bound"] = "objective_bound"
    objective: str
    operator: BoundOperator
    value: float


Constraint = (
    CardinalityConstraint
    | ForceIncludeConstraint
    | ForceExcludeConstraint
    | ObjectiveBoundConstraint
)


# --- Run / Solution ---


class Solution(BaseModel):
    solution_id: int
    selected_options: list[str]
    objective_values: dict[str, float]
    allocations: dict[str, int] | None = None  # proportional mode: option → percentage (0-100)


class QualityIndicators(BaseModel):
    hypervolume_normalized: float | None = None
    spacing_cv: float | None = None


class Run(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    solutions: list[Solution] = []
    quality: QualityIndicators = QualityIndicators()
    constraints_snapshot: list[dict] = []


# --- Feedback ---


class Feedback(BaseModel):
    solution_id: int | None = None
    rating: int | None = None  # 1-5
    notes: str = ""
    stage: str = ""  # "exploration", "decision", "post-refinement"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Problem ---


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Problem(BaseModel):
    problem_id: str = Field(default_factory=_new_uuid)
    name: str = ""
    domain: str = ""
    context: str = ""
    approach: Approach = Approach.binary
    objectives: list[Objective] = []
    options: list[Option] = []
    scores: list[Score] = []
    constraints: list[Constraint] = []
    run: Run | None = None
    runs: list[Run] = []
    results_stale: bool = False
    feedback: list[Feedback] = []
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# --- Validation result ---


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    message: str


class ValidationResult(BaseModel):
    ready: bool
    issues: list[ValidationIssue] = []
    missing_scores: list[dict[str, str]] = []

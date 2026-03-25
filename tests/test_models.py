"""Tests for Frontier engine models — round-trip serialization."""

from frontier.engine.models import (
    CardinalityConstraint,
    ForceExcludeConstraint,
    ForceIncludeConstraint,
    Objective,
    ObjectiveBoundConstraint,
    Option,
    Problem,
    Run,
    Score,
    Solution,
)


def test_problem_defaults():
    p = Problem()
    assert p.problem_id
    assert p.name == ""
    assert p.objectives == []
    assert p.run is None


def test_problem_round_trip():
    p = Problem(
        name="Test",
        objectives=[Objective(name="Rev", direction="maximize", unit="$")],
        options=[Option(name="A"), Option(name="B"), Option(name="C")],
        scores=[Score(option="A", objective="Rev", value=5.0)],
        constraints=[CardinalityConstraint(min=1, max=2)],
    )
    data = p.model_dump_json()
    p2 = Problem.model_validate_json(data)
    assert p2.name == "Test"
    assert len(p2.objectives) == 1
    assert len(p2.options) == 3
    assert len(p2.scores) == 1
    assert p2.constraints[0].type == "cardinality"
    assert p2.constraints[0].min == 1


def test_constraint_types_serialize():
    constraints = [
        CardinalityConstraint(min=2, max=5),
        ForceIncludeConstraint(option="SSO"),
        ForceExcludeConstraint(option="Mobile"),
        ObjectiveBoundConstraint(objective="Effort", operator="max", value=40),
    ]
    p = Problem(constraints=constraints)
    data = p.model_dump_json()
    p2 = Problem.model_validate_json(data)
    assert len(p2.constraints) == 4
    assert p2.constraints[0].type == "cardinality"
    assert p2.constraints[1].type == "force_include"
    assert p2.constraints[2].type == "force_exclude"
    assert p2.constraints[3].type == "objective_bound"


def test_run_with_solutions():
    run = Run(solutions=[
        Solution(solution_id=0, selected_options=["A", "B"], objective_values={"Rev": 10.0}),
        Solution(solution_id=1, selected_options=["A", "C"], objective_values={"Rev": 8.0}),
    ])
    data = run.model_dump_json()
    run2 = Run.model_validate_json(data)
    assert len(run2.solutions) == 2
    assert run2.solutions[0].selected_options == ["A", "B"]

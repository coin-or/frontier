"""Tests for MCP server tool handlers — model, solve, explore."""

import tempfile

import pytest

from frontier.engine.store import Store

# We test the internal handler functions directly, not via MCP protocol.
# This validates the logic without needing an MCP client.
import frontier.mcp_server.server as srv


@pytest.fixture(autouse=True)
def tmp_store(monkeypatch):
    """Use a temp directory for all store operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        s = Store(tmpdir)
        monkeypatch.setattr(srv, "store", s)
        yield s


# ─── model tool ───


class TestModelCreate:
    def test_create_returns_problem_id(self):
        result = srv.model(action="create", name="Test", domain="product")
        assert "problem_id" in result
        assert result["name"] == "Test"
        assert result["domain"] == "product"

    def test_create_defaults(self):
        result = srv.model(action="create")
        assert "problem_id" in result
        assert result["name"] == ""


class TestModelUpdate:
    def test_update_metadata(self):
        created = srv.model(action="create", name="Old")
        pid = created["problem_id"]
        result = srv.model(action="update", problem_id=pid, name="New")
        assert result["problem_id"] == pid

    def test_update_objectives(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        result = srv.model(action="update", problem_id=pid, objectives=[
            {"name": "Revenue", "direction": "maximize", "unit": "$"},
            {"name": "Effort", "direction": "minimize", "unit": "weeks"},
        ])
        assert result["status"]["objectives"] == 2

    def test_update_scores_merge(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[
                      {"name": "Rev", "direction": "maximize"},
                      {"name": "Eff", "direction": "minimize"},
                  ],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}])

        # First batch
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 5},
        ])
        # Second batch — should merge, not replace
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "B", "objective": "Rev", "value": 7},
        ])
        problem = srv.model(action="get", problem_id=pid)
        assert len(problem["scores"]) == 2

    def test_update_scores_upsert(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}])
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 5},
        ])
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 99},
        ])
        problem = srv.model(action="get", problem_id=pid)
        rev_scores = [s for s in problem["scores"] if s["option"] == "A" and s["objective"] == "Rev"]
        assert len(rev_scores) == 1
        assert rev_scores[0]["value"] == 99

    def test_update_clears_run(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        # Build a solvable problem
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
                  scores=[
                      {"option": "A", "objective": "Rev", "value": 8},
                      {"option": "A", "objective": "Eff", "value": 5},
                      {"option": "B", "objective": "Rev", "value": 6},
                      {"option": "B", "objective": "Eff", "value": 3},
                      {"option": "C", "objective": "Rev", "value": 9},
                      {"option": "C", "objective": "Eff", "value": 7},
                  ],
                  constraints=[{"type": "cardinality", "min": 1, "max": 2}])
        srv.solve(action="run", problem_id=pid)
        p = srv.model(action="get", problem_id=pid)
        assert p["run"] is not None

        # Updating scores should clear the run
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 1},
        ])
        p = srv.model(action="get", problem_id=pid)
        assert p["run"] is None

    def test_cascading_removes_scores_on_objective_removal(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
                  scores=[
                      {"option": "A", "objective": "Rev", "value": 5},
                      {"option": "A", "objective": "Eff", "value": 3},
                  ])
        # Remove "Eff" objective
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Impact", "direction": "maximize"}])
        p = srv.model(action="get", problem_id=pid)
        # Only Rev score should remain
        assert all(s["objective"] != "Eff" for s in p["scores"])

    def test_cascading_removes_constraints_on_option_removal(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
                  constraints=[{"type": "force_include", "option": "A"}])
        # Remove option A
        srv.model(action="update", problem_id=pid,
                  options=[{"name": "B"}, {"name": "C"}, {"name": "D"}])
        p = srv.model(action="get", problem_id=pid)
        assert len(p["constraints"]) == 0

    def test_update_nonexistent_problem(self):
        result = srv.model(action="update", problem_id="nonexistent")
        assert "error" in result

    def test_update_missing_problem_id(self):
        result = srv.model(action="update")
        assert "error" in result

    def test_score_references_invalid_option(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}])
        result = srv.model(action="update", problem_id=pid, scores=[
            {"option": "NONEXISTENT", "objective": "Rev", "value": 5},
        ])
        assert "error" in result

    def test_score_references_invalid_objective(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}])
        result = srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "NONEXISTENT", "value": 5},
        ])
        assert "error" in result


class TestModelList:
    def test_list_empty(self):
        result = srv.model(action="list")
        assert result == []

    def test_list_returns_bare_array(self):
        srv.model(action="create", name="One")
        srv.model(action="create", name="Two")
        result = srv.model(action="list")
        assert isinstance(result, list)
        assert len(result) == 2


class TestModelDelete:
    def test_delete(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        result = srv.model(action="delete", problem_id=pid)
        assert result["deleted"] == pid

    def test_delete_nonexistent(self):
        result = srv.model(action="delete", problem_id="nonexistent")
        assert "error" in result


class TestModelGet:
    def test_get(self):
        created = srv.model(action="create", name="Fetch Me")
        pid = created["problem_id"]
        result = srv.model(action="get", problem_id=pid)
        assert result["name"] == "Fetch Me"


class TestUnknownAction:
    def test_unknown_model_action(self):
        result = srv.model(action="foobar")
        assert "error" in result


# ─── solve tool ───


def _build_solvable_problem():
    created = srv.model(action="create")
    pid = created["problem_id"]
    srv.model(action="update", problem_id=pid,
              objectives=[{"name": "Rev", "direction": "maximize"},
                          {"name": "Eff", "direction": "minimize"}],
              options=[{"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"}],
              scores=[
                  {"option": "A", "objective": "Rev", "value": 8},
                  {"option": "A", "objective": "Eff", "value": 5},
                  {"option": "B", "objective": "Rev", "value": 6},
                  {"option": "B", "objective": "Eff", "value": 3},
                  {"option": "C", "objective": "Rev", "value": 9},
                  {"option": "C", "objective": "Eff", "value": 7},
                  {"option": "D", "objective": "Rev", "value": 4},
                  {"option": "D", "objective": "Eff", "value": 2},
              ],
              constraints=[{"type": "cardinality", "min": 2, "max": 3}])
    return pid


class TestSolveValidate:
    def test_validate_ready(self):
        pid = _build_solvable_problem()
        result = srv.solve(action="validate", problem_id=pid)
        assert result["ready"] is True

    def test_validate_not_ready(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        result = srv.solve(action="validate", problem_id=pid)
        assert result["ready"] is False

    def test_validate_nonexistent(self):
        result = srv.solve(action="validate", problem_id="nonexistent")
        assert "error" in result


class TestSolveRun:
    def test_run_success(self):
        pid = _build_solvable_problem()
        result = srv.solve(action="run", problem_id=pid)
        assert "run_id" in result
        assert result["solutions_found"] > 0
        assert len(result["solutions"]) > 0
        assert "quality" in result

    def test_run_validation_failure_includes_missing_scores(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}])
        result = srv.solve(action="run", problem_id=pid)
        assert result["ready"] is False
        assert "missing_scores" in result
        assert len(result["missing_scores"]) == 6  # 3 options * 2 objectives


# ─── explore tool ───


class TestExploreTradeoffs:
    def test_tradeoffs(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="tradeoffs", problem_id=pid)
        assert "total_solutions" in result
        assert "balanced_solution" in result

    def test_tradeoffs_no_run(self):
        created = srv.model(action="create")
        result = srv.explore(action="tradeoffs", problem_id=created["problem_id"])
        assert "error" in result


class TestExploreCompare:
    def test_compare_requires_min_2(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="compare", problem_id=pid, solution_ids=[0])
        assert "error" in result
        assert "at least 2" in result["error"]

    def test_compare_success(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="compare", problem_id=pid, solution_ids=[0, 1])
        assert "shared_options" in result


class TestExploreSolutions:
    def test_solutions_listing(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="solutions", problem_id=pid)
        assert "total_solutions" in result
        assert "solutions" in result

    def test_single_solution(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="solution", problem_id=pid, solution_id=0)
        assert result["solution_id"] == 0

    def test_single_solution_missing_id(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="solution", problem_id=pid)
        assert "error" in result

    def test_single_solution_not_found(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="solution", problem_id=pid, solution_id=9999)
        assert "error" in result


class TestUnknownActions:
    def test_unknown_solve_action(self):
        pid = _build_solvable_problem()
        result = srv.solve(action="foobar", problem_id=pid)
        assert "error" in result

    def test_unknown_explore_action(self):
        pid = _build_solvable_problem()
        result = srv.explore(action="foobar", problem_id=pid)
        assert "error" in result

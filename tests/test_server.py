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
        # Clear injection tracking between tests
        srv._injected_skills.clear()
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

        # Updating scores should mark results stale (not clear the run)
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 1},
        ])
        p = srv.model(action="get", problem_id=pid)
        assert p["run"] is not None  # run preserved for comparison
        assert p["results_stale"] is True

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
        result = srv.explore(action="compare", problem_id=pid, solution_ids=[1])
        assert "error" in result
        assert "at least 2" in result["error"]

    def test_compare_success(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="compare", problem_id=pid, solution_ids=[1, 2])
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
        result = srv.explore(action="solution", problem_id=pid, solution_id=1)
        assert result["solution_id"] == 1

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


class TestRunHistory:
    def test_structural_change_sets_stale(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        p = srv.model(action="get", problem_id=pid)
        assert p["results_stale"] is False

        # Structural change sets stale
        result = srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 1},
        ])
        assert result["status"]["results_stale"] is True
        p = srv.model(action="get", problem_id=pid)
        assert p["results_stale"] is True
        assert p["run"] is not None  # run preserved

    def test_solve_clears_stale(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 1},
        ])
        p = srv.model(action="get", problem_id=pid)
        assert p["results_stale"] is True

        # Re-solve clears stale
        srv.solve(action="run", problem_id=pid)
        p = srv.model(action="get", problem_id=pid)
        assert p["results_stale"] is False

    def test_solve_archives_previous_run(self):
        pid = _build_solvable_problem()
        result1 = srv.solve(action="run", problem_id=pid)
        run1_id = result1["run_id"]

        # Second solve
        result2 = srv.solve(action="run", problem_id=pid)
        run2_id = result2["run_id"]

        p = srv.model(action="get", problem_id=pid)
        assert p["run"]["run_id"] == run2_id
        assert len(p["runs"]) == 1
        assert p["runs"][0]["run_id"] == run1_id

    def test_run_has_constraints_snapshot(self):
        pid = _build_solvable_problem()
        result = srv.solve(action="run", problem_id=pid)
        p = srv.model(action="get", problem_id=pid)
        assert len(p["run"]["constraints_snapshot"]) > 0
        assert p["run"]["constraints_snapshot"][0]["type"] == "cardinality"

    def test_multiple_runs_accumulate(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.solve(action="run", problem_id=pid)
        srv.solve(action="run", problem_id=pid)
        p = srv.model(action="get", problem_id=pid)
        assert len(p["runs"]) == 2  # 2 archived + 1 current
        assert p["run"] is not None

    def test_status_shows_total_runs(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.solve(action="run", problem_id=pid)
        result = srv.model(action="update", problem_id=pid, name="Updated")
        assert result["status"]["total_runs"] == 2


class TestReferencePoints:
    def test_set_reference_points(self):
        pid = _build_solvable_problem()
        result = srv.model(action="update", problem_id=pid, reference_points=[
            {"type": "baseline", "name": "Current", "objective_values": {"Rev": 10, "Eff": 8}},
            {"type": "aspirational", "name": "Target", "objective_values": {"Rev": 20, "Eff": 3}},
        ])
        p = srv.model(action="get", problem_id=pid)
        assert len(p["reference_points"]) == 2
        assert p["reference_points"][0]["type"] == "baseline"

    def test_reference_in_tradeoffs(self):
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, reference_points=[
            {"type": "baseline", "name": "Current", "objective_values": {"Rev": 10, "Eff": 8}},
        ])
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="tradeoffs", problem_id=pid)
        assert "balanced_vs_references" in result
        assert len(result["balanced_vs_references"]) == 1
        assert result["balanced_vs_references"][0]["type"] == "baseline"

    def test_reference_in_solution(self):
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, reference_points=[
            {"type": "aspirational", "name": "Goal", "objective_values": {"Rev": 25, "Eff": 2}},
        ])
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="solution", problem_id=pid, solution_id=1)
        assert "vs_references" in result
        ref = result["vs_references"][0]
        assert "Rev" in ref["objectives"]
        assert "better" in ref["objectives"]["Rev"]

    def test_no_reference_no_field(self):
        """Without reference points, no extra fields in output."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="tradeoffs", problem_id=pid)
        assert "balanced_vs_references" not in result


class TestCompareRuns:
    def test_compare_two_runs(self):
        pid = _build_solvable_problem()
        r1 = srv.solve(action="run", problem_id=pid)
        r2 = srv.solve(action="run", problem_id=pid)
        result = srv.explore(
            action="compare_runs", problem_id=pid,
            run_ids=[r1["run_id"], r2["run_id"]],
        )
        assert "runs_compared" in result
        assert len(result["runs_compared"]) == 2
        assert "frontier_diffs" in result
        assert "option_coverage" in result

    def test_compare_runs_criteria_diff(self):
        pid = _build_solvable_problem()
        r1 = srv.solve(action="run", problem_id=pid)
        # Add a constraint and re-solve
        srv.model(action="update", problem_id=pid, constraints=[
            {"type": "cardinality", "min": 2, "max": 3},
            {"type": "force_include", "option": "A"},
        ])
        r2 = srv.solve(action="run", problem_id=pid)
        result = srv.explore(
            action="compare_runs", problem_id=pid,
            run_ids=[r1["run_id"], r2["run_id"]],
        )
        diffs = result["criteria_diffs"]
        assert len(diffs) == 1
        assert len(diffs[0]["added"]) > 0  # force_include was added

    def test_compare_runs_invalid_id(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(
            action="compare_runs", problem_id=pid,
            run_ids=["nonexistent1", "nonexistent2"],
        )
        assert "error" in result

    def test_compare_runs_needs_two(self):
        pid = _build_solvable_problem()
        r1 = srv.solve(action="run", problem_id=pid)
        result = srv.explore(
            action="compare_runs", problem_id=pid,
            run_ids=[r1["run_id"]],
        )
        assert "error" in result


class TestScenarios:
    def test_set_scenario_config(self):
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "Base", "probability": 0.6, "score_overrides": []},
                {"name": "Growth", "probability": 0.4, "score_overrides": [
                    {"option": "A", "objective": "Rev", "value": 20},
                ]},
            ],
        })
        p = srv.model(action="get", problem_id=pid)
        assert p["scenario_config"]["enabled"] is True
        assert len(p["scenario_config"]["scenarios"]) == 2

    def test_run_scenarios(self):
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "Base", "probability": 0.5, "score_overrides": []},
                {"name": "Alt", "probability": 0.5, "score_overrides": [
                    {"option": "A", "objective": "Rev", "value": 1},
                    {"option": "C", "objective": "Rev", "value": 20},
                ]},
            ],
        })
        result = srv.solve(action="run_scenarios", problem_id=pid)
        assert "error" not in result
        assert result["scenarios_optimized"] == 2
        assert "Base" in result["results"]
        assert "Alt" in result["results"]
        assert result["results"]["Base"]["solutions_found"] > 0

    def test_scenario_results(self):
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "Base", "probability": 0.6, "score_overrides": []},
                {"name": "Growth", "probability": 0.4, "score_overrides": [
                    {"option": "A", "objective": "Rev", "value": 50},
                ]},
            ],
        })
        srv.solve(action="run_scenarios", problem_id=pid)
        result = srv.explore(action="scenario_results", problem_id=pid)
        assert "robust_options" in result
        assert "scenario_specific" in result
        assert "expected_values" in result
        assert "per_scenario" in result
        assert "visualization" in result

    def test_scenario_results_without_run(self):
        pid = _build_solvable_problem()
        result = srv.explore(action="scenario_results", problem_id=pid)
        assert "error" in result

    def test_scenarios_without_probabilities(self):
        """Scenarios should run fine without probabilities — each is an independent solve."""
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "A"},
                {"name": "B"},
            ],
        })
        result = srv.solve(action="run_scenarios", problem_id=pid)
        assert "error" not in result
        assert result["scenarios_optimized"] == 2

    def test_scenarios_with_score_adjustments(self):
        """Score adjustments (multiply/add) should modify scores per scenario."""
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "Base"},
                {"name": "Downside", "score_adjustments": [
                    {"objective": "Revenue", "multiply": 0.8},
                ]},
            ],
        })
        result = srv.solve(action="run_scenarios", problem_id=pid)
        assert "error" not in result
        assert result["scenarios_optimized"] == 2

    def test_scenarios_with_constraint_overrides(self):
        """Constraint overrides should replace base constraints for that scenario."""
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "Base"},
                {"name": "Constrained", "constraint_overrides": [
                    {"type": "cardinality", "min": 1, "max": 2},
                    {"type": "force_include", "option": "A"},
                ]},
            ],
        })
        result = srv.solve(action="run_scenarios", problem_id=pid)
        assert "error" not in result
        assert result["scenarios_optimized"] == 2


class TestCuration:
    def test_curate_solution(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(
            action="curate", problem_id=pid, solution_id=1, custom_name="Pick A",
        )
        assert result.get("curated") is True
        assert result["custom_name"] == "Pick A"
        assert result["total_curated"] == 1

    def test_curate_duplicate(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="Pick A")
        result = srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="Dup")
        assert "error" in result  # duplicate

    def test_list_curated(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="First")
        srv.explore(action="curate", problem_id=pid, solution_id=2, custom_name="Second")
        result = srv.explore(action="curated", problem_id=pid)
        assert result["total_curated"] == 2
        assert all(c["in_current_frontier"] for c in result["curated_solutions"])

    def test_uncurate(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        curate_result = srv.explore(
            action="curate", problem_id=pid, solution_id=1, custom_name="Pick A",
        )
        sig = curate_result["content_signature"]
        result = srv.explore(action="uncurate", problem_id=pid, content_signature=sig)
        assert result["total_curated"] == 0

    def test_rename_curated(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        curate_result = srv.explore(
            action="curate", problem_id=pid, solution_id=1, custom_name="Old",
        )
        sig = curate_result["content_signature"]
        result = srv.explore(
            action="rename_curated", problem_id=pid,
            content_signature=sig, custom_name="New Name",
        )
        assert result["custom_name"] == "New Name"

    def test_compare_curated(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        r1 = srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="A")
        r2 = srv.explore(action="curate", problem_id=pid, solution_id=2, custom_name="B")
        result = srv.explore(
            action="compare_curated", problem_id=pid,
            signatures=[r1["content_signature"], r2["content_signature"]],
        )
        assert "shared_options" in result
        assert "differentiating_options" in result
        assert len(result["solutions"]) == 2
        assert result["solutions"][0]["custom_name"] == "A"

    def test_curated_survives_resolve(self):
        """Curated solutions persist across runs and track survival."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        r = srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="Survivor")
        sig = r["content_signature"]

        # Re-solve (same problem, same constraints — solution should survive)
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="curated", problem_id=pid)
        assert result["total_curated"] == 1
        assert result["curated_solutions"][0]["content_signature"] == sig

    def test_content_signatures_on_solutions(self):
        """Solutions have content_signature field after solving."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="solutions", problem_id=pid)
        for sol in result["solutions"]:
            assert sol["content_signature"] != ""
            assert len(sol["content_signature"]) == 12


class TestFeedbackLoop:
    """Feedback links to content_signature and attaches to curated solutions."""

    def test_feedback_computes_signature_from_solution_id(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(
            action="feedback", problem_id=pid, solution_id=1, rating=4, notes="Looks good",
        )
        assert result["recorded"] is True
        assert result["content_signature"] is not None
        assert len(result["content_signature"]) == 12

    def test_feedback_without_solution_has_no_signature(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(
            action="feedback", problem_id=pid, rating=3, notes="General thoughts",
        )
        assert result["recorded"] is True
        assert result["content_signature"] is None

    def test_feedback_attaches_to_curated_solution(self):
        """Feedback on a curated solution gets attached to its feedback list."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        # Curate first
        curate_r = srv.explore(
            action="curate", problem_id=pid, solution_id=1, custom_name="Fav",
        )
        sig = curate_r["content_signature"]
        # Then give feedback on same solution
        srv.explore(
            action="feedback", problem_id=pid, solution_id=1, rating=5, notes="Love it",
        )
        # Check curated solution has the feedback
        curated = srv.explore(action="curated", problem_id=pid)
        cs = curated["curated_solutions"][0]
        assert cs["feedback_count"] == 1
        assert cs["avg_rating"] == 5.0

    def test_existing_feedback_pulled_into_curation(self):
        """If feedback exists before curation, it's pulled in when curating."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        # Give feedback first
        srv.explore(
            action="feedback", problem_id=pid, solution_id=1, rating=4, notes="Promising",
        )
        # Then curate same solution
        srv.explore(
            action="curate", problem_id=pid, solution_id=1, custom_name="Promising Pick",
        )
        # Check feedback was pulled in
        curated = srv.explore(action="curated", problem_id=pid)
        cs = curated["curated_solutions"][0]
        assert cs["feedback_count"] == 1
        assert cs["avg_rating"] == 4.0

    def test_feedback_survives_rerun(self):
        """Feedback persists across re-optimization via content_signature."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        # Curate and give feedback
        curate_r = srv.explore(
            action="curate", problem_id=pid, solution_id=1, custom_name="Keeper",
        )
        sig = curate_r["content_signature"]
        srv.explore(
            action="feedback", problem_id=pid, solution_id=1, rating=5, notes="Best option",
        )
        # Re-solve
        srv.solve(action="run", problem_id=pid)
        # Curated solution still has its feedback
        curated = srv.explore(action="curated", problem_id=pid)
        cs = next(c for c in curated["curated_solutions"] if c["content_signature"] == sig)
        assert cs["feedback_count"] == 1
        assert cs["avg_rating"] == 5.0

    def test_feedback_by_content_signature_directly(self):
        """Feedback can be given via content_signature without solution_id."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        curate_r = srv.explore(
            action="curate", problem_id=pid, solution_id=1, custom_name="Direct",
        )
        sig = curate_r["content_signature"]
        # Give feedback by signature
        result = srv.explore(
            action="feedback", problem_id=pid, content_signature=sig,
            rating=3, notes="Reconsidering",
        )
        assert result["content_signature"] == sig
        curated = srv.explore(action="curated", problem_id=pid)
        assert curated["curated_solutions"][0]["feedback_count"] == 1

    def test_multiple_feedback_accumulates(self):
        """Multiple feedback entries accumulate on a curated solution."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        curate_r = srv.explore(
            action="curate", problem_id=pid, solution_id=1, custom_name="Multi",
        )
        sig = curate_r["content_signature"]
        srv.explore(action="feedback", problem_id=pid, solution_id=1, rating=3, stage="exploration")
        srv.explore(action="feedback", problem_id=pid, content_signature=sig, rating=5, stage="decision")
        curated = srv.explore(action="curated", problem_id=pid)
        cs = curated["curated_solutions"][0]
        assert cs["feedback_count"] == 2
        assert cs["avg_rating"] == 4.0  # (3+5)/2


class TestUnknownActions:
    def test_unknown_solve_action(self):
        pid = _build_solvable_problem()
        result = srv.solve(action="foobar", problem_id=pid)
        assert "error" in result

    def test_unknown_explore_action(self):
        pid = _build_solvable_problem()
        result = srv.explore(action="foobar", problem_id=pid)
        assert "error" in result


class TestMarginalAnalysis:
    def test_marginal_analysis_returns_pairs(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="marginal_analysis", problem_id=pid)
        assert "pairs" in result

    def test_marginal_analysis_no_run(self):
        created = srv.model(action="create")
        result = srv.explore(action="marginal_analysis", problem_id=created["problem_id"])
        assert "error" in result

    def test_marginal_analysis_has_rates(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="marginal_analysis", problem_id=pid)
        if result["pairs"]:
            pair = result["pairs"][0]
            assert "objectives" in pair
            assert "steepest_transitions" in pair  # summary mode (default)
            assert "visualization" in pair
        # detail=True returns full rates
        detail_result = srv.explore(action="marginal_analysis", problem_id=pid, detail=True)
        if detail_result["pairs"]:
            pair = detail_result["pairs"][0]
            assert "rates" in pair


# ─── Quadratic aggregation ───


class TestQuadraticAggregation:
    """Test quadratic (interaction matrix) aggregation end-to-end."""

    def test_quadratic_solve_produces_solutions(self):
        """Proportional solve with a quadratic objective uses the interaction matrix."""
        pid = srv.model(action="create", name="Quad Test", approach="proportional")["problem_id"]
        srv.model(action="update", problem_id=pid, objectives=[
            {"name": "Return", "direction": "maximize"},
            {"name": "Risk", "direction": "minimize", "aggregation": "quadratic"},
        ], options=["A", "B", "C"])
        # Scores: A high return/high risk, B medium, C low return/low risk
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Return", "value": 20},
            {"option": "B", "objective": "Return", "value": 10},
            {"option": "C", "objective": "Return", "value": 5},
            # Individual risk scores (for display/marginal analysis)
            {"option": "A", "objective": "Risk", "value": 25},
            {"option": "B", "objective": "Risk", "value": 15},
            {"option": "C", "objective": "Risk", "value": 5},
        ])
        # Covariance matrix: A and C are negatively correlated (diversification benefit)
        cov = {
            "A": {"A": 625, "B": 200, "C": -100},  # var(A)=25^2=625
            "B": {"A": 200, "B": 225, "C": 50},     # var(B)=15^2=225
            "C": {"A": -100, "B": 50, "C": 25},     # var(C)=5^2=25
        }
        srv.model(action="update", problem_id=pid, interaction_matrices=[
            {"objective": "Risk", "entries": cov},
        ])
        result = srv.solve(action="run", problem_id=pid)
        assert "error" not in result
        assert len(result["solutions"]) >= 2

    def test_quadratic_validation_missing_matrix(self):
        """Quadratic objective without interaction matrix fails validation."""
        pid = srv.model(action="create", name="Missing Matrix", approach="proportional")["problem_id"]
        srv.model(action="update", problem_id=pid, objectives=[
            {"name": "Return", "direction": "maximize"},
            {"name": "Risk", "direction": "minimize", "aggregation": "quadratic"},
        ], options=["A", "B", "C"])
        srv.model(action="update", problem_id=pid, scores=[
            {"option": o, "objective": obj, "value": 10}
            for o in ["A", "B", "C"] for obj in ["Return", "Risk"]
        ])
        result = srv.solve(action="validate", problem_id=pid)
        assert result["ready"] is False
        assert any("interaction matrix" in i["message"] for i in result["issues"])

    def test_quadratic_diversification_benefit(self):
        """With negative correlation, mixed portfolio should have lower risk than concentrated."""
        pid = srv.model(action="create", name="Diversification", approach="proportional")["problem_id"]
        srv.model(action="update", problem_id=pid, objectives=[
            {"name": "Return", "direction": "maximize"},
            {"name": "Risk", "direction": "minimize", "aggregation": "quadratic"},
        ], options=["Stock", "Bond", "Cash"])
        srv.model(action="update", problem_id=pid, scores=[
            {"option": "Stock", "objective": "Return", "value": 15},
            {"option": "Bond", "objective": "Return", "value": 5},
            {"option": "Cash", "objective": "Return", "value": 2},
            {"option": "Stock", "objective": "Risk", "value": 20},
            {"option": "Bond", "objective": "Risk", "value": 8},
            {"option": "Cash", "objective": "Risk", "value": 1},
        ])
        # Covariance: stock-bond negatively correlated
        cov = {
            "Stock": {"Stock": 400, "Bond": -80, "Cash": 0},
            "Bond": {"Stock": -80, "Bond": 64, "Cash": 0},
            "Cash": {"Stock": 0, "Bond": 0, "Cash": 1},
        }
        srv.model(action="update", problem_id=pid, interaction_matrices=[
            {"objective": "Risk", "entries": cov},
        ], constraints=[{"type": "cardinality", "min": 2, "max": 3}])
        result = srv.solve(action="run", problem_id=pid)
        assert "error" not in result
        # Get solutions and verify some have Risk below individual stock risk (20)
        solutions = srv.explore(action="solutions", problem_id=pid)
        risk_values = [s["objective_values"]["Risk"] for s in solutions["solutions"]]
        # At least one solution should show diversification benefit (risk < 20)
        assert min(risk_values) < 20, f"No diversification benefit found: {risk_values}"


# ─── Skill auto-injection ───


class TestCreateAcceptsObjectivesAndOptions:
    """Bug fix: model/create now accepts objectives and options params."""

    def test_create_with_objectives(self):
        result = srv.model(action="create", name="Test", objectives=[
            {"name": "Rev", "direction": "maximize"},
            {"name": "Eff", "direction": "minimize"},
        ])
        assert result["objectives"] == 2
        p = srv.model(action="get", problem_id=result["problem_id"])
        assert len(p["objectives"]) == 2

    def test_create_with_options(self):
        result = srv.model(action="create", name="Test", options=[
            {"name": "A"}, {"name": "B"}, {"name": "C"},
        ])
        assert result["options"] == 3
        p = srv.model(action="get", problem_id=result["problem_id"])
        assert len(p["options"]) == 3

    def test_create_with_objectives_and_options(self):
        result = srv.model(action="create", name="Test",
            objectives=[
                {"name": "Rev", "direction": "maximize"},
                {"name": "Eff", "direction": "minimize"},
            ],
            options=[{"name": "A"}, {"name": "B"}],
        )
        assert result["objectives"] == 2
        assert result["options"] == 2


class TestSkillInjectionOnCreate:
    def test_create_injects_data_collection(self):
        result = srv.model(action="create", name="Test")
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "data_collection"
        assert "content" in result["_skill_guidance"]
        assert len(result["_skill_guidance"]["content"]) > 100  # actual skill content


class TestSkillInjectionOnUpdate:
    def test_update_objectives_injects_data_collection_when_not_yet_injected(self):
        """If data_collection wasn't already injected (e.g. tracking cleared),
        an objectives update should inject it."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        # Create already injected data_collection — clear it to test update path
        srv._injected_skills[pid].discard("data_collection")
        result = srv.model(action="update", problem_id=pid, objectives=[
            {"name": "Rev", "direction": "maximize"},
            {"name": "Eff", "direction": "minimize"},
        ])
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "data_collection"

    def test_update_options_injects_data_collection_when_not_yet_injected(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv._injected_skills[pid].discard("data_collection")
        result = srv.model(action="update", problem_id=pid, options=[
            {"name": "A"}, {"name": "B"}, {"name": "C"},
        ])
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "data_collection"

    def test_create_already_injects_so_update_does_not_reinject(self):
        """model/create injects data_collection, so a subsequent update with
        objectives/options should NOT re-inject."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        assert created["_skill_guidance"]["skill"] == "data_collection"
        # Update should NOT re-inject
        result = srv.model(action="update", problem_id=pid, objectives=[
            {"name": "Rev", "direction": "maximize"},
            {"name": "Eff", "direction": "minimize"},
        ])
        assert "_skill_guidance" not in result

    def test_scores_complete_injects_optimization_strategy(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
            objectives=[{"name": "Rev", "direction": "maximize"},
                        {"name": "Eff", "direction": "minimize"}],
            options=[{"name": "A"}, {"name": "B"}, {"name": "C"}])
        # Partial scores — no injection
        result = srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 5},
            {"option": "A", "objective": "Eff", "value": 3},
        ])
        assert "_skill_guidance" not in result

        # Complete scores — should inject optimization_strategy
        result = srv.model(action="update", problem_id=pid, scores=[
            {"option": "B", "objective": "Rev", "value": 7},
            {"option": "B", "objective": "Eff", "value": 2},
            {"option": "C", "objective": "Rev", "value": 9},
            {"option": "C", "objective": "Eff", "value": 6},
        ])
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "optimization_strategy"

    def test_optimization_strategy_not_reinjected_on_more_scores(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
            objectives=[{"name": "Rev", "direction": "maximize"},
                        {"name": "Eff", "direction": "minimize"}],
            options=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
            scores=[
                {"option": "A", "objective": "Rev", "value": 5},
                {"option": "A", "objective": "Eff", "value": 3},
                {"option": "B", "objective": "Rev", "value": 7},
                {"option": "B", "objective": "Eff", "value": 2},
                {"option": "C", "objective": "Rev", "value": 9},
                {"option": "C", "objective": "Eff", "value": 6},
            ])
        # Upsert a score — should NOT re-inject
        result = srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 99},
        ])
        assert "_skill_guidance" not in result

    def test_structural_change_resets_optimization_strategy(self):
        """After objectives change, optimization_strategy should re-fire when scores hit 100%."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
            objectives=[{"name": "Rev", "direction": "maximize"},
                        {"name": "Eff", "direction": "minimize"}],
            options=[{"name": "A"}, {"name": "B"}],
            scores=[
                {"option": "A", "objective": "Rev", "value": 5},
                {"option": "A", "objective": "Eff", "value": 3},
                {"option": "B", "objective": "Rev", "value": 7},
                {"option": "B", "objective": "Eff", "value": 2},
            ])
        # optimization_strategy was injected at 100%. Now change objectives.
        srv.model(action="update", problem_id=pid, objectives=[
            {"name": "Rev", "direction": "maximize"},
            {"name": "Risk", "direction": "minimize"},
        ])
        # Re-score to 100%
        result = srv.model(action="update", problem_id=pid, scores=[
            {"option": "A", "objective": "Rev", "value": 5},
            {"option": "A", "objective": "Risk", "value": 3},
            {"option": "B", "objective": "Rev", "value": 7},
            {"option": "B", "objective": "Risk", "value": 2},
        ])
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "optimization_strategy"

    def test_scores_and_objectives_same_call_prioritizes_data_collection(self):
        """When objectives AND scores arrive in the same call and data_collection
        hasn't been injected yet, data_collection takes priority over optimization_strategy."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        # Clear the data_collection injection from create so we can test the elif logic
        srv._injected_skills[pid].discard("data_collection")
        result = srv.model(action="update", problem_id=pid,
            objectives=[{"name": "Rev", "direction": "maximize"},
                        {"name": "Eff", "direction": "minimize"}],
            options=[{"name": "A"}, {"name": "B"}],
            scores=[
                {"option": "A", "objective": "Rev", "value": 5},
                {"option": "A", "objective": "Eff", "value": 3},
                {"option": "B", "objective": "Rev", "value": 7},
                {"option": "B", "objective": "Eff", "value": 2},
            ])
        # data_collection takes priority because objectives were added in same call
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "data_collection"

    def test_scores_and_objectives_same_call_when_data_collection_already_injected(self):
        """When data_collection was already injected (from create), a combined
        objectives+scores update that hits 100% should inject optimization_strategy."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        # data_collection already injected by create
        result = srv.model(action="update", problem_id=pid,
            objectives=[{"name": "Rev", "direction": "maximize"},
                        {"name": "Eff", "direction": "minimize"}],
            options=[{"name": "A"}, {"name": "B"}],
            scores=[
                {"option": "A", "objective": "Rev", "value": 5},
                {"option": "A", "objective": "Eff", "value": 3},
                {"option": "B", "objective": "Rev", "value": 7},
                {"option": "B", "objective": "Eff", "value": 2},
            ])
        # data_collection already marked → elif falls through to optimization_strategy
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "optimization_strategy"


class TestSkillInjectionOnSolve:
    def test_solve_run_injects_solution_interpreter(self):
        pid = _build_solvable_problem()
        result = srv.solve(action="run", problem_id=pid)
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "solution_interpreter"

    def test_solve_rerun_reinjects_solution_interpreter(self):
        """Every successful solve injects solution_interpreter — no dedup."""
        pid = _build_solvable_problem()
        result1 = srv.solve(action="run", problem_id=pid)
        assert result1["_skill_guidance"]["skill"] == "solution_interpreter"
        result2 = srv.solve(action="run", problem_id=pid)
        assert result2["_skill_guidance"]["skill"] == "solution_interpreter"

    def test_solve_validation_failure_no_injection(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        result = srv.solve(action="run", problem_id=pid)
        assert "_skill_guidance" not in result

    def test_validate_ready_injects_optimization_strategy(self):
        pid = _build_solvable_problem()
        # _build_solvable_problem already triggers optimization_strategy via
        # model/update at 100% scores. Clear it to test the validate path.
        srv._injected_skills[pid].discard("optimization_strategy")
        result = srv.solve(action="validate", problem_id=pid)
        assert result["ready"] is True
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "optimization_strategy"

    def test_validate_not_ready_no_injection(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        result = srv.solve(action="validate", problem_id=pid)
        assert result["ready"] is False
        assert "_skill_guidance" not in result

    def test_validate_does_not_reinject_if_already_injected(self):
        """If optimization_strategy was already injected (e.g. from 100% scores),
        validate should NOT re-inject."""
        pid = _build_solvable_problem()
        # optimization_strategy already injected by _build_solvable_problem
        result = srv.solve(action="validate", problem_id=pid)
        assert result["ready"] is True
        assert "_skill_guidance" not in result

    def test_solve_resets_optimization_strategy_for_next_cycle(self):
        """After solve, model changes should allow optimization_strategy to re-inject."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        # solve resets optimization_strategy. Validate should re-inject.
        result = srv.solve(action="validate", problem_id=pid)
        assert result["ready"] is True
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "optimization_strategy"


class TestSkillInjectionOnDelete:
    def test_delete_clears_injection_tracking(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        # Create injects data_collection, marking it as injected
        assert srv._was_injected(pid, "data_collection")
        srv.model(action="delete", problem_id=pid)
        assert not srv._was_injected(pid, "data_collection")

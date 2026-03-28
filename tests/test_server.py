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
        result = srv.explore(action="solution", problem_id=pid, solution_id=0)
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
        assert "scenario_specific_options" in result
        assert "expected_values" in result
        assert "per_scenario" in result
        assert len(result["per_scenario"]) == 2

    def test_scenario_results_without_run(self):
        pid = _build_solvable_problem()
        result = srv.explore(action="scenario_results", problem_id=pid)
        assert "error" in result

    def test_scenarios_invalid_probabilities(self):
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "A", "probability": 0.3},
                {"name": "B", "probability": 0.3},
            ],
        })
        result = srv.solve(action="run_scenarios", problem_id=pid)
        assert "error" in result
        assert "probabilities" in result["error"].lower()


class TestCuration:
    def test_curate_solution(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(
            action="curate", problem_id=pid, solution_id=0, custom_name="Pick A",
        )
        assert result.get("curated") is True
        assert result["custom_name"] == "Pick A"
        assert result["total_curated"] == 1

    def test_curate_duplicate(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.explore(action="curate", problem_id=pid, solution_id=0, custom_name="Pick A")
        result = srv.explore(action="curate", problem_id=pid, solution_id=0, custom_name="Dup")
        assert "error" in result  # duplicate

    def test_list_curated(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.explore(action="curate", problem_id=pid, solution_id=0, custom_name="First")
        srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="Second")
        result = srv.explore(action="curated", problem_id=pid)
        assert result["total_curated"] == 2
        assert all(c["in_current_frontier"] for c in result["curated_solutions"])

    def test_uncurate(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        curate_result = srv.explore(
            action="curate", problem_id=pid, solution_id=0, custom_name="Pick A",
        )
        sig = curate_result["content_signature"]
        result = srv.explore(action="uncurate", problem_id=pid, content_signature=sig)
        assert result["total_curated"] == 0

    def test_rename_curated(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        curate_result = srv.explore(
            action="curate", problem_id=pid, solution_id=0, custom_name="Old",
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
        r1 = srv.explore(action="curate", problem_id=pid, solution_id=0, custom_name="A")
        r2 = srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="B")
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
        r = srv.explore(action="curate", problem_id=pid, solution_id=0, custom_name="Survivor")
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


class TestUnknownActions:
    def test_unknown_solve_action(self):
        pid = _build_solvable_problem()
        result = srv.solve(action="foobar", problem_id=pid)
        assert "error" in result

    def test_unknown_explore_action(self):
        pid = _build_solvable_problem()
        result = srv.explore(action="foobar", problem_id=pid)
        assert "error" in result

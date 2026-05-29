"""Tests for MCP server tool handlers — model, solve, explore."""

import tempfile

import pytest

from engine.store import Store

# We test the internal handler functions directly, not via MCP protocol.
# This validates the logic without needing an MCP client.
import mcp_server.server as srv


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

    def test_update_surfaces_validation_issues_but_not_incomplete_scores(self):
        """Adjacent fix #6: model/update returns validation_issues list on structural
        change, but filters out the incomplete-scores noise. A genuinely broken
        constraint (force_include on unknown option) is surfaced."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}])

        # No scores yet — would be an "incomplete score matrix" validation error.
        # That should NOT appear in validation_issues (it's expected during setup).
        result = srv.model(action="update", problem_id=pid,
            constraints=[{"type": "cardinality", "min": 1, "max": 2}])
        # incomplete-scores noise filtered out
        if "validation_issues" in result:
            for issue in result["validation_issues"]:
                assert "Score matrix incomplete" not in issue["message"]

        # Now trigger a genuine error: force_include on an unknown option
        result = srv.model(action="update", problem_id=pid,
            constraints=[{"type": "force_include", "option": "NONEXISTENT"}])
        assert "validation_issues" in result
        messages = [i["message"] for i in result["validation_issues"]]
        assert any("NONEXISTENT" in m for m in messages)

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
        # Wrapped in {"problems": [...]} so FastMCP serializes to a TextContent
        # block — bare-list returns are dropped by FastMCP 1.25.0 and rejected
        # by the Anthropic MCP connector.
        assert result == {"problems": []}

    def test_list_returns_problems_array(self):
        srv.model(action="create", name="One")
        srv.model(action="create", name="Two")
        result = srv.model(action="list")
        assert isinstance(result, dict)
        assert "problems" in result
        assert isinstance(result["problems"], list)
        assert len(result["problems"]) == 2


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

    def test_get_summary_section(self):
        pid = _build_solvable_problem()
        result = srv.model(action="get", problem_id=pid, section="summary")
        assert result["section"] == "summary"
        assert result["objectives_count"] == 2
        assert result["options_count"] == 4
        assert result["scores_count"] == 8
        # Summary must not contain the heavy fields
        assert "scores" not in result
        assert "run" not in result

    def test_get_scores_section(self):
        pid = _build_solvable_problem()
        result = srv.model(action="get", problem_id=pid, section="scores")
        assert result["section"] == "scores"
        assert len(result["scores"]) == 8
        # Should not include other heavy fields
        assert "constraints" not in result

    def test_get_unknown_section(self):
        pid = _build_solvable_problem()
        result = srv.model(action="get", problem_id=pid, section="nonsense")
        assert "error" in result


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
        assert "quality" in result
        # Compact response: no full solutions array, but objective_ranges + preview present
        assert "solutions" not in result
        assert "objective_ranges" in result
        assert "preview" in result
        assert "extremes" in result["preview"]

    def test_run_echoes_seed_used_when_random(self):
        pid = _build_solvable_problem()
        result = srv.solve(action="run", problem_id=pid)
        assert "seed_used" in result
        assert isinstance(result["seed_used"], int)

    def test_run_reproducible_with_fixed_seed(self):
        pid1 = _build_solvable_problem()
        pid2 = _build_solvable_problem()
        r1 = srv.solve(action="run", problem_id=pid1, seed=1234)
        r2 = srv.solve(action="run", problem_id=pid2, seed=1234)
        assert r1["seed_used"] == 1234
        assert r2["seed_used"] == 1234
        # Same seed on identical problem → same objective ranges
        assert r1["objective_ranges"] == r2["objective_ranges"]
        assert r1["solutions_found"] == r2["solutions_found"]

    def test_run_different_seeds_may_differ(self):
        pid1 = _build_solvable_problem()
        pid2 = _build_solvable_problem()
        r1 = srv.solve(action="run", problem_id=pid1, seed=1)
        r2 = srv.solve(action="run", problem_id=pid2, seed=9999)
        assert r1["seed_used"] == 1
        assert r2["seed_used"] == 9999
        # Both must succeed; frontier shape may vary
        assert r1["solutions_found"] > 0
        assert r2["solutions_found"] > 0

    def test_run_writes_full_result_file(self):
        """Fix 1: every solve writes the complete result to disk and returns the path."""
        import json as _json
        from pathlib import Path

        pid = _build_solvable_problem()
        result = srv.solve(action="run", problem_id=pid)
        assert "full_result_path" in result
        path = Path(result["full_result_path"])
        assert path.exists(), f"{path} was not written"
        payload = _json.loads(path.read_text())
        # File contains all solutions the response omits
        assert "solutions" in payload
        assert len(payload["solutions"]) == result["solutions_found"]
        # First solution has full structure
        sol = payload["solutions"][0]
        assert "solution_id" in sol
        assert "objective_values" in sol

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

    def test_run_includes_frontier_complete_and_quality(self):
        """1.10 + 1.11: solve response carries frontier_complete + frontier_quality."""
        pid = _build_solvable_problem()
        result = srv.solve(action="run", problem_id=pid)
        # 1.10
        assert "frontier_complete" in result
        assert isinstance(result["frontier_complete"], bool)
        # No pruning expected on this small problem → complete
        assert result["frontier_complete"] is True
        assert result["total_pareto_found"] == result["solutions_found"]
        # 1.11
        assert "frontier_quality" in result
        fq = result["frontier_quality"]
        assert fq["status"] in ("GOOD", "WARNING", "POOR")
        assert "gates" in fq and "issues" in fq
        assert set(fq["gates"]) == {"frontier_returned", "non_trivial", "diverse"}

    def test_run_frontier_complete_false_when_pruned(self):
        """1.10: frontier_complete is False when max_solutions truncates the frontier."""
        pid = _build_solvable_problem()
        # Tight cap forces pruning if there's any frontier larger than 1
        result = srv.solve(action="run", problem_id=pid, max_solutions=1)
        if result.get("solutions_found", 0) > 0 and result.get("total_pareto_found", 0) > 1:
            assert result["frontier_complete"] is False
            assert result["solutions_found"] < result["total_pareto_found"]


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
        import json as _json
        from pathlib import Path

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
        # Fix 1: per-scenario full result files written to disk
        assert "full_result_paths" in result
        assert set(result["full_result_paths"].keys()) == {"Base", "Alt"}
        for name, path_str in result["full_result_paths"].items():
            path = Path(path_str)
            assert path.exists()
            payload = _json.loads(path.read_text())
            assert payload["scenario"] == name
            assert len(payload["solutions"]) == result["results"][name]["solutions_found"]

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

    def test_scenario_risk_and_cvar(self):
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
        # Default alpha = 0.2
        default_result = srv.explore(action="scenario_results", problem_id=pid)
        assert "scenario_risk" in default_result
        assert default_result["cvar_alpha"] == 0.2
        for obj, risk in default_result["scenario_risk"].items():
            assert "expected" in risk
            assert "worst_case" in risk
            assert "best_case" in risk
            assert "cvar_20" in risk
            assert "range" in risk
            assert risk["range"][0] <= risk["range"][1]

        # Custom alpha
        alt = srv.explore(action="scenario_results", problem_id=pid, cvar_alpha=0.5)
        assert alt["cvar_alpha"] == 0.5
        for risk in alt["scenario_risk"].values():
            assert "cvar_50" in risk

    def test_scenario_results_invalid_alpha(self):
        pid = _build_solvable_problem()
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [{"name": "A"}, {"name": "B"}],
        })
        srv.solve(action="run_scenarios", problem_id=pid)
        result = srv.explore(action="scenario_results", problem_id=pid, cvar_alpha=1.5)
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

    def test_scenarios_with_interaction_matrix_overrides(self):
        """Per-scenario interaction matrix overrides should change portfolio-level quadratic
        aggregation independently per scenario. Correlation regime shifts (e.g. recession)
        can be modelled by supplying a different covariance matrix for that scenario.
        """
        # Build a 3-option, 2-objective proportional problem with quadratic Volatility.
        created = srv.model(action="create", approach="proportional")
        pid = created["problem_id"]
        srv.model(
            action="update", problem_id=pid,
            objectives=[
                {"name": "Return", "direction": "maximize", "aggregation": "sum"},
                {"name": "Volatility", "direction": "minimize", "aggregation": "quadratic"},
            ],
            options=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
            scores=[
                {"option": "A", "objective": "Return", "value": 10},
                {"option": "B", "objective": "Return", "value": 8},
                {"option": "C", "objective": "Return", "value": 6},
                {"option": "A", "objective": "Volatility", "value": 20},
                {"option": "B", "objective": "Volatility", "value": 20},
                {"option": "C", "objective": "Volatility", "value": 20},
            ],
            constraints=[
                {"type": "cardinality", "min": 2, "max": 3},
                {"type": "max_allocation", "max": 60},
            ],
        )
        # Base: diagonal-only matrix (low correlation → diversification possible)
        base_matrix = {
            "objective": "Volatility",
            "entries": {
                "A": {"A": 400.0, "B": 0.0, "C": 0.0},
                "B": {"A": 0.0, "B": 400.0, "C": 0.0},
                "C": {"A": 0.0, "B": 0.0, "C": 400.0},
            },
        }
        srv.model(action="update", problem_id=pid, interaction_matrices=[base_matrix])

        # Full-correlation override: off-diagonals = variance (correlation = 1)
        full_corr_matrix = {
            "objective": "Volatility",
            "entries": {
                "A": {"A": 400.0, "B": 400.0, "C": 400.0},
                "B": {"A": 400.0, "B": 400.0, "C": 400.0},
                "C": {"A": 400.0, "B": 400.0, "C": 400.0},
            },
        }
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "Diversifiable"},  # uses base matrix
                {"name": "FullCorrelation", "interaction_matrix_overrides": [full_corr_matrix]},
            ],
        })
        result = srv.solve(action="run_scenarios", problem_id=pid, mode="fast")
        assert "error" not in result
        assert result["scenarios_optimized"] == 2

        # Fetch min-vol extremes from each scenario.
        diverse = srv.explore(action="tradeoffs", problem_id=pid, scenario="Diversifiable")
        correlated = srv.explore(action="tradeoffs", problem_id=pid, scenario="FullCorrelation")

        min_vol_diverse = diverse["objective_ranges"]["Volatility"]["min"]
        min_vol_correlated = correlated["objective_ranges"]["Volatility"]["min"]

        # With zero correlation a diversified portfolio achieves sqrt(0.4^2 + 0.4^2 + 0.2^2)*sqrt(400) ≈ 12;
        # with full correlation every portfolio hits sqrt(400) = 20. Correlation should raise min vol.
        assert min_vol_correlated > min_vol_diverse, (
            f"Full-correlation scenario should have higher min vol than diversifiable base. "
            f"Got diverse={min_vol_diverse}, correlated={min_vol_correlated}"
        )

    def test_scenarios_with_scale_groups_override(self):
        """Fix 3: scale_groups on a scenario scales off-diagonal interactions in-group
        without requiring a full-matrix re-upload.

        Shape the problem so equities are correlated modestly in base; scale their
        correlations ×3 in a 'stress' scenario and confirm min-vol rises.
        """
        created = srv.model(action="create", approach="proportional")
        pid = created["problem_id"]
        srv.model(
            action="update", problem_id=pid,
            objectives=[
                {"name": "Return", "direction": "maximize", "aggregation": "sum"},
                {"name": "Volatility", "direction": "minimize", "aggregation": "quadratic"},
            ],
            options=[{"name": "E1"}, {"name": "E2"}, {"name": "E3"}, {"name": "Bond"}],
            scores=[
                # Similar returns on equities, lower on bond
                {"option": "E1", "objective": "Return", "value": 10},
                {"option": "E2", "objective": "Return", "value": 10},
                {"option": "E3", "objective": "Return", "value": 10},
                {"option": "Bond", "objective": "Return", "value": 4},
                # Dummy individual vols
                {"option": "E1", "objective": "Volatility", "value": 20},
                {"option": "E2", "objective": "Volatility", "value": 20},
                {"option": "E3", "objective": "Volatility", "value": 20},
                {"option": "Bond", "objective": "Volatility", "value": 5},
            ],
            constraints=[
                {"type": "cardinality", "min": 2, "max": 4},
                {"type": "max_allocation", "max": 50},
            ],
        )
        # Base matrix: modest equity-equity covariance; equity-bond near zero
        base_matrix = {
            "objective": "Volatility",
            "entries": {
                "E1": {"E1": 400.0, "E2": 100.0, "E3": 100.0, "Bond": 0.0},
                "E2": {"E1": 100.0, "E2": 400.0, "E3": 100.0, "Bond": 0.0},
                "E3": {"E1": 100.0, "E2": 100.0, "E3": 400.0, "Bond": 0.0},
                "Bond": {"E1": 0.0, "E2": 0.0, "E3": 0.0, "Bond": 25.0},
            },
        }
        srv.model(action="update", problem_id=pid, interaction_matrices=[base_matrix])

        # Scenario: scale equity-equity off-diagonals ×3 (stress). Base → factor 1.0 (no change).
        srv.model(action="update", problem_id=pid, scenario_config={
            "enabled": True,
            "scenarios": [
                {"name": "Base"},
                {"name": "Stress", "interaction_matrix_overrides": [{
                    "objective": "Volatility",
                    "mode": "upsert",
                    "entries": {},  # don't change any specific cells
                    "scale_groups": [{"options": ["E1", "E2", "E3"], "factor": 3.0}],
                }]},
            ],
        })
        result = srv.solve(action="run_scenarios", problem_id=pid, mode="fast")
        assert "error" not in result

        base = srv.explore(action="tradeoffs", problem_id=pid, scenario="Base")
        stress = srv.explore(action="tradeoffs", problem_id=pid, scenario="Stress")

        min_vol_base = base["objective_ranges"]["Volatility"]["min"]
        min_vol_stress = stress["objective_ranges"]["Volatility"]["min"]

        # Higher equity-equity correlations → higher min-vol frontier for equity-heavy portfolios
        # The stress min-vol may still route through bonds, but cannot be lower than base.
        assert min_vol_stress >= min_vol_base - 0.01, (
            f"Stress scenario should not produce lower min vol than base. "
            f"Base={min_vol_base}, Stress={min_vol_stress}"
        )


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

    def test_export_curated_markdown(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="First")
        srv.explore(action="curate", problem_id=pid, solution_id=2, custom_name="Second")
        result = srv.explore(action="export_curated", problem_id=pid)
        assert result["format"] == "markdown"
        assert result["total_curated"] == 2
        content = result["content"]
        assert "| name |" in content
        assert "content_signature" in content
        assert "First" in content and "Second" in content

    def test_export_curated_csv(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="First")
        result = srv.explore(action="export_curated", problem_id=pid, format="csv")
        assert result["format"] == "csv"
        content = result["content"]
        assert "name,content_signature" in content
        assert "First" in content

    def test_export_curated_empty(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        result = srv.explore(action="export_curated", problem_id=pid)
        assert result["total_curated"] == 0
        assert result["content"] == ""

    def test_export_curated_bad_format(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        srv.explore(action="curate", problem_id=pid, solution_id=1)
        result = srv.explore(action="export_curated", problem_id=pid, format="xml")
        assert "error" in result

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
        # Default compact: no selected_options or allocations per solution
        assert result["detail"] is False
        for sol in result["solutions"]:
            assert "selected_options" not in sol
            assert "allocations" not in sol

    def test_compare_curated_detail(self):
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        r1 = srv.explore(action="curate", problem_id=pid, solution_id=1, custom_name="A")
        r2 = srv.explore(action="curate", problem_id=pid, solution_id=2, custom_name="B")
        result = srv.explore(
            action="compare_curated", problem_id=pid,
            signatures=[r1["content_signature"], r2["content_signature"]],
            detail=True,
        )
        assert result["detail"] is True
        for sol in result["solutions"]:
            assert "selected_options" in sol

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
        assert result["solutions_found"] >= 2

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

    def test_non_shape_changes_do_not_reset_optimization_strategy(self):
        """Adding a constraint, interaction matrix, or scenario_config between scores→100%
        and solve/validate should NOT re-fire optimization_strategy. Only objective/option
        shape changes invalidate the methodology guidance."""
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
            ])  # optimization_strategy injected here (scores → 100%)

        # Add a constraint — must NOT re-fire
        result = srv.model(action="update", problem_id=pid,
            constraints=[{"type": "cardinality", "min": 1, "max": 2}])
        assert "_skill_guidance" not in result

        # Add a reference point — must NOT re-fire
        result = srv.model(action="update", problem_id=pid,
            reference_points=[{"type": "baseline", "objective_values": {"Rev": 5, "Eff": 3}}])
        assert "_skill_guidance" not in result

        # Validate — must NOT re-fire either (already injected)
        result = srv.solve(action="validate", problem_id=pid)
        assert "_skill_guidance" not in result

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

    def test_solve_rerun_does_not_reinject_solution_interpreter(self):
        """solution_interpreter injects once per problem; a re-solve without
        structural change does not re-inject (throttled)."""
        pid = _build_solvable_problem()
        result1 = srv.solve(action="run", problem_id=pid)
        assert result1["_skill_guidance"]["skill"] == "solution_interpreter"
        result2 = srv.solve(action="run", problem_id=pid)
        assert "_skill_guidance" not in result2

    def test_structural_update_rearms_solution_interpreter(self):
        """Structural model edits reset the solution_interpreter flag so the
        next solve re-injects fresh guidance."""
        pid = _build_solvable_problem()
        srv.solve(action="run", problem_id=pid)
        assert srv._was_injected(pid, "solution_interpreter")
        # Structural edit (constraints replacement) should clear the flag.
        srv.model(
            action="update",
            problem_id=pid,
            constraints=[{"type": "cardinality", "min": 1, "max": 2}],
        )
        assert not srv._was_injected(pid, "solution_interpreter")
        result = srv.solve(action="run", problem_id=pid)
        assert result["_skill_guidance"]["skill"] == "solution_interpreter"

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

    def test_run_scenarios_injects_solution_interpreter(self):
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
        assert "_skill_guidance" in result
        assert result["_skill_guidance"]["skill"] == "solution_interpreter"


class TestSkillInjectionOnDelete:
    def test_delete_clears_injection_tracking(self):
        created = srv.model(action="create")
        pid = created["problem_id"]
        # Create injects data_collection, marking it as injected
        assert srv._was_injected(pid, "data_collection")
        srv.model(action="delete", problem_id=pid)
        assert not srv._was_injected(pid, "data_collection")

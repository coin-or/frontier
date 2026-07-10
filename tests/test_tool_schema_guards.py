"""Schema-level steering guards: the wrong-name params advertise their redirect.

The guard params (model.scenarios, solve.scenario/run_scenarios, explore.label)
are schema-valid by design — FastMCP silently drops unknown arguments, so each
guard must exist in the signature to catch its miscall. But an undescribed guard
param is an attractive nuisance: `run_scenarios: boolean` in the schema reads as
a flag and invites the very call it rejects (both 2026-07-10 demo-replay agents
made exactly these miscalls before the runtime guard corrected them). These
tests pin the fix — every guard param, and the merge-vs-replace contract on the
model data params, carries its steering description in the advertised
inputSchema — and gate it against an SDK upgrade dropping Field descriptions.
"""

import tempfile

import pytest

from engine.store import Store

import mcp_server.server as srv


def _param_desc(tool: str, param: str) -> str:
    tools = {t.name: t for t in srv.mcp._tool_manager.list_tools()}
    return tools[tool].parameters["properties"][param].get("description", "")


class TestGuardParamSteering:
    def test_explore_label_steers_to_custom_name(self):
        assert "custom_name" in _param_desc("explore", "label")

    def test_solve_run_scenarios_steers_to_action(self):
        assert 'action="run_scenarios"' in _param_desc("solve", "run_scenarios")

    def test_solve_scenario_steers_to_action(self):
        desc = _param_desc("solve", "scenario")
        assert 'action="run_scenarios"' in desc and "explore" in desc

    def test_model_scenarios_steers_to_scenario_config(self):
        assert "scenario_config" in _param_desc("model", "scenarios")


class TestReplaceVsMergeContract:
    def test_constraints_declare_full_replacement(self):
        desc = _param_desc("model", "constraints").upper()
        assert "FULL REPLACEMENT" in desc and "COMPLETE" in desc

    def test_objectives_and_options_declare_full_replacement(self):
        for param in ("objectives", "options"):
            assert "FULL REPLACEMENT" in _param_desc("model", param).upper()

    def test_scores_declare_merge(self):
        assert "merge" in _param_desc("model", "scores").lower()


@pytest.fixture()
def tmp_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        s = Store(tmpdir)
        monkeypatch.setattr(srv, "store", s)
        srv._injected_skills.clear()
        yield s


class TestConstraintReplacementEcho:
    """The runtime half of the contract: a replacement that shrinks the set says so."""

    def _make_problem(self):
        result = srv.model(
            action="create",
            options=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
            objectives=[
                {"name": "Value", "direction": "maximize"},
                {"name": "Cost", "direction": "minimize"},
            ],
            constraints=[
                {"type": "cardinality", "min": 1, "max": 2},
                {"type": "force_include", "option": "A"},
            ],
        )
        return result["problem_id"]

    def test_update_status_echoes_constraint_count(self, tmp_store):
        pid = self._make_problem()
        result = srv.model(action="update", problem_id=pid, constraints=[
            {"type": "cardinality", "min": 1, "max": 2},
            {"type": "force_include", "option": "A"},
            {"type": "force_exclude", "option": "C"},
        ])
        assert result["status"]["constraints"] == 3

    def test_shrinking_replacement_carries_note(self, tmp_store):
        pid = self._make_problem()
        result = srv.model(action="update", problem_id=pid, constraints=[
            {"type": "force_include", "option": "A"},
        ])
        assert result["status"]["constraints"] == 1
        assert "full replacement" in result["constraints_note"]

    def test_growing_replacement_has_no_note(self, tmp_store):
        pid = self._make_problem()
        result = srv.model(action="update", problem_id=pid, constraints=[
            {"type": "cardinality", "min": 1, "max": 2},
            {"type": "force_include", "option": "A"},
            {"type": "force_exclude", "option": "C"},
        ])
        assert "constraints_note" not in result

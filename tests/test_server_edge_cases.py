"""Edge-case tests for MCP server — constraint parsing, infeasibility path."""

import tempfile
from unittest.mock import patch

import pytest

from engine.models import Run
from engine.store import Store
import mcp_server.server as srv


@pytest.fixture(autouse=True)
def tmp_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        s = Store(tmpdir)
        monkeypatch.setattr(srv, "store", s)
        yield s


class TestParseConstraintUnknownType:
    def test_unknown_constraint_type_in_update(self):
        """Updating with an unknown constraint type returns a worded error naming the
        valid vocabulary — the tool contract, never an uncaught exception."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        out = srv.model(
            action="update",
            problem_id=pid,
            constraints=[{"type": "magic_constraint"}],
        )
        assert "Unknown constraint type" in out["error"]
        assert "Valid types" in out["error"]


class TestSolveRunInfeasible:
    def test_infeasible_returns_analysis(self):
        """When optimizer returns 0 solutions, should return infeasibility analysis."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(
            action="update",
            problem_id=pid,
            objectives=[
                {"name": "Rev", "direction": "maximize"},
                {"name": "Eff", "direction": "minimize"},
            ],
            options=[
                {"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"},
            ],
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
            constraints=[{"type": "cardinality", "min": 2, "max": 3}],
        )

        # Mock optimizer.optimize to return empty Run
        with patch.object(srv.optimizer, "optimize", return_value=Run(solutions=[])):
            result = srv.solve(action="run", problem_id=pid)

        assert result["feasible"] is False
        assert "binding_constraints" in result
        assert "suggestions" in result

    def test_optimizer_exception_returns_error(self):
        """When optimizer raises, should return feasible=False with error."""
        created = srv.model(action="create")
        pid = created["problem_id"]
        srv.model(
            action="update",
            problem_id=pid,
            objectives=[
                {"name": "Rev", "direction": "maximize"},
                {"name": "Eff", "direction": "minimize"},
            ],
            options=[
                {"name": "A"}, {"name": "B"}, {"name": "C"},
            ],
            scores=[
                {"option": "A", "objective": "Rev", "value": 8},
                {"option": "A", "objective": "Eff", "value": 5},
                {"option": "B", "objective": "Rev", "value": 6},
                {"option": "B", "objective": "Eff", "value": 3},
                {"option": "C", "objective": "Rev", "value": 9},
                {"option": "C", "objective": "Eff", "value": 7},
            ],
            constraints=[{"type": "cardinality", "min": 1, "max": 2}],
        )

        with patch.object(
            srv.optimizer, "optimize",
            side_effect=RuntimeError("pymoo exploded"),
        ):
            result = srv.solve(action="run", problem_id=pid)

        assert result["feasible"] is False
        assert "pymoo exploded" in result["error"]


class TestModelActionNone:
    def test_model_get_missing_id(self):
        result = srv.model(action="get")
        assert "error" in result

    def test_model_delete_missing_id(self):
        result = srv.model(action="delete")
        assert "error" in result

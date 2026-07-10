"""Advisory scale band (solve validate's ``solvers.scale`` block).

Routing signals, never stop signs: the band names the measured regime boundary a
problem sits near and the posture that fits (background polling, a time_limit,
curated-scope certification). Demo-scale problems carry band "interactive" and no
note — zero noise until scale actually changes the right move. Thresholds are
named constants beside the shape gate with benchmark provenance; validate's ready
status is untouched.
"""

import tempfile

import pytest

import mcp_server.server as srv
from engine.models import Objective, Option, Problem, Score
from engine.store import Store
from solvers import _NSGA_BACKGROUND_N, _NSGA_ROUTING_N, scale_band


@pytest.fixture(autouse=True)
def tmp_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        s = Store(tmpdir)
        monkeypatch.setattr(srv, "store", s)
        srv._injected_skills.clear()
        yield s


def _problem(n_options: int) -> Problem:
    names = [f"P{i:05d}" for i in range(n_options)]
    return Problem(
        approach="binary",
        objectives=[Objective(name="value", direction="maximize"),
                    Objective(name="cost", direction="minimize")],
        options=[Option(name=nm) for nm in names],
        scores=[Score(option=nm, objective=o, value=float(i % 9 + 1))
                for o in ("value", "cost") for i, nm in enumerate(names)],
    )


class TestBandEdges:
    def test_interactive_below_background_threshold(self):
        block = scale_band(_problem(_NSGA_BACKGROUND_N - 1))
        assert block["band"] == "interactive"
        assert "note" not in block  # zero noise at demo/interactive scale

    def test_background_at_threshold(self):
        block = scale_band(_problem(_NSGA_BACKGROUND_N))
        assert block["band"] == "background"
        assert "background" in block["note"]
        assert "scope='curated'" in block["note"]

    def test_needs_routing_at_threshold(self):
        block = scale_band(_problem(_NSGA_ROUTING_N))
        assert block["band"] == "needs_routing"
        assert "time_limit" in block["note"]
        assert "scope='curated'" in block["note"]

    def test_notes_route_not_warn(self):
        # The advisory names a lane to take; it never tells the user to shrink the problem.
        for n in (_NSGA_BACKGROUND_N, _NSGA_ROUTING_N):
            note = scale_band(_problem(n))["note"].lower()
            assert not any(w in note for w in ("too large", "too big", "reduce", "avoid"))


class TestBlockShape:
    def test_lean_block_no_speculative_fields(self):
        # n_options + band (+ note when it routes) is the whole working surface —
        # anything more is wire noise nothing consumes.
        block = scale_band(_problem(5))
        assert block == {"n_options": 5, "band": "interactive"}


class TestValidateSurface:
    def test_validate_carries_scale_block_quietly_at_demo_size(self):
        pid = srv.model(action="create")["problem_id"]
        srv.model(action="update", problem_id=pid,
                  objectives=[{"name": "Rev", "direction": "maximize"},
                              {"name": "Eff", "direction": "minimize"}],
                  options=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
                  scores=[{"option": o, "objective": ob, "value": v}
                          for o, ob, v in [("A", "Rev", 8), ("A", "Eff", 5),
                                           ("B", "Rev", 6), ("B", "Eff", 3),
                                           ("C", "Rev", 9), ("C", "Eff", 7)]])
        res = srv.solve(action="validate", problem_id=pid)
        scale = res["solvers"]["scale"]
        assert scale["band"] == "interactive"
        assert "note" not in scale
        assert res["ready"] is True  # advisory only — readiness untouched

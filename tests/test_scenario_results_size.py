"""scenario_results payload sizing: portfolio-scale problems must stay under the MCP
inline result cap.

At 300 options the per-option robustness table (duplicated into viz_data) once pushed
`explore scenario_results` past the inline cap, so clients received a persisted-output
file instead of readable JSON. get_scenario_results ships the ranked head of the table
and summarizes the elided tail; small problems pass through whole.
"""
import json
from pathlib import Path

import pytest

from engine import explorer
from engine.problem_io import read_bundle

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# Engine-payload budget chosen so the served response (payload + tool guidance and
# formatting wrapper) stays comfortably inside the ~100KB inline cap that the 300-option
# example previously blew past (93KB served).
_ENGINE_PAYLOAD_BUDGET = 50_000


def test_capital_300_scenario_results_fits_inline():
    p = read_bundle(EXAMPLES / "capital_project_selection_300")
    res = explorer.get_scenario_results(p)
    size = len(json.dumps(res))
    assert size < _ENGINE_PAYLOAD_BUDGET, f"scenario_results payload {size}B blows the inline budget"

    # The trim is announced, ranked, and mirrored into viz_data — never silent.
    elided = res["option_robustness_elided"]
    assert elided["count"] > 0
    assert "explore solutions" in elided["note"]
    table = res["option_robustness"]
    assert len(table) == len(res["viz_data"]["option_robustness"])
    ranks = [(r["importance"], r["avg_frequency"]) for r in table]
    assert ranks == sorted(ranks, reverse=True), "table must ship importance/frequency-ranked"


def test_small_problem_scenario_results_untrimmed():
    p = read_bundle(EXAMPLES / "production_mix")
    res = explorer.get_scenario_results(p)
    assert "option_robustness_elided" not in res
    # Every option that appears in any scenario solution is present, whole.
    assert len(res["option_robustness"]) <= 60

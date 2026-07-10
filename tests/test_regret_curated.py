"""Scenario regret over the curated set (regret.curated).

The regret lens must cover the plans the user actually shortlisted: curated pins are
content_signature-keyed and carry selected_options/allocations, so they re-score under
each scenario through the same scorers, normalization, and ranked-scenario set as the
base per_solution rows — including exact-overlay finalists that never appear on the
base frontier. Absent when nothing is curated; base block untouched.
"""

import copy

from engine import explorer
from engine.models import (
    CardinalityConstraint,
    CuratedSolution,
    Objective,
    Option,
    Problem,
    Scenario,
    ScenarioConfig,
    ScenarioRun,
    Score,
    ScoreAdjustment,
    _content_signature,
)
from engine.optimizer import OptimizeMode, optimize, optimize_scenarios


def _scenario_problem() -> Problem:
    names = [f"P{i:02d}" for i in range(14)]
    objs = ["value", "cost"]
    p = Problem(
        approach="binary",
        objectives=[Objective(name="value", direction="maximize"),
                    Objective(name="cost", direction="minimize")],
        options=[Option(name=nm) for nm in names],
        scores=[Score(option=nm, objective=o, value=float((i * 7 + j * 5) % 11 + 1))
                for j, o in enumerate(objs) for i, nm in enumerate(names)],
        constraints=[CardinalityConstraint(min=1, max=8)],
        scenario_config=ScenarioConfig(enabled=True, scenarios=[
            Scenario(name="cost_spike",
                     score_adjustments=[ScoreAdjustment(objective="cost", multiply=1.5)]),
            Scenario(name="tight_slate",
                     constraint_overrides=[CardinalityConstraint(min=1, max=4)]),
        ]),
    )
    p.run = optimize(p, mode=OptimizeMode.fast, seed=42)
    p.scenario_run = ScenarioRun(scenario_runs=optimize_scenarios(
        p, mode="fast", seed=42, max_solutions=15))
    return p


def _pin(selected: list[str], name: str) -> CuratedSolution:
    return CuratedSolution(
        content_signature=_content_signature(selected),
        custom_name=name,
        selected_options=selected,
        objective_values={},
    )


class TestCuratedRegret:
    def test_absent_without_curation(self):
        p = _scenario_problem()
        assert "curated" not in explorer.scenario_regret(p)

    def test_rows_cover_base_and_overlay_only_picks(self):
        p = _scenario_problem()
        base_reg = explorer.scenario_regret(p)
        # Pin the base minimax slate itself: its curated row must reproduce the base
        # number exactly (same scorers, normalization, ranked set — the comparability
        # claim, verified numerically). Second pin: a slate absent from the base
        # frontier (the exact-overlay re-curation case) — must score, whatever it scores.
        best = next(s for s in p.run.solutions
                    if s.solution_id == base_reg["minimax_choice"]["solution_id"])
        base_sigs = {s.content_signature for s in p.run.solutions}
        overlay_like = next(sol for run in p.scenario_run.scenario_runs.values()
                            for sol in run.solutions
                            if sol.content_signature not in base_sigs)
        p.curated_solutions = [
            _pin(list(best.selected_options), "balanced pick"),
            _pin(list(overlay_like.selected_options), "certified counterpart"),
        ]
        cur = explorer.scenario_regret(p)["curated"]
        assert len(cur["rows"]) == 2
        scen_names = set(p.scenario_run.scenario_runs)
        for row in cur["rows"]:
            assert set(row) == {"content_signature", "custom_name", "by_scenario",
                                "max_regret", "mean_regret", "feasible_in_all",
                                "feasible_in_ranked"}
            assert set(row["by_scenario"]) == scen_names  # every scenario reported
        # Sorted ascending; the head is the pinned base-minimax slate, at the SAME
        # max_regret the base ranking reported for it — the two lenses compare directly.
        maxes = [r["max_regret"] for r in cur["rows"]]
        assert maxes == sorted(maxes)
        assert cur["rows"][0]["content_signature"] == best.content_signature
        assert cur["rows"][0]["max_regret"] == base_reg["minimax_choice"]["max_regret"]
        assert cur["minimax_choice"]["content_signature"] == best.content_signature
        assert "compares directly" in cur["note"]

    def test_base_block_unchanged_by_curation(self):
        p = _scenario_problem()
        before = explorer.scenario_regret(copy.deepcopy(p))
        p.curated_solutions = [_pin([o.name for o in p.options[:3]], "pick")]
        after = explorer.scenario_regret(p)
        for key in ("per_solution", "per_objective", "minimax_choice",
                    "survivors_by_scenario", "note"):
            assert after[key] == before[key]

    def test_saturated_curated_set_omits_minimax(self):
        p = _scenario_problem()
        # A 6-option pick violates tight_slate's ≤4 cap → infeasible there → regret 1.0
        # in a ranked scenario; as the only pin, the curated lens saturates.
        too_big = [o.name for o in p.options[:6]]
        p.curated_solutions = [_pin(too_big, "oversized pick")]
        cur = explorer.scenario_regret(p)["curated"]
        assert cur["rows"][0]["max_regret"] == 1.0
        assert cur["rows"][0]["feasible_in_ranked"] is False
        assert cur["minimax_choice"] is None
        assert "Saturated" in cur["note"]

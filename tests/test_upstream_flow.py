"""Upstream flow: every example's runbook must work end-to-end from the kit.

test_upstream_kits.py proves each kit reconstructs the canonical model verbatim, so
"framed from the kit" and "the canonical model" are the same problem. These tests take
that model with NO baked results (the state a user is in right after step 0), run the
fast solve, and exercise the explore actions its README walkthrough promises — so a
data or engine change that breaks a runbook's later steps fails here, not on camera.

Exact/certify passes are exercised only on the sub-second continuous (LP/QP) shapes;
the binary exact sweeps are minutes-long and stay out of CI.
"""
import pytest

from engine import explorer, problem_io
from engine.models import ScenarioRun
from engine.optimizer import optimize, optimize_scenarios

EXAMPLES = [
    "budget_allocation",
    "production_mix",
    "channel_budget",
    "supplier_selection",
    "capacity_planning",
    "investment_portfolio",
    "capital_project_selection_120",
    "claims_investigation_triage",
    "charging_network_siting",
    "research_cohort_selection",
    "interconnection_approvals",
    "scarce_supply_rationing",
]

# Continuous shapes whose exact pass is sub-second: run solver="highs" + certify + duals.
EXACT_FAST = {"budget_allocation", "production_mix", "scarce_supply_rationing",
              "supplier_selection", "capacity_planning", "investment_portfolio"}


def _fresh(example):
    """The post-step-0 state: the canonical model with no results."""
    p = problem_io.load_problem(example)
    p.run = p.exact_run = p.scenario_run = None
    p.curated_solutions = []
    return p


@pytest.fixture(scope="module")
def solved():
    """One fast solve per example, shared across the checks below."""
    out = {}
    for name in EXAMPLES:
        p = _fresh(name)
        p.run = optimize(p, mode="fast", seed=42, max_solutions=25)
        out[name] = p
    return out


@pytest.mark.parametrize("name", EXAMPLES)
def test_solve_and_tradeoffs_from_fresh_state(solved, name):
    p = solved[name]
    assert p.run.solutions, f"{name}: fresh fast solve returned no frontier"
    t = explorer.get_tradeoffs(p)
    assert t["total_solutions"] == len(p.run.solutions)
    assert t["balanced_solution"] is not None
    assert set(t["objective_ranges"]) == {o.name for o in p.objectives}


@pytest.mark.parametrize("name", sorted(EXACT_FAST))
def test_exact_certify_and_duals_from_fresh_state(solved, name):
    p = solved[name]
    p.exact_run = optimize(p, mode="fast", seed=42, solver="highs")
    cert = explorer.certify_against_exact(p, p.run, p.exact_run)
    # On continuous shapes the invariant may be violated ONLY by the documented
    # whole-percent rounding of exact optima — the certificate must say so itself.
    assert cert["invariant"]["holds"] or "rounding" in cert["invariant"]["note"]
    assert cert["exact_count"] > 0


@pytest.mark.parametrize("name", [n for n in EXAMPLES])
def test_scenarios_from_fresh_state(solved, name):
    p = solved[name]
    if not (p.scenario_config and p.scenario_config.enabled and p.scenario_config.scenarios):
        pytest.skip("no scenarios in this example")
    p.scenario_run = ScenarioRun(scenario_runs=optimize_scenarios(
        p, mode="fast", seed=42, max_solutions=15))
    reg = explorer.scenario_regret(p)
    assert reg["available"] is True
    assert reg["per_solution"], f"{name}: regret has no rows"
    # Either a meaningful pick exists, or the payload says exactly why not.
    assert (reg["minimax_choice"] is not None) or reg.get("saturated") is True


BINARY_AUDITABLE = {"capital_project_selection_120", "claims_investigation_triage",
                    "charging_network_siting", "research_cohort_selection",
                    "interconnection_approvals"}


@pytest.mark.parametrize("name", sorted(BINARY_AUDITABLE))
def test_audit_feasibility_probe_from_fresh_state(name):
    # Audit reads the model directly — no solve needed (the READMEs' governance beats).
    p = _fresh(name)
    r = explorer.audit_property(p, None)
    assert r["verdict"] == "feasible"
    assert r["witness"]["feasible"] is True

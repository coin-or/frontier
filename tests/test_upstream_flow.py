"""Upstream flow: every example's runbook must work end-to-end from the kit.

test_upstream_kits.py proves each kit reconstructs the canonical model verbatim, so
"framed from the kit" and "the canonical model" are the same problem. These tests take
that model with NO baked results (the state a user is in right after step 0), run the
fast solve, and exercise the explore actions its README walkthrough promises — so a
data or engine change that breaks a runbook's later steps fails here, not on camera.

Exact/certify passes are exercised only on the sub-second continuous (LP/QP) shapes;
the binary exact sweeps (led by the 300-option capital showcase) run minutes and stay
out of CI — small-scale binary exact + certify is covered by test_certify.py,
test_certify_curated.py, and test_anchor_corners.py.
"""
import pytest

import solvers
from engine import explorer, problem_io
from engine.models import Approach, ScenarioRun
from engine.optimizer import optimize, optimize_scenarios

# Derived from the bundled library so a new example is covered the moment it lands —
# an example that must NOT run here needs an explicit exclusion, not a forgotten edit.
EXAMPLES = problem_io.list_available()["examples"]
_PROBLEMS = {name: problem_io.load_problem(name) for name in EXAMPLES}

# Continuous shapes the exact gate accepts: their LP/QP pass is sub-second, so the
# certify leg runs in CI. A future slow continuous example would enroll itself here —
# fail-loud; demote it to an explicit exclusion if that ever costs too much.
EXACT_FAST = sorted(name for name, p in _PROBLEMS.items()
                    if p.approach == Approach.proportional and solvers.exact_solver_fits(p)[0])

BINARY_AUDITABLE = sorted(name for name, p in _PROBLEMS.items()
                          if p.approach == Approach.binary)


def _fresh(example):
    """The post-step-0 state: the canonical model with no results."""
    p = _PROBLEMS[example].model_copy(deep=True)
    p.run = p.exact_run = p.scenario_run = None
    p.curated_solutions = []
    return p


@pytest.fixture(scope="module")
def solved():
    """One fast solve per example, memoized on first request — `pytest -k <example>`
    pays for that example's solve only, and one broken example fails its own tests
    instead of erroring the whole module at fixture setup."""
    cache = {}

    def get(name):
        if name not in cache:
            p = _fresh(name)
            p.run = optimize(p, mode="fast", seed=42, max_solutions=25)
            cache[name] = p
        return cache[name]

    return get


@pytest.mark.parametrize("name", EXAMPLES)
def test_solve_and_tradeoffs_from_fresh_state(solved, name):
    p = solved(name)
    assert p.run.solutions, f"{name}: fresh fast solve returned no frontier"
    t = explorer.get_tradeoffs(p)
    assert t["total_solutions"] == len(p.run.solutions)
    assert t["balanced_solution"] is not None
    assert set(t["objective_ranges"]) == {o.name for o in p.objectives}


@pytest.mark.parametrize("name", EXACT_FAST)
def test_exact_certify_and_duals_from_fresh_state(solved, name):
    p = solved(name)
    p.exact_run = optimize(p, mode="fast", seed=42, solver="highs")
    cert = explorer.certify_against_exact(p, p.run, p.exact_run)
    # On continuous shapes the invariant may be violated ONLY by the documented
    # whole-percent rounding of exact optima — the certificate must say so itself.
    assert cert["invariant"]["holds"] or "rounding" in cert["invariant"]["note"]
    assert cert["exact_count"] > 0


@pytest.mark.parametrize("name", EXAMPLES)
def test_scenarios_from_fresh_state(solved, name):
    p = solved(name)
    if not (p.scenario_config and p.scenario_config.enabled and p.scenario_config.scenarios):
        pytest.skip("no scenarios in this example")
    p.scenario_run = ScenarioRun(scenario_runs=optimize_scenarios(
        p, mode="fast", seed=42, max_solutions=15))
    reg = explorer.scenario_regret(p)
    assert reg["available"] is True
    assert reg["per_solution"], f"{name}: regret has no rows"
    # Either a meaningful pick exists, or the payload says exactly why not.
    assert (reg["minimax_choice"] is not None) or reg.get("saturated") is True


@pytest.mark.parametrize("name", BINARY_AUDITABLE)
def test_audit_feasibility_probe_from_fresh_state(name):
    # Audit reads the model directly — no solve needed (the READMEs' governance beats).
    p = _fresh(name)
    r = explorer.audit_property(p, None)
    assert r["verdict"] == "feasible"
    assert r["witness"]["feasible"] is True

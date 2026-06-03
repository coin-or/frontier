"""Pluggable solver backends for Frontier.

Each backend mirrors the engine's existing solve contract (same inputs, returns a
``Run`` of ``Solution``s in the identical shape) so it can be swapped in behind a
gate without any downstream changes. See ``cuopt_backend`` for the cuOpt QP spike
and ``highs_backend`` for the CPU companion.

This module is the **selection surface** the agent reaches through (via the ``solve``
tool's ``solver`` argument) and that ``engine.optimizer.optimize`` reaches through to
route a run. It owns two pure, dependency-light checks so both callers agree:

  * ``available_solvers()`` — which backends can actually run here (the exact ones
    depend on an optional import being present).
  * ``exact_solver_fits(problem)`` — whether a problem's *shape* is one the exact
    backends solve (binary selection, or a quadratic mean-variance portfolio).

Probing availability with ``importlib.util.find_spec`` keeps this importable with no
solver installed; the backends themselves import their solver lazily inside each
inner solve, so nothing here forces a GPU/`highspy` dependency on the default path.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.models import Problem

# The default engine (``nsga``) is pymoo's NSGA-II/III and is always present. The exact
# backends are keyed by the import that gates their availability.
EXACT_SOLVERS = ("highs", "cuopt")
_SOLVER_PROBE = {
    "nsga": None,      # default evolutionary engine — always available
    "highs": "highspy",
    "cuopt": "cuopt",
}


def available_solvers() -> dict[str, bool]:
    """Map each known solver key to whether it can run in this environment.

    ``nsga`` is always True (the default engine). An exact backend is available iff
    its optional dependency is importable — note this is a *presence* check, not a
    *runnable* one: cuOpt also needs a GPU at solve time, which only surfaces then.
    """
    return {
        key: (probe is None or importlib.util.find_spec(probe) is not None)
        for key, probe in _SOLVER_PROBE.items()
    }


def exact_solver_fits(problem: "Problem") -> tuple[bool, str]:
    """Whether an exact backend supports this problem's shape. Returns ``(fits, reason)``.

    Identical scope for both exact backends (they differ only in the inner solve):

      * **binary** select-a-subset → exact MILP.
      * **proportional + quadratic** (mean-variance) with an interaction matrix →
        exact convex QP, the EA picking the support under cardinality/group caps.

    Anything else stays with the default NSGA engine. The ``reason`` explains a
    rejection so the tool can tell the agent *why* an exact run was declined.
    """
    from engine import optimizer as _opt
    from engine.models import Aggregation, Approach

    if problem.approach == Approach.binary:
        return True, ""
    if problem.approach != Approach.proportional:
        return False, (
            "exact backends support binary selection or proportional mean-variance "
            f"portfolios; approach is '{getattr(problem.approach, 'value', problem.approach)}'"
        )
    if not any(o.aggregation == Aggregation.quadratic for o in problem.objectives):
        return False, (
            "proportional problems need a quadratic-aggregated objective (mean-variance "
            "risk) for the exact QP path; this one has none"
        )
    if len(_opt._build_interaction_matrices(problem)) == 0:
        return False, (
            "the quadratic objective needs an interaction (covariance) matrix for the "
            "exact QP path"
        )
    return True, ""

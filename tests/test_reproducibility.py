"""Seeded reproducibility: a fixed seed must reproduce the exact frontier.

pymoo 0.6.1.6 doesn't thread the algorithm's seeded random_state into the survival /
selection operators (they fall back to an unseeded ``default_rng(None)``), which made
NSGA-III runs non-reproducible even at a fixed seed. ``optimizer._seeded_rng_fallback``
shims that fallback. These tests cover the 4-objective (NSGA-III, with niche
tie-breaking) and 2-objective (NSGA-II) paths, in- and cross-call.
"""

import hashlib

from engine.models import CardinalityConstraint, Objective, Option, Problem, Score
from engine.optimizer import OptimizeMode, optimize


def _frontier_hash(run) -> str:
    return hashlib.md5(
        "".join(sorted(s.content_signature for s in run.solutions)).encode()
    ).hexdigest()


def _binary_problem(n_obj: int) -> Problem:
    names = [f"P{i:02d}" for i in range(12)]
    objs = [f"O{j}" for j in range(n_obj)]
    scores = [
        Score(option=n, objective=o, value=float((i * 7 + j * 13) % 11 + 1))
        for j, o in enumerate(objs)
        for i, n in enumerate(names)
    ]
    return Problem(
        approach="binary",
        objectives=[Objective(name=o, direction="maximize" if k % 2 else "minimize")
                    for k, o in enumerate(objs)],
        options=[Option(name=n) for n in names],
        scores=scores,
        constraints=[CardinalityConstraint(min=2, max=6)],
    )


def _proportional_problem(n_obj: int = 3) -> Problem:
    names = [f"A{i:02d}" for i in range(15)]
    objs = [f"O{j}" for j in range(n_obj)]
    scores = [
        Score(option=n, objective=o, value=float((i * 7 + j * 13) % 11 + 1))
        for j, o in enumerate(objs)
        for i, n in enumerate(names)
    ]
    return Problem(
        approach="proportional",
        objectives=[Objective(name=o, direction="maximize" if k % 2 else "minimize")
                    for k, o in enumerate(objs)],
        options=[Option(name=n) for n in names],
        scores=scores,
    )


class TestReproducibility:
    def test_nsga3_same_seed_same_frontier(self):
        # 4 objectives → NSGA-III, which exercises niche tie-breaking each generation.
        p = _binary_problem(4)
        a = optimize(p, mode=OptimizeMode.fast, seed=42)
        b = optimize(p, mode=OptimizeMode.fast, seed=42)
        assert _frontier_hash(a) == _frontier_hash(b)

    def test_nsga2_same_seed_same_frontier(self):
        p = _binary_problem(2)
        a = optimize(p, mode=OptimizeMode.fast, seed=7)
        b = optimize(p, mode=OptimizeMode.fast, seed=7)
        assert _frontier_hash(a) == _frontier_hash(b)

    def test_proportional_same_seed_same_frontier(self):
        p = _proportional_problem(3)
        a = optimize(p, mode=OptimizeMode.fast, seed=42)
        b = optimize(p, mode=OptimizeMode.fast, seed=42)
        assert _frontier_hash(a) == _frontier_hash(b)

    def test_different_seed_can_differ(self):
        # The seed must actually matter — otherwise "reproducible" is vacuous. A
        # proportional problem has a continuous frontier sampled stochastically, so
        # distinct seeds reliably yield distinct allocations (no flaky convergence).
        p = _proportional_problem(3)
        hashes = {_frontier_hash(optimize(p, mode=OptimizeMode.fast, seed=s)) for s in range(6)}
        assert len(hashes) > 1

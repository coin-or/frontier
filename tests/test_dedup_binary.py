"""Binary hash-based duplicate elimination: equivalence, determinism, wiring.

``_BinaryHashDuplicateElimination`` replaces pymoo's O(pop² × n_var) distance-matrix
default on the binary path (profiled at ~92% of large-n solve time) with an exact
O(pop × n_var) hash set. For 0/1 genomes exact equality is the same duplicate
semantics as the default's epsilon-distance, so these tests pin bit-identical
fronts at a fixed seed — the speedup must be performance-only.
"""

import hashlib

import numpy as np
from pymoo.core.duplicate import DefaultDuplicateElimination
from pymoo.core.population import Population

import engine.optimizer as optimizer
from engine.models import CardinalityConstraint, Objective, Option, Problem, Score
from engine.optimizer import (
    OptimizeMode,
    _BinaryHashDuplicateElimination,
    _tune_parameters,
    optimize,
)


def _frontier_hash(run) -> str:
    return hashlib.md5(
        "".join(sorted(s.content_signature for s in run.solutions)).encode()
    ).hexdigest()


def _binary_problem(n_options: int, n_obj: int = 3, max_pick: int | None = None) -> Problem:
    names = [f"P{i:03d}" for i in range(n_options)]
    objs = [f"O{j}" for j in range(n_obj)]
    scores = [
        Score(option=n, objective=o, value=float((i * 7 + j * 13) % 23 + 1))
        for j, o in enumerate(objs)
        for i, n in enumerate(names)
    ]
    return Problem(
        approach="binary",
        objectives=[Objective(name=o, direction="maximize" if k % 2 else "minimize")
                    for k, o in enumerate(objs)],
        options=[Option(name=n) for n in names],
        scores=scores,
        constraints=[CardinalityConstraint(min=2, max=max_pick or max(3, n_options // 3))],
    )


class TestHashEliminatorSemantics:
    """The hash eliminator reproduces the default's marks exactly on 0/1 genomes."""

    def _random_binary_pop(self, rng, n_ind, n_var, as_float=False):
        X = rng.random((n_ind, n_var)) < 0.4
        if as_float:
            X = X.astype(float)  # operators sometimes hand back 0.0/1.0 floats
        return Population.new("X", X)

    def test_matches_default_within_population(self):
        rng = np.random.default_rng(3)
        for n_var in (5, 8, 13):  # exercise n_var not a multiple of 8 (packbits padding)
            pop = self._random_binary_pop(rng, 60, n_var)  # small space → real duplicates
            expect = DefaultDuplicateElimination()._do(pop, None, np.full(len(pop), False))
            got = _BinaryHashDuplicateElimination()._do(pop, None, np.full(len(pop), False))
            assert np.array_equal(got, expect)

    def test_matches_default_against_other(self):
        rng = np.random.default_rng(4)
        pop = self._random_binary_pop(rng, 40, 6)
        other = self._random_binary_pop(rng, 40, 6)
        expect = DefaultDuplicateElimination()._do(pop, other, np.full(len(pop), False))
        got = _BinaryHashDuplicateElimination()._do(pop, other, np.full(len(pop), False))
        assert np.array_equal(got, expect)

    def test_float_and_bool_genomes_agree(self):
        rng = np.random.default_rng(5)
        pop_bool = self._random_binary_pop(rng, 50, 9)
        pop_float = Population.new("X", pop_bool.get("X").astype(float))
        a = _BinaryHashDuplicateElimination()._do(pop_bool, None, np.full(50, False))
        b = _BinaryHashDuplicateElimination()._do(pop_float, None, np.full(50, False))
        assert np.array_equal(a, b)


class TestEngineEquivalence:
    def test_frontier_identical_to_default_eliminator(self, monkeypatch):
        """Same problem, same seed — hash vs default eliminator, bit-identical front."""
        p = _binary_problem(24)
        with_hash = optimize(p, mode=OptimizeMode.fast, seed=11)
        # Reverting the wiring to ``eliminate_duplicates=True`` selects pymoo's default.
        monkeypatch.setattr(optimizer, "_BinaryHashDuplicateElimination", lambda: True)
        with_default = optimize(p, mode=OptimizeMode.fast, seed=11)
        assert _frontier_hash(with_hash) == _frontier_hash(with_default)

    def test_determinism_at_duplicate_heavy_scale(self):
        # Large enough that dedup fires constantly (tight cardinality → many collisions).
        p = _binary_problem(60, max_pick=5)
        a = optimize(p, mode=OptimizeMode.fast, seed=42)
        b = optimize(p, mode=OptimizeMode.fast, seed=42)
        assert _frontier_hash(a) == _frontier_hash(b)


class TestPerfFloor:
    def test_eliminator_linear_at_industrial_size(self):
        """O(pop × n_var) floor: pop 2000 × n_var 3000 in well under a second.

        The default's O(pop² × n_var) distance matrix takes tens of seconds here
        (92% of a 300s solve in the n=3000 profile), so a very loose bound still
        fails loudly if someone reintroduces quadratic dedup on the binary path.
        Together with TestWiring this guards the whole regression surface without
        a flaky full-solve wall-clock test.
        """
        import time

        rng = np.random.default_rng(6)
        pop = Population.new("X", rng.random((2000, 3000)) < 0.5)
        t0 = time.monotonic()
        _BinaryHashDuplicateElimination().do(pop)
        assert time.monotonic() - t0 < 5.0


class TestWiring:
    def test_binary_path_uses_hash_eliminator(self):
        alg, _ = _tune_parameters(_binary_problem(12), OptimizeMode.fast)
        assert isinstance(alg.eliminate_duplicates, _BinaryHashDuplicateElimination)

    def test_proportional_path_keeps_default(self):
        names = [f"A{i}" for i in range(8)]
        p = Problem(
            approach="proportional",
            objectives=[Objective(name="O0", direction="maximize"),
                        Objective(name="O1", direction="minimize")],
            options=[Option(name=n) for n in names],
            scores=[Score(option=n, objective=o, value=float(i + j))
                    for j, o in enumerate(["O0", "O1"]) for i, n in enumerate(names)],
        )
        alg, _ = _tune_parameters(p, OptimizeMode.fast)
        assert isinstance(alg.eliminate_duplicates, DefaultDuplicateElimination)

# Optimization Strategy — Exact Solvers Depth

Deep guidance for the exact-solver flow in `frontier://skills/optimization_strategy` (its core Exact Solvers section carries the stage trigger and the engine table). Fetch at need: `get_skill('optimization_strategy', section='Exact Solvers — Depth')`. This file owns the *produce* side — when to reach for exact, which scope, what to run. Reading the results back lives in `frontier://skills/solution_interpreter`: *Reading the Certificate (explore certify)* for the certificate blocks, *Exact Sensitivity — Shadow Prices & Reduced Costs (solver duals)* for the duals fields.

## Exact Solvers — Depth

### The three certifiable shapes

Exact is possible **only** for:

- **Binary selection with additive (`sum`) objectives** — every combinatorial constraint (cardinality, force in/out, dependency, exclusion, group limit, objective bound) is linear-integer; solved as a MILP.
- **Proportional mean-variance portfolio** — one **minimize**-`quadratic` risk objective with an interaction/covariance matrix, alongside `sum`/`avg` linear objectives; solved as a convex QP.
- **Purely linear proportional allocation** — ≥2 `sum`/`avg` objectives with no quadratic term; solved as an exact multi-objective LP.

Everything else stays with NSGA. `solve validate`'s `solvers` block reports `available` and `exact_fits_shape` for this problem, so you know whether exact is even on the table before raising it. A request that isn't installed or doesn't fit returns a clear error (no silent fallback), and the engine that ran is echoed as `solver_used`.

### The certify flow, step by step

**Reach for it by stage, not up front.** The trigger isn't an engine the user picks — it's a point they reach: a supported formulation, finalized, with curated candidates they're about to commit to. Let it emerge from the normal flow:

1. **Explore with the EA.** NSGA reveals the frontier shape, tradeoffs, binding constraints, and how scenarios shift the achievable set. This is where the user does the real work — navigating, narrowing. Stay here through exploration and refinement.
2. **Curate candidates** (`explore curate`) — the decision narrows to a handful of picks.
3. **Re-solve exactly** with `solver="highs"` (or `"cuopt"`) once the shape qualifies:
   - The default `scope="curated"` **certifies the frontier you explored** — it exact-solves only your NSGA run's points (any supported shape: binary MILP or proportional QP/LP), so it's fast and usually returns inline. Run a `solve run` first so there's a frontier to certify; with none yet it falls back to a full pass.
   - `scope="full"` makes exact optimization *drive* the exploration, not just certify it — the exact solver runs on every evaluation. Heavier, and usually **backgrounds** to a `{status:"running"}` handle to poll (see *Long Solves Run in the Background*).
   - Either way the result is stored as the **exact overlay** (`exact_run`) *alongside* the NSGA frontier, never replacing it. The scope that ran echoes as `overlay_scope`, and you can navigate the overlay directly with `explore … source="exact"`.
4. **Run `explore certify`** (no params — it checks the exploratory NSGA run against the overlay). The certificate is identical on HiGHS or cuOpt. What each block means and how to present it: `frontier://skills/solution_interpreter` → *Reading the Certificate (explore certify)*.
5. **Close any gaps.** A `completeness` verdict of `under_covered` names witness-backed `gap_regions` — frontier regions the heuristic run holds but the exact sweep never sampled. Close them with `solve(solver=…, scope="fill_gaps")` using the overlay's own backend: a targeted pass that re-solves only those witnesses and merges them in. A gap whose solve hits its budget is discarded and reported in the `fill` block (`unfilled`, `unfilled_witness_ids`) — those regions honestly stay heuristic-best. Re-run `explore certify` after a fill for the updated verdict.

**`exact=true` is a separate, rarely-needed knob.** Pass it only when you need a *formal* zero-gap certificate (a "prove it's optimal" requirement): it drops the default 0.1% gap and solves the MILP to a proven optimum. Slower, and usually the *same* plan — at a 0.1% gap the incumbent is typically already optimal, just not *proven* so (the gap is the solver's remaining certificate margin); `exact=true` closes that proof, and can occasionally surface a plan up to 0.1% better. MILP-only; the QP path is already exact.

### Where exact wins — calibrate the claim to the instance

On a small, already-explored problem the heuristic usually already sits on the frontier, so exact's job is *confirmation* (trust), not a better answer — say that honestly rather than overselling. The catchable slack (dominated points, and the coverage the certificate reports) grows with problem size, so lead with *trust* at small scale and *coverage* at large. Then:

- **Lead with the risk corner for mean-variance.** Exact's clean, repeatable win is the convex variance/risk corner — the minimum-risk portfolio (most-diversified sourcing, firmest grid). That flat bowl is where heuristics wobble and a QP nails it; make it the headline.
- **Per-objective extremes are anchor-sampled — a "short" exact corner should be rare.** Every exact overlay adds one anchor solve per objective (the ε-constraint payoff-table step), so the frontier's extremes don't depend on the EA's sampling budget. A corner that still reads `under-sampled` is an EA-budget signal — from the one shape that defers corners to its seeded search (a cardinality/group-capped mean-variance QP) or from an interior region — not exact being weaker. A denser sweep closes it; don't frame it as a capability gap.

### Where the gate declines — and what to offer instead

- **Non-convex shapes.** A maximize-direction quadratic objective isn't convex; `solvers.exact_solver_fits` declines it rather than overclaim — that stays NSGA. The same goes for *combinatorial membership* on a proportional shape — exclusion pairs, dependencies, cardinality floors above 1, group-limit floors — which gate which options are ACTIVE and can't live in a convex QP/LP (`force_include`/`force_exclude` are fine: they fold into the variable box). A MAX bound on the quadratic risk objective IS served (enforced by exact post-filtering); a MIN floor on it declines. Duals / shadow prices likewise exist on the continuous QP/LP paths only, never for the MILP.
- **Aggregations the backend doesn't formulate — offer a redefine.** The exact MILP is linear, so on a *binary* problem only `sum` objectives certify. `avg` (a fractional ratio over a variable-size pick) and `quadratic` are genuinely outside a linear MILP; `min`/`max` are linearizable *in principle* — their convex direction (maximin / minimax) admits an epigraph reformulation — but the gate doesn't build it. Say "the backend doesn't formulate this," not "it's impossible" — a user who knows the epigraph trick is right that maximin is representable; Frontier just declines it rather than reaching for a bespoke reformulation. On a *portfolio*, `min`/`max` are nonlinear as written and out of scope. The gate declines with a reason instead of silently optimizing the sum. These aggregations run perfectly well on **NSGA** — so when a user wants certification on such a problem, surface the choice plainly rather than dropping it: *redefine the objective as `sum` if a total is what they mean (often it is — total value, total cost, total risk exposure), then certify; or keep the aggregation as a per-member quality/level and explore with the heuristic.* Naming the tradeoff (a `sum` total vs an `avg` quality answer different questions) is the framing help — route it back to `problem_framing` if the intended reading is unclear.
- **"Optimal for its scalarization" can be *weakly* Pareto-efficient on LP/MILP.** Each exact point is optimal for its ε-target, but when that inner solve has ties (alternate optima at the ε boundary — common on integer MILP, possible on a degenerate LP) the winner can be matched on its own axis and beaten on another by some other plan. The **QP** is immune only insofar as its interaction matrix is genuinely positive-definite — a near-singular covariance estimate (common in practice) brings ties effectively back. So keep the certified claim scoped to *"optimal for its tradeoff,"* never *"the single best outcome here, nothing else reaches it"* — and on LP/MILP keep leaning on `explore certify`'s dominance check and `explore composition` to surface look-alike plans.

### The offer

Make it plainly at the commit point: *"You've narrowed to three; this shape lets me re-run it exactly and certify against the heuristic frontier — confirming each pick is optimal to a fraction of a percent, sharpening the risk corner, and flagging any heuristic slack. Worth it before you commit?"* If the shape doesn't qualify, don't raise it — the EA frontier is the answer. Always say which engine produced a result, and claim optimality **only** on an exact run.

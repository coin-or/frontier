# Phase 1 Remaining — Design Plan

**Status:** Draft for review
**Scope:** 4 not-done + 2 partial items from [Phase 1 Requirements - Solution Exploration](../../~/Documents/Obsidian_Vault/projects/frontier/Phase%201%20Requirements%20-%20Solution%20Exploration.md). Prioritization and design choices open for user input — see [Open Questions](#open-questions).

---

## Framing: what each item is worth to the user

Ranked rough-cut by user value before design effort:

| # | Item | Core user need | Effort |
|---|---|---|---|
| 1 | Binding relaxation guidance | "Which constraint is costing me the most, and what do I gain by loosening it?" — often more actionable than picking a solution | M |
| 2 | CVaR risk measures | "In the worst 10% of scenarios, how bad does this solution get?" — lets risk-averse users choose solutions that hold up under tails, not just means | M |
| 3 | Curated export | "Get these 3 solutions out of Frontier and into my deck / doc / email" — the handoff moment where Frontier either lands the recommendation or doesn't | S |
| 4 | Objective redundancy (MI) | "Are two of my objectives secretly measuring the same thing?" — prevents over-counting in the frontier and simplifies 4+ obj problems | S |
| 5 | Seed parameter | "Can I re-run this and show someone the same result?" / "Is this frontier stable or did I get lucky?" — reproducibility + variance testing | XS |
| 6 | Shape analysis — PCA extension | "With 4+ objectives, which pairs are the *real* tradeoffs?" — makes high-dim frontiers legible | M |

---

## 1. Binding Constraint Relaxation Guidance (partial → full)

### User story
> I constrained my budget to $500k and capped headcount at 12. Frontier returns a frontier. I want to know: **is one of those constraints actually limiting my outcomes, and by how much?** If loosening the headcount cap from 12 to 13 unlocks a big jump in value, I'd go fight that fight. If it barely moves, I won't bother.

This is often more valuable than the optimal solution itself — it tells the user what to negotiate.

### Current state
- Detects binding `objective_bound`, `cardinality`, `group_limit` via 95% threshold
- Reports pattern + label + extreme value in diagnostics
- No quantification of the cost of the binding

### Proposed design
Add `binding_analysis` block to the explore/tradeoffs response:

```json
"binding_analysis": [
  {
    "constraint": "budget <= 500000",
    "binding_fraction": 0.98,  // 98% of frontier solutions hit this
    "relaxation_10pct": {
      "objective_gains": {"NPV": "+8.2%", "IRR": "+1.1pp"},
      "confidence": "high"
    },
    "suggestion": "Budget is the most load-bearing constraint. A 10% lift (→$550k) appears to unlock meaningful NPV."
  }
]
```

**How to estimate the 10% gain:** two candidate methods — pick one:
- **(a) Shadow price / local sensitivity:** derivative of Pareto hypervolume wrt constraint bound, computed from solutions near the binding surface. Cheap, approximate.
- **(b) Re-solve with relaxed bound:** actually run a second (smaller) optimization with the constraint at 110% and diff the frontiers. Expensive but honest.

For cardinality / group_limit (discrete): relaxation means +1 slot; same estimation logic.

### Skill coupling
`solution_interpreter` gets a new section: how to surface binding analysis in plain language without sounding like a solver spewing numbers.

---

## 2. CVaR Risk Measures (F4)

### User story
> I have 4 scenarios: base, recession, boom, supply shock — weighted 40/20/30/10. Expected NPV is fine, but in the recession scenario this solution *tanks*. I want solutions that are robust in the tail, not just on average.

CVaR = expected value *conditional* on being in the worst tail (e.g., "average outcome in the worst 10% of scenarios").

### Current state
Scenario analysis computes probability-weighted expected values across scenarios. No tail metrics.

### Proposed design
Extend scenario results with tail metrics per solution per objective:

```json
"scenario_risk": {
  "NPV": {
    "expected": 12.4,
    "worst_case": 3.1,       // min across scenarios
    "cvar_20": 5.8,          // mean of worst 20% by probability mass
    "cvar_10": 3.1,          // mean of worst 10% (here: just the supply shock)
    "range": [3.1, 18.2]
  }
}
```

Then surface a risk-ranked view: "among your curated solutions, solution B has 22% lower expected NPV but 2.3× better CVaR-10."

### Design choices inside this
- **CVaR-α fixed or user-selectable?** Fixed presets (10%, 20%) keep the UX simple; user-selectable adds tuning burden.
- **Integrate into curation compare, or new tool response?** Argue for folding into existing scenario response so no new tool surface.
- **Does CVaR become an objective?** Phase 2 territory (robust optimization). For Phase 1, it's a *diagnostic*, not an optimization target.

---

## 3. Curated Solution Export (F8)

### User story
> I narrowed down to 3 curated solutions. Now I need to put them in a deck for my boss. I don't want to hand-transcribe scores from a JSON blob.

### Current state
`curate/uncurate/rename/list/compare` only. `compare` returns structured JSON; nothing formatted for handoff.

### Proposed design
New action `export` on the curation tool with format options:

```python
curate(action="export", format="markdown" | "csv" | "brief")
```

- **markdown:** ready-to-paste table + one short paragraph per solution explaining its tradeoff profile (from solution_interpreter-style framing)
- **csv:** solutions × (options + objectives + metadata), for Excel/Sheets
- **brief:** one-page-per-solution narrative: "Solution B ('Balanced'): favors X over Y, binding on budget, best-in-curated on risk-adjusted NPV"

The `brief` format is the differentiator — it's what makes the export *Frontier's* work, not just a CSV dump.

### Skill coupling
`solution_interpreter` already has the framing language. Export pulls from it rather than duplicating prose logic in the engine.

---

## 4. Objective Redundancy via Mutual Information (F9)

### User story
> I defined 5 objectives. Two of them — "customer satisfaction" and "NPS" — are probably measuring the same thing. Frontier is wasting search effort treating them as independent axes.

### Current state
Pearson correlation between objective vectors across the frontier, surfaced in tradeoffs response as a redundancy flag when |r| > threshold.

### Proposed design
Replace (or augment) Pearson with **mutual information** on the frontier samples:

- Captures non-linear redundancy (e.g., two objectives that agree except at extremes)
- Normalized MI ∈ [0, 1] — 0 = independent, 1 = deterministic function of each other
- Threshold at ~0.7 for "likely redundant" flag

Output addition:
```json
"objective_redundancy": [
  {"pair": ["CSAT", "NPS"], "mi_normalized": 0.84, "note": "likely redundant — consider dropping one"}
]
```

### Tradeoff
MI requires binning / KDE; with <50 solutions it's noisy. Guard with sample-size check; fall back to Pearson + a "low confidence" note when frontier is small.

---

## 5. Optional Seed Parameter

### User story
> Two needs:
> (a) **Reproducibility:** "Re-run this and get the same frontier so I can share it with my team."
> (b) **Variance testing:** "Vary the seed — if the frontier shape is stable, I trust it. If it jumps around, the problem is underspecified."

### Current state
Seed hardcoded at 42 throughout optimizer and hypervolume approximation.

### Proposed design
Add `seed: int | None = None` to `solve` tool. Semantics:

- `None` (default) → use a fresh random seed, return it in the response so the user *can* reproduce if they want
- explicit int → deterministic run

Response includes `"seed_used": 17234` so reproducibility is always recoverable even when not requested up front.

**Trivial change. Main question is just whether it gets exposed on `solve` only, or also on `explore` for any stochastic analyses.**

---

## 6. Frontier Shape Analysis — PCA Extension for 4+ Objectives

### User story
> I have 6 objectives. Pairwise shape classifications give me 15 plots' worth of detail — cognitive overload. I want to know: **what are the 2–3 principal tradeoff axes?** e.g., "most of your frontier's variation is along (cost vs. quality) and (speed vs. safety) — the other objectives mostly move with those."

### Current state
Pairwise shape classification (linear/concave/convex/discontinuous) is done. No dimensionality reduction.

### Proposed design
When #objectives ≥ 4, run PCA on the normalized frontier solutions (objective values as features):

```json
"principal_axes": [
  {"variance_explained": 0.62, "loadings": {"cost": -0.71, "quality": 0.68, "speed": 0.15, ...}},
  {"variance_explained": 0.24, "loadings": {"speed": 0.81, "safety": -0.55, ...}}
]
```

Surface in `solution_interpreter` as: "Your 6-objective frontier really varies along 2 main axes: cost-vs-quality (62% of variance) and speed-vs-safety (24%). The other objectives are largely determined by these."

This **composes with F9 (redundancy):** if PCA shows obj-X has ~0 loading on the first 3 PCs, and MI flags it as redundant with obj-Y, that's a strong signal to drop it.

### Defer trigger
Only run PCA when #objectives ≥ 4 (below that, pairwise shapes are already legible).

---

## Cross-cutting design choices

1. **Where does this go in the response?** Current `explore` returns tradeoffs + diagnostics. Adding 4 new blocks (binding_analysis, scenario_risk, objective_redundancy, principal_axes) risks a response-bloat problem. Options:
   - (a) Add all to `explore` default
   - (b) Add, but gate each behind a `include=[...]` param
   - (c) New tool `diagnose` that bundles them, keeping `explore` lean

2. **Skill updates:** several items have guidance in `solution_interpreter` already or should. Need to refresh the skill once engine lands — budget one pass per item.

---

## Open Questions

**Prioritization**
1. Rank order above feels right to me (binding > CVaR > export > MI > seed > PCA). Agree, or should something move? In particular: is **seed** a blocker for any upcoming demo / eval that would bump it up?
2. Is there an appetite to ship this as one "Phase 1 complete" push, or slice it into 2–3 PRs with user testing between?
3. Anything here that should actually defer to Phase 2 / drop entirely — e.g., is PCA over-engineering for current user scale?

**Design**
4. **Binding relaxation:** shadow-price estimate (fast, approximate) vs. re-solve at +10% (honest, expensive). Preference? Or offer both with a `method` param?
5. **CVaR:** fixed α (10%, 20%) or user-selectable? And does CVaR stay diagnostic, or do you want it as an optimization target (robust-frontier) — the latter is Phase 2 scope but worth flagging.
6. **Export `brief` format:** is the "narrative per solution" worth the effort, or is markdown table + CSV enough for now?
7. **MI vs Pearson:** replace Pearson entirely, or run both and flag disagreement cases? (Disagreement is itself informative — "linearly uncorrelated but non-linearly dependent" is a pattern worth surfacing.)
8. **Seed on `explore` too**, or `solve` only?
9. **Response structure:** (a) add all blocks to `explore`, (b) `include=[...]` gating, or (c) new `diagnose` tool? This is the biggest architectural choice.

**User research**
10. Any recent user conversations / eval results that should sharpen the framing above? The Phase 1 doc is written from design principles — curious if actual user asks shift any priorities.

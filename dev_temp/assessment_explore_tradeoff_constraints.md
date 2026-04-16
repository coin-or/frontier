# Assessment: Solution Exploration, Tradeoff Assessment, Constraint Respect

Three lenses applied to the same 30-ETF problem (single + scenarios). All data from actual run outputs.

---

## 1. Solution Exploration

*How thoroughly does the method search the decision space, and how well can the user navigate what it found?*

### Frontier

**Search coverage:** 182 solutions (single), 329/scenario (1,316 total). Widest objective ranges on all 3 axes — return 2.1–20.2%, vol 2.6–20.0%, yield 0.1–5.8%. The solver finds concentrated corner solutions (VGSH 97% for safety, GLD 56% + VDE 41% for growth) that the other methods miss entirely.

**Navigation:** The explore tool chain (tradeoffs → solution → compare → curate → compare_curated → marginal_analysis) lets the agent walk the frontier interactively. 178 solutions exist between the 4 curated anchors and are accessible on demand. The response "there are 178 other Pareto-optimal portfolios between these anchors — if you lean toward one direction, we can explore the gradations" is a promise the system can actually deliver on.

**Scenario gap (now fixed):** Before the bug fix, explore tools only accessed the base case — you could optimize 4 scenarios but only inspect one. With the `scenario` parameter now wired through, per-scenario tradeoffs, solutions, curation, and marginal analysis are all accessible.

**Remaining issue:** 329 solutions × 30 allocations overflows MCP token limits, forcing file-based fallback. The agent can't see raw solutions inline — it must use explore tools. This is a design constraint, not a bug, but it means the agent is fully dependent on the explore tool chain.

### pymoo

**Search coverage:** 45 solutions (single), 37–42/scenario (158 total). The frontier is compressed — max return 14.2% vs Frontier's 19.0%, min vol 9.2% vs Frontier's 3.1%. The repair operator's sequential normalization prevents concentrated allocations, so the solver never finds the VGSH-dominated safety corner or the GLD-dominated growth corner. All 4 curated strategies have exactly 12 holdings (the cardinality max) — a repair artifact, not an optimization result.

**Navigation:** None built in. The agent has raw JSON with 45 solutions and must write custom code to traverse it. In the scenario eval, the agent wrote ~30 lines of cross-scenario analysis code to compute robustness frequencies. Useful, but throwaway — must be rewritten for every new problem.

**Scenario strength:** Per-scenario curated strategies with specific allocations are directly available (the agent computed them). Frequency-based robustness (DBA 78%, HYG 77%, VGSH 74%) is the most actionable robustness metric across all 3 methods.

### LLM

**Search coverage:** 4 solutions (single), 16 total (4 strategies × 4 scenarios). The LLM evaluated ~40–50 candidates by hand and selected the best it found. This is a tiny fraction of the feasible space — at 30 ETFs with proportional allocation, the space is effectively infinite.

**Navigation:** There is no frontier to navigate. The LLM presents 4 take-it-or-leave-it portfolios. The response "the question is which tradeoff you can live with" is rhetorical — there are no intermediate portfolios to show. If the user says "I want something between Growth and Balanced," the LLM must construct a new portfolio from scratch.

**What it gets right:** The LLM's Growth portfolio (18.58% return) gets close to Frontier's (19.01%). But this is a lucky hit — one good point on a surface that has 182+ optimal points.

### Verdict

| | Frontier | pymoo | LLM |
|---|:---:|:---:|:---:|
| Solutions found | 182 / 1,316 | 45 / 158 | 4 / 16 |
| Frontier coverage (return range) | 17.7pp | 10.4pp | 17.0pp |
| Frontier coverage (vol range) | 15.7pp | 8.2pp | 15.5pp |
| Navigable by user? | Yes (explore tools) | No (custom code) | No (ask again) |
| Intermediate solutions available? | 178 between anchors | ~41 between anchors | 0 |

---

## 2. Tradeoff Assessment

*How well does each method quantify what you give up to get more of what you want?*

### Frontier

**Computed marginal rates from 182 data points.** The tradeoff quantification is derived from the actual Pareto surface:

- Safety → Balanced: +7.6pp return costs +8.0pp vol (1:1 ratio)
- Balanced → Growth: +9.1pp return costs +6.5pp vol, sacrifices 2.8pp yield
- Balanced → Income: +2.0pp yield costs -5.6pp return but *reduces* vol by 2.6pp

The last finding — that income and stability go together — is a structural insight that only emerges from dense frontier coverage. It's counterintuitive (more yield = less risk?) but correct: HYG has moderate vol (7.9%) and high yield (5.9%), so concentrating in it pushes both yield up and vol down relative to equity-heavy balanced portfolios.

**Correlation-backed:** Return↔Vol r=+0.94, Return↔Yield r=-0.89, Vol↔Yield r=-0.68. These are computed from 182 solutions, not asserted. The agent can answer "what's the cheapest way to gain 1% yield?" with a computed answer from marginal_analysis.

**Scenario tradeoffs (now accessible):** With the scenario explore fix, per-scenario marginal rates are available. The inflation scenario's growth portfolio hits 26.5% return (pymoo) — Frontier's per-scenario tradeoff surface would show exactly how much vol that costs relative to base case growth.

### pymoo

**Computed from 45 solutions, narrower range.** The agent reports:

- Safety → Growth: +9.24pp return costs +7.64pp vol and -1.92pp yield
- "Each additional point of return costs roughly 0.83 points of volatility"

This is honest and computed, but from a compressed frontier. The 0.83 vol-per-return ratio is higher than Frontier's actual rate because pymoo's frontier doesn't reach the corners where the rate changes. The true marginal rate near Growth is steeper (more vol per return) and near Safety is shallower — pymoo's compressed frontier smooths this out.

**Recession finding is the sharpest tradeoff insight across all methods:** The Balanced=Safety collapse. In recession, the Pareto front compresses on the return axis so severely that there is no meaningful balanced portfolio — you're either in gold/infrastructure for growth or in short-term bonds for safety. The optimizer proves this isn't a missing portfolio; it's a missing *region* of the tradeoff surface. No other method surfaced this structural finding.

**Income recession tradeoff:** -1.75% return for 5.40% yield. The optimizer says: yes, you can have income in a recession, but you will lose principal. This is an honest, uncomfortable answer that the LLM's judgment avoided but that the data supports.

### LLM

**Computed from 4 hand-picked portfolios.** The tradeoff quantification is gap measurement between self-constructed points:

- Growth → Income: -15.77pp return for +4.16pp yield

This is a real number, but it measures the gap between two of the LLM's own guesses, not the actual Pareto surface. The gap could be larger or smaller depending on which portfolios were constructed. With only 4 points, there's no way to know whether the tradeoff rate is linear, convex, or has knee points.

**Missing middle:** At 6% target return, Frontier achieves 7.2% vol. pymoo needs 13.2%. The LLM has *no solution at all* — its Safety is at 1.6% return and its Balanced is at 9.8%, with nothing in between. A user asking "what if I want moderate growth with low risk?" gets no answer.

**Where LLM tradeoff judgment adds value:** The LLM's recession income portfolio (3.12% return, 4.09% yield) reflects a tradeoff judgment that the optimizers don't make: it reduced HYG from 50% to 10% because -2% return in recession makes HYG a yield trap that destroys capital. pymoo dutifully maximized yield and shipped -1.75% return. The LLM's intuition that "income should not mean losing money" is not captured by the objective function but is captured by human reasoning.

### Verdict

| | Frontier | pymoo | LLM |
|---|:---:|:---:|:---:|
| Tradeoff source | 182-point Pareto surface | 45-point compressed surface | 4-point gap measurement |
| Marginal rates computed? | Yes (per objective pair) | Yes (aggregate) | No |
| Knee points detected? | Yes (marginal_analysis) | No | No |
| Non-obvious insight? | Income + stability linked | Balanced=Safety collapse in recession | HYG yield trap in recession |
| Can answer "what does 1% more yield cost?" | Yes, with computed rate | Approximately | No |

---

## 3. Respecting Constraints

*Does the method guarantee feasibility? Where does it cut corners or ride boundaries?*

### The 4 constraints

1. Weighted-average volatility ≤ 20%
2. At most 3 Sector ETFs held
3. At most 3 Alternative ETFs held
4. Between 4 and 12 holdings total

### Frontier

**Structurally infeasible solutions are impossible.** Constraints are encoded in the solver — every solution in the Pareto set satisfies all 4 constraints by construction. Across 1,316 solutions (4 scenarios), there are zero violations.

**Boundary behavior:** The Growth portfolio rides the vol constraint at 19.98% — 0.02% headroom. This is correct: the solver found the exact efficient point where adding more return would violate the vol bound. The cardinality constraint binds at the minimum (4–5 holdings for extremes) and max (12 for diversified solutions). The solver uses the full constraint space.

**Dominated options and minimum allocations:** 19 options were flagged as dominated at score entry, but still appear in Pareto solutions at 1% allocations (the minimum for proportional mode). This is mathematically valid — a 1% allocation to a dominated option can be part of an optimal portfolio when cardinality constraints force 4+ holdings — but can confuse users. The solver respects the constraint, but the result looks odd.

### pymoo

**Constraints enforced by repair operator, not solver structure.** The 75-line `PortfolioRepair` class applies corrections sequentially:
1. Truncate to top 12
2. Enforce min 4 holdings
3. Cap sector/alternatives at 3 each
4. Round to integer weights summing to 100%
5. Handle edge cases where rounding drops holdings below minimum

**Zero violations in output** — all 158 solutions across 4 scenarios satisfy all constraints. But the enforcement mechanism introduces artifacts:

- **Over-diversification:** The repair operator's normalization spreads weight too broadly. All 4 curated strategies have exactly 12 holdings. The solver never finds the VGSH-97% safety corner (min vol 9.2% vs Frontier's 3.1%) because the repair operator adds holdings to meet cardinality and then redistributes weight.
- **Fragility:** The sequential repair steps can interact. Zeroing out a sector holding for the cap constraint can drop below the min-4 threshold, requiring a second pass. The implementation handles this case but does not loop, so a pathological sequence could slip through. No evidence this happened in practice.

**The constraint system works but over-constrains the solution.** The repair operator is a net that catches violations — but it also catches solutions that were valid before repair. This is the root cause of pymoo's compressed frontier.

### LLM

**Constraints verified by manual arithmetic, shown in full.** Every portfolio includes a "Weighted vol:" line computing the weighted average, a holding count, and implicit sector/alternative counts. Example from base Growth:

```
Weighted vol: 0.30*15.91 + 0.10*26.59 + 0.10*21.47 + 0.20*15.63 + 0.15*15.32 + 0.15*12.20
= 4.773 + 2.659 + 2.147 + 3.126 + 2.298 + 1.830 = 16.83%
```

**All 16 portfolios satisfy all 4 constraints.** But the verification is fragile:

- **Vol ceiling riding:** Base Growth hits 16.83%, recession Growth hits 11.61%. These have headroom. But the single-problem Growth (from run2) hit 19.98% — 0.02% margin. One arithmetic error or one different allocation and it would violate.
- **Sector/Alternative tracking across 16 portfolios:** The LLM must mentally track which ETFs belong to which group across 4 strategies × 4 scenarios. It flags this as an acknowledged risk: "easy to miss when constructing many portfolios quickly."
- **Arithmetic precision:** The LLM acknowledges "errors on order of 0.01-0.05%" and "10-20% chance of at least one material arithmetic error" across ~150 calculations. A 0.05% error on a portfolio at 19.98% vol could push it to 20.03% — infeasible but undetected.
- **Scaling:** 4 constraints on 30 options is manageable. At 100 options with 10 constraints, manual verification breaks.

**The LLM's constraint respect is a best-effort manual process.** It works here. It would not work reliably at scale.

### Constraint comparison at a glance

| | Frontier | pymoo | LLM |
|---|:---:|:---:|:---:|
| Guarantee mechanism | Solver structure | Repair operator | Manual arithmetic |
| Violations found | 0 / 1,316 | 0 / 158 | 0 / 16 |
| Guarantee is structural? | Yes | No (code quality dependent) | No (arithmetic dependent) |
| Vol constraint headroom (Growth) | 0.02% (precise) | 3.15% (over-conservative) | 0.02% (lucky) |
| Cardinality usage | 4–12 (full range) | 12 only (repair artifact) | 4–7 (manually chosen) |
| Scales to 100+ options, 10+ constraints? | Yes | Yes (with rewrite) | No |
| Constraint artifacts? | Dominated options at 1% | Over-diversification | Near-ceiling riding |

---

## Summary: Three Lenses, One Pattern

The same structural difference shows up in all three lenses:

**Frontier** provides computed, navigable, guaranteed results — but until the scenario explore fix, it could only deliver this for the base case. The fix closes the most critical gap.

**pymoo** provides honest, auditable results with the best cross-scenario insight (Balanced=Safety collapse, frequency-based robustness) — but the engineering burden is high, the repair operator compresses the frontier, and all 362 lines of code are throwaway.

**LLM** provides judgment and narrative that occasionally outperforms the optimizers (avoiding the -1.75% income portfolio) — but at the cost of 16 portfolios vs 1,316, no navigable frontier, manual constraint verification that wouldn't survive scaling, and at least one dominated portfolio (Balanced) that the user would have no way to detect.

The single most telling data point across all three lenses: **at 6% target return, Frontier achieves 7.2% vol, pymoo needs 13.2%, and the LLM has no solution.** That 6pp vol gap is real money left on the table — not in theory, in a portfolio someone would hold.

# Scenario Evaluation Comparison: Frontier vs pymoo vs LLM-Only

**Date:** 2026-04-13
**Problem:** 30-ETF portfolio, 3 objectives, 4 constraints, 4 macro scenarios
**Assignment:** `/dev_temp/scenario_assignment.md` (identical for all methods)

---

## 1. Setup & Effort

| | Frontier | pymoo | LLM Only |
|---|:---:|:---:|:---:|
| **Custom code** | 0 lines | 362 lines | 0 lines |
| **Tool calls** | 11 MCP calls | 1 script run | 0 |
| **Solve time** | ~4s (thorough, all scenarios) | 12s (4 scenarios) | ~5 min (reasoning) |
| **Solutions per scenario** | 329 | 37-42 | 4 |
| **Total Pareto solutions** | 1,316 | 158 | 16 (hand-constructed) |
| **Robustness analysis** | Built-in (`explore scenario_results`) | Custom code (30 lines) | Manual reasoning |
| **Skill guidance received** | 3 phases (data_collection, optimization_strategy, solution_interpreter) | None | None |

---

## 2. Issues Log

### Frontier Issues (9)

*Updated after re-run with per-scenario `explore` capability (scenario param on explore tools).*

1. **Large result payloads overflow token limits.** Solve responses (~347K chars per scenario) exceeded MCP limits, requiring file-based fallback. `explore solutions` output similarly too large for inline consumption.
2. ~~**Per-scenario solution detail not accessible through explore tools.**~~ **RESOLVED.** Per-scenario `explore tradeoffs/solution/curate` now works via the `scenario` parameter. All 16 curated strategies (4 archetypes × 4 scenarios) fully inspected and curated. See `scenario_frontier_v2.md`.
3. **Scenario ranges are nearly identical.** Return ranges barely differ (20.32–20.42% max, 1.96–2.09% min across scenarios). The dominant GLD/VDE/HYG/VGSH positions absorb scenario adjustments — only 1% satellite ETFs rotate. This is a formulation issue (mild adjustments + linear vol), not a solver issue.
4. **28 of 30 options classified as "robust."** Robustness metric too permissive — counts any 1% appearance in any of 329 solutions. Frequency-weighted robustness from curated portfolios is more useful: HYG 15/16, GLD 13/16, VGSH 12/16, VDE 11/16.
5. **Dominated options still appear in solutions.** 19 options flagged as dominated at score entry, but appear in Pareto solutions via 1% allocations.
6. **No non-additive objective warning.** Linear-average vol produces unrealistic concentrated portfolios (97% HYG, zero equity) because it gives no diversification credit. Frontier should detect and warn when a non-additive quantity is scored additively.
7. **Solve overflow.** Requested ~100 solutions, got 329 per scenario. Engine should respect the requested count or document why it generates more.
8. **Marginal analysis output too large.** ~166K chars per scenario. Had to extract knee points via file parsing. Needs summary-first or truncated mode.
9. **`scenario_results` expected values misleading.** Reports best-of-each-objective across scenarios as probability-weighted expected values, representing an impossible ideal point (max return + min vol + max yield simultaneously).

### pymoo Issues (4)

1. **Balanced = Safety collapse in recession.** The balanced scoring function (equal-weight normalization) selects the same portfolio as Safety because the Pareto front is compressed on the return axis. The method correctly identifies and explains this but can't fix it without ad-hoc strategy differentiation constraints.
2. **Repair operator complexity.** 75 lines of hand-written constraint enforcement. Works but is fragile — sequential repair steps can interact unpredictably.
3. **Naive volatility model.** Weighted-average vol ignores correlations, same as Frontier. Acknowledged limitation.
4. **Script length (362 lines).** Self-contained but represents significant engineering effort vs. 0 lines for Frontier or LLM.

### LLM Issues (10)

1. **Arithmetic precision.** All multiplication done mentally, rounded to 2 decimal places. Errors on order of 0.01-0.05%.
2. **Constraint verification difficulty.** Computing weighted averages across 4-12 holdings mentally is error-prone.
3. **No correlation data.** Same limitation as other methods.
4. **Tiny solution space explored.** ~4-5 candidates per strategy per scenario out of trillions.
5. **Cannot verify Pareto optimality.** Portfolios are "reasonable" but almost certainly dominated.
6. **Sector/Alternative constraints easy to lose track of.** Manual tracking across 16 portfolios.
7. **Integer allocation granularity.** Used round-number allocations (multiples of 5%).
8. **Couldn't evaluate all 30 ETFs equally.** Focused on 15-18 most promising per scenario.
9. **Missing sensitivity analysis.** Didn't test whether small rebalances improve portfolios.
10. **Cannot quantify distance from optimal.** Knows portfolios are suboptimal but doesn't know by how much.

---

## 3. Per-Scenario Results

### Solution Counts

| Scenario | Frontier | pymoo | LLM |
|----------|:---:|:---:|:---:|
| Base Case | 329 | 41 | 4 |
| Rate Cuts | 329 | 42 | 4 |
| Recession | 329 | 37 | 4 |
| Inflation | 329 | 38 | 4 |
| **Total** | **1,316** | **158** | **16** |

### Growth Strategy Comparison

| Scenario | | Frontier | pymoo | LLM |
|----------|---|:---:|:---:|:---:|
| **Base** | Return | **20.35%** | 17.46% | 15.46% |
| | Vol | 19.94% | 19.15% | 16.83% |
| | Yield | 0.97% | 1.18% | 1.46% |
| | Core | GLD 59%, VDE 39% | VDE 29, GLD 29, GSG 29 | GLD 30, VOO 20, IGF 15, DBA 15 |
| **Rate Cuts** | Return | **20.35%** | 15.30% | 17.09% |
| | Vol | 19.86% | 16.86% | 16.93% |
| | Yield | 0.92% | — | 0.94% |
| | Core | GLD 61%, VDE 37% | VOO/VUG/VTV/VEA/VGK/VDE/GLD | VDE/GLD/VGT/VOO/VUG/VTV |
| **Recession** | Return | **20.32%** | 15.47% | 11.97% |
| | Vol | 19.60% | 15.94% | 11.61% |
| | Yield | 0.89% | — | 2.29% |
| | Core | GLD 62%, VDE 36% | GLD 44, IGF 43, GSG 12 | GLD 35, DBA 20, IGF 15 |
| **Inflation** | Return | 20.42% | **26.53%** | 19.69% |
| | Vol | 19.69% | 17.65% | 16.00% |
| | Yield | 0.87% | — | 1.22% |
| | Core | GLD 62%, VDE 36% | GLD 49, GSG 49 | GLD 30, GSG 15, DBA 15, VOO 15 |

**Frontier Growth finding:** Structurally identical across all 4 scenarios — a GLD/VDE barbell at ~60/37. Only the 1% decorative satellites rotate (VGT, VPU, VOX, SCHD, IGF). Frontier finds the highest return in 3 of 4 scenarios but sacrifices all yield (<1%) to get there. pymoo wins Inflation (26.53%) by going heavy on GSG (commodities x1.5 override).

### Balanced Strategy Comparison

| Scenario | | Frontier | pymoo | LLM |
|----------|---|:---:|:---:|:---:|
| **Base** | Return | 9.03% | 8.15% | **11.47%** |
| | Vol | **10.40%** | 11.27% | 12.94% |
| | Yield | 3.79% | 3.68% | 2.08% |
| | Core | HYG 60%, GLD 32%, VGSH 6% | HYG 33, GLD 20, VGSH 18, TIP 16 | VOO 20, GLD 15, BND 15, SCHD 10 |
| **Rate Cuts** | Return | 8.63% | — | **13.45%** |
| | Vol | **10.37%** | — | 14.10% |
| | Yield | **4.03%** | — | 2.03% |
| | Core | HYG 64%, GLD 29%, VGSH 3% | — | VOO 15, VDE 15, GLD 15, BND 10 |
| **Recession** | Return | 8.82% | — | **9.09%** |
| | Vol | **10.54%** | — | 9.90% |
| | Yield | **4.03%** | — | 2.96% |
| | Core | HYG 68%, GLD 30% | — | GLD 20, VGSH 20, DBA 15, BND 10 |
| **Inflation** | Return | 8.94% | — | **14.33%** |
| | Vol | **10.49%** | — | 12.35% |
| | Yield | **3.95%** | — | 2.18% |
| | Core | HYG 65%, GLD 30%, VGSH 3% | — | GLD 20, VOO 15, VDE 15, DBA 10 |

**Balanced is the most divergent archetype.** LLM consistently achieves higher return by including equity (VOO, VDE, VGT) that both optimizers ignore. Frontier achieves lower vol and higher yield via HYG concentration (60-68%). pymoo's Base-Balanced sits between. The disagreement highlights the formulation's linear-vol limitation: under proper covariance, equity diversification would be rewarded, likely pushing optimizer results closer to LLM's intuition.

### Safety Strategy Comparison

| Scenario | | Frontier | pymoo | LLM |
|----------|---|:---:|:---:|:---:|
| **Base** | Return | 1.99% | 2.35% | 2.94% |
| | Vol | **2.60%** | 5.64% | 5.80% |
| | Yield | 3.94% | 4.42% | 3.97% |
| | Core | VGSH 97% | VGSH 33, TIP 33, HYG 33 | VGSH 40, BND 20, TIP 15, DBA 15 |
| **Rate Cuts** | Return | 2.08% | — | 2.71% |
| | Vol | **2.65%** | — | 6.11% |
| | Yield | 3.91% | — | 2.97% |
| | Core | VGSH 96% | — | VGSH 40, BND 20, TIP 15 |
| **Recession** | Return | 1.96% | 4.00% | **4.57%** |
| | Vol | **2.53%** | 5.33% | 5.23% |
| | Yield | 3.94% | — | 3.78% |
| | Core | VGSH 97% | VGSH 47, BND 46 | VGSH 50, BND 20 |
| **Inflation** | Return | 2.09% | 4.49% | **5.63%** |
| | Vol | **2.72%** | 5.68% | 6.69% |
| | Yield | 3.96% | — | 4.18% |
| | Core | VGSH 96% | VGSH 42, TIP 42 | VGSH 40, TIP 25, DBA 15 |

**Frontier achieves the lowest volatility in every scenario** (2.53–2.72%) by concentrating 96–97% in VGSH. pymoo and LLM both diversify Safety across 3–5 positions, yielding higher return at the cost of 2–3x the volatility. Frontier is "correct" on the strict min-vol objective but produces an unrealistic single-asset portfolio.

### Income Strategy Comparison

| Scenario | | Frontier | pymoo | LLM |
|----------|---|:---:|:---:|:---:|
| **Base** | Return | 4.03% | — | **6.36%** |
| | Vol | **8.06%** | — | 10.44% |
| | Yield | **5.77%** | — | 4.27% |
| | Core | HYG 97% | — | HYG 25, EMB 15, SCHD 15, VPU 10 |
| **Rate Cuts** | Return | 4.00% | — | **7.34%** |
| | Vol | **8.20%** | — | 10.70% |
| | Yield | **5.73%** | — | 3.60% |
| | Core | HYG 96% | — | HYG 20, EMB 15, VPU 10, SCHD 10 |
| **Recession** | Return | 4.03% | **-1.75%** | 3.12% |
| | Vol | **8.19%** | 12.11% | 8.89% |
| | Yield | **5.76%** | 5.40% | 4.09% |
| | Core | HYG 96%, EMB 2% | HYG 50, EMB 48 | HYG 10, VGSH 30, BND 15 |
| **Inflation** | Return | 4.20% | — | **6.29%** |
| | Vol | **8.26%** | — | 9.49% |
| | Yield | **5.74%** | — | 4.40% |
| | Core | HYG 95%, SCHD 1%, VDE 1%, VPU 1%, IGF 1% | — | HYG 25, DBA 15, VDE 15, VPU 10 |

**Income reveals the concentration tradeoff most starkly.** Frontier maximizes yield (~5.75%) by putting 95–97% in HYG — technically optimal but a single-asset portfolio. LLM diversifies across 6–8 holdings, accepting 1.5pp less yield for more realistic diversification. pymoo's Recession-Income has **negative return (-1.75%)** from 50% HYG + 48% EMB, both with negative recession returns. Frontier avoids this because its HYG still shows positive return even in recession (the score adjustments hit equity and sectors, not bonds directly). The LLM avoided it by intuitively reducing HYG to 10%.

**Key insight:** Frontier's Income portfolio works in recession because HYG's 4.03% return is the *adjusted* score — the recession adjustments only penalize equity and sector groups, not bond yields. This is a formulation artifact: in a real recession, HYG credit spreads would widen and returns would drop, but the scenario scoring doesn't model this for HYG (only EMB gets an explicit -2% override).

---

## 4. Robustness Analysis Comparison

### Robust ETFs (appear across all scenarios)

| | Frontier (Pareto-level) | Frontier (curated-level) | pymoo | LLM |
|---|---|---|---|---|
| **Metric** | Appears in any solution in all 4 scenarios | Appears in curated portfolios (16 total) | Appears in any solution, with frequency | Appears in curated portfolios |
| **Count** | 28 of 30 (too permissive) | 4 core ETFs dominate | 12 ETFs | 3 core + 4 supporting |
| **Top holdings** | Not differentiated | HYG 15/16, GLD 13/16, VGSH 12/16, VDE 11/16 | DBA 78%, HYG 77%, VGSH 74%, GLD 49% | VGSH, GLD, DBA |

### Which robustness analysis is most useful?

- **Frontier's Pareto-level** is too permissive: 28/30 is not actionable. But **Frontier's curated-level** (counting appearances across 16 curated strategies) is now highly informative: HYG (15/16), GLD (13/16), VGSH (12/16), VDE (11/16) clearly separates core from peripheral.
- **pymoo's** frequency-based metric (DBA 78%, VGSH 74%) uses solution-level frequency across all Pareto solutions, which is statistically richer than curated-only but harder to interpret.
- **LLM's** is the most distilled (3 core ETFs) but based on only 16 hand-picked portfolios — the sample is too small to draw statistical conclusions.
- **All three methods converge** on the same core holdings: VGSH (safety), HYG or GLD (return/income engine), VDE (return booster). The disagreement is on satellites and secondary positions.

### Scenario-Specific ETFs

| Frontier | pymoo | LLM |
|----------|-------|-----|
| IGF in all 4 Inflation strategies (strongest signal); VGLT in RateCuts-Income only; VGT in Base-Growth only; BND drops out in Recession and Inflation | VDC (base only), SCHD/VNQ/VUG (rate cuts only), VOX/VPU (inflation only) | VGLT (rate cuts), GSG (inflation), BND (recession) |

With per-scenario curated strategies, Frontier now identifies scenario-specific rotations comparable to pymoo and LLM. IGF's exclusive appearance in all 4 Inflation archetypes is the clearest scenario signal across any method.

---

## 5. Interpretation Response Quality

### Side-by-Side: Cross-Scenario Key Insight

**Frontier (updated with per-scenario curated data):**
> Four ETFs do 90%+ of the work across every scenario: GLD (59–62% of Growth), VDE (36–39% of Growth), HYG (60–97% of Balanced/Income), VGSH (96–97% of Safety). Your archetype choice matters 10x more than your scenario view — Growth vs Safety spans 18pp of return; Base Case vs Recession spans 0.4pp within an archetype. If you're at the extremes (Growth/Income/Safety), don't scenario-tilt. If you're Balanced, watch for IGF (inflation signal) and BND (drops in stress).

**pymoo:**
> The optimizer reveals that your portfolio should have a **stable core** and **adaptive satellites**. Short-term treasuries (VGSH) for stability, high-yield bonds (HYG) for income, and agricultural commodities (DBA) for uncorrelated returns. These three appear in 74-78% of all optimal portfolios across every scenario tested.

**LLM:**
> Three ETFs consistently appear in well-constructed portfolios: VGSH (short-term Treasuries), GLD (gold), and DBA (agriculture commodities). This trio provides complementary characteristics: VGSH contributes ultra-low volatility, GLD delivers strong risk-adjusted returns, and DBA offers a balanced profile.

*All three converge on the same core holdings (VGSH, GLD/HYG, VDE/DBA). Frontier's interpretation is now backed by actual per-scenario curated portfolios (16 total) and is the most quantitatively precise — it can state exact allocation percentages and cross-scenario ranges. pymoo's frequency-based framing is the most statistically grounded. LLM's narrative is the most memorable but least verifiable.*

### Side-by-Side: Recession Impact

**Frontier (updated):**
> Recession barely changes Growth (GLD 62%/VDE 36% vs base GLD 59%/VDE 39%) — the same barbell at 20.32% return. Balanced is the most scenario-sensitive: HYG rises from 60% to 68% as the optimizer doubles down on yield even in a downturn. The biggest recession signal is what *drops out*: BND disappears, VGSH leaves Balanced, and VPU enters as a defensive utility play. Across all archetypes, objective values shift by <0.5pp — the allocations rotate but the tradeoff surface is structurally stable.

**pymoo:**
> If we enter recession: The optimizer's message is blunt: there are no good growth options in equities. Gold and infrastructure are the only assets with strong positive returns. The "balanced" portfolio collapses into the safety portfolio because there is genuinely nothing in the middle.

**LLM:**
> In a recession, even the "growth" portfolio maxes out at 12.0% return because equities become effectively unusable (vol exceeds 20-30%), forcing the portfolio into alternatives and bonds. The growth portfolio's return range across scenarios: 12.0% to 19.7%, a 7.7 percentage point spread.

*Key difference: Frontier finds 20.32% Growth in recession (via the GLD/VDE barbell that dominates regardless), while LLM caps at 12.0% (by diversifying into equity, which gets crushed). pymoo uniquely surfaces the Balanced=Safety collapse. The methods tell complementary stories: Frontier shows the mathematical optimum, pymoo shows structural breaks, LLM shows practitioner intuition.*

---

## 6. Key Findings for Eval Article

### What Frontier does best: Full-stack zero-code optimization with per-scenario exploration
- 329 solutions per scenario, 1,316 total, 0 lines of code
- Per-scenario `explore tradeoffs/solution/curate` — inspected and curated all 16 archetypes (4 × 4)
- Auto-injected skill guidance at 3 workflow phases
- Native scenario configuration in a single `model update` call
- Built-in marginal analysis with knee-point detection (though output too large)
- Widest Pareto front coverage of any method — dense tradeoff surface in every scenario

### What Frontier does worst: Realism of resulting portfolios
- Linear-average vol produces unrealistic concentrated portfolios: 97% HYG for Income, 97% VGSH for Safety, zero equity anywhere. No practitioner would hold these.
- No warning when the formulation produces non-additive objectives scored additively (the root cause).
- Scenario frontiers are near-identical because the GLD/VDE/HYG/VGSH positions absorb all scenario adjustments. Scenarios rotate 1% satellites but don't change the dominant answer.
- Robustness metric at Pareto level (28/30) is still too permissive. Curated-level robustness (HYG 15/16, GLD 13/16) is much better but requires the agent to compute it manually.

### What pymoo does best: Honest per-scenario portfolios with frequency-based robustness
- Actual curated strategies per scenario with specific allocations
- Frequency-based robustness (DBA 78%, VGSH 74%) is the most actionable robustness metric
- Correctly surfaced the Balanced=Safety collapse in recession as a structural finding
- Income portfolio's -1.75% return in recession is an honest, uncomfortable truth

### What pymoo does worst: Engineering burden and repair operator artifacts
- 362 lines of custom code, including 75 lines of fragile repair operator
- Fewer solutions per scenario (37-42) vs. Frontier's 329
- All the code is throwaway — must be rewritten for different problem structures

### What LLM does best: Narrative quality and intuitive judgment
- The "all-weather trio" framing (VGSH + GLD + DBA) is the most memorable takeaway
- Correctly avoided the negative-return income portfolio that pymoo shipped (reduced HYG from 50% to 10% in recession)
- Honest about limitations: "10-20% chance of at least one material arithmetic error"
- VGLT scenario-specific insight (13pp return swing between rate cuts and inflation) is the best single data point

### What LLM does worst: Everything else
- 16 portfolios vs. 1,316 + 158 — radically incomplete
- Cannot verify Pareto optimality
- Growth portfolios significantly lag Frontier (15.46% vs 20.24% base case)
- "Round number" allocations (multiples of 5%) leave optimization quality on the table
- Manual arithmetic across 150+ calculations with acknowledged error risk

---

## 7. Scaling from Single Problem to Scenarios

| Dimension | Frontier | pymoo | LLM |
|-----------|----------|-------|-----|
| **Additional user effort for scenarios** | 1 tool call (`model update` with scenario_config) + 1 solve call | Parameterize script (add ~80 lines for scenario defs + loop) | Repeat entire reasoning 4x (4x effort) |
| **New code needed** | 0 lines | ~80 lines (scenario defs, adjusted scores, cross-scenario analysis) | 0 lines (but 4x reasoning time) |
| **Quality of cross-scenario analysis** | Per-scenario curated portfolios + knee-point marginal analysis + robustness (both Pareto-level and curated-level) | Per-scenario portfolios + frequency-based robustness | Per-scenario portfolios + intuitive robustness |
| **Critical gap** | Linear vol → unrealistic concentrated portfolios; near-identical frontiers across scenarios | Balanced=Safety collapse; all code is throwaway | Arithmetic errors; can't verify optimality |

### The honest summary

Frontier's scenario workflow is now end-to-end: setup (1 tool call) → solve → per-scenario explore/curate/compare. The 16 curated strategies with specific allocations match what pymoo and LLM provide — but with 329 Pareto solutions backing each one.

The remaining gap is **formulation realism**, not exploration capability. Linear-average vol produces portfolios no practitioner would hold (97% in one asset, zero equity). This makes the scenario differentiation superficial — the same 4 ETFs dominate regardless of macro regime. Fixing the vol model or adding concentration constraints would make the scenario feature genuinely valuable.

pymoo provides comparable per-scenario detail with frequency-based robustness but requires 362 lines of throwaway code. The LLM scales worst (4x effort) but compensates with qualitative judgment — notably avoiding the negative-return income portfolio and diversifying into equity that both optimizers ignore.

---

## 8. Raw Data References

- Frontier results: `scenario_frontier_v2.md` (per-scenario curated strategies, cross-scenario comparison, robustness, issues)
- pymoo results: `scenario_pymoo.md` (252 lines), `scenario_pymoo_raw.json`
- LLM results: `scenario_llm_only.md` (780 lines)
- Shared assignment: `scenario_assignment.md`
- Curated strategy data: `scenario_candidates.json` (Frontier), `scenario_pymoo_raw.json` (pymoo)
- Plots: `scenario_pareto_comparison.png`, `scenario_curated_comparison.png`, `scenario_pareto_all_pairs.png`
- Formulation refinements: `formulation_refinements.md`
- Product fix triage: `product_fix_triage.md`

# Frontier Scenario Evaluation v2 — ETF Portfolio Allocation

**Date:** 2026-04-13
**Problem ID:** `db4b50f2-b158-48b0-9eed-4eee038731d1`
**Tool:** Frontier multi-objective optimizer with per-scenario explore capability
**Method:** NSGA-based evolutionary optimization, 329 Pareto-optimal solutions per scenario, 4 scenarios

## Methodology

All exploration used Frontier's `explore` tool with the `scenario` parameter:

1. `explore tradeoffs scenario=<name>` — identified extreme and balanced solution IDs per scenario
2. `explore solution scenario=<name> solution_id=<id>` — inspected each candidate (allocations, objectives)
3. `explore curate scenario=<name> solution_id=<id>` — curated 4 archetypes per scenario (16 total)
4. `explore scenario_results` — robustness analysis (robust vs scenario-specific options)
5. `explore marginal_analysis scenario=<name>` — knee detection and marginal rates per scenario
6. `explore curated` — final verification of all curated solutions

Archetype selection used the `tradeoffs` tool's built-in extreme/balanced identification:
- **Growth** = `extreme_Expected Return` (max return solution)
- **Income** = `extreme_Dividend Yield` (max yield solution)
- **Safety** = `extreme_Volatility` (min vol solution)
- **Balanced** = `balanced_solution` (tool's centroid-based balanced pick)

---

## 1. Per-Scenario Frontier Summaries

### Objective Ranges (from `explore tradeoffs scenario=<name>`)

| Objective | Base Case | Rate Cuts / Risk-On | Recession / Risk-Off | Inflation Surge |
|-----------|-----------|---------------------|----------------------|-----------------|
| **Return (%)** | 1.99 – 20.35 | 2.04 – 20.35 | 1.96 – 20.32 | 2.09 – 20.42 |
| **Volatility (%)** | 2.60 – 19.99 | 2.65 – 19.99 | 2.53 – 20.00 | 2.72 – 19.95 |
| **Yield (%)** | 0.12 – 5.77 | 0.12 – 5.73 | 0.13 – 5.76 | 0.11 – 5.74 |

### Correlations (consistent across all scenarios)

| Pair | r | Interpretation |
|------|---|----------------|
| Return ↔ Volatility | +0.94 to +0.95 | More return costs more risk |
| Return ↔ Yield | −0.89 to −0.90 | Growth assets don't pay dividends |
| Volatility ↔ Yield | −0.68 to −0.72 | High-yield bonds sit at mid-vol |

### Marginal Analysis Knee Points (from `explore marginal_analysis scenario=<name>`)

| Scenario | Return vs Vol Knee | Jump Factor | Return vs Yield Knee | Jump Factor |
|----------|-------------------|-------------|---------------------|-------------|
| Base Case | Solution 174 | 259.4x | Solution 121 | 509.6x |
| Recession | Solution 11 | 630.3x | Solution 305 | 17,278.4x |
| Inflation | Solution 207 | 1,061.9x | Solution 207 | 1,250.5x |

The Recession scenario shows the sharpest knee in Return-vs-Yield (17,278x jump), meaning the marginal cost of yield spikes dramatically beyond solution 305 — a much steeper tradeoff cliff than Base Case or Inflation.

---

## 2. Per-Scenario Curated Strategies

All solutions sourced via `explore solution scenario=<name>` and curated via `explore curate scenario=<name>`.

### 2.1 Base Case (Continuation, 30% probability)

No score adjustments. Reflects 5-year historical performance (2021–2026).

| Strategy | Return | Vol | Yield | # | Allocations |
|----------|--------|-----|-------|---|-------------|
| **Base-Growth** | 20.35% | 19.94% | 0.97% | 4 | GLD 59%, VDE 39%, VGT 1%, DBA 1% |
| **Base-Balanced** | 9.03% | 10.40% | 3.79% | 5 | HYG 60%, GLD 32%, VGSH 6%, SCHD 1%, EWJ 1% |
| **Base-Income** | 4.03% | 8.06% | 5.77% | 4 | HYG 97%, VGSH 1%, EMB 1%, VDE 1% |
| **Base-Safety** | 1.99% | 2.60% | 3.94% | 4 | VGSH 97%, BND 1%, TIP 1%, HYG 1% |

### 2.2 Rate Cuts / Risk-On (25% probability)

Equity returns x1.3, equity vol x0.9, bond yields x0.7, VGLT return → +8.0%.

| Strategy | Return | Vol | Yield | # | Allocations |
|----------|--------|-----|-------|---|-------------|
| **RateCuts-Growth** | 20.35% | 19.86% | 0.92% | 4 | GLD 61%, VDE 37%, VPU 1%, VOX 1% |
| **RateCuts-Balanced** | 8.63% | 10.37% | 4.03% | 6 | HYG 64%, GLD 29%, VGSH 3%, EMB 2%, BND 1%, VDE 1% |
| **RateCuts-Income** | 4.00% | 8.20% | 5.73% | 5 | HYG 96%, VGSH 1%, VGLT 1%, GLD 1%, DBA 1% |
| **RateCuts-Safety** | 2.08% | 2.65% | 3.91% | 5 | VGSH 96%, BND 1%, TIP 1%, HYG 1%, GLD 1% |

### 2.3 Recession / Risk-Off (20% probability)

Equity returns x0.4, equity vol x1.5, sector returns x0.4, sector vol x1.5. Bond flight-to-safety overrides.

| Strategy | Return | Vol | Yield | # | Allocations |
|----------|--------|-----|-------|---|-------------|
| **Recession-Growth** | 20.32% | 19.60% | 0.89% | 4 | GLD 62%, VDE 36%, VGSH 1%, DBA 1% |
| **Recession-Balanced** | 8.82% | 10.54% | 4.03% | 4 | HYG 68%, GLD 30%, EMB 1%, VPU 1% |
| **Recession-Income** | 4.03% | 8.19% | 5.76% | 4 | HYG 96%, EMB 2%, TIP 1%, VDE 1% |
| **Recession-Safety** | 1.96% | 2.53% | 3.94% | 4 | VGSH 97%, TIP 1%, HYG 1%, DBA 1% |

### 2.4 Inflation Surge (25% probability)

Equity returns x0.8, bond yields x1.1. Commodity overrides: GLD x1.5, GSG x1.5, DBA x1.5. TIP → +6%, BND → −3%, VGLT → −8%.

| Strategy | Return | Vol | Yield | # | Allocations |
|----------|--------|-----|-------|---|-------------|
| **Inflation-Growth** | 20.42% | 19.69% | 0.87% | 4 | GLD 62%, VDE 36%, SCHD 1%, IGF 1% |
| **Inflation-Balanced** | 8.94% | 10.49% | 3.95% | 5 | HYG 65%, GLD 30%, VGSH 3%, VDE 1%, IGF 1% |
| **Inflation-Income** | 4.20% | 8.26% | 5.74% | 6 | HYG 95%, SCHD 1%, VGSH 1%, VDE 1%, VPU 1%, IGF 1% |
| **Inflation-Safety** | 2.09% | 2.72% | 3.96% | 4 | VGSH 96%, HYG 2%, EMB 1%, IGF 1% |

---

## 3. Cross-Scenario Comparison: How Do Curated Strategies Shift?

### 3.1 Growth Strategy

| Component | Base | Rate Cuts | Recession | Inflation |
|-----------|------|-----------|-----------|-----------|
| **GLD** | 59% | 61% | 62% | 62% |
| **VDE** | 39% | 37% | 36% | 36% |
| **Satellite 1** | VGT 1% | VPU 1% | VGSH 1% | SCHD 1% |
| **Satellite 2** | DBA 1% | VOX 1% | DBA 1% | IGF 1% |

**Verdict:** Structurally identical — a GLD/VDE barbell at ~60/37. GLD creeps up slightly in stress scenarios. Only the 1% decorative satellites rotate: VGT (base tech), VPU/VOX (rate cuts sector bets), VGSH (recession safety), SCHD/IGF (inflation real assets).

### 3.2 Balanced Strategy

| Component | Base | Rate Cuts | Recession | Inflation |
|-----------|------|-----------|-----------|-----------|
| **HYG** | 60% | 64% | 68% | 65% |
| **GLD** | 32% | 29% | 30% | 30% |
| **VGSH** | 6% | 3% | — | 3% |
| **Satellites** | SCHD 1%, EWJ 1% | EMB 2%, BND 1%, VDE 1% | EMB 1%, VPU 1% | VDE 1%, IGF 1% |

**Key shifts:** Balanced is the most scenario-sensitive archetype. HYG increases from 60% to 68% in Recession — despite credit concerns, HYG's yield dominance keeps it central. VGSH drops out entirely in Recession (the balanced solution found a 4-holding solution without it). In Inflation, IGF appears as an infrastructure hedge.

### 3.3 Income Strategy

| Component | Base | Rate Cuts | Recession | Inflation |
|-----------|------|-----------|-----------|-----------|
| **HYG** | 97% | 96% | 96% | 95% |
| **Satellites** | VGSH, EMB, VDE | VGSH, VGLT, GLD, DBA | EMB 2%, TIP, VDE | SCHD, VGSH, VDE, VPU, IGF |

**Verdict:** HYG dominates (95–97%) in all scenarios. The only meaningful shift: Inflation increases satellite diversity (6 holdings vs 4), spreading 5% across real-asset satellites (SCHD, VDE, VPU, IGF). Rate Cuts uniquely adds VGLT (duration benefit from rate cuts).

### 3.4 Safety Strategy

| Component | Base | Rate Cuts | Recession | Inflation |
|-----------|------|-----------|-----------|-----------|
| **VGSH** | 97% | 96% | 97% | 96% |
| **Satellites** | BND, TIP, HYG | BND, TIP, HYG, GLD | TIP, HYG, DBA | HYG 2%, EMB, IGF |

**Verdict:** VGSH-dominated (96–97%) everywhere. Satellite rotation: BND present in Base/Rate Cuts but drops out in Recession and Inflation. Inflation uniquely brings in IGF and EMB, drops TIP. HYG gets 2% in Inflation (up from 1%).

### 3.5 Assets That Rotate In/Out

| Asset | Appears In (curated) | Absent From | Why It Rotates |
|-------|---------------------|-------------|----------------|
| **VGLT** | RateCuts-Income only | All other scenarios | Duration benefit from rate cuts |
| **IGF** | All 4 Inflation strategies | All other scenarios | Infrastructure as inflation hedge |
| **BND** | Base + RateCuts (Safety, Balanced) | Recession, Inflation | Nominal bonds hurt in inflation (−3%) and not needed in recession |
| **VGT** | Base-Growth only | All other scenarios | Tech sector only optimal in continuation |
| **VPU** | RateCuts-Growth, Recession-Balanced, Inflation-Income | Base only in satellites | Utilities as defensive/income play |
| **EWJ** | Base-Balanced only | All other scenarios | Japan exposure only in continuation |

---

## 4. Robustness Analysis (from `explore scenario_results`)

### 4.1 Option-Level Robustness

- **Robust (appear in all 4 scenarios):** 28 of 30 ETFs
- **Scenario-specific:** VB and MCHI — absent from Inflation Surge entirely

Note: This robustness metric counts *any* appearance in *any* Pareto-optimal solution in that scenario. Since there are 329 solutions per scenario, nearly every ETF shows up somewhere. This is a broad measure; frequency-weighted robustness (below) is more informative.

### 4.2 Core Holdings (by curated-portfolio frequency)

Counting appearances across all 16 curated solutions:

| ETF | Appearances | Role |
|-----|-------------|------|
| **HYG** | 15/16 | Income engine (60–97% in Balanced/Income), tiny satellite in Safety |
| **GLD** | 13/16 | Return engine (59–62% in Growth), diversifier (29–32% in Balanced) |
| **VGSH** | 12/16 | Safety anchor (96–97% in Safety), ballast (3–6% in Balanced) |
| **VDE** | 11/16 | Return co-engine (36–39% in Growth), satellite elsewhere |
| **DBA** | 4/16 | Commodity diversifier at 1%, Base/RateCuts/Recession |
| **EMB** | 5/16 | EM bond yield satellite, across multiple scenarios |
| **TIP** | 4/16 | Inflation protection satellite in Safety/Income |
| **BND** | 4/16 | Nominal bond ballast, Base/RateCuts only |
| **IGF** | 4/16 | Infrastructure, all 4 Inflation strategies exclusively |

### 4.3 Probability-Weighted Expected Values

From `scenario_results`:
- Expected Return: 20.36% (dominated by Growth extremes)
- Volatility: 2.63% (dominated by Safety extremes)
- Dividend Yield: 5.75% (dominated by Income extremes)

---

## 5. Constraint Verification

All 16 curated solutions verified against 4 constraints (from `explore solution` allocations):

| Solution | Holdings | Sectors | Alts | Vol (optimizer) | Status |
|----------|----------|---------|------|-----------------|--------|
| Base-Growth | 4 | 2 (VGT, VDE) | 2 (GLD, DBA) | 19.94% | PASS |
| Base-Balanced | 5 | 0 | 1 (GLD) | 10.40% | PASS |
| Base-Income | 4 | 1 (VDE) | 0 | 8.06% | PASS |
| Base-Safety | 4 | 0 | 0 | 2.60% | PASS |
| RateCuts-Growth | 4 | 3 (VDE, VPU, VOX) | 1 (GLD) | 19.86% | PASS |
| RateCuts-Balanced | 6 | 1 (VDE) | 1 (GLD) | 10.37% | PASS |
| RateCuts-Income | 5 | 0 | 2 (GLD, DBA) | 8.20% | PASS |
| RateCuts-Safety | 5 | 0 | 1 (GLD) | 2.65% | PASS |
| Recession-Growth | 4 | 1 (VDE) | 2 (GLD, DBA) | 19.60% | PASS |
| Recession-Balanced | 4 | 1 (VPU) | 1 (GLD) | 10.54% | PASS |
| Recession-Income | 4 | 1 (VDE) | 0 | 8.19% | PASS |
| Recession-Safety | 4 | 0 | 1 (DBA) | 2.53% | PASS |
| Inflation-Growth | 4 | 1 (VDE) | 2 (GLD, IGF) | 19.69% | PASS |
| Inflation-Balanced | 5 | 1 (VDE) | 2 (GLD, IGF) | 10.49% | PASS |
| Inflation-Income | 6 | 2 (VDE, VPU) | 1 (IGF) | 8.26% | PASS |
| Inflation-Safety | 4 | 0 | 1 (IGF) | 2.72% | PASS |

All 16/16 pass. Holdings range 4–6, sectors max 3, alts max 2, vol max 19.94%.

---

## 6. Interpretation: How Should My Portfolio Change Across These Scenarios?

### Stable Core: What Doesn't Change

Four ETFs do 90%+ of the work across every scenario:

- **GLD (gold)** is the growth engine in every scenario — 59–62% of Growth portfolios, 29–32% of Balanced. Gold benefits from different macro drivers (safe haven in recession, real asset in inflation, momentum in base case), making it the most robust return source.

- **VDE (energy)** is GLD's growth partner — 36–39% across all Growth portfolios. Energy's high base return (25.83%) persists because the scenario adjustments either don't affect it (it's a Sector, not Equity) or affect it less than alternatives.

- **HYG (high yield bonds)** is the income engine — 95–97% of every Income portfolio, 60–68% of Balanced. Its 5.60% yield is so dominant that no scenario adjustment dislodges it. Even in Recession (where credit spreads widen), HYG's yield still wins the yield objective.

- **VGSH (short-term treasuries)** is the safety anchor — 96–97% of every Safety portfolio. At 1.40% volatility, nothing else comes close for capital preservation.

### Adaptive Satellites: What Does Change

The **Balanced portfolio** is where your macro view matters most. Key rotations:

1. **If you expect Rate Cuts:** Stay close to the Base Case. HYG rises from 60% to 64%, GLD drops from 32% to 29%. Add EMB (2%) for EM bond yield. VGLT enters Income portfolios for duration benefit.

2. **If you fear Recession:** HYG actually increases to 68% — the optimizer prioritizes yield even in downturns. The Balanced solution simplifies to just 4 holdings (drops VGSH as a separate position). VPU enters as a defensive utility play.

3. **If you expect Inflation:** IGF (infrastructure) appears in all 4 archetypes — the strongest scenario-specific signal. BND drops out entirely (nominal bonds crushed at −3% return). SCHD enters Growth and Income as a dividend-equity hedge.

### Quantified Tradeoffs Between Archetypes

Within any scenario, the archetype transitions cost roughly the same:

| Transition | Return Cost | Vol Reduction | Yield Gain |
|-----------|-------------|---------------|------------|
| Growth → Balanced | −11.3pp avg | −9.4pp avg | +3.0pp avg |
| Balanced → Income | −4.8pp avg | −2.3pp avg | +1.8pp avg |
| Income → Safety | −2.1pp avg | −5.5pp avg | −1.8pp avg |

The biggest "bang for buck" is the Growth → Balanced step: you give up ~11pp of return but cut volatility in half and triple your yield. The Income → Safety step is expensive in yield terms (−1.8pp) for a vol reduction you may not need (8% → 2.6%).

### What Barely Changes Across Scenarios

The within-archetype objective shifts are remarkably small:

| Archetype | Return Range | Vol Range | Yield Range |
|-----------|-------------|-----------|-------------|
| Growth | 20.32 – 20.42% | 19.60 – 19.94% | 0.87 – 0.97% |
| Balanced | 8.63 – 9.03% | 10.37 – 10.54% | 3.79 – 4.03% |
| Income | 4.00 – 4.20% | 8.06 – 8.26% | 5.73 – 5.77% |
| Safety | 1.96 – 2.09% | 2.53 – 2.72% | 3.91 – 3.96% |

Each archetype's objective values vary by less than 0.5pp across scenarios. The *allocations* change but the *outcomes* are similar — the optimizer finds equivalently good tradeoff points in every regime.

### Bottom Line

- **Your archetype choice matters 10x more than your scenario view.** Growth vs Safety spans 18pp of return; Base Case vs Recession spans 0.4pp within an archetype.
- **If you're at the extremes (Growth/Income/Safety), don't scenario-tilt.** The core positions are robust.
- **If you're Balanced, watch for IGF (inflation signal) and BND (drops in stress).** These are the most actionable satellite rotations.
- **Four ETFs (GLD, VDE, HYG, VGSH) and the choice among them is the real decision.**

---

## 7. Issues Log (Frontier-Specific)

| # | Category | Severity | Detail |
|---|----------|----------|--------|
| 1 | **Robustness metric too broad** | Design limitation | `scenario_results` reports 28/30 ETFs as "robust" (appearing in all 4 scenarios). With 329 solutions per scenario, nearly every ETF appears somewhere at 1%. The metric doesn't distinguish GLD at 62% (core) from VGT at 1% (decorative). Need an allocation-weighted or frequency-weighted robustness metric. |
| 2 | **`explore solutions` output too large** | UX limitation | Each scenario's full solution list is ~347K characters (329 solutions x 30 ETF allocations). Overflows inline display. For 30-option problems, paginated or filtered solution views would improve usability. Not needed for this eval since `tradeoffs` provided the IDs directly. |
| 3 | **`marginal_analysis` output too large** | UX limitation | Each scenario's marginal analysis is ~166K characters (328 pairwise transitions). Had to extract knee points via file parsing. A summary-only mode or top-N transitions would be useful. |
| 4 | **`in_current_frontier` = false for scenario curations** | Expected behavior | All 16 per-scenario curated solutions show `in_current_frontier: false` because they were curated from scenario-specific runs, not the base run. The 4 pre-existing base-run curations show `true`. Correct behavior, not a bug. |
| 5 | **Balanced solution selection** | Methodology note | The `tradeoffs` tool selects the "balanced" solution via its own centroid-based algorithm. Reasonable default but may not match every user's notion of "balanced." No way to pass custom weighting to the balanced selection. |
| 6 | **`scenario_results` expected values misleading** | Design limitation | Probability-weighted expected values (Ret 20.36%, Vol 2.63%, Yld 5.75%) are computed from the best-of-each-objective across scenarios, not from any achievable portfolio. These numbers can't coexist in a single solution — they represent an impossible ideal point. |
| 7 | **No non-additive objective warning** | Missing guardrail | Linear-average vol produces unrealistic portfolios (97% concentration, zero equity) because it gives no diversification credit. Frontier should detect and warn when a known non-additive quantity (variance, correlation-dependent metrics) is scored additively. This is the root cause of the biggest realism gap vs LLM portfolios. |
| 8 | **Solve overflow** | UX issue | Requested ~100 solutions, got 329 per scenario. Engine should respect the requested count or document why it generates more. Combined with large output sizes (issues #2, #3), this compounds the token cost of exploration. |
| 9 | **No scenario overlap detection** | Missing feature | Frontier could detect when scenario frontiers overlap >95% in objective space and warn that scenario adjustments may be insufficient to produce meaningfully different results. Would have caught the "identical frontiers" problem early. |

---

## 8. Comparison Context (3-Way: Frontier vs pymoo vs LLM)

### 8.1 Method Summary

| Dimension | Frontier (this eval) | pymoo (NSGA-II) | LLM-only |
|-----------|---------------------|-----------------|----------|
| Solutions per scenario | 329 Pareto-optimal | 37–42 | 4 hand-built |
| Archetype selection | Extreme/balanced from `tradeoffs` | Frequency-based robustness | Expert judgment |
| Constraint enforcement | Optimizer-native | Repair operator | Manual verification |
| Per-scenario exploration | `explore solution/tradeoffs scenario=<name>` | Post-hoc dataframe analysis | Built into prompts |
| Robustness metric | Option appearance across scenarios | Option selection frequency | Narrative reasoning |
| Marginal analysis | Built-in knee detection | Manual calculation | Not available |
| Curation workflow | `explore curate` with persistence | Manual selection | Manual selection |
| Total curated | 16 (4 archetypes x 4 scenarios) | 16 | 16 |

### 8.2 Visual Comparison (from Pareto plots)

Plots: `scenario_pareto_comparison.png`, `scenario_curated_comparison.png`, `scenario_pareto_all_pairs.png`

**Frontier coverage dominates.** In every scenario and every objective pair, Frontier's 329-solution cloud (blue) spans the widest Pareto front — from the low-vol/low-return Safety corner to the high-return Growth extreme. pymoo's ~40 solutions (green diamonds) cluster more tightly, particularly compressed in the mid-range where Frontier fills in the Return-vs-Vol curve more densely. LLM's 4 hand-crafted points (red squares) sit inside Frontier's coverage but are competitive individually.

**Curated strategies converge at extremes, diverge at center.** On the curated comparison plot:
- **Safety** (bottom-left): All three methods land within ~1pp of each other. Low-vol is a narrow target — not much room to disagree.
- **Growth** (top-right): Frontier and pymoo nearly overlap (both find the GLD/VDE barbell). LLM's Growth is noticeably lower-return in most scenarios — it diversifies into equity, which hurts under linear vol.
- **Balanced** (center): Largest divergence. Frontier's Balanced sits at ~9% return / ~10.5% vol; pymoo's is often higher-return / higher-vol; LLM's Balanced is between. This confirms that "balanced" is the most subjective archetype and that selection methodology matters.
- **Income** (mid-left): Frontier and pymoo both find HYG-dominant solutions. LLM picks a more diversified income portfolio with lower yield but better vol, reflecting expert intuition about concentration risk that the optimizer ignores.

**pymoo compression effect.** pymoo's green diamonds form a visibly tighter band than Frontier's cloud — especially in the Yield-vs-Vol plane. This is likely due to pymoo's repair operator, which aggressively normalizes constraint-violating solutions and collapses them toward the interior. Frontier's enumeration-based approach preserves more diversity at the extremes.

**Scenarios don't separate visually.** The 2x2 panels look nearly identical — the blue clouds overlap almost perfectly across Base Case, Rate Cuts, Recession, and Inflation. This confirms the quantitative finding: scenario adjustments are too mild to shift the dominant GLD/VDE/HYG/VGSH positions. The 3x4 all-pairs grid reinforces this — Yield-vs-Vol and Yield-vs-Return patterns are effectively identical across scenarios.

### 8.3 Comparative Strengths

| Strength | Frontier | pymoo | LLM |
|----------|----------|-------|-----|
| **Coverage / exploration** | Best — widest Pareto front, 329 solutions fill the full tradeoff surface | Good — 37-42 solutions, slightly compressed | Minimal — 4 points, no continuous frontier |
| **Constraint feasibility** | Perfect — infeasibility impossible by construction | Good — repair operator enforces, but can distort | Risky — manual arithmetic, errors possible |
| **Scenario differentiation** | Weak — near-identical frontiers, satellite rotation only | Weak — same underlying limitation | Better — LLM can reason about macro regime and shift allocations qualitatively |
| **Diversification / realism** | Weak — linear vol gives no credit, produces concentrated portfolios | Weak — same formulation limitation | Better — expert intuition caps concentration, includes equity |
| **Workflow efficiency** | Best — explore/curate/compare in-tool, persistent curation | Manual — requires code to analyze | Manual — requires full re-prompting per scenario |
| **Marginal analysis** | Built-in knee detection (but output too large) | Not available | Not available |

### 8.4 Key Takeaways for Frontier Product

1. **Frontier wins on exploration and coverage** — the core value prop (dense Pareto front, structured curation, scenario-aware exploration) works as designed.
2. **Frontier loses on realism** — the linear-average vol formulation produces portfolios no practitioner would hold (97% HYG, zero equity). This is a formulation issue, not a solver issue, but Frontier should warn users.
3. **Scenario feature underdelivers here** — the near-identical frontiers are a formulation problem (mild adjustments), not a product problem. But Frontier could detect when scenario frontiers overlap >95% and flag that the scenario adjustments may be insufficient.
4. **LLM's advantage is qualitative reasoning** — an LLM can say "97% in one bond is insane" and diversify. Frontier faithfully optimizes whatever formulation it's given. The ideal workflow combines both: Frontier for rigorous exploration, LLM for sanity-checking and narrative interpretation.

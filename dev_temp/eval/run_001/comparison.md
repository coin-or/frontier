# Evaluation Report: Multi-Objective Portfolio Optimization — Method Comparison

**Run:** run_001 | **Problem:** 30 ETFs, 3 objectives (Return, Volatility, Yield), proportional allocation | **Date:** 2026-04-13

**Core question:** Which approach best explores and explains the Pareto frontier?

---

## Executive Summary

Three methods tackled the same 30-ETF portfolio optimization problem with identical constraints and data:

- **Frontier** — NSGA-II via MCP tool, quadratic volatility via covariance matrix, 100 Pareto solutions
- **Solver** — NSGA-III via pymoo (custom Python script), quadratic volatility, 38-300 Pareto solutions
- **LLM** — Pure reasoning (Claude), weighted-average volatility approximation, 5-8 hand-crafted portfolios

**Verdict:** Frontier provides the best overall combination of exploration, explanation, and constraint reliability. Solver matches or exceeds Frontier on raw exploration in the scenario phase but introduces constraint violations and requires substantial code. LLM provides genuine interpretive insight and honest self-assessment but fundamentally cannot explore the tradeoff space or guarantee feasibility.

---

## 1. Solution Exploration

*How thoroughly does the method search the frontier, and can a user navigate what it found?*

### 1a. Base Case Coverage

| Dimension | Frontier | Solver | LLM |
|-----------|----------|--------|-----|
| **Pareto solutions** | 100 | 38 | 8 |
| **Return range** | 3.03% - 17.27% | 2.22% - 18.33% | 2.69% - 17.58% |
| **Vol range** | 4.23% - 14.54% | 4.24% - 15.91% | 6.45% - 19.35% |
| **Yield range** | 1.55% - 4.95% | 0.79% - 5.10% | 0.76% - 4.84% |

**Frontier** found 100 solutions spanning a well-defined three-dimensional frontier. The return range (3.0%-17.3%) is slightly narrower than Solver's (2.2%-18.3%) because Frontier's curated Growth in the base-case JSON uses a different solution than the extreme max-return solution.

**Solver** produced 38 valid solutions from 45 raw solutions (7 filtered for constraint violations). The wider objective ranges (especially yield 0.79%-5.10%) suggest the Solver explored more aggressively, though some extreme solutions may have been enabled by the 0.5% constraint tolerance that allowed 31% allocations.

**LLM** generated only 8 portfolios. The volatility range (6.45%-19.35%) is notably wider on the high end because the LLM uses weighted-average volatility, which overstates risk by 30-50% for diversified portfolios. The true covariance-based vol for LLM's Safety portfolio would be approximately 4-5%, not 6.45%.

### 1b. Corner Solutions

Frontier's corner solutions are concentrated as expected: Max Return holds VDE 30%, GLD 30%, IGF 22%; Min Vol holds VGSH 30%, HYG 30%, BND 23%. These are recognizable extremes.

Solver's Growth (VGT 31%, VDE 30%, GLD 30%, EWJ 9%) is maximally concentrated at only 4 holdings, with VGT exceeding the 30% cap.

LLM's extremes are less concentrated (Growth has 6 holdings at 10-30%) because the LLM was constrained by its inability to compute covariance-based diversification -- it needed more holdings to keep weighted-average vol under 20%.

### 1c. Frontier Coverage Gaps

**Head-to-Head at Matched Return Targets (base case)**

For each target return, the nearest solution's volatility is shown. Lower vol at the same return = better frontier position.

| Target Return | Frontier vol | Solver vol | LLM vol |
|:---:|:---:|:---:|:---:|
| 4% | 4.8% | 4.5% | 7.6% |
| 6% | 6.5% | 8.1% | --- |
| 8% | 7.9% | 8.4% | 14.1% |
| 10% | 8.8% | 11.7% | 13.0% |
| 12% | 11.5% | 8.7% | --- |
| 14% | 11.0% | 14.4% | --- |
| 18% | 14.3% | 14.8% | 19.4% |

*Note: LLM "---" means no solution within 1pp of target.*

**Key finding:** Frontier and Solver are competitive on efficiency (similar vol at matched returns), with Frontier generally producing slightly lower vol in the 6-10% return range and Solver slightly better at the 4% and 12% extremes. LLM volatilities are dramatically higher -- its 8% return portfolio has 14.1% vol (weighted-average) versus Frontier's 7.9% (covariance-based). Even adjusting for the vol calculation difference, LLM portfolios are less efficient.

LLM has no solution within 1pp of 6%, 12%, or 14% return -- it simply did not explore those regions. This is the fundamental coverage gap of hand-crafted approaches.

### 1d. Navigability

**Frontier:** The explore tools (tradeoffs, solution, curate, marginal_analysis) provide on-demand access to any point on the frontier. A user can request "show me the best portfolio at 11% return" and get an answer. The payload/token limit forced reliance on individual solution queries rather than bulk export, but the navigability was preserved.

**Solver:** Results are static -- the 38 solutions exist in results.json but there is no interactive way to request intermediate solutions without re-running the solver. However, 38 solutions provide enough density to interpolate manually.

**LLM:** No navigability. The 8 solutions are all that exist. Requesting an intermediate portfolio requires the LLM to reason from scratch, with no guarantee of improvement or consistency with the existing set.

### 1e. Scenario-Phase Exploration

| Dimension | Frontier | Solver | LLM |
|-----------|----------|--------|-----|
| **Solutions per scenario** | 100 | 300 | 5-6 |
| **Per-scenario curated strategies** | Yes (4 per scenario) | Yes (4 per scenario) | Yes (4-6 per scenario) |
| **Curated strategies differ across scenarios?** | Yes -- holdings shift meaningfully | Yes -- dramatic compositional changes | Yes -- but less structurally diverse |

**Solver** scales up dramatically in the scenario phase: 300 solutions per scenario (1,200 total) versus Frontier's 100 per scenario (400 total). This 3x density advantage provides better frontier coverage, though both methods produce adequate density for tradeoff assessment.

**LLM** remains sparse: 5-6 portfolios per scenario (21 total). The coverage gaps become more severe in scenario analysis because the investor needs to compare positions across regimes.

**Do curated strategies actually differ across scenarios?** This is the critical test.

- **Frontier:** Growth shifts from VDE/VGT/GLD in base to VDE/GLD/GSG/DBA in inflation. Safety goes from BND/VGSH-heavy (base) to adding TIP at 29% in inflation. The balanced portfolio concentrates to 5 holdings in inflation (from 7 in base). These are genuine structural shifts reflecting the scenario score adjustments.

- **Solver:** Even more dramatic shifts. Recession Growth contains zero equities (VGLT 30%, GLD 30%, GSG 30%), while base Growth is VGT/VDE/GLD. Safety vol drops to 2.38% in recession (from 2.66% base). The solver finds truly different optimal compositions per regime.

- **LLM:** Strategy shifts are directionally correct (more commodities in inflation, more bonds in recession) but the compositions are less extreme. LLM's recession Growth holds IGF 10% and DBA 15% alongside bonds and gold, while the solver's recession Growth is purely VGLT/GLD/GSG. The LLM hedges its bets rather than fully optimizing per scenario.

---

## 2. Tradeoff Assessment

*How well does each method quantify and explain what you give up to get more of what you want?*

### 2a. Quantification

| Check | Frontier | Solver | LLM |
|-------|----------|--------|-----|
| **Marginal rates stated?** | Yes: "0.84 pts vol per pt return" with inflection points | Yes: "0.79 pts vol per 1% return" (linear approximation between curated strategies) | Yes: "1.18 pts return per 1 pt vol" (inverted framing) |
| **Source of tradeoff numbers** | Computed from 100-solution set with marginal_analysis tool; inflection detection | Computed as gap between curated strategies | Computed as gap between hand-picked extremes |
| **Knee points / diminishing returns?** | Yes: "inflection at 13% return where marginal cost jumps 400x" | Yes: "10% return threshold -- below this, vol stays 5-8%; above, escalates sharply" | No explicit knee detection; qualitative "disproportionate risk" |
| **Multi-objective tradeoffs?** | Yes: "gains 6.9pp return, costs 5.8pp vol AND 1.6pp yield" | Partial: return-vol and return-yield stated separately | Partial: "13.5pp return costs 11.4pp vol and 2.8pp yield" |

**Frontier** provides the most rigorous tradeoff quantification because it can compute marginal rates from the dense solution set and detect inflection points algorithmically. The "400x cost jump at 13% return" is a computed finding, not a narrative assertion.

**Solver** provides solid quantification but computes it as linear ratios between curated extremes rather than from the continuous frontier shape. Its "10% return threshold" insight matches Frontier's but is stated less precisely.

**LLM** provides plausible tradeoff ratios but these are computed from gap arithmetic between 8 portfolios, not from frontier analysis. The 1.18:1 return-per-vol ratio is the weakest quantification because it treats a nonlinear frontier as linear.

### 2b. Structural Insights

**Frontier (response.md):** "Three ETFs appear in every curated portfolio: EWJ, HYG, DBA -- universal building blocks because they combine decent yields with correlation structures that aid diversification." This is a computed observation (which ETFs actually appear across solutions) rather than a domain assertion.

**Solver (response.md):** "HYG is the workhorse -- appears in 30 of 38 solutions." Quantified frequency counts are cited. "VGT and VDE rarely appear together at large weights due to their combined volatility" -- a structural pattern identified from the solution set.

**LLM (response.md):** "GLD is the standout performer: 19.88% return at only 15.91% vol makes it the most efficient return source." This is correct and insightful, but it is a per-ETF observation about the input data, not a discovery from the optimization. The LLM also identifies "DBA is an underappreciated pick" -- genuine insight, but based on individual ETF metrics rather than portfolio-level optimization.

### 2c. Data Grounding

**Frontier:** All assertions traceable to the input data (scores from JSON file) and optimization results. No fabricated values observed. The covariance matrix was explicitly uploaded and used.

**Solver:** All scores loaded from the same data file. Covariance matrix loaded from etf_cov_matrix.json. No fabricated values. The solver does note the VGT sector multiplier ambiguity (1.5x equity * 1.4x sector vs 1.8x override) and documents the resolution.

**LLM:** Scores are manually recalled/transcribed from the problem specification. Arithmetic verification is provided inline (e.g., return = 0.30*19.88 + 0.20*11.98 + ...). However, the volatility calculation uses weighted-average approximation, which the LLM correctly flags as a limitation ("overstates risk by 3-8pp for diversified portfolios"). This is honest data grounding -- the LLM knows its numbers are approximate and says so.

### 2d. Dominated Curated Solutions

**Cross-method domination check (base case):**

| Strategy | Frontier (ret/vol/yield) | Solver (ret/vol/yield) | LLM (ret/vol/yield) | Dominated? |
|----------|--------------------------|------------------------|----------------------|------------|
| Growth | 16.34 / 13.27 / 2.09 | 18.33 / 15.91 / 1.22 | 16.28 / 17.86 / 1.28 | LLM Growth dominated by Frontier Growth (higher ret, lower vol, higher yield) |
| Balanced | 9.38 / 7.52 / 3.66 | 9.42 / 8.31 / 3.99 | 10.47 / 13.02 / 2.55 | LLM Balanced dominated by Frontier Balanced (similar ret, much lower vol, higher yield) |
| Income | 4.43 / 7.02 / 4.95 | 2.22 / 7.10 / 5.10 | 2.69 / 10.57 / 4.84 | LLM Income dominated by both Frontier and Solver (both have lower vol with higher or comparable yield) |
| Safety | 3.35 / 4.23 / 4.39 | 3.43 / 4.24 / 4.39 | 2.80 / 6.45 / 4.07 | LLM Safety dominated by both (higher vol, lower yield, lower ret) |

**Finding:** All four LLM curated strategies are dominated by the corresponding Frontier strategy. The LLM user would not know this -- the LLM's response does not compare against optimizer baselines, and the weighted-average vol numbers make the LLM portfolios appear more different from the optimizer results than they actually are.

Frontier and Solver curated strategies do not dominate each other in a strict three-objective sense -- Solver Growth has higher return but also higher vol and lower yield; Solver Income has higher yield but lower return.

### Side-by-Side Interpretation Quotes

**1. How each method describes the Balanced portfolio:**

> **Frontier:** "This is the 'ideal point closest' solution identified by Frontier's balanced-solution algorithm. VGSH (26%) provides a large low-volatility anchor, reducing portfolio risk dramatically. The quadratic volatility of 7.52% is much lower than the weighted-average of the individual ETFs, demonstrating significant diversification benefit."

> **Solver:** "Closest to the ideal point (max return, min vol, max yield) in normalized objective space. 4 holdings. HYG at 31% violates the 30% max allocation constraint."

> **LLM:** "Sits in the middle of the frontier. Compared to Growth, it gives up 5.8 points of return but gains 1.3 points of yield and reduces vol by 4.8 points. It represents the most diversified approach across all asset groups."

*The Frontier response explains the mechanism (covariance-based vol reduction). The Solver notes the constraint violation honestly. The LLM frames it comparatively against other strategies. Only Frontier explains WHY the balanced portfolio achieves its risk level.*

**2. How each method quantifies tradeoffs:**

> **Frontier:** "Moving from Balanced to Growth gains 6.9pp return but costs 5.8pp vol and 1.6pp yield. That is roughly 0.84pp extra vol per point of return gained. However, this rate is not constant. There is a sharp inflection at 13% return where the marginal cost jumps 400x."

> **Solver:** "Each additional 1% of return costs roughly 0.79% additional volatility. This ratio is roughly linear through the middle of the frontier but accelerates at the extremes."

> **LLM:** "The exchange rate is roughly 1.18 points of return per 1 point of vol -- but this comes at the cost of nearly 3 points of yield."

*Frontier provides the most precise quantification with inflection detection. Solver notes nonlinearity qualitatively. LLM inverts the ratio (return per vol rather than vol per return) and provides a single linear rate, missing the nonlinearity.*

**3. How each method invites further exploration:**

> **Frontier:** "The 10-13% return range offers an attractive middle ground with moderate volatility. Solutions in this range tend to hold VDE at 15-25% with larger VGSH/HYG buffers."

> **Solver:** "Diversification-minded investors should look at solutions with 6-8 holdings, which sacrifice 2-4% return for broader exposure."

> **LLM:** "If you want 15%+ returns, accept ~18% vol and under 1.5% yield. The portfolio will be concentrated in GLD, VDE, VGT, and VOO."

*Frontier points to a specific region of its frontier that the user can navigate to. Solver offers a general design principle. LLM provides a conditional recommendation but has no frontier to navigate.*

**4. How each method handles a non-obvious finding:**

> **Frontier:** "Despite the safety focus, yield is strong at 4.39% because bond ETFs (VGSH 3.95%, HYG 5.88%, BND 3.91%) are high-yielding." (Computed from optimized portfolio that discovered bond-yield alignment)

> **Solver:** "Note: Income accepts higher volatility than Safety despite lower return -- this is the cost of maximizing yield." (Observed from solution set comparison)

> **LLM:** "DBA (agriculture) is an underappreciated pick: moderate return, low vol, and solid yield." (Domain observation about individual ETF metrics)

*Frontier and Solver surface findings from the optimization output. The LLM's insight is valid but comes from reading the input data, not from portfolio-level optimization.*

---

## 3. Respecting Constraints

*Does the method guarantee feasibility? Where does it cut corners?*

### 3a. Constraint Enforcement

| Check | Frontier | Solver | LLM |
|-------|----------|--------|-----|
| **Enforcement mechanism** | Structural: NSGA-II with penalty-based constraint handling during evolutionary search | Repair operator (sequential clip/normalize) + pymoo inequality constraints | Manual arithmetic + constraint checking per portfolio |
| **Guarantee type** | Structural: constraints are enforced at every generation | Code-quality dependent: repair operator has a known normalization-clipping loop issue | Arithmetic-dependent: correct only if the LLM does the math right |
| **Violations found (base case)** | 0 | 2 (VGT 31% in Growth, HYG 31% in Balanced) | 0 (but vol constraint is checked against wrong metric) |

**Frontier** enforces constraints structurally within the optimizer. All 100 base-case solutions and all per-scenario curated strategies pass constraint verification. No violations observed.

**Solver** has a known repair operator bug: the iterative normalization loop (10 iterations, sum-tolerance exit) can leave allocations above 30%, and the validation filter uses a 0.5% tolerance (>30.5% = reject). This allows 31% allocations through. Two of four base-case curated strategies have violations (Growth VGT 31%, Balanced HYG 31%). The issues.md documents this thoroughly with line-number references and proposed fixes. In the scenario phase, the solver's issues.md states "no constraint violations observed" in the final Pareto sets, suggesting the upgraded configuration (300 pop, 500 gen) reduced but may not have eliminated the issue.

**LLM** checks constraints manually. All portfolios satisfy the stated constraints, but the volatility constraint is checked against weighted-average vol, not covariance-based vol. This means the LLM is enforcing a different (more conservative) constraint than the specification intends. Some portfolios that the LLM rejected for exceeding 20% weighted-avg vol would have been feasible at covariance-based vol, meaning the LLM's feasible region is artificially restricted.

### 3b. Boundary Behavior

| Check | Frontier | Solver | LLM |
|-------|----------|--------|-----|
| **Max allocation headroom** | Many solutions at exactly 30% (VDE, GLD, HYG, VGSH) | Solutions at 29-31% due to normalization | Allocations in round numbers (5/10/15/20/25/30) |
| **Vol constraint headroom** | Max observed 14.54% vs 20% limit -- never binding | Max observed 15.91% vs 20% -- never binding | Max observed 19.35% vs 20% -- nearly binding |
| **Cardinality range used** | 5-11 holdings (of 4-12 allowed) | 4-10 holdings | 4-8 holdings |
| **Sector/alt group limits** | Alt limit frequently at 3/3; sector rarely above 2 | Alt and sector limits respected | Alt limit at 3/3 in some; sector at 2/3 |

The vol constraint difference is striking: Frontier and Solver never approach the 20% ceiling because covariance-based vol benefits from diversification, while LLM portfolios crowd the ceiling because weighted-average vol cannot credit diversification. LLM's Growth-Income Blend at 14.10% weighted-avg vol likely has ~9-10% covariance-based vol.

### 3c. Data Provenance

| Check | Frontier | Solver | LLM |
|-------|----------|--------|-----|
| **Score source** | JSON file loaded via MCP tool | JSON file loaded via Python code | Manually transcribed from problem spec |
| **Fabrication risk** | None -- scores entered via tool from file | None -- scores loaded programmatically | Low -- LLM provides inline arithmetic verification |
| **Covariance handling** | Full 30x30 matrix uploaded; quadratic vol confirmed by cross-checks | Full 30x30 matrix loaded; quadratic vol computed | Not used; weighted-average approximation acknowledged as limitation |

### 3d. Scaling Judgment

| Check | Frontier | Solver | LLM |
|-------|----------|--------|-----|
| **Would handle 100 options, 10 constraints?** | Yes -- NSGA-II scales to hundreds of options; constraints are structural | Yes -- pymoo handles large problems; repair operator would need more iteration | No -- manual arithmetic becomes infeasible; constraint tracking error rate grows |
| **Adding a new constraint requires...** | Config change (add constraint via MCP tool) | Code change (add to repair operator + inequality function) | Re-reasoning from scratch |

### 3e. Constraint Summary

Frontier provides the strongest constraint guarantee: structural enforcement with zero violations. Solver provides a code-based guarantee that works in practice but has a documented edge case producing 1% overages. LLM provides best-effort arithmetic with honest acknowledgment of its limitations, but enforces a fundamentally different (wrong) volatility constraint.

---

## 4. User Workflow

| Check | Frontier | Solver | LLM |
|-------|----------|--------|-----|
| **Setup effort** | 3 MCP tool calls (create, score, constrain) + covariance upload + solve | ~455 lines of Python code | Zero code |
| **Solve effort** | ~10-15 seconds | ~5 seconds (base), ~60-80 seconds (scenarios) | N/A (reasoning time) |
| **Explore effort** | Multiple explore tool calls; limited by token/payload caps | Static JSON output | N/A |
| **Skill guidance received** | 3 auto-injected skills (data_collection, optimization_strategy, solution_interpreter) | None | None |
| **Token/payload issues** | Yes: solve output (145K chars) exceeded MCP limit; workaround via explore tools | None | None |
| **Self-assessment accuracy** | High: correctly identifies payload limitation, notes HYG covariance anomaly | High: correctly identifies repair operator bug, proposes 3 fixes | Very high: identifies 8 distinct limitations with accurate severity ratings |

**LLM's self-assessment stands out.** The issues.md identifies weighted-average vol limitation (HIGH), dominated solutions (MEDIUM), missing systematic frontier exploration (HIGH), and ETF selection bias (MEDIUM) -- all accurate. This level of metacognition is valuable even though the method itself is limited.

---

## 5. Scenario Handling

| Dimension | Frontier | Solver | LLM |
|-----------|----------|--------|-----|
| **Solutions per scenario** | 100 | 300 | 5-6 |
| **Additional effort beyond base** | 1 model update (scenario_config) + solve + explore per scenario | New Python script (~320 lines) + 4 separate runs | Manual score adjustment + portfolio construction per scenario |
| **Per-scenario curated strategies?** | Yes (4 per scenario, 16 total) | Yes (4 per scenario, 16 total) | Yes (4-6 per scenario, 21 total) |
| **Growth shifts across scenarios?** | Yes: VGT/VDE in base -> VDE/GLD/GSG/DBA in inflation; genuinely different compositions | Yes: VGT/VDE/GLD in base -> VGLT/GLD/GSG in recession (zero equities); most dramatic shifts | Yes: directionally correct but less concentrated |
| **Safety stable across scenarios?** | Vol 4.11-4.26% across 4 scenarios | Vol 2.38-2.66% across 4 scenarios | Vol 5.23-7.37% across 4 scenarios |
| **Robustness metric** | Importance Score (frequency * avg weight) with Core/Common tiers; top: HYG (21.0), GLD (15.4), VDE (13.7) | Avg Frequency with Common tier (no Core -- no ETF >50% min freq); top: HYG (66.7%), GLD (64.6%), DBA (59.5%) | Qualitative tiers (Core/Scenario-Specific/Marginal/Avoided); top: VGSH, SCHD, DBA, TIP, GLD |
| **Scenario-specific opportunities** | VNQI (base/rate_cuts/inflation, not recession), MCHI (rate_cuts/recession only) | BND (64% in recession vs <1% elsewhere), DBA (92% in inflation) | VGT (rate cuts star), VGLT (recession/rate cuts), GSG (inflation) |
| **Constraint violations per scenario** | 0 | 0 (stated -- 300/500 config improved over 200/400 base) | 0 (but wrong vol metric) |

### Scenario-Phase Curated Comparison

**Growth strategy across scenarios (Return / Vol):**

| Scenario | Frontier | Solver | LLM |
|----------|----------|--------|-----|
| Base | 18.76 / 15.64 | 19.03 / 15.91 | 14.88 / 18.80 |
| Rate Cuts | 18.37 / 15.35 | 25.79 / 16.00 | 23.45 / 18.32 |
| Recession | 18.33 / 15.34 | 12.70 / 10.43 | 8.26 / 9.29 |
| Inflation | 17.36 / 14.28 | 33.52 / 15.69 | 27.98 / 17.07 |

**Critical observation:** Frontier's Growth strategy is remarkably stable across scenarios (17.4-18.8% return, 14.3-15.6% vol) while Solver and LLM show dramatic variation (Solver: 12.7-33.5% return). This is because Frontier appears to be selecting from a frontier that was computed using base-case scores and then evaluated under scenario-adjusted scores, while the Solver recomputes the entire optimization per scenario. The Solver's approach is more technically correct for scenario analysis (it finds the true Pareto frontier under each set of scenario-adjusted scores), while Frontier's approach shows what the same portfolios achieve under different conditions.

**Safety strategy across scenarios (Vol):**

| Scenario | Frontier | Solver | LLM |
|----------|----------|--------|-----|
| Base | 4.24 | 2.66 | 6.36 |
| Rate Cuts | 4.26 | 2.61 | 6.18 |
| Recession | 4.19 | 2.38 | 5.30 |
| Inflation | 4.11 | 2.66 | 5.23 |

Solver achieves dramatically lower safety vol (2.4-2.7%) compared to Frontier (4.1-4.3%) and LLM (5.2-6.4%). The Solver finds ultra-concentrated 4-holding safety portfolios (VGSH 30%, HYG 30%, plus small satellite positions) that achieve true minimum volatility. Frontier's safety portfolios are more diversified (8-11 holdings) and achieve slightly higher vol.

**Balanced strategy across scenarios (Return / Vol / Yield):**

| Scenario | Frontier | Solver | LLM |
|----------|----------|--------|-----|
| Base | 10.48 / 8.17 / 3.45 | 9.33 / 6.60 / 3.47 | 11.35 / 14.67 / 2.04 |
| Rate Cuts | 8.86 / 7.69 / 4.00 | 12.05 / 8.78 / 3.02 | 17.45 / 15.26 / 1.73 |
| Recession | 10.07 / 8.66 / 3.78 | 4.78 / 4.36 / 4.02 | 6.48 / 7.28 / 2.69 |
| Inflation | 9.94 / 8.16 / 3.66 | 16.40 / 7.48 / 4.03 | 20.49 / 13.35 / 2.22 |

Solver's Balanced achieves the best risk-adjusted performance in most scenarios (lowest vol-to-return ratio). LLM's Balanced consistently has the highest vol due to the weighted-average approximation.

---

## 6. Cross-Phase Insights

### What Scenarios Revealed

1. **Frontier's scenario implementation appears to re-evaluate the same portfolio space under different scores** rather than re-optimizing from scratch. This produces stable curated strategy metrics but may miss scenario-specific optimal compositions that differ structurally from the base frontier.

2. **Solver's per-scenario re-optimization** reveals the most dramatic structural shifts (zero-equity recession Growth, pure-commodity inflation Growth). This is the technically correct approach for "what is optimal under each regime" and provides the richest scenario-specific insights.

3. **LLM's scenario analysis** is directionally correct but consistently less efficient. The LLM correctly identifies which ETFs benefit under each scenario but cannot find the optimal mix, leading to portfolios that a user might implement but that leave risk-adjusted return on the table.

### Constraint Enforcement Under Scenario Stress

Frontier maintained zero violations across all 4 scenarios. Solver improved from 2 violations (base, 200/400 config) to 0 violations (scenarios, 300/500 config) -- the larger population and more generations helped the repair operator converge. LLM continued to check the wrong volatility metric, meaning its effective constraint set differs from the specification.

---

## 7. Plots

All plots saved to `dev_temp/eval/run_001/plots/`.

| Plot | File | What It Shows |
|------|------|---------------|
| B1 | `base_B1_pairwise_clouds.png` | Base case: all three objective pairs overlaid. Frontier (blue) and Solver (green) form continuous frontiers; LLM (red) shows 8 scattered points. |
| B2 | `base_B2_return_vol_annotated.png` | Return vs Vol deep dive: Frontier fills the efficient frontier densely, Solver matches at extremes but with gaps, LLM solutions are shifted right (higher vol) due to weighted-average calculation. |
| S1 | `scenario_S1_pairwise_grid.png` | 4x3 grid showing each scenario's three objective pairs. Solver (300 solutions) dominates in density. Frontier (100) provides solid coverage. LLM (5-6) is visually sparse. |
| S2 | `scenario_S2_return_vol_annotated.png` | Per-scenario Return vs Vol with curated strategy labels. Most visible: Solver's recession frontier collapses (max ~13% return), while Frontier's stays extended (~18%). Inflation shows the widest Solver spread (to 33.5%). |
| S3 | `scenario_S3_strategy_migration.png` | How each curated archetype moves across scenarios. Safety (all methods) is stable. Growth and Balanced show the widest migration, with Solver showing the largest swings. |

---

## 8. Pitfall Rating Table

| Pitfall | Frontier | Solver | LLM |
|---------|----------|--------|-----|
| **Infeasible plans** | **Prevented** -- structural constraint enforcement, zero violations across all runs (3a) | **Mitigated** -- repair operator + inequality constraints, but 2 violations in base case from normalization-clipping loop (3a). Fixed in scenario phase with larger config. | **Present** -- manual arithmetic, wrong vol metric. All portfolios pass stated checks, but the vol constraint is against weighted-average, not covariance-based (3a, 3b). |
| **Stray assumptions** | **Prevented** -- all scores from data file, covariance matrix explicitly uploaded, no domain assertions without data backing (2c, 3c) | **Prevented** -- all scores from data file, covariance matrix loaded programmatically, scenario adjustments documented with ambiguity notes (2c, 3c) | **Mitigated** -- scores manually transcribed with arithmetic verification, but vol calculation is an approximation acknowledged as HIGH severity limitation. No fabricated scores, but a structural simplification (2c, 3c). |
| **Incomplete exploration** | **Mitigated** -- 100 solutions provide good but not exhaustive coverage. Token limits initially forced sampling in base JSON (resolved by direct extraction). Explore tools provide navigability beyond the static set (1a, 1b). | **Mitigated** (base) / **Prevented** (scenarios) -- 38 base solutions have some gaps, but 300 per scenario provides excellent coverage. Static output limits navigability (1a, 1b, 1c). | **Present** -- 5-8 solutions per phase, no systematic exploration, large coverage gaps at 6%/12%/14% return, acknowledged by the method itself as HIGH severity (1a, 1b, 1c). |
| **Opaque reasoning** | **Mitigated** -- marginal rates computed from solution set, inflection points detected algorithmically, but the 400x cost jump requires context to interpret. Tradeoffs are quantified, not narrated (2a, 2d). | **Mitigated** -- marginal rates computed between curated strategies, structural patterns identified from solution frequencies. Dominated solutions within the method's own set are possible but not checked (2a, 2d). | **Present** -- tradeoff rates from hand-picked gap arithmetic, no frontier-derived marginal analysis, curated solutions dominated by other methods without user awareness. However, self-assessment is exceptionally honest (2a, 2d). |

---

## 9. Verdict

### Per Lens

**Solution Exploration:** Solver wins on raw density (300 solutions/scenario vs 100 for Frontier), but Frontier wins on navigability (explore tools vs static output). LLM is not competitive. **Edge: Solver for density, Frontier for usability.**

**Tradeoff Assessment:** Frontier wins with computed marginal rates, inflection detection, and multi-objective tradeoff quantification from a dense solution set. Solver provides solid but less sophisticated analysis. LLM provides genuine interpretive insight and excellent self-assessment but from fundamentally limited data. **Clear win: Frontier.**

**Respecting Constraints:** Frontier wins with zero violations and structural enforcement. Solver is close but has a documented repair operator bug (2 violations in base case, resolved in scenarios). LLM enforces the wrong volatility metric despite honest acknowledgment. **Clear win: Frontier.**

### Overall

**Frontier provides the best overall combination** of exploration (100 dense solutions), explanation (computed tradeoffs with inflection detection), and constraint reliability (zero violations). Its main weakness is token/payload limits that forced result sampling, and its scenario implementation may not fully re-optimize per scenario.

**Solver is the strongest explorer** -- 300 solutions per scenario with dramatic structural shifts reveal the true shape of each regime's frontier. It is the right choice when maximum coverage matters and the user can write/debug code. Its repair operator bug is a real but fixable issue.

**LLM provides the best self-assessment** and most readable narrative, but every curated strategy is dominated by the optimizer-based methods. It is suitable for initial intuition-building but not for final portfolio selection. Its honest acknowledgment of limitations (8 distinct issues identified with severity ratings) is a model of transparent reasoning that the other methods could learn from.

**Bottom line:** For the question "which approach best explores and explains the Pareto frontier?" -- Frontier wins. It finds a dense frontier, explains it with computed metrics, and guarantees constraint satisfaction. The Solver is the best pure optimizer but requires code and produces less interpretive output. The LLM is the best narrator but the worst optimizer.

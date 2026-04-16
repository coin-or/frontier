# Pitfall Assessment: 30-ETF Portfolio Demo

**Date:** 2026-04-13
**Methods:** Frontier (MCP tools + skills), Agent + pymoo, LLM-only reasoning
**Data:** 30 ETFs, 3 objectives (return ↑, volatility ↓, yield ↑), 4 constraints

---

## 1. Infeasible Plans

*Does the method propose portfolios that violate hard constraints?*

| Method | Verdict | Evidence |
|--------|---------|----------|
| **Frontier** | **Pass** | Constraints are encoded in the solver. All 182 solutions satisfy vol ≤ 20%, sector ≤ 3, alternatives ≤ 3, cardinality 4-12, sum = 100%. Infeasibility is structurally impossible — the engine rejects violations before they reach the output. |
| **pymoo** | **Pass** | Custom repair operator enforces constraints during evolution. All 45 solutions verified post-hoc. However, the repair operator is 80+ lines of hand-written code — if a user wrote it wrong, infeasible solutions could leak through silently. The constraint enforcement is only as good as the code the agent writes. |
| **LLM** | **Pass, but fragile** | All 4 portfolios happen to satisfy constraints. The LLM verified them in a table. But there's no structural guarantee — it did mental arithmetic and could have miscounted sector holdings or misclassified an ETF's group. The Growth portfolio lands at 19.98% vol, 0.02% under the 20% ceiling. One small allocation change and it would have violated. The LLM got lucky that the problem is small enough for mental tracking. At 100 options with 10 constraints, this approach breaks. |

**Bottom line:** Frontier makes infeasibility impossible by construction. pymoo makes it unlikely but depends on correct custom code. LLM makes it a manual verification burden that scales poorly.

---

## 2. Stray Assumptions

*Does the method invent plausible-sounding scores or relationships rather than flagging missing data?*

| Method | Verdict | Evidence |
|--------|---------|----------|
| **Frontier** | **Pass** | All scores came from the user-provided `etf_30_consolidated.json` data file. The agent entered 90 scores (30 ETFs × 3 objectives) in a single batch from the JSON. No scores were invented. The solver operates on exactly the data entered — it has no mechanism to "fill in" missing values. |
| **pymoo** | **Pass** | Same data file loaded directly via `json.load()`. The script reads hard numbers and passes them to the optimizer. No gap-filling. |
| **LLM** | **Pass with a caveat** | The LLM used the same data file and cited specific numbers (VDE 22.08% return, GLD 19.88%, etc.) that match the source. No fabricated scores. **However**, the LLM did make one soft assumption that colored its portfolio construction: it treated VNQI as a yield play worth 15% allocation despite its -0.58% return and 18.22% volatility, reasoning "alternatives group has strong yielders." This isn't fabricated data — it's a judgment call that a solver would have penalized automatically. The LLM itself flagged this in its limitations section ("VNQI is a yield trap"), which is honest, but it still shipped the portfolio with VNQI in it. |

**Bottom line:** In this demo, all three methods drew from the same data file, so fabrication risk was low. The real test of stray assumptions would come when data has gaps — Frontier would flag missing scores (the data_collection skill explicitly instructs "flag unknowns"), pymoo would crash on missing values, and the LLM would be the most tempted to fill them in with plausible guesses.

---

## 3. Incomplete Exploration

*Does the method enumerate the solution space, or just compress prior training data into plausible answers?*

| Method | Solutions | Return Range | Vol Range | Yield Range |
|--------|-----------|-------------|-----------|-------------|
| **Frontier** | 182 | 2.31 – 19.01% | 3.06 – 18.76% | 0.26 – 5.50% |
| **pymoo** | 45 | 3.75 – 14.17% | 9.23 – 17.43% | 1.78 – 4.53% |
| **LLM** | 4 | 1.56 – 18.58% | 4.52 – 19.98% | 0.90 – 5.06% |

| Method | Verdict | Evidence |
|--------|---------|----------|
| **Frontier** | **Best coverage** | 182 solutions spanning the full objective space. Found the VGSH-concentrated safety region (3.06% vol) and the GLD-concentrated growth region (19.01% return) that both other methods missed or undershot. The `explore tradeoffs` tool reveals 165 marginal rate segments per objective pair with knee detection, giving continuous visibility into the tradeoff surface. |
| **pymoo** | **Systematically incomplete** | 45 solutions, all with exactly 12 holdings. The repair operator's normalization logic prevents concentrated allocations, which means it never explores the corners of the feasible space where the most extreme (and often most interesting) tradeoffs live. It missed 5pp of return range at the top, 6pp of vol range at the bottom, and 1pp of yield range at the top. This isn't random sampling noise — it's a structural gap caused by the repair operator spreading weight too broadly. A user who only saw pymoo's results would believe the maximum achievable return is 14.17% when it's actually 19.01%. |
| **LLM** | **Radically incomplete** | 4 solutions. The LLM itself estimates it explored "approximately 40-50 candidate allocations" out of a space on the order of trillions. It found competitive Growth and Safety endpoints but missed the interior of the Pareto surface entirely. There's no solution between Safety (4.52% vol) and Income (10.78% vol), or between Balanced (9.82% return) and Growth (18.58% return). A user who wanted "a little more return than Balanced but not as much risk as Growth" has no options to examine — they'd have to ask the LLM to generate another portfolio and hope it lands in the right region. |

**The matched comparison makes this concrete.** At 6% return target: Frontier achieves 7.24% vol, pymoo needs 13.19% vol, and the LLM has no solution at all. At 14% return: Frontier needs 13.28% vol, pymoo needs 16.87% vol.

**The most dangerous gap is the one the user can't see.** LLM's Balanced (9.82% return, 12.90% vol, 2.72% yield) is dominated by Frontier's Balanced (9.89% return, 11.07% vol, 3.52% yield) — better on all three objectives. A user with only the LLM's output would never know.

---

## 4. Opaque Reasoning

*Can you audit the tradeoff logic, or was there no tradeoff computation — just generation?*

| Method | Verdict | Evidence |
|--------|---------|----------|
| **Frontier** | **Transparent and quantified** | Every tradeoff is computable. The `explore compare` tool shows exact marginal costs: "Moving from Safety to Balanced: gaining 7.6pp of return costs 8.0pp of additional volatility — roughly 1:1." The `explore tradeoffs` tool gives continuous marginal rates across the frontier (165 segments per pair). You can ask "what does one more percent of return cost me in vol?" and get a number, not a narrative. The tradeoff logic is recoverable because it was computed, not generated. |
| **pymoo** | **Transparent but limited** | The 45 solutions are computed, and you can calculate marginal rates between any pair. But the agent has to do this analysis manually in post-processing — there's no built-in exploration tooling. The interpretation the agent writes is a narrative layer on top of computable data, so it's auditable in principle. In practice, a user would need to write their own analysis code. |
| **LLM** | **Opaque by construction** | The LLM says "I started with balanced mixes of GLD/VDE/VGT/VOO, then realized GSG dominates VOO on return while keeping vol manageable." This reads like reasoning but it's not recoverable — you can't replay it, perturb it, or verify that the mental search actually visited the paths it claims. When it says its Balanced portfolio "sits in the middle on every metric," it can't tell you what it gave up vs. the next-best alternative. It narrates that "moving from Growth to Income costs 15.77pp of return" — but that's comparing two of its own hand-picked portfolios, not measuring the efficient frontier's marginal rate. The marginal cost *between* its 4 portfolios is not the same as the marginal cost along the true Pareto surface. |

**The key distinction:** Frontier and pymoo can answer "what's the cheapest way to gain 1% more yield from this portfolio?" with a computed answer. The LLM can only answer it by generating a new portfolio and hoping it's better — and it has no way to know if the new one is Pareto-optimal or just different.

---

## Summary Matrix

| Pitfall | Frontier | pymoo | LLM |
|---------|----------|-------|-----|
| **Infeasible plans** | Impossible by construction | Unlikely (depends on code quality) | Possible, manually verified |
| **Stray assumptions** | Not applicable (data entered explicitly) | Not applicable (data loaded from file) | Low risk here, high risk with gaps |
| **Incomplete exploration** | 182 solutions, full range | 45 solutions, compressed range, missed corners | 4 solutions, massive gaps |
| **Opaque reasoning** | Fully auditable marginal rates | Auditable with custom analysis | Narrative only, non-recoverable |

The LLM's honest self-assessment in its limitations section is genuinely impressive — it correctly identified that its Income portfolio might be dominated, that its Balanced allocations are somewhat arbitrary, and that it explored a vanishingly small fraction of the solution space. But self-awareness doesn't fix the problem. A user reading the LLM's 4 portfolios with no comparison point would have no reason to suspect that a strictly better Balanced portfolio exists, or that Safety could reach 3% vol instead of 4.5%. The narratives are polished enough to feel complete when they're not.

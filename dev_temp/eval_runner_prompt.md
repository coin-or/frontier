# Eval Runner Prompt

Sandboxed execution instructions for each method. Each runner agent receives ONLY the Problem Specification + its method section. No cross-method awareness, no eval criteria, no expected results.

---

## Problem Specification

### Decision

Allocate a portfolio across 30 ETFs to optimize three objectives simultaneously:
- **Expected Return (%)** — maximize, aggregation: sum
- **Volatility (%)** — minimize, aggregation: quadratic (uses covariance matrix for true portfolio risk)
- **Dividend Yield (%)** — maximize, aggregation: avg

Proportional allocation: assign a percentage (integer, minimum 1% if held) to each ETF, summing to 100%.

### Data

- **ETF scores:** `dev_temp/etf_cache/etf_30_consolidated.json`
  Each ETF has: ticker, category, group, dividend_yield_pct, ann_return_5yr_pct, ann_volatility_5yr_pct.
  Groups: US Equity (6), Intl Equity (5), Bonds (6), Sectors (7), Alternatives (6).

- **Covariance matrix:** `dev_temp/etf_cov_matrix.json`
  Pairwise annualized return covariance between all 30 ETFs. Use this for portfolio volatility calculation where the method supports it (quadratic/interaction-based aggregation). Otherwise fall back to weighted-average volatility.

### Constraints

1. **Max single allocation ≤ 30%** — no single ETF can exceed 30% of portfolio
2. **Portfolio volatility ≤ 20%** (quadratic-computed where supported, weighted-average otherwise)
3. At most 3 Sector ETFs held (group = "Sectors": VGT, VHT, VDE, VFH, VPU, VDC, VOX)
4. At most 3 Alternative ETFs held (group = "Alternatives": VNQ, VNQI, GLD, GSG, DBA, IGF)
5. Between 4 and 12 holdings total

### Scenarios (include only if running with scenarios)

The base-case data reflects 5-year historical performance (2021-2026). Stress-test portfolios against four forward-looking macro regimes. For each scenario, adjust the base-case scores as described, then optimize independently.

**Scenario 1: Base Case (Continuation)** — Probability: 30%. No changes.

**Scenario 2: Rate Cuts / Risk-On** — Probability: 25%.
- Score adjustments: equity returns × 1.5, equity vol × 0.8, bond yields × 0.5, sector returns × 1.4
- Overrides: VGLT return → +10.0%, VGT return → base × 1.8

**Scenario 3: Recession / Risk-Off** — Probability: 20%.
- Score adjustments: equity returns × 0.2, equity vol × 1.8, sector returns × 0.2, sector vol × 1.8, alternative returns × 0.5
- Overrides: VGSH return → +4.5%, BND return → +5.0%, VGLT return → +7.0%, HYG return → -4.0%, HYG vol → base × 1.8, EMB return → -5.0%, EMB vol → base × 1.8, GLD return → base × 1.3

**Scenario 4: Inflation Surge** — Probability: 25%.
- Score adjustments: equity returns × 0.6, equity vol × 1.3, bond returns × 0.3, bond yields × 1.2
- Overrides: GLD return → base × 2.0, GSG return → base × 2.0, DBA return → base × 2.0, TIP return → +8.0%, BND return → -5.0%, VGLT return → -12.0%, VDE return → base × 1.5

### Volatility note

Portfolio volatility depends on correlations between holdings. The covariance matrix enables proper quadratic calculation: vol = sqrt(w^T * Cov * w). Methods that can only do weighted-average volatility will overstate risk for diversified portfolios and get no credit for diversification. This is a known limitation — note it in issues but proceed with whatever your method supports.

### Deliverables

1. **Base case optimization** — Pareto-optimal portfolios for the base case.
2. **Per-scenario optimization** (if scenarios included) — Pareto-optimal portfolios per scenario.
3. **Robustness analysis** (if scenarios) — Which ETFs appear across all scenarios? Which are scenario-specific?
4. **Curated strategies** — Growth, Balanced, Income, Safety for base case (and per scenario if applicable).
5. **Cross-scenario comparison** (if scenarios) — How do curated strategies shift across scenarios?
6. **Interpretation** — Explain tradeoffs, quantify marginal costs, note inflection points.

---

## Shared Runner Setup

**What each runner does NOT receive:**
- Any knowledge of other methods being compared
- Any expected results, prior run data, or evaluation criteria
- Any guidance on what "good" looks like
- The eval checklist

**Output location:** `dev_temp/eval/<run_id>/<method>/`

**Required artifacts (all methods must produce these):**

1. **results.md** — Solution counts, objective ranges, per-scenario breakdowns. **Also produce `results.json`** with all solutions in a consistent format:
   ```json
   {
     "base": {
       "solutions": [
         {"return_pct": 10.5, "volatility_pct": 12.3, "yield_pct": 3.1,
          "allocations": {"VOO": 25, "GLD": 30, ...}},
         ...
       ],
       "curated": {
         "Growth": {"return_pct": ..., "volatility_pct": ..., "yield_pct": ..., "allocations": {...}},
         "Safety": {...}, "Income": {...}, "Balanced": {...}
       }
     },
     "rate_cuts": { ... },
     "recession": { ... },
     "inflation": { ... }
   }
   ```
   If base case only (no scenarios), use `{"base": {...}}` only.
2. **curated.md** — Curated strategies with objective values, allocations, and which constraints bind. If scenarios: curate per scenario independently.
3. **response.md** — Interpretation response written as if presenting to a user. Explain the tradeoff space, quantify what you give up to get more of what you want, invite further exploration. Do not say "best."
4. **issues.md** — Every issue encountered: bugs, limitations, surprises, dead ends, data gaps, constraint difficulties, payload problems. Be honest.

**Rules:**
- Work from the problem specification and data files alone.
- Use only the tools/capabilities specified for your method.
- Do not fabricate scores or data. If data is missing, flag it in issues.md.
- Show your work.
- Track solve time where possible.

---

## Method A: Frontier (MCP tools + skills)

**Available tools:** Frontier MCP server — `model` (create, update, get), `solve` (run, validate, run_scenarios), `explore` (tradeoffs, solutions, solution, compare, curate, compare_curated, marginal_analysis, scenario_results), `get_skill`.

**How to run:**
1. Read the ETF data and covariance matrix.
2. Create the problem via `model create` with approach="proportional", 3 objectives. For the Volatility objective, use `aggregation="quadratic"` — this enables proper portfolio volatility calculation using the covariance matrix instead of naive weighted average.
3. Enter scores via `model update` — load all score data from the ETF JSON. Enter every score; do not estimate or skip.
4. Upload the covariance matrix via `model update` with `interaction_matrices` parameter: `[{"objective": "Volatility", "entries": <cov_matrix>}]`. This tells the optimizer to compute portfolio volatility as sqrt(w^T * Cov * w).
5. Add constraints via `model update` — max_allocation 30, objective_bound (Volatility max 20), two group_limits (Sectors max 3, Alternatives max 3), cardinality (min 4, max 12).
6. Solve via `solve run` (mode="thorough").
7. Explore results: use `explore tradeoffs` for overview, `explore solution` for detail, `explore curate` to build the curated set, `explore marginal_analysis` for tradeoff rates and knee points.
8. If scenarios: configure via `model update` with `scenario_config`, then `solve run_scenarios`. Use `explore` with `scenario="<name>"` param to inspect per-scenario results (tradeoffs, solutions, curate per scenario). Use `explore scenario_results` for cross-scenario robustness.
9. Write interpretation response based on what the explore tools returned.

**What to capture in issues.md:**
- Skill guidance received (which skills auto-injected at which phase)
- Whether quadratic volatility worked correctly (did the optimizer use the covariance matrix?)
- Any payload/token limit problems
- Any explore actions that failed or returned incomplete data
- Constraint verification: structural guarantee or manual check?

---

## Method B: Agent + Solver (pymoo / custom code)

**Available tools:** Python execution (pymoo, numpy, json). No Frontier MCP tools. No skill resources.

**How to run:**
1. Read the ETF data and covariance matrix.
2. Write a Python script using pymoo (NSGA-II or NSGA-III) to solve the multi-objective optimization problem. Encode objectives, constraints, and options in code. For volatility, use the covariance matrix to compute true portfolio volatility: `vol = sqrt(w^T @ cov @ w)`.
3. Run the script. Capture solution count, solve time, raw results.
4. Write post-processing code to curate representative strategies from the Pareto set.
5. If scenarios: parameterize the script to run per-scenario with adjusted scores. Write cross-scenario analysis code (robustness, frequency, etc.).
6. Write interpretation response based on your computed results.

**What to capture in issues.md:**
- Total lines of code written (script + post-processing)
- Constraint enforcement approach (penalty, repair operator, etc.)
- Any constraint violations found in output
- Solver configuration decisions (population, generations, seed) and why
- How you handled the covariance matrix in the objective function
- Repair operator complexity if applicable

---

## Method C: LLM Only (pure reasoning)

**Available tools:** None. No code execution, no solver, no calculator, no tools. Pure reasoning only.

**How to run:**
1. Read the ETF data. You may read the covariance matrix but cannot compute matrix operations mentally — use weighted-average volatility as your approximation and note this limitation.
2. Construct portfolios for distinct strategy archetypes (Growth, Balanced, Income, Safety) by reasoning about which ETFs best serve each strategy while satisfying constraints.
3. Verify all constraints by computing weighted averages manually. Show the arithmetic.
4. If scenarios: compute adjusted scores using mental arithmetic (show all work), then repeat portfolio construction per scenario.
5. Write interpretation response based on your constructed portfolios.

**What to capture in issues.md:**
- How many candidate portfolios you considered before settling on final selections
- Any arithmetic you're uncertain about — flag precision concerns honestly
- That you used weighted-average volatility (not covariance-based) and what this means for your results
- Constraints that were difficult to track manually
- Your honest assessment of whether your portfolios might be dominated by solutions you didn't consider

---

## After All Runs Complete

Hand all three sets of artifacts (`results.md`, `results.json`, `curated.md`, `response.md`, `issues.md`) plus the eval checklist (`dev_temp/eval_checklist.md`) to an evaluator agent. The evaluator compares across methods — the runners do not.

---

## Execution Playbook

### Two phases, 3 sandboxed agents per phase, 1 evaluator

**Phase 1 — Base case only:** Each method solves the problem without scenarios. Remove the Scenarios section from the Problem Specification before passing to runners.

**Phase 2 — Multi-scenario:** Each method solves the full problem including all four scenarios. Include the Scenarios section.

Each phase launches 3 sandboxed agents in parallel (worktree isolation):

```
# Phase 1: Base case

Agent 1 (Frontier):
  Prompt: [Problem Specification WITHOUT Scenarios] + [Shared Runner Setup] + [Method A]
  Output: dev_temp/eval/<run_id>/base/frontier/

Agent 2 (Solver):
  Prompt: [Problem Specification WITHOUT Scenarios] + [Shared Runner Setup] + [Method B]
  Output: dev_temp/eval/<run_id>/base/solver/

Agent 3 (LLM):
  Prompt: [Problem Specification WITHOUT Scenarios] + [Shared Runner Setup] + [Method C]
  Output: dev_temp/eval/<run_id>/base/llm/

# Phase 2: Multi-scenario

Agent 4 (Frontier):
  Prompt: [Problem Specification WITH Scenarios] + [Shared Runner Setup] + [Method A]
  Output: dev_temp/eval/<run_id>/scenarios/frontier/

Agent 5 (Solver):
  Prompt: [Problem Specification WITH Scenarios] + [Shared Runner Setup] + [Method B]
  Output: dev_temp/eval/<run_id>/scenarios/solver/

Agent 6 (LLM):
  Prompt: [Problem Specification WITH Scenarios] + [Shared Runner Setup] + [Method C]
  Output: dev_temp/eval/<run_id>/scenarios/llm/
```

Wait for all 6 to complete, then launch the evaluator:

```
Evaluator agent:
  Input: dev_temp/eval/<run_id>/base/{frontier,solver,llm}/ +
         dev_temp/eval/<run_id>/scenarios/{frontier,solver,llm}/ +
         eval_checklist.md
  Output: dev_temp/eval/<run_id>/comparison.md + dev_temp/eval/<run_id>/plots/
```

### Key rules for sandboxing
- Each runner agent gets ONLY the Problem Specification + Shared Runner Setup + its method section. NOT the full prompt with all 3 methods.
- Runner agents must use worktree isolation so they can't see each other's output.
- The evaluator is the only agent that sees all methods' artifacts from both phases.
- Never show a runner the eval checklist — it would bias the response artifact toward checklist criteria rather than natural interpretation.

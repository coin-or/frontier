# Evaluation Checklist: Multi-Objective Optimization Methods

Reusable framework for comparing Frontier vs Agent+Solver vs LLM-Only across problem formulations (with/without scenarios). Each section specifies what to measure, where the evidence lives, and what "good" looks like.

---

## Inputs Per Run

Each evaluation run produces these artifacts per method. The checklist below references them by tag.

| Tag | Artifact | Example |
|-----|----------|---------|
| **[results]** | Raw solution data (Pareto set, objective values, allocations) | `scenario_frontier_v2.md`, `scenario_pymoo_raw.json` |
| **[curated]** | Curated strategies (Growth/Balanced/Income/Safety) with allocations and objectives | Tables in each method's results doc |
| **[response]** | Agent interpretation text presented to user | "Here is how the tradeoff space breaks down..." |
| **[issues]** | Issues log (bugs, limitations, surprises encountered during the run) | Issues sections in each method's doc |
| **[assignment]** | Shared problem specification given to all methods | `scenario_assignment.md` |

---

## 1. Solution Exploration

*How thoroughly does the method search the decision space, and can the user navigate what it found?*

### 1a. Coverage

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Total Pareto solutions found | **[results]** solution counts | More = better explored space |
| Objective range per axis (min–max for each objective) | **[results]** ranges | Wider = found more of the true frontier |
| Did it find corner solutions? (concentrated allocations at extremes) | **[curated]** Growth and Safety allocations | Does Safety push vol below 5%? Does Growth approach the vol ceiling? |
| Frontier coverage gaps — return levels with no solution | **[results]** interpolate between curated strategies | "At X% target return, method has no nearby solution" |

### 1b. Navigability

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Can user request intermediate solutions between anchors? | **[response]** + **[issues]** | "178 other portfolios" vs "ask again" vs "write code" |
| Are per-scenario results independently explorable? | **[results]** per-scenario curated strategies | Curated per scenario, or base-case only? |
| How many tool calls / lines of code to go from solve to curated insight? | **[issues]** workflow log | 0 code + N tool calls vs M lines of custom code vs pure reasoning |

### 1c. Scenario-Specific (when applicable)

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Solutions per scenario | **[results]** per-scenario counts | Consistent coverage across scenarios? |
| Do curated strategies actually differ across scenarios? | **[curated]** cross-scenario comparison | Growth in rate cuts vs recession — different assets? Or same portfolio relabeled? |
| Robustness metric quality | **[results]** robust options analysis | Actionable (frequency-weighted) vs trivial (28/30 "robust")? |
| Scenario-specific opportunities identified | **[results]** scenario-specific options | Which assets only appear under specific conditions? |

---

## 2. Tradeoff Assessment

*How well does each method quantify what you give up to get more of what you want?*

### 2a. Quantification

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Marginal rates stated? (cost per unit of improvement) | **[response]** tradeoff text | "Each point of return costs 0.83 points of vol" vs qualitative only |
| Source of tradeoff numbers | **[response]** + **[results]** | Computed from N-point Pareto surface vs gap between hand-picked portfolios |
| Knee points / diminishing returns identified? | **[response]** or **[results]** marginal analysis | "Beyond 15% return, each additional point costs 3x more vol" |
| Multi-objective tradeoffs (not just pairwise)? | **[response]** | "Gaining return costs vol AND sacrifices yield" — 3-way stated? |

### 2b. Structural Insights

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Non-obvious findings surfaced? | **[response]** | e.g., "income and stability go together" (counterintuitive), "balanced collapses to safety in recession" |
| Asset role analysis (why specific holdings matter) | **[response]** | "HYG appears everywhere because it uniquely combines moderate return with high yield" |
| Cross-scenario shifts explained? | **[response]** | "Growth rotates from equities (rate cuts) to gold (recession) to commodities (inflation)" |
| Correlation / dependency structure reported? | **[response]** or **[results]** | r=0.94 between return and vol — computed or asserted? |

### 2c. Data Grounding *(absorbs "stray assumptions" pitfall — interpretation side)*

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Domain assertions backed by input data? | **[response]** vs **[assignment]** source data | "This sector typically returns Y" — traceable to scores or invented? |
| Qualitative claims without quantitative backing? | **[response]** + **[results]** | "Commodity supercycle continues" (editorial) vs "r=0.94" (computed) |
| Missing data flagged or silently filled? | **[response]** + **[issues]** | "No correlation data available" (honest) vs assumed diversification benefit (invented) |

### 2d. Dominated Solutions

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Any curated solution dominated by another method's? | **[curated]** cross-method comparison | Same role, strictly worse on all objectives = dominated |
| Would user know their solution is dominated? | **[response]** | Does the method acknowledge uncertainty or claim optimality? |

---

## 3. Respecting Constraints

*Does the method guarantee feasibility? Where does it cut corners or ride boundaries?*

### 3a. Guarantee Mechanism

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| How are constraints enforced? | **[issues]** + method architecture | Solver structure vs repair operator vs manual arithmetic |
| Is the guarantee structural or best-effort? | **[issues]** | "Impossible by construction" vs "code-quality dependent" vs "arithmetic dependent" |
| Violations found in output? | **[results]** verify all curated solutions | Check every curated solution against every constraint |

### 3b. Boundary Behavior

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Constraint headroom on binding constraints | **[curated]** vol values vs 20% ceiling | 0.02% headroom (precise) vs 3% headroom (over-conservative) |
| Cardinality range actually used | **[curated]** holding counts | 4–12 (full range) vs always 12 (repair artifact) vs always 4–7 (manual conservatism) |
| Constraint artifacts? | **[results]** + **[issues]** | Over-diversification from repair? Near-ceiling riding from manual? Dominated options at minimum allocation? |

### 3c. Data Provenance *(absorbs "stray assumptions" pitfall — input side)*

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Are all scores traceable to input data? | **[results]** scores vs **[assignment]** source data | Loaded from file vs entered via tool vs "estimated" in reasoning |
| Did the method fabricate or default any values? | **[results]** + **[response]** | Silently assumed capability/score vs flagged as unknown |
| Score entry mechanism prevents fabrication? | Architecture | Explicit score matrix (tool) vs code-loaded (file) vs mental recall (LLM) |

### 3d. Scaling Judgment

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Would this method's constraint handling survive 100 options, 10 constraints? | **[issues]** + architecture | Structural solvers scale. Manual arithmetic does not. |
| Would adding a new constraint require code changes? | **[issues]** | Config change vs rewrite repair operator vs re-reason from scratch |

---

## 4. User Workflow (from Issues Logs)

*What friction did the agent/user encounter?*

| Check | Evidence | What to compare |
|-------|----------|-----------------|
| Setup effort (code written, tool calls, reasoning time) | **[issues]** | 0 lines + 11 calls vs 362 lines vs 0 lines + 5min reasoning |
| Payload / token limit issues | **[issues]** | Results too large for inline return? |
| Skill/guidance received | **[issues]** | Auto-injected at phase transitions vs none |
| Dead ends encountered | **[issues]** | Features that produced data the user couldn't access |
| Self-assessment accuracy | **[response]** limitations sections | Did the method correctly identify its own weaknesses? |

---

## 5. Cross-Method Comparison Table Template

Fill one per run. Quote actual numbers from **[results]** and **[curated]**.

| Dimension | Frontier | Solver | LLM |
|-----------|----------|--------|-----|
| **Pareto solutions** | | | |
| **Return range** | | | |
| **Vol range** | | | |
| **Yield range** | | | |
| **Growth return / vol** | | | |
| **Safety return / vol** | | | |
| **Balanced return / vol / yield** | | | |
| **Income return / vol / yield** | | | |
| **Dominated curated solutions?** | | | |
| **Marginal rates computed?** | | | |
| **Constraint violations** | | | |
| **Code written** | | | |
| **Issues count** | | | |

---

## 6. Scenario Comparison Table Template (when applicable)

| Dimension | Frontier | Solver | LLM |
|-----------|----------|--------|-----|
| **Solutions per scenario** | | | |
| **Per-scenario curated strategies available?** | | | |
| **Growth shifts across scenarios?** | | | |
| **Safety stable across scenarios?** | | | |
| **Robustness metric (type + top 3)** | | | |
| **Scenario-specific assets identified?** | | | |
| **Structural scenario finding** | | | |
| **Constraint violations per scenario** | | | |
| **Additional effort for scenarios** | | | |

---

## 7. Pitfall Summary

*Maps the four LLM decision-making pitfalls to where they're assessed in the lenses above. Use this table to frame findings for article narrative.*

| Pitfall | Covered by | Key checks |
|---------|-----------|------------|
| **Infeasible plans** | **3. Constraints** (3a, 3b, 3d) | Guarantee mechanism, violations found, boundary headroom, scaling |
| **Stray assumptions** | **2. Tradeoffs** (2c) + **3. Constraints** (3c) | Data grounding in interpretation (2c), score provenance and fabrication (3c) |
| **Incomplete exploration** | **1. Exploration** (1a, 1b, 1c) | Coverage, corner solutions, frontier gaps, navigability, per-scenario coverage |
| **Opaque reasoning** | **2. Tradeoffs** (2a, 2d) | Marginal rates computed vs narrated, dominated solutions user can't detect |

### Pitfall Rating Table Template

| Pitfall | Frontier | Solver | LLM |
|---------|----------|--------|-----|
| **Infeasible plans** | | | |
| **Stray assumptions** | | | |
| **Incomplete exploration** | | | |
| **Opaque reasoning** | | | |

For each cell: **Prevented** (structurally impossible), **Mitigated** (reduced by tooling but not eliminated), or **Present** (fully exposed). Cite the lens check that provides the evidence.

---

## How to Use

1. **Before each run:** Confirm identical **[assignment]** across all methods.
2. **During each run:** Collect **[results]**, **[curated]**, **[response]**, **[issues]** per method.
3. **After each run:** Walk sections 1–4, filling evidence from artifacts. Fill comparison tables (5–6).
4. **Cross-run comparison:** Compare tables across runs (e.g., pre-fix vs post-fix Frontier, single-problem vs scenarios, different problem formulations).
5. **For the article:** Pull the most telling data points and response excerpts from each section. The "single number" format works well — e.g., "at 6% return: Frontier 7.2% vol, pymoo 13.2%, LLM no solution."

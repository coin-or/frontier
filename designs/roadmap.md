# Frontier Roadmap: Literature-Validated Feature Directions

> Extracted from Lessons 1-6, cross-referenced against the Frontier codebase, and merged with v1_features.md open items. Organized by timeline with stack rank informed by the Frontier vision: improve the core loop first, reduce data collection friction, deepen analysis, then expand algorithms.

---

## Table-Stakes Gaps (from validation plan cross-reference)

These are capabilities the lesson plans document as "existing" but the codebase audit reveals as missing or partial. Fix these before pursuing new features.

### Gap 1: Scale Mismatch Detection
**Lesson**: L3 (data_collection skill references "scale mismatch detection")
**Current state**: `metrics.py` reports variance by objective but doesn't flag when objectives are on different scales (e.g., ROI on 1-100, Risk on 1-5).
**Fix**: Add a check in `_compute_data_metrics()` that compares score ranges across objectives. Flag when max range / min range > 3x. ~20 lines.

### Gap 2: Frontier Shape Classification
**Lesson**: L1 ("frontier shape tells a story — convex = smooth, concave = diminishing returns, discontinuous = different strategies")
**Current state**: Scatter plot visualizes the shape, marginal_analysis detects knee points. But no automatic classification or narrative description.
**Fix**: Extend `_analyze_tradeoffs()` in explorer.py — for each objective pair, check convexity via second derivative of sorted frontier points. Report "smooth tradeoffs" vs "diminishing returns" vs "distinct strategy clusters." ~80 lines.

### Gap 3: Binding Constraint Detection (Full)
**Lesson**: L2, L4 ("binding constraint detection" as existing diagnostic)
**Current state**: `metrics.py:319-355` only checks objective bounds at 95% saturation. Cardinality, group limits, and other constraint types aren't checked for binding.
**Fix (two parts)**:
1. **Metrics extension** (~60 lines): Extend binding detection in metrics.py to check if cardinality constraints are at max (all solutions hit the cap), group limits are saturated, etc.
2. **Tradeoffs augmentation** (~80 lines, from v1_features binding constraint analysis design): Augment `explore tradeoffs` response with `binding_analysis` array. For each `objective_bound` and `cardinality` constraint, compute: `binding_pct` (% of Pareto solutions within 5% of bound), `tightest_solution_id`, `slack_range` [min, max], and a qualitative suggestion ("85% of solutions are near the effort cap. Relaxing from 30 to 35 could open new tradeoff space."). Pure analysis of existing frontier — no re-runs. Skill update: `optimization_strategy` Binding Constraint Detection section references `binding_analysis` in tradeoffs response.

### Gap 4: Run-to-Run Variance (Fixed Seed)
**Lesson**: L6 (bias-variance-compute triangle implies different runs produce different results)
**Current state**: Seed is fixed at 42 in optimizer.py. Every run with same inputs produces identical results.
**Decision needed**: This is a design choice (reproducibility vs diversity). Options: (a) keep fixed seed as default, add optional `seed` parameter; (b) randomize by default, add `deterministic=true` option. Recommend (a) — reproducibility is more valuable for MCP tool use.

---

## Near-Term Features (incremental, builds on existing)

### 1. Question Anchor in Problem Framing ★
**Source**: v1_features [next-2] scoped design
**Problem**: The agent jumps straight to objectives without capturing the user's "How should we...?" question. The `model` tool stores `domain` and `context` but doesn't distinguish the driving question.
**Design scope**:
- **Skill-only change** — no model or tool changes needed.
- Add "Question First" section to `problem_framing` skill: capture the user's question, reflect it back, store in `context` field, use it to select approach (binary vs proportional vs "maybe you don't need optimization").
- Update `solution_interpreter` skill: connect results back to original question when presenting.
- ~0 engine lines. Skill text edits only.
**Dependencies**: None.
**Why first**: Improves every session from the opening turn. Highest leverage per effort — pure skill change, zero risk.

### 2. Warm-Starting from Previous Runs
**Source**: L2 (future directions item 4)
**Problem**: After small changes (`results_stale = true`), optimizer restarts from random initialization. Wastes compute for incremental edits.
**Design scope**:
- `optimizer.py`: Extract decision variables from archived `runs[]`, use as 70% of initial population. Pad 30% random for diversity. pymoo supports initial population via `pop` parameter.
- `models.py`: Add `warm_start: bool = True` to run parameters.
- ~50 lines. No new dependencies.
**Dependencies**: Archived run must exist.
**Success metric**: Fewer generations to reach equivalent hypervolume on re-runs.

### 3. Frontier Pruning / Max Solutions
**Source**: v1_features "What to Watch" item 1, L2 §2.3 (combinatorial vs continuous MOO)
**Problem**: Proportional mode produces 100+ Pareto solutions for small problems. The continuous search space is richer than binary — this is fundamental, not a bug. L2 §2.3 explains why: binary mode searches a discrete 2^n landscape where the Pareto set is naturally small (often dozens), while proportional mode explores a continuous simplex where the Pareto set is theoretically infinite and the evolutionary algorithm samples densely from it. Conversely, binary mode with 40+ options may produce noisy or incomplete frontiers because combinatorial landscapes are rugged — expect and communicate this asymmetry.
**Design scope**:
- `optimizer.py` or `explorer.py`: Post-solve pruning to retain a representative subset. Strategy: keep extreme points + knee points + evenly-spaced samples via crowding distance. Default max ~30; parameterizable.
- `models.py`: Optional `max_solutions: int` on solve parameters.
- `optimization_strategy` skill: Add guidance on expected frontier size by mode — proportional frontiers are naturally large (pruning is curation, not failure), binary frontiers with many options may be incomplete (more generations or population may help).
- ~60 lines. No new dependencies.
**Dependencies**: None.
**Success metric**: Proportional frontiers consistently under 30 solutions without losing strategy diversity.

### 4. CVaR and Risk Measure Options
**Source**: L4 (4.1), L1 (1.6)
**Problem**: Scenario aggregation is expected-value only. Risk-sensitive users need tail-risk measures.
**Design scope**:
- `models.py`: Add `risk_measure: Literal["expected", "cvar_20", "cvar_10", "minimax"] = "expected"` to scenario config.
- `explorer.py`: In scenario_results, add CVaR (average of worst N% scenarios) and minimax (worst scenario per option) alongside expected values.
- `solution_interpreter` skill: Guidance for explaining risk measures.
- ~30 lines core logic. No new dependencies.
**Dependencies**: Scenarios with probabilities assigned. 3+ scenarios for CVaR to be meaningful.
**Success metric**: Users in risk-sensitive domains engage more with scenario analysis.

### 5. VoI-Driven Score Collection Priority
**Source**: L1 (1.5), L3 (3.3, 3.5)
**Problem**: Users fill the score matrix arbitrarily. Some missing scores would change the frontier dramatically; others wouldn't.
**Design scope**:
- `metrics.py`: For each missing score, sample from column distribution (mean +/- 1 SD), run fast dominance check, measure hypervolume delta. Return `score_priorities: list[{option, objective, estimated_impact}]` sorted by impact.
- `server.py`: Include `score_priorities` in `model/update` and `solve/validate` responses alongside existing `missing_scores`.
- `data_collection` skill: Add guidance to request highest-VoI scores first.
- No new dependencies. ~100 lines core logic.
**Dependencies**: None.
**Success metric**: Fewer scores collected before frontier stabilizes (hypervolume change per additional score < 1%).

### 6. Score Sensitivity Report
**Source**: L4 (4.3), v1_features [next-2] scoped design
**Problem**: Users don't know which scores are load-bearing. They discover this only by manually editing and re-running.
**Design scope**:
- `explorer.py`: New `explore sensitivity` action. For each score, perturb ±10%, re-evaluate all current Pareto solutions, check which gain/lose Pareto membership. No full re-optimization — just re-evaluation.
- Report: `most_sensitive_scores` (option × objective pairs ranked by frontier_impact), `most_sensitive_options`, `most_sensitive_objectives`, `robust_solutions` (survive all perturbations), `fragile_solutions` (eliminated by any single perturbation).
- Top-N reporting (default 10) to avoid overwhelming output. Works for both binary and proportional.
- `data_collection` skill: "High-sensitivity scores deserve careful elicitation."
- ~100 lines. No new dependencies.
**Dependencies**: Requires solved frontier.
**Success metric**: Fewer re-runs due to small score corrections.
**Note**: v1_features and roadmap both scoped this independently — designs are aligned. Combined here.

### 7. Preference Cycle Detection
**Source**: L1 (1.4 — transitivity axiom)
**Problem**: Intransitive preferences (A > B > C > A) produce unstable optimization. Currently undetected.
**Design scope**:
- `explorer.py`: Track pairwise preference graph from curate/uncurate/feedback. After each action, run cycle detection (topological sort).
- `models.py`: Add `preference_graph: list[tuple[str, str]]` built incrementally.
- `solution_interpreter` skill: Surface detected cycles.
- ~40 lines. No new dependencies.
**Dependencies**: Content signature system (exists). 3+ curated solutions for cycles to be possible.
**Success metric**: Cycles surfaced before they cause re-optimization confusion.

### 8. Curated Solution Export
**Source**: v1_features Open Question 3
**Problem**: The curated set is the natural unit of output/sharing, but `explore curated` only returns JSON. Users presenting to stakeholders need a structured summary.
**Design scope**:
- `explorer.py`: New `explore export_curated` action (or option on `curated`). Returns a formatted summary: table of curated solutions with key objectives, notes, survival status, and comparison to reference points.
- Consider markdown output for easy pasting into docs/slides.
- ~50 lines.
**Dependencies**: Curated solutions exist.
**Success metric**: Users share curated summaries directly without manual reformatting.

### 9. Non-Linear Objective Redundancy (Mutual Information)
**Source**: L4 (4.4), L6 (6.4)
**Problem**: Pearson correlations miss non-linear relationships between objectives. Users over-specify with redundant objectives.
**Design scope**:
- `explorer.py`: Supplement Pearson with MI estimation (scikit-learn `mutual_info_regression` or binned estimator).
- Tradeoffs response: Add `redundancy_flags` for pairs with MI > threshold.
- `problem_framing` skill: Guidance to suggest consolidating flagged objectives.
- ~30 lines. Possible scikit-learn dependency.
**Dependencies**: Complete (or mostly complete) score matrix.
**Success metric**: Problems with flagged redundancies get consolidated (tracked via objective count decrease after tradeoffs).

### 10. Frontier Shape Analysis
**Source**: L1 (1.1, 1.7), L4 (4.6)
**Problem**: Users see the frontier but don't understand its structure. "Are my tradeoffs smooth or regime-based?"
**Design scope**:
- `explorer.py`: For each objective pair, classify convexity (second derivative). Detect regime boundaries (marginal rate changes > 2x). For 4+ objectives, PCA on frontier with labeled principal tradeoff axes.
- Tradeoffs response: Add `frontier_shape: {type, knees, regimes, principal_tradeoffs}`.
- `solution_interpreter` skill: Narration guidance for shape.
- ~150 lines. numpy/scipy only.
**Dependencies**: Solved frontier. PCA useful for 4+ objectives.
**Success metric**: Knee-point solutions curated at disproportionally high rates.
**Note**: Subsumes Gap 2 (Frontier Shape Classification). Gap 2 is the minimal version; this is the full feature.

---

## Medium-Term Features (new capability, moderate scope)

### 11. Preference-Biased Re-Optimization
**Source**: L2 (2.3 — R-NSGA-II), L1 (1.0, 1.3), L6 (TAM Stage 2)
**Problem**: Curation and feedback data don't influence the optimizer. The feedback loop doesn't close.
**Design scope**:
- `optimizer.py`: R-NSGA-II variant — modify crowding distance to favor solutions near curated centroid. pymoo supports custom survival operators.
- `models.py`: `preference_mode: Literal["explore", "focus"] = "explore"`.
- `server.py`: In `focus` mode, auto-extract preference point from curated solutions.
- `optimization_strategy` skill: Suggest focus mode after curation.
- ~200 lines custom survival operator.
**Preference articulation**: L1 §1.3 (NIMBUS classification-based methods) establishes that ordinal preference articulation ("improve this / sacrifice that") is cognitively lighter than cardinal (weights, utility functions). Frontier's existing curation + objective ranking elicitation already follows this pattern. Focus mode should accept ordinal input (ranked objectives, improve/acceptable/sacrifice categories) not just a cardinal preference point — convert ordinal signals to a reference direction internally.
**Dependencies**: Feature 2 (warm-starting) pairs well. 2+ curated solutions for meaningful preference point.
**Success metric**: In focus mode, frontier density near curated region increases > 30%.

### 12. Automatic Solution Clustering (Strategy Archetypes)
**Source**: L4 (4.5)
**Problem**: 15-30 solution frontiers overwhelm users. People think in strategies, not individual configurations.
**Design scope**:
- `explorer.py`: K-means or GMM on normalized objective space. Auto-select K via silhouette score. Label clusters by dominant characteristic.
- Tradeoffs response: `strategy_clusters: list[{name, solutions, centroid, description}]`.
- `solution_interpreter` skill: "Your frontier has N distinct strategy types..."
- Visualization: Group solutions by cluster in scatter plot.
- ~150 lines. scikit-learn dependency.
**Dependencies**: 8+ solutions for meaningful clustering.
**Success metric**: Users curate from different clusters (not just adjacent solutions).

### 13. GP Surrogate for Partial-Data Optimization
**Source**: L3 (3.2, 3.5)
**Problem**: Frontier blocks solving until 100% score matrix completion. Large problems (20 options x 8 objectives = 160 scores) have a high barrier to first results.
**Design scope**:
- New `surrogate.py`: GP per objective (scikit-learn `GaussianProcessRegressor`). Predict missing cells with posterior mean + variance.
- `models.py`: `ScoreEstimate` model with `value`, `confidence`, `source: observed|predicted`.
- `optimizer.py`: Accept predicted scores. Tag solutions depending on predictions with confidence field.
- `explorer.py`: Annotate low-confidence solutions. "Dominates with ~X% confidence."
- `server.py`: New solve mode `"preliminary"` (allows predicted scores) vs `"final"` (current behavior).
- ~300 lines. New dependency: scikit-learn GP.
**Dependencies**: Feature 5 (VoI) should ship first — validates the UX pattern.
**Success metric**: Meaningful preliminary frontier at 60% data completion (rank correlation with final > 0.7).

### 14. Pairwise Preference Learning from Exploration
**Source**: L1 (1.3), L6 (6.7)
**Problem**: Users reveal preferences implicitly through exploration behavior (drill-in, compare, curate) but this signal is discarded.
**Design scope**:
- `server.py` / `explorer.py`: Log exploration actions as implicit preference signals.
- New utility: Fit linear utility model from interaction log (logistic regression on solution features vs engagement).
- Feed inferred preference direction to Feature 11 (focus mode) automatically.
- `solution_interpreter` skill: Confirm inferred preferences before using.
- Prefer ordinal inference (rank objectives, classify as improve/acceptable/sacrifice per L1 §1.3) over cardinal weight estimation — cognitively lighter to confirm and correct.
- ~200 lines. Moderate complexity.
**Dependencies**: Feature 11 (preference-biased optimization) as consumer.
**Success metric**: Inferred top-3 matches actually curated solutions > 70%.

### 15. Algorithm Routing (Auto-Selection)
**Source**: L2 (2.3 — three EMOA paradigms), v1_features [later+]
**Problem**: NSGA-II handles 2-3 objectives, NSGA-III for 4+. MOEA/D produces better-spread frontiers for smooth proportional problems. Currently no auto-routing. L2 §2.3 now frames MOEA/D as a co-equal paradigm alongside dominance-based (NSGA) and indicator-based (SMS-EMOA), not a niche alternative — decomposition is the fastest-growing direction in the literature (Ehrgott).
**Design scope**:
- `optimizer.py`: Add MOEA/D (pymoo `MOEAD`, TCH or PBI variant). Auto-selection logic: NSGA-II for binary/2-3 objectives, NSGA-III for 4+ objectives, MOEA/D for proportional mode with 3-6 objectives. Consider indicator-based (SMS-EMOA/HypE) as a future third option for problems where spread matters most.
- `models.py`: `algorithm: Literal["auto", "nsga2", "nsga3", "moead"] = "auto"` for expert users.
- `optimization_strategy` skill: When to suggest overriding auto-selection.
- Quality comparison across algorithms: use IGD (convergence + spread) and spacing CV, not just hypervolume — per L1 §1.7, hypervolume alone can mask poor spread. IGD and epsilon-indicator give complementary views.
- ~150 lines integration + parameter tuning.
**Dependencies**: None beyond pymoo (existing).
**Success metric**: Better IGD and spacing CV on proportional problems vs NSGA-III alone.
**Note**: Merges v1_features "Algorithm Routing" [later+] with roadmap Feature 13 (MOEA/D). Elevated priority given L2 §2.3 positioning of decomposition as a major paradigm.

### 16. Feedback-Driven Skill Improvement (DAgger-Like)
**Source**: L6 (6.9), L5 (5.5)
**Problem**: Skill files are static. No systematic way to identify failure modes and update them.
**Design scope**:
- `metrics.py` extension: Aggregate feedback by `stage`. Surface lowest-rated interactions.
- Skill versioning via git tags or internal version field.
- Manual review pipeline: surface failures, write patches, A/B test.
- Primarily operational/process, with analytics code ~100 lines.
**Dependencies**: Sufficient feedback volume across problems.
**Success metric**: Average feedback rating increases across skill versions.

---

## Longer-Term Features (significant new subsystem)

### 17. Guided Data Collection (Full UX)
**Source**: L3, v1_features [later]
**Problem**: The `data_collection` skill is instruction-only. Feature 5 (VoI) provides priority logic and Feature 6 (Sensitivity) identifies load-bearing scores, but the tool doesn't actively assist with collection itself.
**Design scope**:
- Auto-research researchable scores (pricing, benchmarks) via web search or structured data sources
- Track confidence per score (metadata, not used by optimizer)
- Integrate VoI priority + sensitivity results into a "next best score to collect" recommendation
- Agent-assisted elicitation workflows (e.g., pairwise comparisons to triangulate missing scores)
- Moderate complexity. Depends on external data access patterns.
**Dependencies**: Features 5 (VoI) and 6 (Sensitivity) as foundations.
**Success metric**: Time from problem creation to first meaningful frontier cut by 50%.

### 18. Cross-Problem Transfer Learning
**Source**: L3 (future directions), L6 (6.7)
**Problem**: Every new problem starts cold. Domain patterns (e.g., "cost-efficient options trade off against flexibility") could reduce score collection burden.
**Design scope**:
- New `transfer.py`: Aggregate anonymized score matrices across problems by domain. Learn GP priors over (option_type, objective_type) -> score distribution.
- `surrogate.py` (Feature 13): Accept external priors for cold-start prediction.
- Privacy/consent framework for data sharing.
- High complexity. Requires 20+ problems per domain.
**Dependencies**: Feature 13 (GP surrogate).
**Success metric**: 30% fewer manually-provided scores for new problems in known domains.

### 19. Epsilon-Constraint for Provable Optimality
**Source**: L1 (1.2), L6 (TAM Stage 3)
**Problem**: No optimality guarantee. Regulated industries need "proof no better solution exists."
**Design scope**:
- `optimizer.py`: Epsilon-constraint method. Binary: 0-1 integer program (PuLP/OR-Tools). Proportional: LP/QP (scipy/cvxpy).
- `models.py`: `method: Literal["evolutionary", "exact"] = "evolutionary"`.
- Hybrid workflow: evolutionary for exploration, exact for certification of curated solutions.
- New dependency: exact solver.
- High complexity, especially for binary mode.
**Dependencies**: Feature 11 (preference bias) narrows the search region, making exact methods tractable.
**Success metric**: For tractable problems, report gap between evolutionary and exact frontier hypervolume.

---

## Curation Refinements (minor, do opportunistically)

These are open questions from v1_features that don't warrant full feature slots but should be addressed when touching nearby code.

- **Stale curation values on score changes**: When scores change (not structure), curated solutions' objective values are stale but composition is valid. Consider recomputing from current scores on `explore curated` access.
- **Max curated set size**: No hard limit currently. Add soft warning at 10-15 if dogfooding reveals bloat.
- **Scenario run archival**: `scenario_run` stores latest per-scenario results only. No history. Not urgent — scenario iteration is less common than constraint iteration.

---

## Recommended Sequencing

Stack-ranked by vision alignment: core loop quality > data collection friction > analysis depth > new algorithms.

```
Quarter 1 — Core loop & quick wins:
  ├── Gap fixes (1, 3, 4): scale mismatch, binding constraints (full), fixed seed
  ├── Feature 1: Question Anchor (skill-only, zero risk, improves every session)
  ├── Feature 2: Warm-starting (reduce iteration cost)
  ├── Feature 3: Frontier pruning (proportional mode UX fix)
  └── Feature 7: Preference cycle detection

Quarter 2 — Data quality & analysis depth:
  ├── Features 5 + 6: VoI priority + Score sensitivity (same principle, paired)
  ├── Features 9 + 10: MI redundancy + Frontier shape (both enhance tradeoffs)
  │   └── Gap 2 subsumed by Feature 10
  ├── Feature 4: CVaR risk measures
  └── Feature 8: Curated solution export

Quarter 3 — Preference feedback loop (TAM Stage 2):
  ├── Feature 11: Preference-biased re-optimization (closes the loop)
  ├── Feature 12: Solution clustering (strategy archetypes)
  ├── Feature 14: Implicit preference learning
  └── Feature 15: Algorithm routing (MOEA/D + auto-selection)

Quarter 4+ — Expand capabilities (TAM Stage 3):
  ├── Feature 13: GP surrogate (partial data)
  ├── Feature 16: Feedback-driven skill improvement
  ├── Feature 17: Guided data collection (full UX)
  ├── Feature 18: Cross-problem transfer
  └── Feature 19: Epsilon-constraint
```

This sequence follows the strategic logic from L6 and the Frontier vision: first make the existing core loop excellent (Q1 — framing, iteration speed, UX fixes), then deepen the analysis available within that loop (Q2 — data quality, tradeoff understanding), then close the preference feedback loop (Q3 — TAM Stage 2), then expand to new capabilities and formal methods (Q4+ — toward TAM Stage 3).

---

*Last updated: April 2026. Living document — update as decisions are made and dogfooding reveals friction.*

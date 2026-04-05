# Frontier Table-Stakes Validation Plan

> Capabilities that Frontier SHOULD already support based on the multi-objective optimization theory it claims to implement. Each capability includes a concrete test/validation plan with example workflows.

---

## Test Problem: "Project Portfolio Selection"

All test plans below use a shared example problem unless otherwise noted.

**Setup:**
- **Approach**: binary (select/deselect)
- **Options** (8): Alpha, Bravo, Charlie, Delta, Echo, Foxtrot, Golf, Hotel
- **Objectives** (3): Maximize ROI, Maximize Strategic Alignment, Minimize Risk
- **Score matrix** (all 8x3 cells filled, 1-10 scale):

| Option   | ROI | Strategic Alignment | Risk (lower=better) |
|----------|-----|---------------------|---------------------|
| Alpha    | 9   | 4                   | 8                   |
| Bravo    | 7   | 7                   | 5                   |
| Charlie  | 3   | 9                   | 2                   |
| Delta    | 8   | 3                   | 7                   |
| Echo     | 5   | 8                   | 4                   |
| Foxtrot  | 6   | 6                   | 6                   |
| Golf     | 4   | 5                   | 3                   |
| Hotel    | 2   | 2                   | 9                   |

**Constraints:**
- Cardinality: min 2, max 4
- Force include: none
- Force exclude: none

**Why this problem**: 8 options with 3 objectives is small enough to reason about manually, large enough to produce a meaningful frontier. Hotel is intentionally dominated (worst on 2 of 3 objectives). Binary mode exercises the NP-hard path. 3 objectives keeps us in NSGA-II territory.

---

## Capability 1: Interactive Preference Timing (Solve-Explore-Refine-Re-solve Loop)

**Lessons**: 1 (Section 1.0 - Three Timings of Preference)
**Why table-stakes**: Lesson 1 explicitly states this is "Frontier's primary mode." The interactive/progressive timing is the core UX claim -- that users can discover preferences through exploration rather than specifying them upfront. If this loop doesn't work fluidly, the entire product thesis fails.

### Test Plan

**Step 1 -- Initial solve (no preferences articulated)**
```
model/update: load the test problem (all options, objectives, scores, constraints)
solve/run: mode=fast
```
- Expected: Returns a set of non-dominated solutions (portfolios of 2-4 projects)
- Check: Multiple distinct solutions returned, not a single "best"

**Step 2 -- Explore the frontier**
```
explore/solutions: view full solution set
explore/compare: pick 2 solutions that differ meaningfully
explore/tradeoffs: see objective correlations and tradeoff scatter
```
- Expected: Solutions are comparable side-by-side. Tradeoff visualization shows the frontier shape. Correlations between objectives are reported.

**Step 3 -- Refine based on exploration**
Based on what the user sees, they decide "I care more about low Risk than high ROI." They add:
```
model/update: add constraint objective_bound on Risk <= 5 (sum or average)
```

**Step 4 -- Re-solve with refined preferences**
```
solve/run: mode=fast
```
- Expected: New frontier is a subset of objective space. High-risk options (Alpha, Delta, Hotel) should appear less frequently. Solutions should cluster around low-risk portfolios.

**Step 5 -- Compare runs**
```
explore/compare_runs: compare run 1 vs run 2
```
- Expected: Shows which options gained/lost frontier presence. Shows how the frontier shifted in objective space.

### Pass Criteria
- Each step produces meaningful output without errors
- Run 2 frontier is demonstrably different from Run 1 (tighter on Risk)
- compare_runs clearly shows the impact of the preference refinement
- The loop can be repeated (add another refinement, re-solve, compare again)

---

## Capability 2: A Posteriori Mode (Generate Full Frontier, Compare, Curate)

**Lessons**: 1 (Section 1.0 - "solutions + compare + curate workflow is classic a posteriori")
**Why table-stakes**: Lesson 1 explicitly names this as a supported mode. Users who want to see everything before deciding need the full generate-then-choose workflow.

### Test Plan

**Step 1 -- Generate full frontier**
```
solve/run: mode=thorough
```
- Expected: Larger/more diverse solution set than fast mode

**Step 2 -- Browse and compare**
```
explore/solutions: view all solutions
explore/compare: compare the "balanced" solution vs an extreme (highest ROI portfolio)
explore/marginal_analysis: see cost-per-unit tradeoffs between adjacent solutions
```

**Step 3 -- Curate shortlist**
```
explore/curate: mark 2-3 solutions as "shortlisted"
```
- Expected: Curated solutions are tracked. content_signature identifies them stably.

**Step 4 -- Provide feedback**
```
explore/feedback: rate a curated solution, provide stage-tagged feedback
```
- Expected: Feedback is recorded against the content_signature

**Step 5 -- Re-solve and check curation survival**
```
solve/run: mode=thorough (no changes to problem)
explore/solutions: check in_current_frontier flag for previously curated solutions
```
- Expected: Previously curated solutions should show whether they survived the new run via content_signature matching

### Pass Criteria
- Full frontier is generated with multiple diverse solutions
- Compare shows meaningful tradeoff information between any two solutions
- Curate successfully marks solutions
- Feedback is recorded
- content_signature enables cross-run tracking of curated solutions

---

## Capability 3: Scenario Analysis for Robustness

**Lessons**: 1 (Section 1.6), 2 (Section 2.4 - constraint_overrides), 4 (Section 4.1 - two paradigms)
**Why table-stakes**: Lessons 1 and 4 both describe scenario analysis as an existing Frontier implementation. Score overrides, score adjustments (multiply/add), and constraint overrides are listed as current features. Robust options and expected values are documented as product outputs.

### Test Plan

**Scenario setup**: Three scenarios with probabilities:

**Scenario A: "Base Case"** (p=0.5)
- No overrides (use original scores)

**Scenario B: "Economic Downturn"** (p=0.3)
- score_adjustments: ROI multiply by 0.7 (all options lose 30% ROI)
- score_adjustments: Risk add +2 (all options get riskier)
- constraint_overrides: cardinality max reduced to 3 (tighter budget)

**Scenario C: "Strategic Pivot"** (p=0.2)
- score_overrides: Charlie Strategic Alignment = 5 (was 9, strategy changed)
- score_overrides: Alpha Strategic Alignment = 8 (was 4, now aligned)
- No constraint changes

```
solve/run_scenarios: define the 3 scenarios above
```

### Expected Outputs
1. **Per-scenario frontiers**: Each scenario produces its own Pareto set
2. **Robust options**: Options appearing in ALL scenario frontiers (likely Bravo, Echo -- good across all conditions)
3. **Expected values**: Probability-weighted objective values across scenarios
4. **Scenario-specific options**: Options that only appear in certain scenarios (Alpha probably only in Scenario C)

### Validation Checks
- Scenario B frontier should have lower ROI solutions and smaller portfolios (max 3)
- Scenario C frontier should include Alpha more and Charlie less than Base Case
- Robust options should be genuinely good across all scenarios (verify manually)
- Expected values should be weighted: 0.5*Base + 0.3*Downturn + 0.2*Pivot

### Pass Criteria
- All three scenario types work: no overrides, score_adjustments (multiply + add), score_overrides, constraint_overrides
- Robust options are correctly identified (appear in all scenario frontiers)
- Expected values are mathematically correct (probability-weighted)
- Visualization (`_render_scenario_viz`) shows robust vs scenario-specific options

---

## Capability 4: All 7 Constraint Types Working Correctly

**Lessons**: 2 (Section 2.4 - full table of 7 constraint types)
**Why table-stakes**: Lesson 2 documents all 7 as existing implementations with specific handling strategies (repair vs constraint domination). If any constraint type silently fails or is ignored, the optimizer produces invalid solutions.

### Test Plan

Run 7 separate tests, each exercising one constraint type on the test problem. Verify solutions respect the constraint.

**Test 4a: Cardinality**
- Constraint: min=3, max=3 (exactly 3 options)
- Verify: Every solution has exactly 3 options selected

**Test 4b: Force Include**
- Constraint: force_include = [Charlie]
- Verify: Every solution includes Charlie

**Test 4c: Force Exclude**
- Constraint: force_exclude = [Hotel]
- Verify: No solution includes Hotel

**Test 4d: Objective Bounds**
- Constraint: objective_bound on Risk <= 4 (average per selected option)
- Verify: Every solution's average Risk score is <= 4. Only low-risk options (Charlie=2, Golf=3, Echo=4) should dominate selections.

**Test 4e: Exclusion Pairs**
- Constraint: exclusion_pair = [Alpha, Delta] (can't have both)
- Verify: No solution contains both Alpha AND Delta

**Test 4f: Dependencies**
- Constraint: dependency = Echo requires Bravo (if Echo selected, Bravo must be too)
- Verify: Every solution containing Echo also contains Bravo. Solutions with Bravo but not Echo are allowed.

**Test 4g: Group Limits**
- Define groups: "High ROI" = [Alpha, Bravo, Delta], "Low Risk" = [Charlie, Golf, Echo]
- Constraint: group_limit on "High ROI" max=2
- Verify: No solution contains more than 2 of {Alpha, Bravo, Delta}

**Test 4h: Combined constraints**
- Apply cardinality(min=2, max=4) + force_include(Charlie) + exclusion_pair(Alpha, Delta) simultaneously
- Verify: All constraints satisfied simultaneously in every solution

### Pass Criteria
- Each individual constraint type produces only feasible solutions
- Combined constraints produce only solutions satisfying ALL constraints
- No silent constraint violations (spot-check every solution in each test)

---

## Capability 5: NSGA-II vs NSGA-III Auto-Selection

**Lessons**: 1 (Section 1.2), 2 (Section header table)
**Why table-stakes**: Lesson 1 explicitly states "auto-selects NSGA-II (2-3 obj) vs NSGA-III (4+) with adaptive parameter tuning." This is documented as existing behavior, not aspirational.

### Test Plan

**Test 5a: 2 objectives (expect NSGA-II)**
- Problem: ROI + Risk only (drop Strategic Alignment)
- Run: solve/run mode=thorough
- Verify: Solutions show good crowding distance diversity (well-spread along 2D frontier)

**Test 5b: 3 objectives (expect NSGA-II)**
- Problem: Full test problem (ROI + Strategic Alignment + Risk)
- Run: solve/run mode=thorough
- Verify: Solutions distributed across 3D objective space

**Test 5c: 4+ objectives (expect NSGA-III)**
- Problem: Add a 4th objective (e.g., "Innovation Score") to the test problem
- Run: solve/run mode=thorough
- Verify: Solutions show reference-direction-based diversity (more uniform spread in 4D space than NSGA-II would produce)

### Validation
- Compare spacing CV across the three runs. NSGA-III (4+ obj) should maintain reasonable spacing CV even with more objectives, whereas NSGA-II would degrade.
- The switch should be automatic -- no user configuration needed.

### Pass Criteria
- 2-3 objectives: NSGA-II is used (can verify via diagnostics or behavior)
- 4+ objectives: NSGA-III is used
- No user intervention required for the switch
- Spacing CV remains reasonable (< some threshold) across all objective counts

---

## Capability 6: Fast vs Thorough Mode Behavior Differences

**Lessons**: 2 (header table + Section 2.5), 6 (Section 6.3 - Bias-Variance-Compute Triangle)
**Why table-stakes**: Lesson 6 provides a full table mapping fast vs thorough to bias/variance/compute. Lesson 2 describes this as existing behavior. Users need to trust that "fast" is genuinely faster and "thorough" is genuinely better.

### Test Plan

```
solve/run: mode=fast on test problem
solve/run: mode=thorough on test problem (same inputs)
```

### Expected Differences

| Metric | Fast | Thorough |
|--------|------|----------|
| Wall clock time | Lower | Higher |
| Number of solutions | May be fewer | More / better spread |
| Hypervolume | Lower or equal | Higher or equal |
| Spacing CV | Higher (more gaps) | Lower (better spread) |
| Run-to-run variance | Higher (noisier) | Lower (more stable) |

### Validation
- Run fast mode 3 times, thorough mode 3 times (same inputs)
- Compare hypervolume distributions: thorough should have higher mean and lower variance
- Compare spacing CV: thorough should have lower mean
- Compare timing: fast should be meaningfully faster

### Pass Criteria
- Thorough mode produces equal or better hypervolume than fast mode
- Thorough mode produces equal or better spacing CV than fast mode
- Fast mode is meaningfully faster (at least 2x)
- Both modes produce valid, non-dominated solution sets

---

## Capability 7: Quality Metrics Reporting (Hypervolume + Spacing CV)

**Lessons**: 1 (Section 1.7), 2 (header table)
**Why table-stakes**: Lesson 1 documents `QualityIndicators` as existing implementation. These metrics are the only way to assess whether the optimizer did a good job. Without them, users are flying blind.

### Test Plan

```
solve/run: mode=thorough on test problem
```

### Expected Output
- **Normalized hypervolume**: A value between 0 and 1 (or documented scale). Higher = better objective space coverage.
- **Spacing CV**: A value indicating distribution uniformity. Lower = more evenly spread solutions. Lesson 1 says "Low CV = well-spread. High CV = solutions are clumped."

### Validation Checks
1. Both metrics are present in the solve output (not null/missing)
2. Hypervolume increases or stays the same when problem constraints are relaxed (more feasible space = higher hypervolume)
3. Spacing CV is interpretable (documented units/scale)
4. Metrics change between fast and thorough modes (thorough should be better on both)

### Pass Criteria
- Both metrics reported after every solve/run
- Values are non-trivial (not always 0 or 1)
- Direction is correct: relaxing constraints improves hypervolume
- Thorough mode produces better metrics than fast mode

---

## Capability 8: Reference Points (Baseline + Aspirational)

**Lessons**: 1 (Section 1.3, header table)
**Why table-stakes**: Lesson 1 documents `ReferencePoint` model with baseline and aspirational types as existing implementation. Reference points are the primary preference mechanism replacing weights.

### Test Plan

**Step 1 -- Set baseline reference point**
```
model/update: set baseline reference point
  - ROI: 6 (current portfolio average)
  - Strategic Alignment: 5
  - Risk: 6
```

**Step 2 -- Set aspirational reference point**
```
model/update: set aspirational reference point
  - ROI: 8
  - Strategic Alignment: 8
  - Risk: 3
```

**Step 3 -- Solve and interpret**
```
solve/run: mode=thorough
explore/solutions: check how solutions relate to reference points
```

### Expected Behavior
- Solutions should be contextualized relative to reference points
- "Balanced" solution should be the one closest to the aspirational point (or best achievement scalarizing value)
- Users can see which solutions improve over baseline on which objectives
- Aspirational point may be infeasible -- the system should handle this gracefully (find nearest feasible frontier point)

### Pass Criteria
- Baseline and aspirational reference points are accepted and stored
- Solutions are presented in context of reference points
- The balanced/closest solution to aspirational is identifiable
- Infeasible aspirational points don't crash the system

---

## Capability 9: Marginal Analysis / Cost-Per-Unit Between Adjacent Solutions

**Lessons**: 1 (Section 1.3, header table - "marginal_analysis action: cost-per-unit between adjacent solutions, knee point detection")
**Why table-stakes**: Lesson 1 documents this as existing implementation of Marginal Rate of Substitution -- a core concept in multi-objective optimization for understanding tradeoff steepness.

### Test Plan

```
solve/run: mode=thorough
explore/marginal_analysis
```

### Expected Output
For adjacent solutions on the frontier, report:
- **Cost-per-unit**: "Moving from Solution 2 to Solution 3 costs 1.5 units of ROI per unit of Risk reduction"
- **Knee point detection**: Identify where marginal cost changes sharply (the "elbow" where you get diminishing returns)
- **Visualization**: `_render_marginal_rates` shows the marginal tradeoff curve

### Validation
- Pick two adjacent solutions manually. Calculate the ratio of objective changes. Compare to reported cost-per-unit.
- Knee point (if detected) should correspond to where the frontier curvature changes most.

### Pass Criteria
- Marginal analysis produces cost-per-unit ratios between adjacent solutions
- Ratios are mathematically correct (verifiable by hand)
- Knee point detection identifies the point of sharpest tradeoff change
- Output includes visualization

---

## Capability 10: Content Signature Stability Across Runs

**Lessons**: 5 (header table), 6 (Section 6.7 - Data Flywheel)
**Why table-stakes**: Lesson 5 documents content_signature (MD5) as existing. Lesson 6 describes it as "the key" to the data flywheel -- stable identifiers enabling cross-run learning. If signatures aren't stable for identical solutions across runs, the entire curation/feedback system breaks.

### Test Plan

**Step 1 -- Run and record signatures**
```
solve/run: mode=thorough
explore/solutions: record content_signatures of all solutions
```

**Step 2 -- Re-run with no changes**
```
solve/run: mode=thorough (identical inputs)
explore/solutions: record content_signatures of all solutions
```

**Step 3 -- Compare**
- Solutions with identical option sets and objective values should have identical content_signatures across runs
- If the optimizer produces the same portfolio {Bravo, Charlie, Echo} in both runs, the signature should match

### Pass Criteria
- Identical solutions produce identical content_signatures across runs
- Signatures are deterministic (based on solution content, not run metadata like timestamps)
- Curated/feedback-tagged solutions from Run 1 can be matched to equivalent solutions in Run 2

---

## Capability 11: Dominated Option Detection

**Lessons**: 1 (Section 1.1), 3 (header table - "dominated options"), 6 (Section 6.4)
**Why table-stakes**: Lesson 3 documents "dominated options" as part of score quality signals in the data_collection skill. Lesson 6 lists it as an existing diagnostic. A dominated option is provably suboptimal on all objectives -- keeping it wastes optimizer capacity and confuses users.

### Test Plan

Using the test problem, Hotel (ROI=2, Alignment=2, Risk=9) is dominated by Golf (ROI=4, Alignment=5, Risk=3) -- Golf is better on ALL three objectives.

```
model/update: load test problem with all 8 options
```

### Expected Behavior
- Diagnostics or data_collection signals should flag Hotel as dominated by Golf
- Message: "Hotel is dominated by Golf (worse on all objectives). Consider removing it."

### Validation
- Add a clearly dominated option (e.g., "India" with ROI=1, Alignment=1, Risk=10)
- System should flag it immediately
- Add a non-dominated option that's bad on one objective but good on another -- system should NOT flag it

### Pass Criteria
- Dominated options are detected and reported
- Non-dominated options (even poor-performing ones) are not falsely flagged
- Detection works before solving (during validation/data collection phase)

---

## Capability 12: Binding Constraint Detection

**Lessons**: 2 (header table), 4 (Section 4.3)
**Why table-stakes**: Both Lesson 2 and 4 document binding constraint detection as existing in `diagnostics` in `metrics.py`. Lesson 4 calls this "underrated UX" and says "telling users which constraints limit them is often more valuable than the optimal solution itself."

### Test Plan

**Test 12a: Binding cardinality**
```
Constraints: cardinality max=2
solve/run: mode=thorough
```
- Expected: Cardinality constraint is reported as binding. Many good options exist but only 2 can be selected. Diagnostic: "Increasing cardinality max from 2 to 3 would expand the frontier."

**Test 12b: Non-binding constraint**
```
Constraints: cardinality max=7, force_exclude=[Hotel]
solve/run: mode=thorough
```
- Expected: Cardinality max=7 is NOT binding (no solution wants 7+ options). Force_exclude on Hotel may or may not be binding (Hotel is dominated, so excluding it may not matter).

**Test 12c: Binding objective bound**
```
Constraints: objective_bound Risk <= 2.5 (very tight)
solve/run: mode=thorough
```
- Expected: Only Charlie (Risk=2) qualifies alone. Constraint is severely binding. Diagnostic should indicate this.

### Pass Criteria
- Binding constraints are correctly identified after each run
- Non-binding constraints are correctly identified as non-binding
- Diagnostic output suggests the impact of relaxation
- The distinction is meaningful and accurate (verifiable by inspection)

---

## Capability 13: Score Quality Signals (Variance, Scale Mismatch)

**Lessons**: 3 (header table - "variance by objective, scale mismatch detection")
**Why table-stakes**: Lesson 3 documents these as existing features of the data_collection skill. Bad scores produce bad frontiers -- catching quality issues early prevents garbage-in-garbage-out.

### Test Plan

**Test 13a: Low variance detection**
```
Modify test problem: set all ROI scores to 5 (no differentiation)
```
- Expected: Signal that ROI has zero/near-zero variance across options. "ROI doesn't differentiate between options -- consider removing or re-scoring."

**Test 13b: Scale mismatch**
```
Modify test problem: ROI scores are 1-100, Strategic Alignment scores are 1-5, Risk scores are 1-10
```
- Expected: Signal that objectives are on different scales. "ROI (range 1-100) and Strategic Alignment (range 1-5) are on different scales. Normalization will be applied, but consider whether the raw scales reflect intended importance."

**Test 13c: Dominated option detection (cross-ref with Capability 11)**
- Already covered in Capability 11

### Pass Criteria
- Low/zero variance objectives are flagged
- Scale mismatches across objectives are detected and reported
- Signals appear during data collection / validation phase (before solving)
- Signals are actionable (suggest what to do about the issue)

---

## Capability 14: Frontier Shape Interpretation

**Lessons**: 1 (Section 1.1, Key Takeaways #3: "Frontier shape tells a story")
**Why table-stakes**: Lesson 1 explicitly describes frontier shape as encoding tradeoff nature: convex = smooth tradeoffs, concave = diminishing returns, discontinuous = fundamentally different strategies. The product claims to help users "navigate" the frontier -- shape interpretation is how.

### Test Plan

**Test 14a: Convex-ish frontier**
```
Use test problem as-is. ROI vs Risk should show a relatively smooth tradeoff.
explore/tradeoffs: examine ROI vs Risk scatter
```
- Expected: Visualization shows the frontier shape. Ideally, description or interpretation notes the tradeoff character.

**Test 14b: Discontinuous frontier**
```
Modify test problem to create a gap:
- Options cluster into two types: "cheap & safe" (low ROI, low Risk) and "expensive & risky" (high ROI, high Risk)
- No options in the middle
```
- Expected: Frontier shows two clusters with a gap. This indicates fundamentally different strategy types.

### Validation
- Tradeoff visualizations (`_render_tradeoffs_viz`) render the frontier shape
- Marginal analysis shows where tradeoff rates change sharply
- Shape information helps users understand whether tradeoffs are smooth or discontinuous

### Pass Criteria
- Frontier shape is visualized (scatter plot or similar)
- Different problem structures produce visibly different frontier shapes
- Knee points / discontinuities are detectable via marginal_analysis
- ASCII visualizations render inline without extra tool calls

---

## Capability 15: Curation and Feedback Loop

**Lessons**: 1 (Section 1.4 - preference cycle detection potential), 6 (Section 6.7 - Data Flywheel)
**Why table-stakes**: Lesson 6 documents the full current loop: users curate solutions, provide feedback, system tracks survival via content_signature. This is described as existing ("Current Loop"), not future.

### Test Plan

**Full loop walkthrough:**

```
1. solve/run: mode=thorough
2. explore/solutions: view all
3. explore/curate: shortlist Solution A and Solution B
4. explore/feedback: rate Solution A positively, tag stage="interpreting"
5. explore/feedback: rate Solution B negatively, tag stage="interpreting"
6. model/update: change one score slightly
7. solve/run: mode=thorough
8. explore/solutions: check in_current_frontier for previously curated solutions
```

### Expected Behavior
- Step 3: Solutions A and B are marked as curated
- Step 4-5: Feedback recorded with stage tags
- Step 7: New run produces updated frontier
- Step 8: System indicates whether Solutions A and B (by content_signature) survived the re-run

### Pass Criteria
- Curate action works and persists across explore calls
- Feedback is recorded with stage parameter
- content_signature enables matching across runs
- The full loop completes without errors
- User can see which curated solutions survived re-optimization

---

## Capability 16: Adaptive Parameter Tuning

**Lessons**: 2 (header table, Section 2.2)
**Why table-stakes**: Lesson 2 documents "adaptive parameter tuning adjusts population size and generations based on solution space size and objective count" as existing behavior. This is the mechanism that makes the optimizer work across different problem sizes without manual configuration.

### Test Plan

**Test 16a: Small problem**
```
3 options, 2 objectives, binary mode
solve/run: mode=thorough
```

**Test 16b: Medium problem (test problem)**
```
8 options, 3 objectives, binary mode
solve/run: mode=thorough
```

**Test 16c: Large problem**
```
30 options, 5 objectives, binary mode
solve/run: mode=thorough
```

### Expected Behavior
- Population size should scale up with problem complexity
- Generation count should scale up
- Larger problems take more time but produce reasonable frontiers
- Small problems don't waste compute on oversized populations

### Pass Criteria
- All three problem sizes produce valid frontiers
- Thorough mode on the large problem doesn't timeout or crash
- Quality metrics (hypervolume, spacing CV) are reasonable across all sizes
- No manual parameter tuning required from the user

---

## Capability 17: Binary vs Proportional Mode

**Lessons**: 2 (header table - "binary vs proportional"), 6 (Section 6.8)
**Why table-stakes**: Lesson 2 documents both modes as existing. Lesson 6 explains the computational difference (NP-hard vs tractable). The approach field is the mechanism.

### Test Plan

**Test 17a: Binary mode**
```
approach: binary
Options: Alpha through Hotel
solve/run: mode=thorough
```
- Expected: Solutions are sets of selected options (each option is in or out)

**Test 17b: Proportional mode**
```
approach: proportional
Options: Alpha through Hotel (now representing budget allocations)
solve/run: mode=thorough
```
- Expected: Solutions are allocation weights (e.g., Alpha=30%, Bravo=25%, ...) summing to 100% (or some total)

### Pass Criteria
- Binary mode produces discrete select/deselect solutions
- Proportional mode produces continuous allocation weights
- Both modes respect constraints appropriately
- Both modes produce non-dominated solution sets

---

## Summary Checklist

| # | Capability | Lessons | Priority |
|---|-----------|---------|----------|
| 1 | Interactive preference loop (solve-explore-refine-re-solve) | L1 | Critical |
| 2 | A posteriori mode (generate, compare, curate) | L1 | Critical |
| 3 | Scenario analysis (overrides, adjustments, constraint overrides) | L1, L2, L4 | Critical |
| 4 | All 7 constraint types | L2 | Critical |
| 5 | NSGA-II vs NSGA-III auto-selection | L1, L2 | High |
| 6 | Fast vs thorough mode differences | L2, L6 | High |
| 7 | Quality metrics (hypervolume + spacing CV) | L1, L2 | High |
| 8 | Reference points (baseline + aspirational) | L1 | High |
| 9 | Marginal analysis / cost-per-unit | L1 | High |
| 10 | Content signature stability | L5, L6 | High |
| 11 | Dominated option detection | L1, L3, L6 | Medium |
| 12 | Binding constraint detection | L2, L4 | Medium |
| 13 | Score quality signals (variance, scale mismatch) | L3 | Medium |
| 14 | Frontier shape interpretation | L1 | Medium |
| 15 | Curation and feedback loop | L1, L6 | High |
| 16 | Adaptive parameter tuning | L2 | Medium |
| 17 | Binary vs proportional mode | L2, L6 | High |

### Execution Order Recommendation
1. **First**: Capabilities 1-4 (core loop + constraints) -- if these fail, nothing else matters
2. **Second**: Capabilities 5-10 (optimizer behavior + metrics + reference points) -- these make the core loop useful
3. **Third**: Capabilities 11-17 (diagnostics + quality signals + modes) -- these make the product robust

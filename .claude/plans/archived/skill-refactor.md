# Skill File Refactor: Principle-Based, Domain-Agnostic

## Goal
Replace hardcoded keyword matches, lookup tables, and domain-specific examples with principle-based heuristics. Eliminate cross-file redundancy with cross-references.

## Changes by file

### 1. `problem_framing.md`

**A. Replace "User says → Model concept" lookup table (lines 19-28)**
- Remove the 8-row table mapping specific phrases to model concepts
- Replace with the underlying classification principle: constraints exclude solutions, preferences rank them. User intent falls into one of these categories — classify by asking "does this eliminate options or rank them?"
- Keep the constraint type taxonomy (objective_bound, force_include/exclude, cardinality, exclusion_pair, dependency, group_limit) but frame as "types of constraints the user may express" rather than keyword triggers

**B. Replace approach selection table + domain heuristics (lines 65-84)**
- Remove the keyword/domain lookup table (lines 69-72)
- Remove the domain-aware heuristic bullet list (lines 76-80)
- Keep and elevate the decision heuristic (line 74): "which ones?" = binary, "how much of each?" = proportional
- Add the deeper principle: "Does the quantity assigned to each option matter, or is it a yes/no decision? If swapping allocations between two options produces a meaningfully different outcome, use proportional."

**C. Remove Domain Patterns section (lines 109-117)**
- Delete entirely. These 5 domain templates narrow the LLM's generalization.
- Replace with a generative heuristic: "For any domain, identify 2-4 objectives that represent genuinely conflicting goals. Use the conflict test to validate."

**D. Aggregation section (lines 92-103) — canonical location**
- Keep as-is. This is the single source of truth for aggregation. Other files will cross-reference here.

### 2. `data_collection.md`

**A. Replace Aggregation Implications section (lines 73-82)**
- Replace detailed definitions with cross-reference: "See aggregation modes in `frontier://skills/problem_framing`"
- Keep only the scoring-specific guidance that's unique to this file: how aggregation mode affects anchoring technique (line 82)

### 3. `optimization_strategy.md`

**A. Replace Approach Selection section (lines 29-32)**
- Replace with cross-reference to `frontier://skills/problem_framing` for approach selection logic
- Keep only the proportional mode technical differences (lines 34-38) since those are solver-specific

**B. Replace Constraint Strategy "User says" mapping (lines 52-58)**
- Remove verbatim phrase matching
- Replace with principle: classify user constraints by what they restrict (portfolio composition vs. objective bounds vs. option relationships). The constraint types are: bounds on objectives, inclusion/exclusion of specific options, relationships between options (mutual exclusion, dependency), limits on groups or portfolio size.

**C. Remove duplicate Structural Change Narration (lines 113-118)**
- Lines 113-118 are an exact duplicate of lines 102-105. Delete the duplicate block.

### 4. `solution_interpreter.md`

**A. Aggregation-Aware Framing (lines 58-66)**
- Cross-reference `frontier://skills/problem_framing` for mode definitions
- Keep the presentation framing examples — these are about *how to communicate*, not what the modes mean

**B. Trim Preference Learning (lines 200-218)**
- Keep revealed preference signals: gravitating toward certain solutions, repeated interest in specific options, indecision patterns
- Keep the waffling detection (lines 212-218) — this is genuinely useful behavioral guidance
- Remove the "likely preference" column that maps patterns to pop-psychology conclusions. Instead: "Surface the pattern to the user and let them confirm."

**C. Keep Common Misconceptions (lines 220-229)**
- These are valuable guardrails, not keyword matching. Keep as-is.

## Cross-reference convention
Use: `(See [section name] in frontier://skills/[skill_name])`

## What we're NOT changing
- Stage Awareness / Modeling Progression (problem_framing) — these are structural, not domain-specific
- Data readiness tiers, anchoring technique, batch efficiency (data_collection) — domain-agnostic methods
- Algorithm awareness, infeasibility response, binding constraint detection (optimization_strategy) — solver-specific judgment
- Five Things Users Need, dominance explanation, curation workflow (solution_interpreter) — presentation principles
- Hidden Objective Detection probing questions (problem_framing) — these are principle-based already
- Diagnostic Patterns table (solution_interpreter) — pattern detection, not keyword matching
- Recommendation Calibration (solution_interpreter) — signal-based, not keyword-based

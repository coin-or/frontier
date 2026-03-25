# Phase 0: Foundation MVP

**Goal:** Smallest possible end-to-end loop — model a problem, solve it, explore results — testable via Claude Code MCP in a single conversation.

This phase is about learning. Build bare bones, see how it feels, let implementation inform the broader design. Everything deferred here is tracked for Phase 1+.

---

## What's in

### Engine (pure Python, no API)

**Problem model** — in-memory with JSON save/load. No abstract store interface yet — just `json.dump`/`json.load` to a file. Single file per problem containing everything.

```
Problem
├── problem_id: string (uuid)
├── name: string
├── domain: string
├── context: string
├── objectives: Objective[]
├── options: Option[]
├── scores: Score[]     (flat list, option+objective pairs)
├── constraints: Constraint[]
├── run: Run | null      (latest only, no archival)
├── created_at: datetime
└── updated_at: datetime
```

**Objective, Option, Score** — exactly as design doc. No changes.

**Constraints** — simplified from full Criteria system. Phase 0 supports:

| Type | Example | Notes |
|---|---|---|
| `cardinality` | Pick 3-5 | `{ type: "cardinality", min: 3, max: 5 }` |
| `force_include` | Must have SSO | `{ type: "force_include", option: "SSO" }` |
| `force_exclude` | Can't do Mobile | `{ type: "force_exclude", option: "Mobile" }` |
| `objective_bound` | Effort ≤ 40 | `{ type: "objective_bound", objective: "Effort", operator: "max", value: 40 }` |

All constraints are hard (applied during optimization). No filter mode, no promote/demote, no exclusion pairs. These are Phase 1.

**Optimizer** — binary mode only (pick K of N). Single algorithm: NSGA-II via pymoo. No proportional allocation, no algorithm routing. Just run it.

**Validation** — before optimization:
- ≥ 2 objectives
- ≥ 3 options
- Score matrix 100% complete (no missing scores)
- Constraints feasible (no force_include + force_exclude conflict, cardinality min ≤ available options)
- Returns structured errors on failure

**Explorer** — minimal:
- `get_solutions()` → full Pareto frontier, sorted by first objective
- `get_solution(id)` → single solution detail
- `get_tradeoffs()` → objective ranges, correlation signs, balanced solution (min normalized distance to ideal), extreme solutions (best per objective)

No run diffing. No filter-time criteria.

### MCP Server: 3 tools, mapped to workflow

Tools map to what the LLM is *doing*, not the data model. The three phases of any decision process:

```
model  →  solve  →  explore
  │          │          │
  │          │          └── understand results, compare, iterate
  │          └── validate constraints, run optimizer
  └── define objectives, options, scores, constraints
```

---

#### Tool 1: `model`

Build and modify the problem. All problem definition lives here — objectives, options, scores, constraints are things you're modeling, not independent resources.

**Actions:**

**`create`** — Start a new problem.
```
Params: name, domain, context (all optional)
Returns: { problem_id, name, domain, created_at }
```

**`update`** — Modify any part of the problem definition. Accepts any subset of fields. Clears existing run when objectives, options, scores, or constraints change (you need to re-solve).
```
Params: problem_id (required), plus any of:
  - name, domain, context (metadata)
  - objectives: [ { name, direction, unit } ]                   — full replacement
  - options: [ { name, description? } ]                         — full replacement
  - scores: [ { option, objective, value } ]                    — merge (upsert by option+objective)
  - constraints: [ { type, ... } ]                              — full replacement

Returns: { problem_id, updated_at, status }
  status: { objectives: N, options: N, scores_complete: 0.0-1.0, has_run: bool }
```

Scores use merge semantics (set the ones you send, keep the rest) so the LLM can build the matrix incrementally. Everything else is full replacement — send the complete list.

Cascading on replacement: if you replace objectives or options, scores referencing removed items are dropped. Constraints referencing removed options are dropped.

**`get`** — Full problem state.
```
Params: problem_id
Returns: full problem including objectives, options, scores, constraints,
         and solutions (if solved)
```

**`list`** — All problems.
```
Returns: [ { problem_id, name, domain, status, created_at, updated_at } ]
```

**`delete`** — Remove problem and its data file.
```
Params: problem_id
Returns: { deleted: problem_id }
```

---

#### Tool 2: `solve`

Validate and run the optimizer.

**Actions:**

**`validate`** — Check if the problem is ready to solve. Returns structured issues.
```
Params: problem_id
Returns: { ready: bool, issues: [ { severity, message } ], missing_scores: [...] }
```

**`run`** — Validates first, then optimizes. Returns the full Pareto frontier inline.
```
Params: problem_id
Returns on success:
  { run_id, solutions_found, solutions: [...], quality: { hypervolume_normalized, spacing_cv } }
Returns on validation failure:
  { ready: false, issues: [...] }
Returns on infeasibility:
  { feasible: false, binding_constraints: [...], suggestions: [...] }
```

Solutions come back directly — no need for a separate fetch.

---

#### Tool 3: `explore`

Navigate results after solving. Owns the mechanical computation (balanced solution, extremes, correlations) so the LLM focuses on interpretation, not arithmetic.

**Actions:**

**`tradeoffs`** — Frontier overview.
```
Params: problem_id
Returns: {
  total_solutions: N,
  objective_ranges: { objective: { min, max } },
  key_tradeoffs: [ { objectives: [A, B], correlation: -0.72 } ],
  extreme_solutions: { best_{objective}: { solution_id, value, selected_options } },
  balanced_solution: { solution_id, objective_values, selected_options }
}
```

**`compare`** — Side-by-side two or more solutions.
```
Params: problem_id, solution_ids: [1, 5]
Returns: {
  solutions: [...],
  shared_options: [...],
  differentiating_options: [...],
  tradeoff_summary: { objective: { best: id, worst: id, range: [min, max] } }
}
```

---

### Why model / solve / explore?

This is how optimization practitioners describe the workflow:
- **Model** the decision space (what are we choosing between, what do we care about)
- **Solve** for the efficient frontier (let the algorithm work)
- **Explore** the tradeoff landscape (understand what you're giving up)

Each verb describes an *activity*, not an artifact. The LLM knows what it's doing at each step. The tool boundary matches the cognitive shift — from "building" to "computing" to "understanding."

---

### Tool vs client responsibility

Where does judgment live? This is the key architectural question.

```
Tool-side (deterministic)              Client-side (contextual)
─────────────────────────              ────────────────────────
Needs: problem state only              Needs: what the user said + domain context

• Parameter scaling                    • Binary vs proportional
  (pop_size from option count)           ("pick 4 features" vs "allocate budget")

• Validation rules                     • How many objectives is too many
  (can't do X with Y constraint)         (domain-dependent)

• Feasibility detection                • Relax constraint vs restructure problem
  (constraints contradict)               (depends on user's flexibility)

• Algorithm compatibility              • Which algorithm class fits
  (NSGA-III needs ≥3 objectives)         (user's problem shape + tolerance)
```

**The dividing line: if you need to know what the user said to decide, it's client-side. If you only need problem state, it's tool-side.**

Tool-side judgment is encoded as heuristics in the engine (deterministic, testable, same answer every time). Client-side judgment is encoded in skills (contextual, requires reasoning about the user's situation).

**For Phase 0 this barely matters** — binary only, NSGA-II only, reasonable defaults. No routing decisions to make. But the architecture needs to be right for Phase 1+ when we add proportional mode, algorithm variants, and parameter tuning.

The tool should:
- Auto-scale parameters (pop_size, n_gen) based on problem dimensions — pure heuristic, always right
- Reject invalid configurations with clear errors — deterministic validation
- Return structured metadata about what it did and why — so the client can explain it

The client (via skills) should:
- Choose the approach (binary/proportional) based on conversational context
- Recommend constraint strategies based on what the user is trying to achieve
- Decide when to re-run vs when to suggest restructuring the problem
- Explain solver output in terms the user cares about

This means skills carry real optimization knowledge — not just conversational technique. The "how to think about solving" judgment is genuinely client-side because it requires understanding the user's intent.

---

### Skills: Expert Personas

Skills encode expertise the LLM draws on at different conversational phases. Each represents a specialist's judgment. They don't tell the LLM what tools to call — they tell it what an expert would be thinking about.

#### Skill 1: `problem_framing`
*"The decision analyst who makes sure you're solving the right problem."*

Expertise:
- **Objective vs constraint distinction** — "Budget under $50K" is a constraint, not an objective. "Minimize cost" is an objective.
- **Objective consolidation** — 8 objectives means you haven't figured out what you care about. Combine correlated ones. If two things always move together, one is redundant.
- **Completeness check** — are these really all the options? What's the obvious one you're forgetting? What about the status quo?
- **Direction clarity** — every objective needs an unambiguous direction. "Quality" isn't an objective. "Maximize user satisfaction score" is.
- **Scope calibration** — 3 options is a comparison, not an optimization. 50 options means you haven't filtered enough.
- **Domain patterns** — common objective structures for hiring, product planning, vendor selection, architecture decisions.

When activated: Early conversation. Before any tool calls.

#### Skill 2: `data_collection`
*"The researcher who knows how to get numbers you can trust."*

Expertise:
- **Anchoring technique** — for each objective, identify the best and worst option first. Score everything else relative to those anchors. Reduces cognitive load, improves consistency.
- **Batch efficiency** — don't ask for one score at a time. Group by objective ("for Revenue Impact, rate all 10 options") or by option ("for SSO, rate all 3 objectives"). Minimize back-and-forth.
- **Scale calibration** — 1-10 is fine. Normalize later. Don't overthink precision — ordinal ranking matters more than exact values.
- **Uncertainty handling** — if the user doesn't know, ask for a range and take the midpoint. Flag low-confidence scores for sensitivity analysis later (Phase 1+).
- **Web research patterns** — when to look up data vs ask the user. Pricing is researchable. "How much will my team like this" is not.
- **Completeness drive** — the matrix must be 100% before solving. Track what's missing, fill gaps efficiently.

When activated: After framing, during score entry.

#### Skill 3: `optimization_strategy`
*"The operations researcher who knows which approach fits the problem."*

This is the client-side judgment that can't live in tool heuristics because it requires understanding the user's intent.

Expertise:
- **Approach selection** — "pick K features" is binary. "Allocate budget across initiatives" is proportional. "Rank candidates" might not need optimization at all. Read what the user is actually trying to do.
- **Constraint strategy** — user says "I don't want to spend too much" → that's an objective bound, not a force_exclude. User says "we can't do X and Y together" → that's an exclusion pair (Phase 1), suggest force_exclude on one for now.
- **Infeasibility response** — solver says infeasible. Is the right move to relax the tightest constraint? Or did the user frame something wrong? Depends on context.
- **Re-run judgment** — user changed one score slightly → probably don't need to re-run, the frontier won't change much. User added a new objective → definitely re-run, the landscape is fundamentally different.
- **Iteration coaching** — "The frontier gave you 8 solutions. That's a lot of tradeoff space. Want to add a constraint to narrow it?" vs "Only 2 solutions survived. Your constraints might be too tight."
- **Phase 1+ readiness** — recognize when the user's problem outgrows Phase 0 (needs proportional, needs >6 objectives, needs scenario analysis). Surface this rather than forcing a bad fit.

When activated: At the boundary between modeling and solving, and when interpreting solver results that suggest structural changes.

#### Skill 4: `solution_interpreter`
*"The advisor who helps you understand what you're choosing between — without choosing for you."*

Expertise:
- **Never say "best"** — there is no best. There are tradeoffs. Present them.
- **Extremes → balanced → preference** — start with the endpoints of the frontier (best revenue vs best effort vs best satisfaction). Then show the balanced middle. Then ask what the user gravitates toward.
- **Tradeoff framing** — "Solution 3 gives you 20% more revenue than Solution 7, but costs 35% more engineering effort. What's that worth to you?"
- **Differentiating options** — when comparing solutions, focus on what's different. Shared options are noise.
- **Iteration prompting** — when the user gravitates toward something, ask what would make it better. That's the next constraint or objective tweak.
- **Sensitivity intuition** — "This solution barely makes the cut on your effort constraint. If effort estimates are off by 10%, it might not be feasible." (Phase 1 formalizes this.)
- **Correlation narration** — explain tradeoff structure. "Revenue and effort are strongly correlated in your data — the high-impact features are also the expensive ones. That's the core tension here."

When activated: After solving, during exploration.

---

### Why 4 skills?

Each skill maps to a *type of expertise*, not a workflow step:

| Skill | Expert type | Key judgment |
|---|---|---|
| `problem_framing` | Decision analyst | "Are you solving the right problem?" |
| `data_collection` | Researcher | "Can we trust these numbers?" |
| `optimization_strategy` | Operations researcher | "Which approach fits this problem?" |
| `solution_interpreter` | Advisor | "What are you actually giving up?" |

`optimization_strategy` was originally folded into the `solve` tool description. But the dividing line is clear: *mechanical* optimization knowledge (parameter defaults, validation rules) belongs in the tool. *Contextual* optimization judgment (which approach, when to restructure, how to respond to infeasibility) requires understanding the user's intent and belongs in a skill.

The test: could a deterministic heuristic make this decision? If yes → tool. If it depends on "what did the user say" → skill.

---

### Skill delivery

Each skill is an MCP resource:
- `frontier://skills/problem_framing`
- `frontier://skills/data_collection`
- `frontier://skills/optimization_strategy`
- `frontier://skills/solution_interpreter`

The LLM loads the relevant skill when entering each workflow phase. The skill doesn't tell it what tools to call — it tells it what an expert would be thinking about.

---

## What's deferred (and why)

| Deferred | Why | When |
|---|---|---|
| Filter-mode criteria | Need constraint mode working first to prove value | Phase 1 |
| Promote/demote lifecycle | Depends on filter mode | Phase 1 |
| Exclusion pair constraints | Edge case, adds combinatorial complexity | Phase 1 |
| Proportional allocation | Binary mode covers most use cases | Phase 1 |
| REST API | LLM via MCP is the primary consumer; REST adds nothing for validation | Phase 2 |
| Run archival & comparison | No multi-run workflow to test yet | Phase 1 |
| `results_stale` flag | Phase 0 just clears results on change | Phase 1 |
| Scenario engine | Post-MVP entirely | Phase 4 |
| Export/import | Nobody exports before they've used it | Phase 2+ |
| CSV score format | Batch JSON is sufficient | Phase 2+ |
| Algorithm routing (NSGA-III, MOEA/D) | NSGA-II handles 2-6 objectives fine | Phase 1 |
| Score confidence/source metadata | Nice-to-have, not load-bearing | Phase 1 |
| Content signatures | Cross-run tracking, no runs to cross yet | Phase 1 |
| API authentication | Local tool, single user | Phase 2+ |
| Solution annotation | Defer to dogfooding | Phase 5 |

---

## Implementation plan

### Step 1: Data model + store

```
frontier/
├── engine/
│   ├── __init__.py
│   ├── models.py        # Pydantic models: Problem, Objective, Option, Score, Constraint, Run, Solution
│   └── store.py         # save(problem), load(id), list(), delete(id) — JSON files in ./data/
├── data/                # JSON problem files (gitignored)
└── pyproject.toml       # Python project with pymoo, pydantic deps
```

Verify: Create a problem in Python, save, load, assert round-trip.

### Step 2: Optimizer + explorer

```
frontier/
├── engine/
│   ├── ...
│   ├── optimizer.py     # validate() + optimize() — wraps pymoo NSGA-II
│   └── explorer.py      # get_tradeoffs(), compare_solutions() — reads from Run
```

The optimizer:
- Takes a Problem, returns a Run with Solution[]
- Encodes constraints as pymoo constraints (cardinality, force include/exclude, objective bounds)
- Binary decision variables (0/1 per option)
- NSGA-II with reasonable defaults (pop_size=100, n_gen=200 for ≤20 options; scale up for more)

Verify: Script that creates a problem, optimizes, checks solutions respect constraints.

### Step 3: MCP server + skills

```
frontier/
├── engine/ ...
├── mcp_server/
│   ├── __init__.py
│   └── server.py        # 3 tools: model, solve, explore
├── skills/
│   ├── problem_framing.md
│   ├── data_collection.md
│   ├── optimization_strategy.md
│   └── solution_interpreter.md
└── pyproject.toml       # Add mcp dependency
```

Wire 3 tools to engine. Register 4 skills as MCP resources. Install in Claude Code.

Verify: Run checkpoint conversation.

---

## Checkpoint: "Can Claude help me make a decision?"

The checkpoint is a scripted end-to-end conversation that exercises every tool, every skill, and every phase transition. It's the single test that tells us if Phase 0 works.

### Test Problem

**"Pick 4 of 10 product features for next quarter given revenue impact (maximize), eng effort (minimize), and user satisfaction (maximize)."**

This problem is deliberately in the sweet spot: enough options for combinatorial complexity (252 ways to pick 4 of 10), enough objectives for genuine tradeoffs (revenue vs effort is the classic tension), and a constraint (must include SSO) that meaningfully shapes the frontier.

### Test Data

```
10 options, 3 objectives, 30 scores (complete matrix)
Constraints: cardinality 3-5, force_include "SSO Integration"
```

Reference scores (from the SaaS Feature Prioritization demo, adapted):

| Feature | Revenue Impact (1-10) | Eng Effort (days) | User Satisfaction (1-10) |
|---|---|---|---|
| Real-time Collaboration | 9 | 21 | 9 |
| Analytics Dashboard | 8 | 18 | 7 |
| AI Content Generation | 9 | 25 | 8 |
| Template Library | 6 | 8 | 7 |
| Workflow Automation | 8 | 15 | 7 |
| Third-party Integrations | 7 | 12 | 8 |
| Mobile App | 7 | 45 | 6 |
| SSO Integration | 5 | 8 | 8 |
| Version Control | 6 | 10 | 7 |
| API Access | 7 | 14 | 5 |

### Conversation Script

The checkpoint follows the natural workflow: frame → score → solve → explore → refine → re-solve. Each phase tests specific tool calls and skill activations.

**Phase 1: Framing** (problem_framing skill)

User opens with the problem statement. The LLM should:
1. Validate objectives are directional and measurable ✓
2. Note the option count is in the sweet spot (10) ✓
3. Ask about constraints — "Any features that must be included or excluded?"
4. Translate "pick 4" into a cardinality constraint
5. Call `model create` then `model update` with objectives, options, constraints

Expected tool calls: `model create`, `model update` (objectives + options + constraints)

**Phase 2: Scoring** (data_collection skill)

User provides or confirms scores. The LLM should:
1. Batch scores efficiently — by objective or by option, not one at a time
2. Use anchoring: "For Revenue Impact, which feature has the highest impact? Which has the lowest?"
3. Build matrix incrementally via `model update` with score merge
4. Confirm completeness before proceeding

Expected tool calls: 1-3 `model update` calls with scores (not 30 individual calls)

**Phase 3: Solve** (optimization_strategy skill)

LLM runs the optimizer:
1. Call `solve validate` — should return ready
2. Call `solve run` — should return Pareto frontier
3. Note that binary mode is correct for "pick K of N"
4. Interpret solution count: 5-15 solutions is healthy

Expected tool calls: `solve run` (validation is built in)

**Phase 4: Explore** (solution_interpreter skill)

LLM presents results:
1. Call `explore tradeoffs` to get frontier overview
2. Present extremes first: "Solution X maximizes revenue (picks the high-impact features). Solution Y minimizes effort (picks the quick wins)."
3. Show balanced solution: "Solution Z balances all three objectives."
4. Ask: "Which of these feels closest to what you want?"
5. When user asks about two specific solutions, call `explore compare`
6. Focus on differentiating options — what's different between the solutions, not what's shared

Expected tool calls: `explore tradeoffs`, `explore compare`

**Phase 5: Refine** (optimization_strategy + solution_interpreter skills)

User says: "What if effort must be under 30 days total?"
1. LLM recognizes this as an objective_bound constraint
2. Calls `model update` with new constraint (clears existing run)
3. Calls `solve run` — new frontier should be smaller
4. Explains what changed: "Adding the effort cap eliminated solutions that included Mobile App and AI Content Generation together."
5. Presents the new tradeoff landscape

Expected tool calls: `model update` (constraint), `solve run`, `explore tradeoffs`

### Pass Criteria

**Engine correctness:**
- [ ] `solve run` returns Pareto frontier with ≥5 solutions
- [ ] All solutions respect cardinality (3-5 features selected)
- [ ] All solutions include SSO Integration
- [ ] After adding effort bound, all solutions have total effort ≤ 30
- [ ] New frontier is strictly smaller than original
- [ ] Solutions are genuinely Pareto-optimal (no solution dominates another)

**Skill activation:**
- [ ] LLM validates objectives before building (problem_framing)
- [ ] LLM batches scores, doesn't ask one at a time (data_collection)
- [ ] LLM identifies binary mode as correct approach (optimization_strategy)
- [ ] LLM presents extremes → balanced → asks preference (solution_interpreter)
- [ ] LLM translates "effort under 30" to objective_bound constraint (optimization_strategy)
- [ ] LLM explains tradeoffs without saying "best" (solution_interpreter)
- [ ] LLM uses the Five Things framework when explaining a solution the user is considering

**Tool usage:**
- [ ] LLM creates problem via `model create`, builds via `model update`
- [ ] Score matrix built in ≤3 `model update` calls (not 30)
- [ ] LLM uses `explore tradeoffs` for overview, `explore compare` for side-by-side
- [ ] Total tool calls for full workflow: ≤ 12
- [ ] LLM re-runs after constraint change without being told to

**Conversation quality:**
- [ ] LLM asks what matters most to the user before recommending
- [ ] When user gravitates toward a solution, LLM quantifies what they're giving up
- [ ] LLM offers iteration: "Would you like to explore what changes if we adjust...?"
- [ ] No hallucinated scores or solution details — everything references tool output

### Fail Signals

**Hard failures** (checkpoint does not pass):
- Optimization returns 0 solutions without clear error or infeasibility diagnosis
- Solutions violate constraints (cardinality, force_include, or objective_bound)
- LLM says "the best solution is..." or ranks solutions as #1, #2, #3
- Score entry takes more than 5 back-and-forth exchanges for 30 scores
- LLM doesn't know what tool to call next (gets stuck)

**Soft failures** (checkpoint passes but needs design attention):
- LLM doesn't load relevant skill at phase transition (works but less expert)
- LLM can't reason about approach fit — treats everything as binary without considering if that's right
- `explore` doesn't add value beyond what `solve run` already returned
- LLM over-explains or under-explains (progressive disclosure not calibrated)
- LLM recommends without the user expressing any preferences (weak signal, should ask)
- LLM doesn't detect hidden objectives from user comments during exploration

### Checkpoint Variants

After the primary checkpoint passes, run these variants to stress-test:

**Variant A: Infeasibility**
Add constraints: force_include 3 expensive features + cardinality max=4 + effort bound ≤ 20. This should be infeasible. Test that the LLM diagnoses which constraint to relax and explains why.

**Variant B: Vague framing**
User says: "Help me figure out which features to build." No objectives, no scores. Test that problem_framing skill activates, draws out objectives through conversation, and doesn't jump to scoring.

**Variant C: Reconsidering after results**
User sees results and says "actually, I think we should also consider technical risk." Test that the LLM recognizes this as a new objective, warns that results will be cleared, and smoothly re-frames the problem.

**Variant D: Misconception handling**
User says "which one should I pick?" after seeing results. Test that the LLM correctly explains Pareto optimality and asks about preferences rather than picking for them.

---

## Dependency stack

```
python >= 3.11
pymoo >= 0.6        # NSGA-II
pydantic >= 2.0     # Data models + validation
mcp >= 1.0          # MCP server SDK (FastMCP)
```

No FastAPI, no database, no async, no background tasks. Pure synchronous Python + MCP.

---

## Eval Harness

The eval harness measures two axes: (1) does the agent guide the workflow effectively, and (2) does the optimization journey improve the user's decision. It's designed to be part of the natural workflow, not a separate system.

### Layer 1: Automated Metrics

A `metrics` module (`frontier/engine/metrics.py`) computes deterministic health signals from problem state. These are included in tool responses at natural checkpoints — no extra tool calls needed.

**When metrics appear:**

| Tool response | Metrics included |
|---|---|
| `model update` (structural change) | `framing` + `data` |
| `solve run` (success) | `solve` + `diagnostics` |
| `explore feedback` | `outcome` |

**What's measured:**

- **Framing**: objective/option counts, directions set, constraint count
- **Data**: score completeness, per-objective variance, dominated options
- **Solve**: solution count, feasibility, hypervolume, spacing, per-objective variation, per-option coverage
- **Outcome**: user-selected solution, rating (1-5), feedback count
- **Diagnostics**: clustered solutions, low-variation objectives, never-selected options, binding constraints, zero solutions

The LLM uses these to coach the user (e.g., "Objective X doesn't differentiate your options" or "Only 2 solutions survived — constraints may be too tight"). The diagnostics patterns are adapted from the v2 Decision Assistant.

### Layer 2: User Feedback

A new `explore feedback` action collects lightweight signals at the decision point:

```
explore feedback problem_id=X solution_id=3 rating=4 notes="..." stage="decision"
```

Feedback is stored on the Problem model and persisted with the problem JSON. It captures:
- Which solution the user chose (if any)
- Satisfaction rating (1-5)
- Free-text notes
- Stage (exploration, decision, post-refinement)

This feeds into outcome metrics and is available for cross-problem analysis once we have enough data.

### Eval Checkpoint Script

`tests/eval_checkpoint.py` exercises the full workflow programmatically using the checkpoint test data:

1. Create problem with 10 options, 3 objectives, cardinality 3-5, force_include SSO
2. Add 30 scores (complete matrix)
3. Validate and optimize
4. Check metrics: ≥5 solutions, all respect constraints, hypervolume > 0.3
5. Explore: tradeoffs overview, compare two solutions
6. Refine: add effort ≤ 30 constraint, re-solve
7. Check: fewer solutions, all respect new bound
8. Record feedback, verify persistence

Run: `python -m tests.eval_checkpoint`

### What this does NOT include

- No CSV test case management (v2 pattern, too heavy)
- No LLM-in-the-loop eval (conversation quality tested manually via checkpoint variants)
- No dashboard (stdout sufficient)
- No regression baselines (no baseline yet)

---

## What this teaches us

After running the checkpoint, we'll know:

1. **Does model/solve/explore feel right?** Is `model update` too overloaded, or does it flow naturally? Does the LLM sequence the updates well?
2. **Is score entry tolerable?** 30 scores via merge — does the LLM batch efficiently with the data_collection skill? Do we need CSV or a different input pattern?
3. **Does explore earn its keep?** Or does the LLM do fine navigating the solution list from `solve run`?
4. **Do the skills activate naturally?** Does the LLM shift persona at the right moments? Does `optimization_strategy` pull its weight even in Phase 0 (binary only)?
5. **What's the first thing we want to add?** Filter mode? Proportional? Run comparison? Let the friction tell us.

These answers update the design doc priors for Phase 1+.

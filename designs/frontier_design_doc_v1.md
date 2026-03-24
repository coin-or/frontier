# Frontier — Design Document

**Multi-objective portfolio exploration for decisions too combinatorial for intuition.**

Version 1.0 · March 2026 · Cameron Afzal

---

## Table of Contents

1. [Product Thesis](#1-product-thesis)
2. [Architecture](#2-architecture)
3. [Data Model](#3-data-model)
4. [API Specification](#4-api-specification)
5. [Criteria System](#5-criteria-system)
6. [Scenario Engine](#6-scenario-engine)
7. [Client-Side Skills](#7-client-side-skills)
8. [MCP Server](#8-mcp-server)
9. [Workflow Scenarios](#9-workflow-scenarios)
10. [Implementation Phases & Checkpoints](#10-implementation-phases--checkpoints)
11. [Design Decisions Log](#11-design-decisions-log)
12. [Open Questions](#12-open-questions)

---

## 1. Product Thesis

Frontier is a multi-objective optimization engine that finds and navigates Pareto-optimal portfolios for combinatorial selection and allocation problems. It pairs with an LLM client: Frontier does the computation (searching solution spaces, computing tradeoffs), the LLM does the conversation (helping users frame problems, translate data, and understand results). The engine has zero AI dependencies.

### Target Problem Profile

Problems with 5-40 options, 2-6 conflicting objectives, meaningful stakes, and data the user roughly has but isn't synthesizing well. The solution space must be too large for intuition — combinatorial portfolio selection ("pick K of N") or proportional allocation ("distribute budget across N").

| Too Simple | Sweet Spot | Too Complex |
|---|---|---|
| Single-objective ranking | "Pick 5 of 20 features given revenue, effort, risk, satisfaction" | Simulation-driven optimization |
| Pros/cons lists | "Allocate budget across 12 channels given ROI, awareness, CAC" | Sequential multi-stage decisions |
| Weighted scoring | "Select 3 of 10 vendors given cost, integration, capability, lock-in" | Real-time continuous optimization |

### Why Not Just an LLM?

For "pick 5 of 20" with 4 objectives, there are 15,504 combinations — each with different tradeoffs. LLMs can't systematically search this space. Frontier finds the Pareto frontier; the LLM helps navigate it.

### Core Principle: Computation vs. Conversation

Frontier does **computation** — storing state, running optimization, computing tradeoffs. The LLM client does **conversation** — helping users articulate objectives, translate rough data into scores, and understand results. This separation is strict.

---

## 2. Architecture

```
┌─────────────────────────────────────────────┐
│  Tier 3: Clients (future)                   │
│  React UI · CLI · Notebooks                 │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│  Tier 2: Interface Layer                    │
│  REST API (FastAPI) — primary interface      │
│  MCP Server — optional wrapper for LLM clients│
│  Skills — client-side markdown docs          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│  Tier 1: Engine (pure Python, no AI)        │
│  Problem Store · Optimizer · Explorer        │
│  Criteria System · Scenario Engine           │
└──────────────────────────────────────────────┘
```

### Engine Components

**Problem Store** — CRUD for problems. JSON file per problem with abstract store interface (swappable to SQLite/Postgres). Current state + latest run in one file; archived runs in separate files. Interface: `save(id, data)`, `load(id)`, `list()`, `delete(id)`, `save_run(id, run)`, `list_runs(id)`, `load_run(id, run_id)`.

**Optimizer** — Wraps pymoo. Routes to NSGA-II (2-3 objectives), NSGA-III (4-7), or MOEA/D (8+). Binary selection and proportional allocation (integer percentages 0-100). Snapshots criteria per run. Hard validation before execution — returns structured errors or explicit infeasibility response, never misleading fallback solutions.

**Explorer** — Pareto frontier navigation. Compare solutions, tradeoff analysis, balanced/extreme identification. Applies filter-mode criteria when querying solutions.

**Criteria System** — Unified model for constraints and filters. Both modes hard-exclude non-matching solutions; the only difference is when (optimization time vs query time). See [Section 5](#5-criteria-system).

**Scenario Engine** — Per-scenario optimization with probabilistic analysis: expected value, robust (minimax regret), scenario-specific frontiers. See [Section 6](#6-scenario-engine).

---

## 3. Data Model

### Problem

```
Problem
├── problem_id: string
├── name: string (optional)
├── domain: string
├── context: string
├── results_stale: boolean
│   Set true when objectives/options/scores change after optimization.
│   Engine doesn't auto-clear results; signals they may not reflect current data.
├── objectives: Objective[]
├── options: Option[]
├── scores: Score[]
├── criteria: Criterion[]
├── scenarios: ScenarioConfig
├── current_run: Run (latest run with full solution set)
├── created_at: datetime
└── updated_at: datetime
```

**Storage:** Each problem is a single JSON file (`{problem_id}.json`) containing full state plus latest run's complete solution set. Archived runs stored in separate files (`{problem_id}_run_{run_id}.json`) with criteria snapshot, solutions, and quality indicators.

### Objective

```
Objective
├── name: string (unique within problem)
├── direction: "maximize" | "minimize"
├── unit: string
└── aggregation: "sum" | "avg" | "min" | "max"
```

### Option

```
Option
├── name: string (unique within problem)
└── description: string (optional)
```

### Score

```
Score
├── option: string (ref → Option.name)
├── objective: string (ref → Objective.name)
├── value: number
├── confidence: "high" | "medium" | "low" (optional — metadata only, not used by optimizer)
├── source: string (optional)
└── notes: string (optional)
```

### Criterion

```
Criterion
├── name: string (optional — auto-generated from target+operator if omitted)
│   Examples: Eng_Effort_max_40, include_SSO_Integration, cardinality_3_to_6
├── target_type: "objective" | "option" | "cardinality" | "exclusion"
├── target: string | string[] | null
├── operator: "min" | "max" | "equals" | "range" | "include" | "exclude" | "exclude_pair"
├── value: number | { min, max } | null
├── mode: "constraint" | "filter"
│   constraint = applied during optimization (solutions violating never generated)
│   filter = applied when querying solutions (non-matching hidden, full frontier preserved)
└── created_at: datetime
```

Criteria on objectives always refer to the **aggregated** (post-optimization) value. A criterion `Revenue Impact > 200k` means the portfolio's total/avg revenue (per aggregation setting) must exceed 200k. Per-option thresholds aren't supported in v1 — use include/exclude for specific options.

### Scenario Config

```
ScenarioConfig
├── enabled: boolean
└── scenarios: Scenario[]

Scenario
├── name: string
├── probability: number (0-1)
├── description: string
└── score_overrides: ScoreOverride[]

ScoreOverride
├── option: string
├── objective: string
└── value: number
```

Overrides are efficient (only store changed scores) and highlight what actually differs between scenarios. The engine materializes full matrices at optimization time. Export format materializes full matrices per scenario for portability.

### Run

```
Run
├── run_id: string
├── timestamp: datetime
├── mode: "fast" | "thorough"
├── approach: "binary" | "proportional"
├── criteria_snapshot: Criterion[] (full copy at time of run)
├── solutions: Solution[] (full Pareto frontier)
├── quality: QualityIndicators
├── summary: RunSummary (solution count, objective ranges, top options)
└── duration_ms: number
```

Latest run's full solution set lives in the problem file. When a new run completes, the previous run is archived to a separate file. `GET /runs` returns summaries; `GET /solutions?run_id=X` loads archived files.

### Solution

```
Solution
├── solution_id: number
├── content_signature: string (stable MD5 hash for cross-run matching)
├── selected_options: string[] (binary mode)
├── allocations: { option: integer_percentage } (proportional mode, 0-100 summing to 100)
├── num_options: number
├── objective_values: { objective: value }
└── is_locally_dominant: boolean
```

---

## 4. API Specification

### Design Principles

- RESTful with JSON request/response bodies
- No AI dependencies — pure computation
- Stateful per-problem (JSON file-backed store with abstract interface)
- Idempotent where possible (PUT for full replacement, PATCH for partial)
- Errors return structured `{ "error": string, "details": object, "suggestions": string[] }` with appropriate HTTP status codes
- Hard validation before optimization — no misleading fallback solutions

### Authentication

Optional API key via `Authorization: Bearer <key>` header. Set via `FRONTIER_API_KEY` environment variable. If unset, API runs without authentication.

---

### 4.1 Problem Management (5 endpoints)

#### `POST /problems`

Create a new problem. Also accepts a full export payload for import.

```json
// Request — new problem
{
  "domain": "Select features for Q3 roadmap",
  "context": "10-person eng team, 3-month cycle, targeting enterprise segment",
  "name": "Q3 Feature Prioritization"
}

// Request — import from export
{
  "import": { ... }  // full export payload from GET /export
}

// Response 201
{
  "problem_id": "abc123",
  "domain": "Select features for Q3 roadmap",
  "created_at": "2026-03-24T10:00:00Z"
}
```

#### `GET /problems`

```json
// Response 200
{
  "problems": [
    {
      "problem_id": "abc123",
      "name": "Q3 Feature Prioritization",
      "domain": "Select features for Q3 roadmap",
      "created_at": "2026-03-24T10:00:00Z",
      "updated_at": "2026-03-24T12:00:00Z",
      "results_stale": false,
      "status": {
        "objectives": 4,
        "options": 12,
        "scores_complete": 0.75,
        "has_results": true,
        "runs": 3
      }
    }
  ]
}
```

#### `GET /problems/{id}`

Returns full problem state including objectives, options, scores, criteria, scenarios, and run summaries.

#### `PUT /problems/{id}`

Update problem metadata (domain, context, name). Marks results as stale if domain changes.

```json
// Request
{ "context": "Team grew to 15, expanded scope" }

// Response 200
{ "problem_id": "abc123", "updated_at": "...", "results_stale": true }
```

#### `DELETE /problems/{id}`

Delete a problem and all associated data (scores, criteria, runs, archived run files).

```json
// Response 200
{ "deleted": "abc123", "runs_deleted": 4 }
```

---

### 4.2 Objectives (3 endpoints)

#### `POST /problems/{id}/objectives`

Add one or more objectives. Marks results as stale.

```json
// Single
{ "name": "Revenue Impact", "direction": "maximize", "unit": "$/quarter", "aggregation": "sum" }

// Batch
{ "objectives": [
    { "name": "Revenue Impact", "direction": "maximize", "unit": "$/quarter", "aggregation": "sum" },
    { "name": "Eng Effort", "direction": "minimize", "unit": "person-weeks", "aggregation": "sum" },
    { "name": "Tech Debt Risk", "direction": "minimize", "unit": "score 1-10", "aggregation": "avg" },
    { "name": "User Satisfaction", "direction": "maximize", "unit": "score 1-10", "aggregation": "avg" }
] }

// Response 201
{ "added": ["Revenue Impact", "Eng Effort", "Tech Debt Risk", "User Satisfaction"], "total_objectives": 4 }
```

#### `PUT /problems/{id}/objectives/{name}`

Update objective properties (any subset of direction, unit, aggregation). Marks results as stale.

#### `DELETE /problems/{id}/objectives/{name}`

Remove objective. Cascading delete: removes associated scores and criteria. Marks results as stale.

---

### 4.3 Options (2 endpoints)

#### `POST /problems/{id}/options`

Add one or more options. Marks results as stale.

```json
// Batch
{ "options": [
    { "name": "Real-time Collaboration" },
    { "name": "SSO Integration" },
    { "name": "Mobile App v2" }
] }

// Response 201
{ "added": ["Real-time Collaboration", "SSO Integration", "Mobile App v2"], "total_options": 12 }
```

#### `DELETE /problems/{id}/options/{name}`

Remove option. Cascading delete: removes associated scores, criteria referencing this option, and scenario overrides. Marks results as stale.

---

### 4.4 Scores (1 endpoint)

#### `PUT /problems/{id}/scores`

Set scores. Three formats, detected from payload. Marks results as stale.

```json
// Format 1: Single
{ "option": "SSO Integration", "objective": "Revenue Impact", "value": 80000,
  "confidence": "high", "source": "Q2 data", "notes": "Based on renewal analysis" }

// Format 2: Batch
{ "scores": [
    { "option": "SSO Integration", "objective": "Revenue Impact", "value": 80000 },
    { "option": "SSO Integration", "objective": "Eng Effort", "value": 3 }
] }

// Format 3: CSV string
{ "csv": "Option,Revenue Impact,Eng Effort\nSSO Integration,80000,3\nMobile App v2,120000,8\n..." }

// Response 200
{ "scores_set": 48, "matrix_completeness": 1.0, "missing": [] }
```

---

### 4.5 Criteria (3 endpoints)

See [Section 5: Criteria System](#5-criteria-system) for the full model. API endpoints:

#### `GET /problems/{id}/criteria`

```json
// Response 200
{ "criteria": [
    { "name": "budget_cap", "target_type": "objective", "target": "Eng Effort",
      "operator": "max", "value": 40, "mode": "constraint", "created_at": "..." },
    { "name": "must_have_sso", "target_type": "option", "target": "SSO Integration",
      "operator": "include", "value": null, "mode": "constraint" },
    { "name": "prefer_low_debt", "target_type": "objective", "target": "Tech Debt Risk",
      "operator": "max", "value": 5, "mode": "filter" },
    { "name": "team_size", "target_type": "cardinality", "target": null,
      "operator": "range", "value": { "min": 3, "max": 6 }, "mode": "constraint" },
    { "name": "no_both_collab_and_mobile", "target_type": "exclusion",
      "target": ["Real-time Collaboration", "Mobile App v2"],
      "operator": "exclude_pair", "value": null, "mode": "constraint" }
] }
```

#### `PUT /problems/{id}/criteria`

Full replacement — omitted criteria are removed.

```json
// Request
{ "criteria": [
    { "target_type": "objective", "target": "Eng Effort", "operator": "max", "value": 40, "mode": "constraint" },
    { "target_type": "objective", "target": "User Satisfaction", "operator": "min", "value": 7, "mode": "filter" }
] }

// Response 200
{ "criteria_set": 2, "constraints": 1, "filters": 1 }
```

#### `PATCH /problems/{id}/criteria/{name}`

Update single criterion. Primary use: promote filter → constraint (or demote).

```json
// Promote
{ "mode": "constraint" }

// Update value
{ "value": 35 }

// Response 200
{ "name": "User_Satisfaction_min_7", "mode": "constraint", "updated_at": "..." }
```

---

### 4.6 Scenarios (3 endpoints)

#### `PUT /problems/{id}/scenarios/config`

```json
// Request
{ "enabled": true, "scenarios": [
    { "name": "Base Case", "probability": 0.5, "description": "Current trajectory" },
    { "name": "High Growth", "probability": 0.3, "description": "Enterprise deal closes" },
    { "name": "Contraction", "probability": 0.2, "description": "Key customer churns" }
] }

// Response 200
{ "enabled": true, "scenarios": 3, "probabilities_sum": 1.0 }
```

#### `PUT /problems/{id}/scenarios/{name}/scores`

Set score overrides — only include scores that differ from base matrix.

```json
// Request
{ "overrides": [
    { "option": "Real-time Collaboration", "objective": "Revenue Impact", "value": 250000 }
] }

// Response 200
{ "scenario": "High Growth", "overrides_set": 1 }
```

#### `GET /problems/{id}/scenarios/results`

Returns per-scenario results + probabilistic analysis. Only available after `POST /scenarios/optimize`.

```json
// Response 200
{ "scenario_results": {
    "Base Case": { "solution_count": 15, "objective_ranges": {...}, "top_options": [...] },
    "High Growth": { ... }
  },
  "probabilistic_analysis": {
    "expected_value_solution": { "objective_values": { "Revenue Impact": 340000 } },
    "robust_solution": { "description": "Best worst-case", "objective_values": {...} },
    "robust_options": ["SSO Integration", "API v3"],
    "scenario_specific_options": ["Real-time Collaboration"]
} }
```

---

### 4.7 Optimization (2 endpoints)

#### `POST /problems/{id}/optimize`

Hard validation before execution:
- All scores must be numeric (no null/NaN)
- Constraint-mode criteria must be feasible (no forced include + exclude conflict, cardinality min ≤ available options)
- At least 2 objectives and 3 options

If validation fails → `400` with structured errors. If zero feasible solutions → `200` with `{ "feasible": false, "binding_constraints": [...], "suggestions": [...] }`.

```json
// Request
{ "mode": "thorough", "approach": "binary" }

// Response 200
{ "run_id": "run_004", "solutions_found": 23, "algorithm": "NSGA-II",
  "criteria_snapshot": { "constraints_applied": 3, "filters_deferred": 1 },
  "quality": { "hypervolume_normalized": 0.82, "spacing_cv": 0.25, "assessment": "good" },
  "duration_ms": 1450 }
```

#### `POST /problems/{id}/scenarios/optimize`

Runs optimization independently per scenario.

```json
// Request
{ "mode": "fast", "approach": "binary" }

// Response 200
{ "scenarios_optimized": 3,
  "results": { "Base Case": { "solutions_found": 18 }, "High Growth": { "solutions_found": 22 } },
  "probabilistic_analysis_available": true }
```

---

### 4.8 Exploration (3 endpoints)

#### `GET /problems/{id}/solutions`

Filter-mode criteria automatically applied. Supports sorting and pagination.

```
Query params: ?sort=Revenue+Impact&order=desc&limit=10&offset=0&run_id=run_003
```

```json
// Response 200
{ "run_id": "run_004", "total_solutions": 23, "filters_applied": 1, "solutions_after_filter": 19,
  "solutions": [
    { "solution_id": 1,
      "selected_options": ["SSO Integration", "API v3", "Advanced Analytics", "Audit Logging"],
      "num_options": 4,
      "objective_values": { "Revenue Impact": 420000, "Eng Effort": 28, "Tech Debt Risk": 3.5 },
      "content_signature": "a1b2c3d4e5f6",
      "is_locally_dominant": true }
] }
```

#### `GET /problems/{id}/solutions/compare?ids=1,5,12`

```json
// Response 200
{ "solutions": [...],
  "tradeoff_summary": {
    "Revenue Impact": { "best": 1, "worst": 12, "range": [380000, 420000] },
    "Eng Effort": { "best": 12, "worst": 1, "range": [20, 28] }
  },
  "shared_options": ["SSO Integration"],
  "differentiating_options": ["API v3", "Mobile App v2", "Audit Logging"] }
```

#### `GET /problems/{id}/solutions/tradeoffs`

```
Query params: ?type=overview (default) | ?type=pairwise&a=1&b=5 | ?type=extremes
```

```json
// Response 200 (overview)
{ "frontier_summary": {
    "total_pareto_solutions": 23, "locally_dominant": 8,
    "objective_ranges": { "Revenue Impact": { "min": 280000, "max": 450000 } },
    "key_tradeoffs": [
      { "objectives": ["Revenue Impact", "Eng Effort"], "correlation": -0.72 }
    ] },
  "extreme_solutions": { "best_Revenue_Impact": { "solution_id": 3, "value": 450000 } },
  "balanced_solution": { "solution_id": 8, "method": "min normalized distance to ideal" } }
```

---

### 4.9 Runs (1 endpoint)

#### `GET /problems/{id}/runs`

```
Query params: ?compare=3,4 (diff two runs)
```

```json
// Response 200 (list)
{ "runs": [
    { "run_id": "run_001", "timestamp": "...", "mode": "fast", "approach": "binary",
      "solutions_found": 15, "criteria_snapshot": { "constraints": 1, "filters": 0 } }
] }

// Response 200 (compare)
{ "run_a": "run_003", "run_b": "run_004",
  "criteria_changes": [
    { "criterion": "budget_cap", "change": "value 50 → 40" },
    { "criterion": "must_have_sso", "change": "added as constraint" }
  ],
  "result_changes": { "solutions_delta": "+8",
    "objective_range_changes": { "Revenue Impact": { "before": [250000, 400000], "after": [280000, 450000] } }
} }
```

---

### 4.10 Validation & Export (2 endpoints)

#### `POST /problems/{id}/validate`

```json
// Response 200
{ "ready": false, "completeness": 0.75,
  "missing_scores": [ { "option": "Mobile App v2", "objective": "Tech Debt Risk" } ],
  "issues": [
    { "severity": "warning", "message": "12 missing scores (25% incomplete)" },
    { "severity": "info", "message": "Consider adding cardinality constraint" }
] }
```

#### `GET /problems/{id}/export`

Full problem + results as JSON. Importable back via `POST /problems { import: ... }`.

```json
// Response 200
{ "export_version": "0.1", "exported_at": "...",
  "problem": { ... }, "runs": [ ... ], "solutions": [ ... ] }
```

---

## 5. Criteria System

Criteria are the unified model for all conditions that shape the solution space. They apply at two stages, controlled by the `mode` field:

- **`constraint` mode** — Applied during optimization. Solutions violating constraints are never generated. Prunes the search space for faster, more focused runs.
- **`filter` mode** — Applied when querying solutions via `GET /solutions`. Non-matching solutions are **hidden** (hard exclude, not soft rank). The full Pareto frontier is preserved in storage; filters control what the user sees.

### Why unified?

The only functional difference between modes is *when* the criterion is evaluated. This makes the promote/demote lifecycle clean:

- **Promote (filter → constraint):** "I keep filtering this out. Save the compute and exclude it during optimization."
- **Demote (constraint → filter):** "I want to see what I was missing. Keep the solutions but let me browse the full frontier."

### Criterion types

| target_type | operator | value | Example |
|---|---|---|---|
| `objective` | `min` / `max` / `range` | number or {min, max} | Eng Effort ≤ 40 |
| `option` | `include` / `exclude` | null | Must include SSO |
| `cardinality` | `range` | {min, max} | Select 3-5 options |
| `exclusion` | `exclude_pair` | null | Can't pick both A and B |

### Auto-generated names

Criterion names are optional. If omitted, generated as `{target}_{operator}_{value}`:
- `Eng_Effort_max_40`
- `include_SSO_Integration`
- `cardinality_3_to_6`
- `exclude_pair_Collab_Mobile`

### Interaction with scenarios

Criteria apply to all scenarios uniformly. Scenario-specific criteria are not supported in v1 — if a constraint should only apply in one scenario, model it as a score override instead.

---

## 6. Scenario Engine

Per-scenario optimization answers: "Which portfolio holds up across different futures?"

### How it works

1. Define scenarios with probabilities (must sum to 1.0)
2. Set score overrides per scenario (only changed scores — base matrix applies for the rest)
3. Run `POST /scenarios/optimize` — optimization runs independently per scenario
4. Results include per-scenario Pareto frontiers + probabilistic analysis

### Probabilistic analysis

**Expected value solution:** Probability-weighted average of objective values across scenarios. Best average outcome; accepts risk.

**Robust solution:** Best worst-case across all scenarios (minimax regret). Sacrifices upside for safety.

**Robust options:** Options appearing in the Pareto frontier across all scenarios — "safe bets."

**Scenario-specific options:** Options strong in one scenario but weak in others — "high-reward bets."

---

## 7. Client-Side Skills

Three markdown documents instructing the LLM client how to orchestrate the API. No executable code — purely instructional. Ship alongside the API as files, MCP resources, or system prompt attachments.

---

### Skill 1: Problem Framing

**Scope:** Everything before optimization — defining objectives, options, scores, and initial criteria.

#### Eliciting Good Objectives

Guide users toward objectives that are measurable, concrete, non-overlapping, and genuinely conflicting.

**Probing questions:**
- "What are you trying to achieve?" → extract candidates
- "If you could only optimize one thing, what would it be?" → identify primary
- "What would you have to give up to get more of [primary]?" → surface tradeoffs
- "How would you measure [objective]? What units?" → ensure measurability
- "Are [A] and [B] really different, or do they move together?" → check overlap

**Anti-patterns to catch:**
- Too many objectives (>6): consolidate correlated ones
- Non-conflicting objectives: if two always move together, they're one objective
- Objectives that are really constraints: "budget must be under $100k" is a criterion, not an objective
- Vague objectives: "quality" → "defect rate" or "NPS score" or "test coverage %"

**Determining problem type:**
- "Are you picking a subset or allocating resources?" → binary vs proportional
- "Can you pick just one, or do you need a combination?" → exclusive vs combination binary

#### Translating Fuzzy Data into Scores

**Anchoring and adjusting:** Establish a range ("cheapest to most expensive?"), then place options within that range.

**Relative scoring:** For subjective measures, anchor with extremes on a 1-10 scale, fill others relative.

**Batch estimation:** After establishing anchors, estimate remaining scores transparently. Mark with `confidence: "low"`.

#### Criteria Coaching

**Language signals for mode selection:**
- "Must," "cannot," "absolutely," "non-negotiable" → constraint
- "Prefer," "ideally," "lean toward," "nice to have" → filter
- "Budget is $X" → constraint on sum-aggregated cost objective
- "I want at least 3" → cardinality constraint
- "We can't do both A and B" → exclusion constraint

**Default advice:** Start most criteria as filters. Promote to constraints after exploring.

---

### Skill 2: Optimization & Iteration

**Scope:** Running optimization, interpreting results, scenario design, the iterative refinement loop.

#### Running Optimization

**Mode:** `fast` for early iteration (problem still forming), `thorough` for stable matrix.

**Approach:** `binary` for subset selection (most common), `proportional` for resource allocation.

**Pre-flight:** Call `POST /validate` first. Need ≥2 objectives, ≥3 options, >50% matrix complete.

#### Interpreting Results

- All Pareto solutions are equally valid — different tradeoffs, not better/worse
- "Locally dominant" = optimal in at least one 2D projection — good starting points
- More solutions = more tradeoffs to explore (feature, not bug)
- `hypervolume_normalized` > 0.7 → good coverage; `spacing_cv` < 0.3 → well-distributed
- Few solutions (<5) with thorough mode → constraints likely too tight

#### Scenario Design

**Prompting:** "What are 2-3 futures that would change which option is best?" Not: "What probabilities do you assign?"

**Guidance:** Only override scores that actually change. Start with 2-3 scenarios. Probabilities don't need to be precise. If all options perform similarly across scenarios, scenarios aren't adding insight.

#### The Iteration Loop

**Filter → constraint promotion:**
1. Run with loose constraints
2. Explore with filters
3. Notice recurring filter → promote to constraint
4. Re-run → compare runs to see impact

**Constraint relaxation:** Few solutions → check binding constraints → relax → re-run.

**Score refinement:** Surprising results → check scores → update → re-run → diff.

**Run diffs:** `GET /runs?compare=3,4` shows cause-and-effect.

---

### Skill 3: Frontier Exploration

**Scope:** Navigating Pareto solutions, explaining tradeoffs, helping users converge without prescribing.

#### Core Principles

**Never say "best."** All Pareto solutions are equally valid mathematically.

**Reveal tradeoffs, don't hide them.** Show what's gained and lost with each option.

**Follow the user's interests.** Weight narrative toward what they keep asking about.

#### Exploration Patterns

**Start with the map:** `GET /solutions/tradeoffs?type=overview`. Present key tradeoffs, extremes, balanced.

**Zoom into comparisons:** `GET /solutions/compare?ids=1,5`. Highlight shared vs differentiating options.

**Use extremes as anchors:** "Here's full cost optimization. Here's full revenue. Everything else is a blend."

**Preference-responsive ranking:** When user expresses preference, sort accordingly but always show the sacrifice.

#### Criteria Feedback Loop

Notice filtering patterns during exploration:
- User repeatedly filters by same criterion → suggest promoting
- User always prefers solutions with specific option → suggest force-include
- User avoids high values on one objective → suggest ceiling constraint

#### Convergence Signals

- Comparing only 2-3 solutions → close to deciding
- Shift to "what would make you choose A over B?"
- Offer to export or create a chained problem for the next decision

#### Presenting Scenario Results

1. Robust options first — "strong picks regardless"
2. Scenario-specific opportunities — "if X happens, adding Y becomes valuable"
3. Frame around risk tolerance — "optimizing for expected case or protecting against downside?"

---

## 8. MCP Server

Optional wrapper over REST API for LLM clients (Claude Desktop, Claude Code). 11 compound tools with `action` parameters covering all 24 endpoints.

| MCP Tool | Actions | REST Endpoints |
|---|---|---|
| `manage_problem` | create, update, delete, list, get, import | POST/PUT/DELETE/GET `/problems` |
| `manage_objectives` | add, update, delete | POST/PUT/DELETE `/objectives` |
| `manage_options` | add, delete | POST/DELETE `/options` |
| `set_scores` | (multi-format) | PUT `/scores` |
| `manage_criteria` | get, set, update, promote, demote | GET/PUT/PATCH `/criteria` |
| `manage_scenarios` | configure, set_scores, get_results | PUT/GET `/scenarios/*` |
| `optimize` | run, run_scenarios | POST `/optimize`, `/scenarios/optimize` |
| `explore_solutions` | list, compare, tradeoffs | GET `/solutions*` |
| `get_runs` | list, compare | GET `/runs` |
| `validate` | (single) | POST `/validate` |
| `export` | (single) | GET `/export` |

### MCP Resources

| URI | Content |
|---|---|
| `frontier://skills/problem-framing` | Skill 1 |
| `frontier://skills/optimization-iteration` | Skill 2 |
| `frontier://skills/frontier-exploration` | Skill 3 |

### MCP Prompts

| Name | Description |
|---|---|
| `new_decision` | Start new decision with Problem Framing skill |
| `resume_problem` | Resume existing problem with stage-appropriate skill |
| `explore_tradeoffs` | Focused tradeoff exploration session |

---

## 9. Workflow Scenarios

These show how the user + agent interact across the API and skills.

### Scenario 1: New Problem from Scratch

1. **User:** "I need to figure out which features to build next quarter."
2. **Agent** (Framing skill): Asks about team size, timeline, context. Creates problem: `POST /problems`.
3. **Agent:** Probes for objectives until 3-5 conflicting ones emerge. `POST /objectives` batch.
4. **Agent:** Lists candidate features. `POST /options` batch.
5. **Agent:** Elicits scores via anchoring. `PUT /scores` incrementally.
6. **Agent:** At ~60% complete, suggests fast run for early signal.
7. **Agent:** `POST /validate` → `POST /optimize { mode: "fast" }`. Presents frontier overview.

### Scenario 2: Adding Scenarios to Existing Problem

1. **User:** "What if our biggest customer churns?"
2. **Agent** (Optimization skill): Probes for 2-3 futures. `PUT /scenarios/config`.
3. **Agent:** Identifies which scores shift per scenario. `PUT /scenarios/{name}/scores` with overrides.
4. **Agent:** `POST /scenarios/optimize`. Presents robust vs scenario-specific options.

### Scenario 3: Iterating via Constraints and Filters

1. **User:** "We can only do 4-5 features." → Agent adds cardinality constraint, re-runs.
2. **User:** "We need SSO." → Agent adds force-include constraint, re-runs.
3. **User:** "Prefer under 30 eng-weeks." → Agent adds filter (not constraint).
4. **User:** "Actually, 30 is a hard limit." → Agent promotes filter → constraint, re-runs.
5. **Agent:** Uses `GET /runs?compare` to explain what changed. User converges.

### Scenario 4: Chaining Problems

1. User completes feature prioritization. Selects features A-D.
2. Agent creates new problem: "Staff the Q3 features." New objectives: utilization, skill coverage, risk.
3. Prior problem's output (effort estimates) informs new problem's scoring.

### Scenario 5: Updating a Past Problem

1. **User:** "Vendor C dropped their price. Also there's a new vendor."
2. **Agent:** `PUT /scores` with new price. `POST /options` for new vendor. Scores new vendor.
3. **Agent:** Reviews criteria: "Still $50k budget?" User updates. Re-runs.
4. **Agent:** `GET /runs?compare` shows impact of changes.

### Scenario 6: User Doesn't Know What to Decide

1. **User:** "Our data infrastructure is a mess."
2. **Agent** (Framing skill): Asks structuring questions. Doesn't create problem prematurely.
3. Eventually frames as prioritization: "Pick top N fixes given business impact, effort, and risk."

### Scenario 7: Assessing Data Gaps

1. **Agent:** `POST /validate` → "60% complete. Biggest gap: Tech Debt Risk."
2. **Agent:** Triages: "These gaps are most likely to affect results."
3. **Agent:** Offers estimation via anchoring. Marks as `confidence: "low"`.
4. **Agent:** "Run fast to see if estimates matter? If not, don't bother refining."

### Scenario 8: Converging on Optimal Set

1. **User:** "I need the final 5 features today."
2. **Agent:** Thorough optimize. Identifies clusters: revenue-max vs balanced.
3. Progressive constraints narrow to 4-6 finalists. Compare endpoint shows specifics.
4. User picks. Agent confirms and offers export.

### Scenario 9: Divergent Exploration

1. **User:** "Show me the full range. I'm bringing options to leadership."
2. **Agent:** Full frontier, no filters. Categorizes into clusters.
3. Pulls representative from each cluster + outlier for presentation.

### Scenario 10: Partial Data, Best Assumptions

1. **Agent:** Enters known data (high confidence), rough guesses (medium), estimates (low).
2. **Agent:** `POST /validate` shows confidence landscape.
3. **Agent:** Runs optimization. "Vendor D appears in most solutions despite low-confidence scores — worth getting better data there specifically."

---

## 10. Implementation Phases & Checkpoints

Each phase has deliverables and a testing checkpoint that validates the phase end-to-end before proceeding.

---

### Phase 1: Engine Core

**Goal:** Core computation layer — pure Python, no API, no AI.

**Deliverables:**
- [ ] Problem store with JSON persistence + abstract store interface
- [ ] Criteria system (unified, auto-named, constraint + filter modes)
- [ ] Optimization core (binary + proportional, NSGA-II/III/MOEA-D routing)
- [ ] Hard validation (numeric, feasibility, infeasibility detection)
- [ ] Exploration core (compare, tradeoffs, balanced/extreme, filter application)
- [ ] Run archival (current in problem file, previous in separate files)

**Checkpoint — "Engine smoke test":**

```python
store = ProblemStore("./data")
problem = store.create("Q3 Feature Prioritization", context="10-person team")

problem.add_objectives([...])  # 4 objectives
problem.add_options([...])     # 12 options
problem.set_scores([...])      # full matrix

problem.set_criteria([
    Criterion(target_type="cardinality", operator="range", value={"min": 3, "max": 5}, mode="constraint"),
    Criterion(target_type="option", target="SSO", operator="include", mode="constraint"),
    Criterion(target_type="objective", target="Eng Effort", operator="max", value=30, mode="filter"),
])

assert problem.validate()["ready"] == True

run = problem.optimize(mode="fast", approach="binary")
assert run.solutions_found > 0

solutions = problem.get_solutions()  # filter applied
assert all(s.objective_values["Eng Effort"] <= 30 for s in solutions)

tradeoffs = problem.get_tradeoffs()
assert "key_tradeoffs" in tradeoffs

comparison = problem.compare_solutions([1, 3, 5])
assert "shared_options" in comparison

problem.update_criterion("Eng_Effort_max_30", mode="constraint")
run2 = problem.optimize(mode="fast", approach="binary")
diff = problem.compare_runs(run.run_id, run2.run_id)
assert "criteria_changes" in diff
```

**Pass:** Runs without errors. Valid Pareto solutions. Filters hide correctly. Run diff shows promoted criterion.

---

### Phase 2: REST API

**Goal:** FastAPI wrapping all 24 endpoints.

**Deliverables:**
- [ ] FastAPI app with Pydantic models
- [ ] All 24 endpoints wired to engine
- [ ] `results_stale` tracking
- [ ] Structured error responses with suggestions
- [ ] Infeasibility response (no fallbacks)
- [ ] pytest suite (happy paths + error cases)

**Checkpoint — "API walkthrough":**

```bash
POST /problems → problem_id
POST /problems/{id}/objectives  (batch)
POST /problems/{id}/options     (batch)
PUT  /problems/{id}/scores      (batch)
POST /problems/{id}/validate    → { ready: true }
POST /problems/{id}/optimize    → { solutions_found: N }
GET  /problems/{id}/solutions   → solutions list
GET  /problems/{id}/solutions/tradeoffs → frontier summary
GET  /problems/{id}/solutions/compare?ids=1,3,5 → comparison
PUT  /problems/{id}/criteria    → add filter
GET  /problems/{id}/solutions   → fewer solutions (filtered)
PATCH /problems/{id}/criteria/{name} → promote to constraint
POST /problems/{id}/optimize    → new run
GET  /problems/{id}/runs?compare=1,2 → criteria diff
GET  /problems/{id}/export      → full JSON importable via POST /problems
```

**Pass:** Correct HTTP codes. Validation catches gaps. Filters hide. Run diff shows promotion. Export round-trips.

---

### Phase 3: Skills & MCP

**Goal:** Three skill docs + MCP server. End-to-end via LLM client.

**Deliverables:**
- [ ] Skill 1: Problem Framing
- [ ] Skill 2: Optimization & Iteration
- [ ] Skill 3: Frontier Exploration
- [ ] MCP server (11 compound tools)
- [ ] Skills as MCP resources
- [ ] 3 MCP prompt templates

**Checkpoint — "First real decision via Claude":**

Test problem: *"Pick 5 of 15 product features for next quarter given revenue impact, eng effort, tech debt risk, and user satisfaction."*

Through natural conversation:
- [ ] Claude uses Framing skill (probes for conflicts, units)
- [ ] Claude translates rough descriptions → scores via anchoring
- [ ] Claude validates before optimizing
- [ ] Claude presents frontier without saying "best"
- [ ] User adds cardinality constraint conversationally → Claude creates criterion
- [ ] User says "prefer low debt" → Claude creates filter (not constraint)
- [ ] Claude suggests promoting filter after repeated use
- [ ] Claude re-runs and uses run diff to explain changes
- [ ] User converges on a selection

**Pass:** Complete workflow via conversation. No direct API calls needed. Skills used at appropriate stages.

---

### Phase 4: Scenarios

**Goal:** Multi-scenario support with probabilistic analysis.

**Deliverables:**
- [ ] Scenario engine (per-scenario optimization, score overrides)
- [ ] Probabilistic analysis (expected value, robust, option categorization)
- [ ] 3 scenario API endpoints
- [ ] Skills 2 + 3 updated with scenario guidance

**Checkpoint — "Scenario stress test":**

Extend Phase 3 test problem:
- [ ] User triggers scenario exploration ("What if we lose our biggest customer?")
- [ ] Claude sets up 3 scenarios, identifies which scores change
- [ ] Claude runs scenario optimization
- [ ] Claude presents robust vs scenario-specific options
- [ ] Claude frames choice around risk tolerance
- [ ] User can compare scenario frontiers

**Pass:** Different frontiers per scenario. Robust options correctly identified. No statistical jargon.

---

### Phase 5: Dogfooding & Iteration

**Goal:** Real decisions. Friction identification. Iteration.

**Deliverables:**
- [ ] 3+ real decisions completed
- [ ] Friction log documented
- [ ] Skill and API iterations based on findings
- [ ] Blog post with worked example

**Checkpoint — three problem types:**

**Test A — Feature prioritization (binary):** "Pick 5 of 20 features" with real data.

**Test B — Resource allocation (proportional):** "Allocate budget across 8 channels."

**Test C — Vendor selection with scenarios (binary + scenarios):** "Select 3 cloud providers under growth/contraction."

**Pass for each:** User reaches better-informed decision than spreadsheet/LLM alone. Frontier revealed ≥1 unexpected tradeoff. Iteration loop used ≥1 time.

---

## 11. Design Decisions Log

| Decision | Resolution | Rationale |
|---|---|---|
| Criteria model | Unified constraints + filters with `mode` field | Elegant promote/demote; both hard-hide; exclusions/cardinality fit as target_type variants |
| Filter semantics | Hard exclude (not rank) | Simpler; constraint vs filter is about *when*, not *how much* |
| Criteria on aggregated values | Always post-optimization aggregated value | Per-option thresholds handled via include/exclude; avoids ambiguity |
| Criteria naming | Optional, auto-generated from target+operator | Users rarely name criteria; auto-names are descriptive |
| Allocation unit | Integer percentages (0-100) | Proven, user-interpretable; revisit if >50 options cause granularity issues |
| Storage | JSON files + abstract interface | Simplest for solo dogfooding; swappable to SQLite/Postgres |
| Run storage | Full frontier for latest + archived separate files | Problem file bounded; full history accessible on demand |
| MCP tools | 11 compound tools | Under 15-tool guideline; natural groupings reduce selection errors |
| Problem lifecycle | Full CRUD (create, read, update, delete) | Problems evolve for scenarios, sequences, new data |
| Validation | Engine-side hard checks before optimization | Catches NaN/null/conflicts; no wasted compute |
| Infeasibility | Explicit `{ feasible: false }` + suggestions | No misleading fallback solutions |
| Results staleness | `results_stale` flag on structural changes | Engine doesn't auto-clear; signals may not reflect current data |
| Scenario overrides | Base matrix + per-scenario overrides (changed scores only) | Efficient, highlights differences; export materializes full matrices |
| Score confidence | Metadata only (not used by optimizer) | Useful for user/LLM; optimizer weighting adds complexity with unclear calibration |

---

## 12. Open Questions

Non-blocking. Worth tracking and revisiting during dogfooding.

**Proportional mode edge cases.** Per-option allocation bounds map awkwardly to the criteria model (structurally different from objective thresholds). Proportional + cardinality interactions need validation (if min allocation is 5%, max options is 20). Monitor during Phase 5.

**Exploration endpoints.** "Rank by weighted objectives" (`?sort_by_weights=`) and "find similar solutions" are useful but can be computed client-side. Add as query params in Phase 5 if LLM-side computation proves unreliable.

**Export schema versioning.** Import via `POST /problems` needs a `schema_version` field for forward compatibility. Add before Phase 5.

**Cross-run solution tracking.** `content_signature` enables "Solution A from run 3 persists in run 4." Useful for iteration UX but no endpoint explicitly surfaces this yet. Add to `GET /runs?compare` if needed.

**Naming.** "Frontier" is strong but overloaded in tech. The tagline does positioning. Low priority.

**Score validation ranges.** Engine doesn't know "score 1-10" means a score of -1 is invalid. Purely a skill/LLM concern for v1; could add optional `valid_range` to Objective model later.

**Solution annotation.** Users will want to name/tag solutions ("the conservative pick"). Could be `PATCH /solutions/{id}` or client-side. Defer to Phase 5.

**Undo/revert.** Run snapshots partially handle this for optimization results. Problem definition changes aren't versioned. True undo requires event sourcing — defer indefinitely.

**Explicitly out of scope for v1:** Standalone UI, timestep/NPV scoring, decision log/commitment tracking, data collection agents, user auth/multi-tenancy, webhooks, collaborative editing, problem templates.

---

*© 2026 Cameron Afzal. All Rights Reserved.*

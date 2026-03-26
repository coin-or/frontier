# Frontier

Multi-objective portfolio optimization engine for decisions too combinatorial for intuition.

Frontier finds Pareto-optimal portfolios for "pick K of N" selection problems with 2-6 conflicting objectives. It pairs with an LLM client via MCP: Frontier does the computation, the LLM does the conversation. The engine has zero AI dependencies.

## When to use Frontier

| Too Simple | Sweet Spot | Too Complex |
|---|---|---|
| Single-objective ranking | "Pick 5 of 20 features given revenue, effort, risk, satisfaction" | Simulation-driven optimization |
| Pros/cons lists | "Allocate budget across 12 channels given ROI, awareness, CAC" | Sequential multi-stage decisions |
| Weighted scoring | "Select 3 of 10 vendors given cost, integration, capability, lock-in" | Real-time continuous optimization |

Problems with 5-40 options, 2-6 conflicting objectives, and a solution space too large for intuition.

## Setup

### Prerequisites

- Python 3.11+
- pip

### Install locally

```bash
git clone https://github.com/cafzal/frontier.git
cd frontier
pip install -r requirements.txt
```

### Connect to Claude Code

If using the hosted deployment:

```bash
claude mcp add frontier --transport sse --url https://frontier-592q.onrender.com/sse
```

Or run locally:

```bash
claude mcp add frontier --transport sse --url http://localhost:8080/sse
```

Start the local server with:

```bash
MCP_TRANSPORT=sse PORT=8080 python -m frontier.mcp_server.server
```

### Connect to Claude Desktop

Add to your Claude Desktop config file:

- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "frontier": {
      "transport": "sse",
      "url": "https://frontier-592q.onrender.com/sse"
    }
  }
}
```

Restart Claude Desktop after saving.

## Workflow

Frontier uses three tools that map to the natural decision-making workflow:

```
model  →  solve  →  explore  →  refine (loop back to model)
```

Each tool represents an activity: building the problem, computing the frontier, understanding the results. A typical session moves through all three, then loops back to refine.

### Phase 1: Frame the problem (`model`)

Start by creating a problem and defining what you're deciding.

**Create the problem:**
```
model create  name="Q3 Feature Prioritization"  domain="Product"  context="Pick features for beta"
→ { problem_id: "abc-123", ... }
```

**Add objectives, options, and constraints in one update:**
```
model update  problem_id="abc-123"
  objectives=[
    { name: "Revenue Impact",     direction: "maximize", unit: "1-10" },
    { name: "Eng Effort",         direction: "minimize", unit: "days" },
    { name: "User Satisfaction",   direction: "maximize", unit: "1-10" }
  ]
  options=[
    { name: "Real-time Collaboration" },
    { name: "Analytics Dashboard" },
    { name: "AI Content Generation" },
    ...
  ]
  constraints=[
    { type: "cardinality", min: 3, max: 5 },
    { type: "force_include", option: "SSO Integration" }
  ]
→ { status: { objectives: 3, options: 10, scores_complete: 0.0 }, metrics: { framing: {...} } }
```

The response includes framing metrics so the LLM can validate the problem structure before moving on.

**Objectives** — what you're optimizing. Each needs a name, direction (`maximize`/`minimize`), and unit. 2-6 objectives is the sweet spot.

**Options** — what you're choosing between. 5-40 is the sweet spot.

**Constraints** — hard limits on the solution space:

| Type | What it does | Format |
|---|---|---|
| `cardinality` | Pick between N and M items | `{ type: "cardinality", min: 3, max: 5 }` |
| `force_include` | Solution must contain this option | `{ type: "force_include", option: "SSO" }` |
| `force_exclude` | Solution cannot contain this option | `{ type: "force_exclude", option: "Mobile" }` |
| `objective_bound` | Cap a total objective value | `{ type: "objective_bound", objective: "Effort", operator: "max", value: 40 }` |

### Phase 2: Score the options (`model update` with scores)

Rate every option on every objective. Send scores in batches — the tool uses merge semantics (upsert by option+objective), so you can build the matrix incrementally across 1-3 calls.

```
model update  problem_id="abc-123"
  scores=[
    { option: "Real-time Collaboration", objective: "Revenue Impact",    value: 9 },
    { option: "Real-time Collaboration", objective: "Eng Effort",        value: 21 },
    { option: "Real-time Collaboration", objective: "User Satisfaction",  value: 9 },
    { option: "Analytics Dashboard",     objective: "Revenue Impact",    value: 8 },
    ...all 30 scores in one call...
  ]
→ { status: { scores_complete: 1.0 }, metrics: { data: { dominated_options: ["Mobile App"], ... } } }
```

The response includes data metrics: score completeness, variance per objective, and dominated options (options that are worse on every objective — worth flagging to the user).

The score matrix must be 100% complete before solving.

### Phase 3: Solve (`solve`)

Validate the problem and run the NSGA-II optimizer.

```
solve run  problem_id="abc-123"
→ {
    solutions_found: 22,
    quality: { hypervolume_normalized: 0.567, spacing_cv: 0.457 },
    solutions: [
      { solution_id: 0, selected_options: ["Collab", "Analytics", "AI", "Workflow", "SSO"],
        objective_values: { "Revenue Impact": 39, "Eng Effort": 87, "User Satisfaction": 39 } },
      ...
    ],
    metrics: { solve: {...}, diagnostics: [...] }
  }
```

Every returned solution is Pareto-optimal — no solution dominates another. All solutions respect constraints.

If the problem isn't ready, `solve validate` returns specific issues and missing scores. If constraints are contradictory, it returns `feasible: false` with binding constraints and suggestions for what to relax.

### Phase 4: Explore results (`explore`)

Navigate the Pareto frontier to understand what you're choosing between.

**Start with the tradeoff overview:**
```
explore tradeoffs  problem_id="abc-123"
→ {
    total_solutions: 22,
    objective_ranges: { "Revenue Impact": { min: 17, max: 39 }, ... },
    key_tradeoffs: [ { objectives: ["Revenue", "Effort"], correlation: 0.92 } ],
    extreme_solutions: { "best_Revenue Impact": { solution_id: 0, value: 39, ... }, ... },
    balanced_solution: { solution_id: 10, selected_options: [...], ... }
  }
```

This gives you the shape of the frontier: what's achievable, what trades off against what, and which solutions represent the extremes and the balanced middle.

**Compare specific solutions side-by-side:**
```
explore compare  problem_id="abc-123"  solution_ids=[0, 10]
→ {
    shared_options: ["SSO Integration", "Workflow Automation"],
    differentiating_options: ["AI Content Generation", "Template Library", ...],
    tradeoff_summary: { "Revenue Impact": { best: 0, worst: 10, range: [28, 39] }, ... }
  }
```

Focus on differentiating options — what's different between solutions matters more than what's shared.

**Get a single solution's detail:**
```
explore solution  problem_id="abc-123"  solution_id=0
→ { selected_options: [...], objective_values: {...}, ... }
```

**Record feedback when the user gravitates toward a choice:**
```
explore feedback  problem_id="abc-123"  solution_id=3  rating=4  notes="Good balance"  stage="decision"
→ { recorded: true, feedback_count: 1, outcome: { user_selected_solution: 3, user_rating: 4 } }
```

### Phase 5: Refine and re-solve

When the user wants to adjust — "what if effort must be under 30 days?" — update constraints and re-solve.

```
model update  problem_id="abc-123"
  constraints=[
    { type: "cardinality", min: 3, max: 5 },
    { type: "force_include", option: "SSO Integration" },
    { type: "objective_bound", objective: "Eng Effort", operator: "max", value: 30 }
  ]
→ { status: { has_run: false }, ... }    ← run auto-cleared
```

```
solve run  problem_id="abc-123"
→ { solutions_found: 2, ... }           ← frontier narrowed from 22 to 2
```

```
explore tradeoffs  problem_id="abc-123"
→ new balanced solution reflecting tighter constraints
```

This loop — frame → score → solve → explore → refine — is the core interaction pattern. Each iteration sharpens the decision.

**Other `model` actions:**
```
model get     — Full problem state (objectives, options, scores, constraints, solutions)
model list    — All problems with summary status
model delete  — Remove a problem
```

## Skills (MCP resources)

Frontier includes four expert skill resources that Claude loads at different workflow phases. Each contains domain expertise for that phase — the guidance lives in the skills themselves, not here.

| Skill | Expert role | When to load |
|---|---|---|
| `frontier://skills/problem_framing` | Decision analyst | Before framing — validates objectives, checks scope |
| `frontier://skills/data_collection` | Researcher | During scoring — anchoring, batching, uncertainty |
| `frontier://skills/optimization_strategy` | Operations researcher | Before/after solving — approach fit, constraint strategy |
| `frontier://skills/solution_interpreter` | Advisor | During exploration — tradeoff framing, preference elicitation |

These are served as MCP resources and are automatically available when the server is connected. See `CLAUDE.md` for instructions on activating them.

## Reference

See [reference.md](reference.md) for deployment (Render, local), architecture, testing, and development details.

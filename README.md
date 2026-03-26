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
model  →  solve  →  explore
  │          │          │
  │          │          └── understand results, compare, iterate
  │          └── validate constraints, run optimizer
  └── define objectives, options, scores, constraints
```

### 1. Model — frame the problem

```
model create  — Start a new problem (name, domain, context)
model update  — Add objectives, options, scores, constraints
model get     — View full problem state
model list    — List all problems
model delete  — Remove a problem
```

**Objectives** define what you're optimizing (direction + unit):
```json
{"name": "Revenue Impact", "direction": "maximize", "unit": "1-10"}
{"name": "Eng Effort", "direction": "minimize", "unit": "days"}
```

**Options** are the things you're choosing between:
```json
{"name": "Real-time Collaboration", "description": "Multiple users editing simultaneously"}
```

**Scores** rate each option on each objective (sent in batches, merge semantics):
```json
{"option": "Real-time Collaboration", "objective": "Revenue Impact", "value": 9}
```

**Constraints** shape the feasible space:

| Type | Example | Format |
|---|---|---|
| `cardinality` | Pick 3-5 items | `{"type": "cardinality", "min": 3, "max": 5}` |
| `force_include` | Must have SSO | `{"type": "force_include", "option": "SSO"}` |
| `force_exclude` | Can't do Mobile | `{"type": "force_exclude", "option": "Mobile"}` |
| `objective_bound` | Effort ≤ 40 days | `{"type": "objective_bound", "objective": "Effort", "operator": "max", "value": 40}` |

### 2. Solve — run the optimizer

```
solve validate  — Check if the problem is ready (≥2 objectives, ≥3 options, 100% scores)
solve run       — Validate + optimize. Returns full Pareto frontier.
```

Returns solution count, quality metrics (hypervolume, spacing), and all Pareto-optimal solutions. If infeasible, returns binding constraints and suggestions.

### 3. Explore — navigate results

```
explore tradeoffs   — Frontier overview: ranges, correlations, extremes, balanced solution
explore compare     — Side-by-side comparison of 2+ solutions (shared vs differentiating options)
explore solutions   — Full Pareto frontier listing
explore solution    — Single solution detail
explore feedback    — Record user rating/notes on a solution
```

## Iteration pattern

The typical flow involves refinement cycles:

1. Frame → Score → Solve → Explore tradeoffs
2. User says "effort must be under 30 days" → add `objective_bound` constraint
3. Re-solve → frontier narrows → explore new tradeoffs
4. User gravitates toward a solution → record feedback

Changing objectives, options, scores, or constraints automatically clears the previous run.

## Skills (MCP resources)

Frontier includes four expert skill resources that Claude loads at different workflow phases:

| Skill | Expertise | When |
|---|---|---|
| `problem_framing` | Objective vs constraint distinction, completeness, scope | Before building the problem |
| `data_collection` | Anchoring technique, batch scoring, uncertainty handling | During score entry |
| `optimization_strategy` | Approach selection, constraint strategy, infeasibility response | Before/after solving |
| `solution_interpreter` | Tradeoff framing, differentiation, never say "best" | During exploration |

These are served as MCP resources at `frontier://skills/{name}` and are automatically available when the server is connected.

## Deployment

### Render

The repo includes `render.yaml` for one-click deployment:

| Setting | Value |
|---|---|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `MCP_TRANSPORT=sse python -m frontier.mcp_server.server` |
| **Env Var** | `PYTHON_VERSION=3.11` |

Render sets `PORT` automatically. The server binds to `0.0.0.0:$PORT`.

### Run locally

```bash
# stdio mode (default, for direct MCP client piping)
python -m frontier.mcp_server.server

# SSE mode (for network clients)
MCP_TRANSPORT=sse PORT=8080 python -m frontier.mcp_server.server
```

## Tests

```bash
# Eval checkpoint (full end-to-end workflow)
python -m tests.eval_checkpoint

# Unit tests
pip install pytest
pytest tests/ -v
```

## Architecture

```
frontier/
├── engine/
│   ├── models.py        # Pydantic data models
│   ├── store.py          # JSON file store (one file per problem)
│   ├── optimizer.py      # NSGA-II via pymoo, validation, infeasibility analysis
│   ├── explorer.py       # Tradeoff analysis, solution comparison
│   └── metrics.py        # Automated quality metrics (framing, data, solve, outcome)
├── mcp_server/
│   └── server.py         # 3 MCP tools: model, solve, explore
├── skills/               # 4 expert skill resources (markdown)
└── tests/
    ├── fixtures/         # 3 example problems (SaaS, Marketing, Investment)
    └── eval_checkpoint.py
```

# Frontier Reference

Development, deployment, and architecture details.

## Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# stdio mode (default, for direct MCP client piping)
python -m frontier.mcp_server.server

# SSE mode (for network clients)
MCP_TRANSPORT=sse PORT=8080 python -m frontier.mcp_server.server
```

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

Current deployment: `https://frontier-592q.onrender.com/sse`

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `MCP_TRANSPORT` | Transport protocol (`stdio` or `sse`) | `stdio` |
| `PORT` | Port for SSE mode (set by Render) | `8000` |
| `PYTHON_VERSION` | Python runtime version (Render) | — |

## Tests

```bash
# Eval checkpoint — full end-to-end workflow (model → score → solve → explore → refine)
python -m tests.eval_checkpoint

# Unit tests
pip install pytest
pytest tests/ -v
```

### Example fixtures

Three pre-built problems in `tests/fixtures/` for testing and demos:

| Fixture | Objectives | Options | Constraints |
|---|---|---|---|
| `saas_feature_prioritization.json` | 5 (User Value, Dev Days, Tech Risk, Revenue, Differentiation) | 12 features | Cardinality 4-6, dev days ≤ 90 |
| `marketing_channel_mix.json` | 6 (CAC, Reach, Conversion, Setup Time, Brand, Attribution) | 14 channels | Cardinality 4-6, force Email, setup ≤ 60 days |
| `investment_portfolio.json` | 6 (Return, Risk, Expense Ratio, Liquidity, Tax, Inflation) | 14 ETFs | Cardinality 4-7, force VOO |

## Architecture

```
frontier/
├── engine/
│   ├── models.py        # Pydantic data models (Problem, Objective, Option, Score, Constraint, Run, Solution)
│   ├── store.py          # JSON file store — one file per problem in ./data/
│   ├── optimizer.py      # NSGA-II via pymoo — validation, optimization, infeasibility analysis
│   ├── explorer.py       # Tradeoff analysis, solution comparison, balanced/extreme identification
│   └── metrics.py        # Automated quality metrics (framing, data, solve, outcome, diagnostics)
├── mcp_server/
│   └── server.py         # MCP server — 3 tools (model, solve, explore) + 4 skill resources
├── skills/               # Expert skill resources served as MCP resources
│   ├── problem_framing.md
│   ├── data_collection.md
│   ├── optimization_strategy.md
│   └── solution_interpreter.md
├── tests/
│   ├── fixtures/         # 3 example problems
│   └── eval_checkpoint.py
├── designs/
│   ├── phase0_mvp.md     # Current implementation spec
│   └── frontier_design_doc_v1.md  # Full design document
├── requirements.txt
├── render.yaml           # Render deployment blueprint
└── pyproject.toml
```

### Engine components

**Store** — CRUD for problems. JSON file per problem. Data lives in `./data/` (gitignored). Ephemeral on Render free tier.

**Optimizer** — Wraps pymoo NSGA-II. Binary decision variables (0/1 per option). Auto-scales population size and generations based on problem dimensions. Returns Pareto-optimal solutions or structured infeasibility diagnosis.

**Explorer** — Computes tradeoff analysis from the Pareto frontier: objective ranges, correlations, extreme solutions (best per objective), balanced solution (min normalized distance to ideal). Comparison highlights shared vs differentiating options.

**Metrics** — Deterministic health signals included in tool responses at natural checkpoints. Framing metrics on structural changes, data metrics on score updates, solve/diagnostics metrics after optimization, outcome metrics on feedback.

### Data model

```
Problem
├── problem_id: string (uuid)
├── name, domain, context: string
├── objectives: Objective[] — { name, direction, unit }
├── options: Option[] — { name, description? }
├── scores: Score[] — { option, objective, value }
├── constraints: Constraint[] — cardinality | force_include | force_exclude | objective_bound
├── run: Run | null — latest optimization result
├── feedback: Feedback[] — user ratings and notes
├── created_at, updated_at: datetime
```

### Dependencies

```
python >= 3.11
pymoo >= 0.6        # NSGA-II multi-objective optimizer
pydantic >= 2.0     # Data models + validation
mcp[cli] >= 1.0     # MCP server SDK (FastMCP)
scipy >= 1.11       # Scientific computing (used by pymoo)
uvicorn >= 0.30     # ASGI server for SSE transport
```

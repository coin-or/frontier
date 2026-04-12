# Frontier: Extensible Architecture Plan

## Context

Frontier is a multi-objective optimization engine with strong domain expertise encoded in 4 skill files (~800 lines of workflow guidance). Currently it's locked to Claude Code users because skills are delivered as MCP resources (which only Claude Code reads reliably), storage is ephemeral JSON files on Render, and there's no auth or multi-tenancy. The goal is to make Frontier accessible to any LLM client user (Claude Desktop, claude.ai, other MCP hosts) with persistent, user-scoped state — without losing the workflow quality that differentiates it.

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│  LLM Clients (Claude Code, Desktop, claude.ai, etc.)  │
└──────────────────┬──────────────────────────┘
                   │ MCP (SSE or stdio)
┌──────────────────▼──────────────────────────┐
│  Protocol Layer (FastMCP)                    │
│  - 3 tools: model, solve, explore           │
│  - 1 new tool: get_skill                    │
│  - 4 resources (backward compat)            │
│  - Auth middleware (SSE only)               │
│  - Server instructions → get_skill guidance │
├─────────────────────────────────────────────┤
│  Store Layer (StoreBackend protocol)         │
│  - JsonFileStore (local dev/tests)          │
│  - PostgresStore (production)               │
│  - User-scoped by owner field               │
├─────────────────────────────────────────────┤
│  Engine Layer (unchanged)                    │
│  - optimizer.py, explorer.py, metrics.py    │
│  - models.py (+ owner field)               │
│  - Pure computation, no protocol awareness  │
└─────────────────────────────────────────────┘
```

---

## Phase 1: Multi-Client Skill Delivery (do now)

**Goal:** Make Frontier usable from any MCP client without losing workflow guidance.

**The Problem:** Skills are served as MCP resources (`frontier://skills/*`). Claude Desktop and claude.ai don't reliably read MCP resources. Without skills, the agent just calls tools mechanically — the guided decision workflow is lost.

**Solution: Hybrid skill delivery**

### 1a. Add `get_skill` tool

New tool in `server.py` that returns skill content on demand:

```python
@mcp.tool()
def get_skill(skill_name: str) -> str:
    """Retrieve workflow guidance for a specific stage.

    Available skills:
    - problem_framing — call before model/create
    - data_collection — call before entering scores
    - optimization_strategy — call before solve/run
    - solution_interpreter — call before presenting results

    Returns the full skill guide as markdown.
    """
    mapping = {
        "problem_framing": "problem-framing",
        "data_collection": "data-collection",
        "optimization_strategy": "optimization-strategy",
        "solution_interpreter": "solution-interpreter",
    }
    dirname = mapping.get(skill_name)
    if not dirname:
        return f"Unknown skill: {skill_name}. Available: {list(mapping.keys())}"
    path = SKILLS_DIR / dirname / "SKILL.md"
    return path.read_text()
```

This works with **every** MCP client — it's just a tool call that returns text.

### 1b. Expand tool descriptions with compact guidance

Add ~200-word guidance summaries to each tool's docstring so that even without calling `get_skill`, the agent has minimum viable workflow awareness. The full skill remains available via `get_skill` for deeper guidance.

Example for `model` tool docstring addition:
```
Key guidance (call get_skill('problem_framing') for full guide):
- Objectives: 2-4 is sweet spot. If >4, look for consolidation.
- Ask "does quantity matter?" to choose binary vs proportional.
- Classify carefully: "budget" might be an objective OR constraint.
- Hidden objectives surface through hedging language.
- First formulation is a hypothesis — rough scores > no scores.
```

### 1c. Update server instructions

```python
instructions=(
    "Multi-objective portfolio optimization engine.\n\n"
    "WORKFLOW: model → solve → explore\n\n"
    "IMPORTANT: Call get_skill() before each stage for guidance:\n"
    "  get_skill('problem_framing') — before model/create\n"
    "  get_skill('data_collection') — before entering scores\n"
    "  get_skill('optimization_strategy') — before solve/run\n"
    "  get_skill('solution_interpreter') — before presenting results\n\n"
    "Skills contain domain expertise that drives workflow quality. "
    "Do not skip them."
)
```

### 1d. Keep existing `@mcp.resource()` decorators

Backward compatible. Claude Code users still get resources if their client reads them. No removal needed.

**Files changed:**
- `frontier/mcp_server/server.py` — add `get_skill` tool, expand 3 tool docstrings, update instructions
- No engine changes, no infrastructure changes

**Verification:**
- Connect from Claude Desktop via SSE — confirm `get_skill` is callable and returns skill content
- Connect from Claude Code — confirm resources still work alongside the new tool
- Run existing tests (`pytest tests/test_server.py`) — confirm no regressions

---

## Phase 2: Persistent Storage + Multi-Tenancy (next)

**Goal:** Durable, user-scoped state that survives Render deploys and supports multiple users.

### 2a. Store backend protocol

Refactor `Store` into a protocol with pluggable backends:

```python
# frontier/engine/store.py

class StoreBackend(Protocol):
    def save(self, problem: Problem) -> None: ...
    def load(self, problem_id: str, owner: str = "") -> Problem: ...
    def list(self, owner: str = "") -> list[dict]: ...
    def delete(self, problem_id: str, owner: str = "") -> None: ...
    def exists(self, problem_id: str, owner: str = "") -> bool: ...

class JsonFileStore:  # current implementation, renamed
    ...

class PostgresStore:
    """Single table: problems(id, owner, data jsonb, created_at, updated_at)"""
    ...
```

**Key design choice:** Store the full Pydantic JSON in a `jsonb` column. No ORM, no schema mapping. The Problem model is already self-contained — `model_dump_json()` / `model_validate_json()` round-trips perfectly. PostgreSQL gives us durability, indexing on owner, and Render provides managed Postgres.

### 2b. Add `owner` field to Problem model

```python
# frontier/engine/models.py
class Problem(BaseModel):
    owner: str = ""  # empty = legacy/local problems
    ...
```

Backward compatible — existing JSON files deserialize with `owner=""`.

### 2c. Auth middleware

New file `frontier/auth.py`:
- API keys stored in env var or Postgres table
- Starlette middleware extracts `Authorization: Bearer <key>` from SSE connections
- Sets `owner` in `contextvars` for the request
- Stdio transport skips auth (local dev)
- `server.py` reads `contextvars` to scope all store operations

### 2d. Auto-select backend

```python
# server.py
import os
if os.environ.get("DATABASE_URL"):
    store = PostgresStore(os.environ["DATABASE_URL"])
else:
    store = JsonFileStore()
```

### 2e. Render config update

```yaml
# render.yaml
services:
  - type: web
    name: frontier
    runtime: python
    branch: main
    buildCommand: pip install -r requirements.txt
    startCommand: MCP_TRANSPORT=sse python -m frontier.mcp_server.server
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
      - key: DATABASE_URL
        fromDatabase:
          name: frontier-db
          property: connectionString

databases:
  - name: frontier-db
    plan: starter
```

**New dependency:** `psycopg[binary]>=3.1` (modern async-capable Postgres driver, lightweight)

**Files changed:**
- `frontier/engine/store.py` — protocol + dual backends
- `frontier/engine/models.py` — add `owner` field
- `frontier/auth.py` (new) — API key auth, contextvars middleware
- `frontier/mcp_server/server.py` — backend selection, owner scoping on all store calls
- `render.yaml` — Postgres addon
- `pyproject.toml` / `requirements.txt` — add psycopg
- `tests/test_store.py` — test both backends

**Verification:**
- `pytest` — all existing tests pass with JsonFileStore (default when no DATABASE_URL)
- Deploy to Render with Postgres — confirm problems persist across deploys
- Test auth: create problem with key A, verify key B can't see it

---

## Phase 3: Future Extensibility (later)

These are enabled by the layered architecture but not built yet:

### REST API alongside MCP
- Add FastAPI app that wraps the same engine functions
- Enables custom UIs, webhooks, integrations
- Engine is already protocol-agnostic — this is purely additive

### Background optimization
- Long-running problems queued and solved async
- Results delivered via webhook or polling endpoint
- "Optimization as a service" pattern

### Custom web UI
- Purpose-built decision interface (comparison tables, frontier visualizations, shareable links)
- Calls REST API, no MCP needed
- Agent still available via embedded chat

### LLM API integration
- Server-side Claude calls for users without their own LLM client
- Skills injected as system prompt
- Full guided workflow without needing Claude Code/Desktop

---

## What We Preserve

| Differentiator | How it survives |
|---|---|
| 4 skill resources (800 lines of domain expertise) | Delivered via `get_skill` tool (universal) + MCP resources (backward compat) |
| Guided workflow (model → solve → explore) | Tool descriptions include compact guidance + server instructions direct to `get_skill` |
| Iterative refinement (stale results, run comparison, curation) | Engine unchanged — all state management stays in models/explorer |
| content_signature stability | Engine unchanged — signatures persist across runs, backends |
| Metric-driven feedback (diagnostics, quality indicators) | Engine unchanged |

## What We Don't Do

- No ORM — Pydantic JSON in jsonb column
- No microservices — single Python process
- No REST API yet — MCP-only until Phase 3
- No custom UI yet — LLM clients are the UI for now
- No breaking changes — `owner=""` is backward compatible, resources stay alongside tools

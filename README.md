## Overview
<p align="center">
  <img src="assets/frontier-logo.png" alt="Frontier" width="160" />
</p>

<p align="center">
  Multi-objective decision optimization toolkit. Use in any MCP client or via the integrated web UI.
</p>

Frontier helps you make hard decisions that have many options and conflicting goals: which projects to fund, how to split a budget, who to source from. You describe the decision to an AI agent in plain language; it models the problem, optimizes it, and walks you through the **full set of optimal tradeoffs**. You make the final call.

Under the hood it maps the **Pareto frontier** (every outcome where improving one goal means giving up another) with evolutionary search plus optional exact solvers. Every number it reports is computed, not guessed, so the decision stays explainable and auditable, and framing the problem and picking the tradeoff stay yours.

**Try it:** the [hosted demo](https://frontier-ui.onrender.com/) (ask @cafzal for access), or [set up your own](#setup).

## Examples

[Worked examples](examples/) you can load and adapt: each ships a paste-ready prompt that reproduces the result. Two shown:

<table>
<tr>
<td width="50%" valign="top">
<img src="assets/example-portfolio.png" alt="ETF efficient frontier with a plain-language tradeoff read" /><br/>
<sub>Investment portfolio: risk / return / yield frontier with a plain-language tradeoff read</sub>
</td>
<td width="50%" valign="top">
<img src="assets/example-capital.png" alt="Capital project formulation and per-scenario frontiers" /><br/>
<sub>Capital project selection: 120 projects, exact-certified, with per-scenario frontiers</sub>
</td>
</tr>
</table>

## Workflow

<p align="center"><img src="assets/workflow-progression-icon.png" alt="Workflow progression: frame, score, solve, explore, decide" width="560" /></p>

Drive Frontier by interacting with a coding agent or the hosted web chat, in plain language. AI translates your decision into Frontier's model, runs the solver, and reads the results back.

The loop runs in three phases. **Explore** maps the tradeoff space broadly with the approximate solver, measured by *coverage* (how much of the space you hold). **Certify** proves the finalists you'd commit to with an exact solver, measured by the *optimality gap* (how far from proven-best). **Explain** names what would move the answer: the biggest lever, what survives across scenarios, and a guarantee that holds across every feasible plan. A typical sequence walks all three:

1. **Frame it.** Name the objectives (what to maximize or minimize), the options to choose among, and any hard constraints, plus scenarios if the future is uncertain. *e.g. "We're choosing a CRM for a 10-person startup: maximize features and support, minimize cost; budget under $50k/yr; pick one."*
2. **Score the options.** Hand over the numbers, or let the agent estimate and flag what's shaky. *e.g. "Score these five CRMs on cost and support from their pricing pages."*
3. **Solve.** The agent validates the setup, then runs the optimizer for the Pareto frontier, optionally once per scenario. *e.g. "Solve it."*
4. **Explore the tradeoffs.** Frontier shape, the extremes, the balanced/knee, the marginal cost of pushing an objective, robustness across scenarios. *e.g. "Show the tradeoffs and recommend a balanced pick."*
5. **Certify and examine.** Before committing, stress-test the finalists where the problem's shape supports it: have an exact solver certify your finalists, see which constraints bind and what relaxing each would buy, and get a guarantee that a guardrail holds across every feasible plan. *e.g. "Certify the finalists and show me what's binding."*
6. **Iterate.** Tighten a constraint, add a scenario, re-solve, and compare against the previous run. *e.g. "Cap cost at $40k and re-run: what dropped off the frontier?"*
7. **Decide.** Curate the finalists and commit to the pick that fits your tradeoffs: the engine lays out the options and leaves the final call to you. *e.g. "Curate the balanced plan as 'Lean choice' and commit."*

## Purpose

Spreadsheets hit a complexity wall once options and constraints in a decision multiply. Generative AI models reason about tradeoffs but can't *solve* them: reliably enumerating a huge option space, enforcing hard constraints, and producing the frontier are beyond them. Frontier fills the gap: the LLM translates and narrates, an optimizer does the math, and the judgment stays with you.

**When it fits:** any decision that picks a subset from many options or splits an allocation across them, under conflicting objectives and hard constraints, with data to score the options. Pairwise interactions between options, where one's value depends on another, make the problem genuinely nonlinear: beyond what a ranking or weighted sum can capture. **When it's overkill:** one objective, a handful of options, or goals that mostly agree; a spreadsheet or a sorted ranking already answers those.

**What it adds beyond an LLM alone** (its design principles):
- **The full frontier**: every Pareto-optimal plan, yours to weigh.
- **Explore broadly, certify selectively**: the heuristic maps the whole space; an exact solver then proves the finalists you'd commit to on supported shapes, catching dominated points the heuristic showed as efficient. It can only confirm or improve them.
- **Constraints enforced**: eight hard types (cardinality, force include, force exclude, objective bounds, exclusion pairs, dependencies, group limits, allocation caps), respected by every plan the search returns.
- **Governance guarantees**: on selection problems, a proof that a guardrail holds for *every* feasible plan, or a concrete counterexample.
- **Grounded and reproducible**: every number traces to a score, an objective value, a dual, or a binding constraint, and the same inputs + seed reproduce the exact frontier.
- **Scenarios & risk**: independent frontiers per scenario, plus CVaR / worst-case / expected / minimax-regret per objective.
- **Knowledge discovery**: mine the frontier for selection rates, recurring rules, and strategy families.
- **Durable decisions**: problems persist across sessions; curated picks and feedback attach to the decision and survive re-runs.

## Architecture

<p align="center"><img src="assets/architecture.png" alt="Frontier architecture: agent clients and the web UI speak MCP to one server exposing four tools, with skills and solvers attached and a deterministic engine beneath" width="560" /></p>

Frontier is a Python MCP server (FastMCP) wrapping pymoo's NSGA-II/III evolutionary solvers, with two exact-solver backends (HiGHS on CPU, cuOpt on GPU). State persists per-problem as JSON; the optimizer produces a Pareto frontier with indicators to guide the decision. Domain expertise lives in skill markdown files that the server auto-injects at workflow transitions.

For full schemas, action parameters, data model, persistence layout, and the skill auto-injection mechanism, see [`architecture.md`](architecture.md). For skill, prompt, and MCP design principles, see [`best-practices.md`](best-practices.md).

### Tools

Full action lists and parameters in [`architecture.md`](architecture.md):

- **`model`**: define and edit the problem (objectives, options, scores, 8 constraint types, interaction matrices, scenarios): `create` / `update` / `get`, plus `save` / `load` for named problems.
- **`solve`**: validate and optimize (NSGA-II/III, fast/thorough, seeded): `run`, `run_scenarios`, and `status` to poll background runs; opt-in `solver="highs"|"cuopt"` exact backends on supported shapes.
- **`explore`**: navigate results, or probe the feasible region before a solve: `tradeoffs`, `certify` (audit the exact overlay), `audit` (selection problems: prove a guardrail holds across the *whole* feasible space, or return a counterexample), `sensitivity` (solver-exact shadow prices + near-misses), `composition` (mine selection rates, principles, strategy families), plus `compare` / `solutions` / `scenario_results` / `curate`.
- **`get_skill`**: fetch the workflow guidance below.

### Skills

Markdown guides the server auto-injects at workflow transitions (also fetchable via `get_skill`) – the domain judgment for each phase:

- **`problem_framing`**: objectives vs constraints, approach + aggregation, scenario definition.
- **`data_collection`**: score elicitation without anchoring bias, quality signals.
- **`optimization_strategy`**: iteration, constraint strategy, infeasibility, re-run judgment.
- **`solution_interpreter`**: presenting tradeoffs without a "best", eliciting preferences, curation.

### Saving & loading

Every problem is auto-persisted in the engine's store (`data/`, keyed by id) – session state the engine manages for you. Separately, `model save` writes a **named, portable copy** in the [examples](examples/) format, to reload or share by name:

- **`model save problem_id=… save_as="<name>"`**: save to your gitignored `saved/` library (override with `FRONTIER_SAVED_DIR`), bundling the solved frontier when present.
- **`model load source="<name>"`**: rebuild a problem, resolving `saved/` first, then bundled `examples/`; omit `source` to list available names.

## Setup

Two ways to use Frontier:

- **Web UI**: a browser chat shell over the engine, with interactive charts and curation. Try the hosted app at **[frontier-ui.onrender.com](https://frontier-ui.onrender.com/)** (password-gated – ask @cafzal for access), or run/deploy your own (requires an API key; see [`ui/`](ui/) and [Deploy your own](#deploy-your-own)).
- **MCP client**: connect any MCP-compatible client (Claude Code, Claude Desktop, claude.ai, Cursor, Codex). The hosted beta engine (`https://frontier-592q.onrender.com/sse`) is gated by a token – ask @cafzal for the `FRONTIER_MCP_TOKEN` value; or [self-host](#self-host) your own (ungated by default).

The MCP-client snippets below assume the hosted engine.

### Claude Code (terminal)

```bash
claude mcp add frontier --transport sse \
  --url https://frontier-592q.onrender.com/sse \
  --header "Authorization: Bearer $FRONTIER_MCP_TOKEN"
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "frontier": {
      "transport": "sse",
      "url": "https://frontier-592q.onrender.com/sse",
      "headers": { "Authorization": "Bearer YOUR_FRONTIER_MCP_TOKEN" }
    }
  }
}
```

### claude.ai (MCP integrations)

Add Frontier as a remote MCP server in claude.ai settings using the SSE URL `https://frontier-592q.onrender.com/sse`, with an `Authorization: Bearer <FRONTIER_MCP_TOKEN>` header.

### Self-host

Run your own instance. Requires Python 3.11+.

```bash
git clone https://github.com/cafzal/frontier.git
cd frontier
pip install -e .

# stdio transport (for Claude Desktop / coding agents on the same machine)
python -m mcp_server.server

# SSE transport (for remote MCP clients)
MCP_TRANSPORT=sse python -m mcp_server.server

# Gate a public instance with a shared bearer token – clients must then send
# `Authorization: Bearer <token>`. Leave unset for an open local instance.
FRONTIER_MCP_TOKEN=your-secret MCP_TRANSPORT=sse python -m mcp_server.server
```

Point your MCP client at the local server – for SSE that's `http://localhost:8000/sse`. The optional web UI lives in [`ui/`](ui/) – see its [README](ui/README.md).

**Exact solvers (optional).** Install `highspy` (CPU; `pip install highspy`) or cuOpt (NVIDIA GPU) to unlock `solver="highs"|"cuopt"`: exact certification (`explore certify`) and solver-exact sensitivity (`explore sensitivity`) on supported shapes. No GPU at hand? [examples/cuopt_colab.ipynb](examples/cuopt_colab.ipynb) is a ready Colab template for the cuOpt arc. How it works (the shared scalarization engine, the certify invariant, which shapes carry duals) is in [`architecture.md`](architecture.md#solver-backends-pluggable).

### Deploy your own

Both pieces are plain web services – host them anywhere (Render, Fly, Railway, a VPS, Docker):

- **Engine** (Python) – `pip install ".[sse]"` (add `,highs` for the CPU exact backend), then run the SSE server as in [Self-host](#self-host), bound publicly: set `MCP_HOST=0.0.0.0` and `FRONTIER_MCP_TOKEN`, with the host supplying `$PORT`. Must be publicly reachable – Anthropic's MCP connector calls it.
- **Web UI** (Node, in `ui/`) – `npm install && npm run build`, then `npm start`. Set `FRONTIER_MCP_URL` (the engine's `/sse`), `FRONTIER_MCP_TOKEN`, `ANTHROPIC_API_KEY`, `AGENT_BACKEND=messages-api`, and `UI_ACCESS_PASSWORD`. Long-session context management and prompt caching are env-tunable (`AGENT_CONTEXT_WINDOW`, `AGENT_CONTEXT_MANAGEMENT`, `AGENT_PROMPT_CACHE`, and related); [`architecture.md`](architecture.md#5-web-ui--hosting) documents the knobs and defaults.

`FRONTIER_MCP_TOKEN` must match on both – that's what authenticates the UI to the engine.

**Render (one-click example):** [`render.yaml`](render.yaml) provisions both as a blueprint.

## Background

Optional background – the thinking behind Frontier and how it's evolved:

- [Building an AI-Powered Decision Tool Prototype: A Product Manager's Journey](https://camafzal.substack.com/p/building-an-ai-powered-decision-tool) – May 2025
- [Lowering the Barriers to Decision Optimization with AI](https://camafzal.substack.com/p/lowering-the-barriers-to-decision) – Sep 2025
- [Making optimization accessible: AI as the translation layer](https://camafzal.substack.com/p/making-optimization-accessible-ai) – Jan 2026
- [Agents have a convergent reasoning gap](https://camafzal.substack.com/p/agents-have-a-convergent-reasoning) – Apr 2026

## Contributing

Contributions welcome – start with the developer docs:

- [`architecture.md`](architecture.md) – system architecture & data flow
- [`best-practices.md`](best-practices.md) – skill & prompt design guidelines

## Acknowledgements

Frontier builds on open-source optimization work, with thanks to:

- **[pymoo](https://github.com/anyoptimization/pymoo)** (Apache-2.0) – the NSGA-II / NSGA-III evolutionary solvers at Frontier's core. Blank, J. & Deb, K. (2020). *pymoo: Multi-Objective Optimization in Python.* IEEE Access, 8, 89497–89509. The underlying algorithms are Deb et al., NSGA-II (2002) and Deb & Jain, NSGA-III (2014).
- **[HiGHS](https://github.com/ERGO-Code/HiGHS)** (MIT) – CPU exact-solver backend (`solver="highs"`). Huangfu, Q. & Hall, J.A.J. (2018). *Parallelizing the dual revised simplex method.* Mathematical Programming Computation, 10(1), 119–142.
- **[NVIDIA cuOpt](https://github.com/NVIDIA/cuopt)** (Apache-2.0) – GPU exact-solver backend (`solver="cuopt"`).

## License

Apache License 2.0 – see [LICENSE](LICENSE) and [NOTICE](NOTICE).

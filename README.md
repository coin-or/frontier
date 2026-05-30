<p align="center">
  <img src="assets/frontier-logo.png" alt="Frontier" width="160" />
</p>

<p align="center">
  Multi-objective decision optimization engine, exposed as an MCP server. Works with any MCP-compatible client.
</p>

**Developer docs:** [`architecture.md`](architecture.md) — system architecture & data flow | [`best-practices.md`](best-practices.md) — skill & prompt design guidelines

## Summary

Frontier gives AI agents a grounded optimization engine for hard decisions. The agent describes a problem in business terms; Frontier enumerates the full Pareto frontier — every non-dominated solution that balances conflicting objectives under hard constraints — and the agent narrates the tradeoffs back. NSGA-II/III under the hood (via pymoo), exposed as 4 MCP tools (`model`, `solve`, `explore`, `get_skill`). Frontier is the engine; the agent is the interface.

The design is **explainable, governable optimization**: the engine owns the *deterministic guardrails* — hard constraints it never violates, reproducible runs (same inputs → same frontier), dominance filtering, pre-solve validation, and quality gates — while the *human judgment* stays at the two calls that matter: which objectives and constraints define the problem, and which non-dominated solution to commit to. The agent explains every tradeoff (shadow prices, frontier shape, marginal rates, dominance) and never names a "best"; every claim it makes traces back to returned data, so the result is explainable and the decision is auditable line by line. The wedge is combinatorial, constrained, portfolio-like decisions with conflicting objectives.

## Examples

Several [worked examples](examples/) are included for you to learn from and adapt. Select results displayed below. 

<table>
<tr>
<td width="50%" valign="top">
<img src="assets/example-portfolio.png" alt="ETF efficient frontier with a plain-language tradeoff read" /><br/>
<sub>Investment portfolio</sub>
</td>
<td width="50%" valign="top">
<img src="assets/example-capital.png" alt="Capital project formulation and per-scenario frontiers" /><br/>
<sub>Capital project selection</sub>
</td>
</tr>
</table>

## Purpose

LLMs can reason about tradeoffs conversationally but can't *solve* them — they can't reliably enumerate a combinatorial option space, enforce hard constraints, and produce the actual Pareto frontier. These are the decisions teams used to grind out in spreadsheets, until the spreadsheet hit a complexity wall: too many options, too many interacting constraints, objectives that genuinely conflict. Frontier supplies the missing half — the **LLM translates** the decision into a structured model and narrates the result; a real **optimization solver** does the math neither a spreadsheet nor an LLM can. It fits problems where data can score options, objectives genuinely conflict (no single "best"), and the space is too large and too constrained for intuition.

**By shape, not domain:** any decision that selects a subset from many options (which K of N) or allocates a budget across them (how much of each), balancing conflicting objectives under hard constraints — with data to score the options and a space too large for a spreadsheet or intuition. Pairwise interactions (covariance, audience overlap, correlated risk) make it genuinely nonlinear.

**What Frontier adds beyond an LLM alone:**
- **The full non-dominated frontier** — every Pareto-optimal tradeoff, not a single recommendation or a weighted ranking
- **Hard constraints, enforced** — 8 constraint types (cardinality, forced include/exclude, objective bounds, exclusion pairs, dependencies, group limits, allocation caps), never violated during search
- **Auditable by construction** — every reported tradeoff traces to returned data (scores, shadow prices, dominance), not a fluent guess; runs are reproducible (same inputs → same frontier), so a stakeholder can re-examine the decision line by line
- **Scenario & risk modeling** — independent frontiers per scenario, plus CVaR / worst-case / expected risk per objective
- **Longitudinal state** — problems persist across sessions; curated picks track survival across re-runs

*Why not just ask an agent to write a solver?* You can — for a one-shot problem. Frontier is the turnkey pairing: an LLM translation-and-narration layer over a real solver, grounded (every number computed, not guessed), auditable, and reusable across problems and re-runs — instead of bespoke optimization code rebuilt and re-verified each time.

**Worked examples:** [`examples/`](examples/) — loadable, runnable problem definitions you can drop into Frontier.

## Workflow

You describe a decision to an AI agent in natural language; the agent translates it into Frontier's structured model, runs optimization, and interprets the results back. The 4 tools, in order:

1. **`model`** — define objectives, options, scores, constraints
2. **`solve`** — run NSGA-II/III to produce the Pareto frontier
3. **`explore`** — tradeoffs, comparisons, marginal analysis, scenarios, curation
4. **`get_skill`** — workflow guidance: `problem_framing`, `data_collection`, `optimization_strategy`, `solution_interpreter`

Skills auto-inject at workflow transitions, so domain rigor — how to classify objectives vs constraints, elicit scores without anchoring bias, present tradeoffs without implying a "best" — extends past the solver into how the agent frames and communicates.

## Setup

Two ways to use Frontier:

- **Web UI** — a browser chat shell over the engine, with interactive charts (2D/3D scatter and parallel coordinates that adapt to objective count, per-scenario overlays) and curate-straight-from-the-chart. A hosted instance is available to beta users; or run/deploy your own (requires API key; see [`ui/`](ui/) and [Deploy your own](#deploy-your-own))
- **MCP client** — connect any MCP-compatible client (Claude Code, Claude Desktop, claude.ai, Cursor, Codex). The hosted beta engine (`https://frontier-592q.onrender.com/sse`) is gated by a token — ask @cafzal for `FRONTIER_TOKEN`; or [self-host](#self-host) your own (ungated by default).

The MCP-client snippets below assume the hosted engine.

### Claude Code (terminal)

```bash
claude mcp add frontier --transport sse \
  --url https://frontier-592q.onrender.com/sse \
  --header "Authorization: Bearer $FRONTIER_TOKEN"
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "frontier": {
      "transport": "sse",
      "url": "https://frontier-592q.onrender.com/sse",
      "headers": { "Authorization": "Bearer YOUR_FRONTIER_TOKEN" }
    }
  }
}
```

### claude.ai (MCP integrations)

Add Frontier as a remote MCP server in claude.ai settings using the SSE URL `https://frontier-592q.onrender.com/sse`, with an `Authorization: Bearer <FRONTIER_TOKEN>` header.

### Self-host

Run your own instance instead of using the hosted one. Requires Python 3.11+.

```bash
git clone https://github.com/cafzal/frontier.git
cd frontier
pip install -e .

# stdio transport (for Claude Desktop / coding agents on the same machine)
python -m mcp_server.server

# SSE transport (for remote MCP clients)
MCP_TRANSPORT=sse python -m mcp_server.server

# Gate a public instance with a shared bearer token — clients must then send
# `Authorization: Bearer <token>`. Leave unset for an open local instance.
FRONTIER_MCP_TOKEN=your-secret MCP_TRANSPORT=sse python -m mcp_server.server
```

Point your MCP client at the local server — for SSE that's `http://localhost:8000/sse`. The optional web UI lives in [`ui/`](ui/) — see its [README](ui/README.md).

### Deploy your own

Both pieces are plain web services — host them anywhere (Render, Fly, Railway, a VPS, Docker):

- **Engine** (Python) — `pip install -r requirements.txt`, then `MCP_TRANSPORT=sse python -m mcp_server.server`. Set `MCP_HOST=0.0.0.0` and `FRONTIER_MCP_TOKEN`; the host supplies `$PORT`. Must be publicly reachable — Anthropic's MCP connector calls it.
- **Web UI** (Node, in `ui/`) — `npm install && npm run build`, then `npm start`. Set `FRONTIER_MCP_URL` (the engine's `/sse`), `FRONTIER_MCP_TOKEN`, `ANTHROPIC_API_KEY`, `AGENT_BACKEND=messages-api`, and `UI_ACCESS_PASSWORD`.

`FRONTIER_MCP_TOKEN` must match on both — that's what authenticates the UI to the engine.

**Render (one-click example):** [`render.yaml`](render.yaml) provisions both as a blueprint — auto-generates the shared token, derives the engine URL, leaves only `ANTHROPIC_API_KEY` to set. Point Render at your fork (New → Blueprint).

## Architecture

Frontier is a Python MCP server (FastMCP) wrapping pymoo's NSGA-II/III evolutionary solvers. State persists per-problem as JSON; the optimizer produces a Pareto frontier with quality indicators, scenario-aware results, and shadow-price rates per binding constraint. Domain expertise lives in skill markdown files that the server auto-injects at workflow transitions, so the same rigor reaches every MCP client.

For full schemas, action parameters, data model, persistence layout, and the skill auto-injection mechanism, see [`architecture.md`](architecture.md). For skill, prompt, and MCP design principles, see [`best-practices.md`](best-practices.md).

### Tools

**`model`** — define and edit a problem
- Objectives (2-7) with aggregation modes: sum, avg, min, max, quadratic
- Options scored against objectives; binary (select/reject) or proportional (allocate %) approach
- 8 constraint types: cardinality, force include/exclude, objective bounds, exclusion pairs, dependencies, group limits, max allocation (proportional only)
- Interaction matrices for quadratic aggregation (e.g. covariance matrices for portfolio risk), with scale groups for regime shifts
- Reference points (baseline / aspirational) and scenarios (probability-weighted alternative scores + interaction matrices)
- Save & load problems by name in the portable examples format (`model save` / `model load`)

**`solve`** — run optimization
- NSGA-II (2-3 objectives) and NSGA-III (4+ objectives) via pymoo
- Fast mode for iterative exploration, thorough mode for final convergence; `max_solutions` caps the Pareto set size (default 100)
- Quality signals: hypervolume and spacing per run; `frontier_complete` flag (full set vs pruned sample); `frontier_quality` status (GOOD / WARNING / POOR with progressive gates and actionable issues)
- Reproducibility: optional `seed`; when omitted, the drawn seed is echoed as `seed_used` so any run can be reproduced after the fact
- Per-scenario optimization with score overrides/adjustments; per-scenario seeds deterministically derived so each scenario reproduces while starting from distinct initializations
- Infeasibility analysis identifies conflicting constraints with relaxation suggestions
- Full result persisted to disk (`full_result_path`) for bulk export or artifact assembly; run history with constraint snapshots for cross-run comparison

**`explore`** — navigate results
- Tradeoff analysis: objective ranges, correlations (Pearson + normalized mutual information), extremes, balanced solution, inflection-point candidates, frontier shape per pair (linear / concave / convex / discontinuous), reference-point comparisons
- Objective redundancy: Pearson/MI disagreement flags non-linear dependence
- Binding-constraint analysis: shadow-price rates per binding constraint — how much each objective shifts per unit of slack relaxation (covers objective_bound, cardinality, group_limit)
- Solution listing (compact by default; `detail=true` for full options/allocations), single-solution detail with reference analysis, side-by-side comparison
- Marginal analysis: cost-per-unit rates between adjacent solutions with knee-point detection
- Per-scenario exploration: tradeoffs, compare, solutions, marginal analysis, and curation all accept an optional `scenario` parameter
- Scenario results: robust options across all scenarios, scenario-specific options, probability-weighted expected values, per-objective scenario risk (expected / worst-case / best-case / CVaR with tunable `cvar_alpha`)
- Run comparison: criteria diffs, frontier diffs, option coverage changes across runs
- Curation: curate solutions with custom names; content-signature identity tracks survival across re-runs; `export_curated` ships a formatted handoff artifact (markdown table or CSV)
- Feedback: rating + notes linked to curated set via content signatures
- Visualizations: inline ASCII for coding agents (scatter, parallel coordinates, marginal rates), plus structured `viz_data` the web UI renders as interactive Plotly charts — dimensionality-adaptive 2D/3D scatter and parallel coordinates, per-scenario overlays with curated picks highlighted, and a formulation card

**`get_skill`** — fetch workflow guidance by name (works with any MCP client)

### Skills

Skills are markdown files the server auto-injects into tool responses at workflow transitions, and also retrievable directly via `get_skill`. They encode domain judgment, not tool docs.

- **`problem_framing`** — classify objectives vs constraints (principle-based, not keyword matching), hidden objective detection, approach selection (binary vs proportional), aggregation modes, interaction matrices, reference points, scenario definition
- **`data_collection`** — score elicitation, anchoring techniques, batch efficiency, source evaluation, conflict resolution, quality signals (variance, scale mismatch), completeness drive
- **`optimization_strategy`** — iteration expectations, validate → run → examine flow, constraint strategy, infeasibility response, binding-constraint detection, curated-solution survival tracking, stale-result judgment
- **`solution_interpreter`** — present results without bias ("never say best"), five explanation dimensions, presentation order (Extremes → Balanced → Inflection → Risk → Preference), tradeoff framing, objective-ranking elicitation, scenario presentation, preference learning

## Saving & loading problems

Every problem is auto-persisted in the engine's internal store (`data/`, keyed by id) — session state you don't manage. Separately, `save` writes a **named, portable copy** in the same format as the [examples](examples/), to reload or share by name:

- **`model save problem_id=… save_as="<name>"`** — save to your gitignored `saved/` library (sibling of `examples/`; override with `FRONTIER_SAVED_DIR`), bundling the solved frontier when present.
- **`model load source="<name>"`** — rebuild a problem, resolving your `saved/` library first, then bundled `examples/`; omit `source` to list available names.

## Background

Optional background — the thinking behind Frontier and how it's evolved:

- [Building an AI-Powered Decision Tool Prototype: A Product Manager's Journey](https://camafzal.substack.com/p/building-an-ai-powered-decision-tool) — May 2025
- [Lowering the Barriers to Decision Optimization with AI](https://camafzal.substack.com/p/lowering-the-barriers-to-decision) — Sep 2025
- [Making optimization accessible: AI as the translation layer](https://camafzal.substack.com/p/making-optimization-accessible-ai) — Jan 2026
- [Agents have a convergent reasoning gap](https://camafzal.substack.com/p/agents-have-a-convergent-reasoning) — Apr 2026

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

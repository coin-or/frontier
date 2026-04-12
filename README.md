# Frontier

Multi-objective portfolio optimization engine, exposed as an MCP server. Works with any MCP-compatible client.

**Developer docs:** [`architecture.md`](architecture.md) — system architecture & data flow | [`best-practices.md`](best-practices.md) — skill & prompt design guidelines

## Setup

### Claude Code (terminal)

```bash
claude mcp add frontier --transport sse --url https://frontier-592q.onrender.com/sse
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### claude.ai (MCP integrations)

Add Frontier as a remote MCP server in claude.ai settings using the SSE URL: `https://frontier-592q.onrender.com/sse`

## Workflow

Frontier provides 4 tools: `model`, `solve`, `explore`, and `get_skill`. The workflow is:

1. Call `get_skill('problem_framing')` for guidance, then use `model` to define your decision problem
2. Call `get_skill('data_collection')` for guidance, then use `model` to enter scores
3. Call `get_skill('optimization_strategy')` for guidance, then use `solve` to run optimization
4. Call `get_skill('solution_interpreter')` for guidance, then use `explore` to navigate results

The `get_skill` tool delivers domain expertise that guides the agent through each stage — translating business language into solver language, eliciting scores efficiently, interpreting tradeoffs without bias, and surfacing preferences through the right questions.

## Capabilities

### Problem Definition (`model`)

- **Objectives** (2-7) with aggregation modes (sum, avg, min, max)
- **Options** scored against each objective; binary (select/reject) or proportional (allocate %) approach
- **7 constraint types**: cardinality, force include/exclude, objective bounds, exclusion pairs, dependencies, group limits
- **Reference points**: baseline and aspirational for contextual comparison
- **Scenarios**: probability-weighted alternative scores for uncertainty analysis

### Optimization (`solve`)

- **NSGA-II** (2-3 objectives) and **NSGA-III** (4+ objectives) via pymoo
- **Fast mode** for iterative exploration, **thorough mode** for final convergence; quality indicators (hypervolume, spacing) with each run
- **Scenario optimization**: independent runs per scenario with score overrides/adjustments
- **Infeasibility analysis**: when no feasible solutions exist, identifies conflicting constraints with relaxation suggestions
- **Run history**: archived runs with constraint snapshots for comparison

### Exploration (`explore`)

- **Tradeoff analysis**: objective ranges, correlations, extremes, balanced solution, reference point comparisons
- **Solution comparison**: side-by-side with shared/differentiating options and tradeoff summaries
- **Marginal analysis**: cost-per-unit rates between adjacent solutions with knee-point detection
- **Scenario results**: robust options (all scenarios), scenario-specific options, probability-weighted expected values
- **Run comparison**: criteria diffs, frontier diffs, option coverage changes across runs
- **Solution curation**: bookmark solutions with custom names; content-based signatures track survival across re-runs
- **Feedback**: rate and annotate solutions; linked to curated set via stable content signatures
- **Visualizations**: inline ASCII scatter plots, parallel coordinates, marginal rate charts

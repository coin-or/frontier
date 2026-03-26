# Frontier

Multi-objective portfolio optimization engine. Finds Pareto-optimal portfolios for "pick K of N" selection problems with 2-6 conflicting objectives.

## MCP Tools

This project runs as an MCP server with 3 tools: `model`, `solve`, `explore`.

## Frontier Skills

When using Frontier's optimization tools, load the relevant skill resource at each workflow phase to activate expert guidance:

- **Before framing a problem:** read `frontier://skills/problem_framing` — validates objectives vs constraints, checks completeness, calibrates scope
- **During score entry:** read `frontier://skills/data_collection` — anchoring technique, batch scoring, uncertainty handling
- **Before/after solving:** read `frontier://skills/optimization_strategy` — approach selection, constraint strategy, infeasibility diagnosis
- **When exploring results:** read `frontier://skills/solution_interpreter` — tradeoff framing, never say "best", differentiation focus

## Key Principles

- **Never say "best"** — every Pareto solution is optimal at its tradeoff. Present tradeoffs, not rankings.
- **Extremes → Balanced → Preference** — show frontier endpoints first, then the balanced middle, then ask what the user gravitates toward.
- **Batch scores** — send all scores in 1-3 `model update` calls, not one at a time.
- **Constraints shape, not shrink** — don't add constraints just to reduce the frontier. Let the user decide.
- **Quantify tradeoffs** — "Solution 3 gives 20% more revenue but costs 35% more effort" is better than "Solution 3 is good."

## Development

- Python 3.11+, dependencies in `requirements.txt`
- Run tests: `python -m tests.eval_checkpoint` or `pytest tests/ -v`
- Run server locally: `MCP_TRANSPORT=sse PORT=8080 python -m frontier.mcp_server.server`
- Design docs in `designs/` — `phase0_mvp.md` is the current implementation

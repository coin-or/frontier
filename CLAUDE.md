# Frontier

Multi-objective portfolio optimization engine. Finds Pareto-optimal portfolios for "pick K of N" selection problems with 2-6 conflicting objectives.

## MCP Tools

This project runs as an MCP server with 3 tools: `model`, `solve`, `explore`.

## Frontier Skills

When using Frontier's optimization tools, load the relevant skill resource at each workflow phase:

- **Before framing a problem:** read `frontier://skills/problem_framing`
- **During score entry:** read `frontier://skills/data_collection`
- **Before/after solving:** read `frontier://skills/optimization_strategy`
- **When exploring results:** read `frontier://skills/solution_interpreter`

Each skill contains expert guidance for that phase. Follow its instructions.

## Development

- Python 3.11+, dependencies in `requirements.txt`
- Run tests: `python -m tests.eval_checkpoint` or `pytest tests/ -v`
- Run server locally: `MCP_TRANSPORT=sse PORT=8080 python -m frontier.mcp_server.server`
- Design docs in `designs/` — `phase0_mvp.md` is the current implementation

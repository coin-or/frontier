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

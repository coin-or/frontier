# Frontier

Multi-objective portfolio optimization engine, exposed as an MCP server.

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

# Frontier Web

Lightweight web UI prototype for [Frontier](../README.md). Chat shell on top of the existing Frontier MCP server. Identity-only system prompt; all workflow behavior driven by the MCP server's tool descriptions, tool-response auto-injection, and skills.

## Setup

```bash
cd ui
cp .env.example .env.local         # add your ANTHROPIC_API_KEY
npm install
npm run dev                        # http://localhost:3000
```

By default points at the live Frontier MCP at `https://frontier-592q.onrender.com/sse`. Override via `FRONTIER_MCP_URL` in `.env.local` to point at a local instance.

## Stack

- **Next.js 15** (App Router, Node runtime for `/api/chat`)
- **React 19**, **Tailwind CSS**, **react-markdown** + `remark-gfm` for ASCII viz / table rendering
- **Anthropic SDK** (Messages API + MCP connector, `mcp-client-2025-11-20` beta)
- No DB, no auth, no AI SDK — straight SSE proxy from Anthropic streaming events to the client

## Pluggable agent runtime

[`lib/agent-runtime.ts`](lib/agent-runtime.ts) selects backend by `AGENT_BACKEND` env var:

| Value | Status | What it gets you |
|---|---|---|
| `messages-api` (default) | ✅ working | Anthropic Messages API + MCP connector — simplest, fewest deps |
| `managed-agents` | 🚧 stub | Claude Managed Agents — adds memory, dreaming, telemetry, event SSE |
| `agent-sdk` | 🚧 stub | Claude Agent SDK — for local dev / async workers |

Anthropic lock-in is bounded to this file. Swap cost: 3–5 days, mostly conversation-memory + telemetry reimplementation.

## Architecture notes

- **System prompt is identity-only** ([`lib/system-prompt.ts`](lib/system-prompt.ts)) — ~3 lines. **No skill content is duplicated here.** All workflow guidance flows from the MCP server. If you find yourself wanting to "fix" agent behavior by editing the system prompt, the fix actually belongs in `server.py` or a skill file in the engine.
- **Streaming is direct SSE** — no AI SDK on the server, no wire-format translation. Each `data: {...}` line is a raw Anthropic event the client renders incrementally.
- **Tool calls render inline** ([`components/ToolCallBlock.tsx`](components/ToolCallBlock.tsx)) — collapsed by default; click to expand input + result. Status dot is green/amber/red.
- **ASCII viz from the MCP server renders correctly** because `react-markdown` preserves monospace + whitespace in fenced code blocks. D3 charts swap in later once structured viz payloads land in `explorer.py`.
- **Sessions are ephemeral.** A random `problem_id` is created per chat session (until D.1 multi-tenancy + Clerk auth lands). Refreshing the page = new session.

## Deployment

`frontier-web` ships as a second service in the repo's [`render.yaml`](../render.yaml) — pushing to `main` auto-deploys both the MCP engine and the web app. After Render provisions the new service for the first time, set `ANTHROPIC_API_KEY` (or `CLAUDE_API_KEY`) manually in the Render dashboard — it's declared `sync: false` so it stays out of source control.

Reference (already in `render.yaml`):

```yaml
services:
  - type: web
    name: frontier              # existing MCP service — unchanged
    runtime: python
    # ...

  - type: web
    name: frontier-web
    runtime: node
    rootDir: ui
    buildCommand: npm install && npm run build
    startCommand: npm start
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false             # set in Render dashboard
      - key: FRONTIER_MCP_URL
        value: https://frontier-592q.onrender.com/sse
      - key: AGENT_BACKEND
        value: messages-api
```

## Status

Phase 0.b MVP — pre-D.1, no auth, ephemeral sessions, single-user (every browser is a fresh user as far as Frontier MCP knows). Validates the chat UX + Anthropic Messages API + MCP connector path end-to-end before any heavier work.

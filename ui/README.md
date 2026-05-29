# Frontier Web

Lightweight web UI prototype for [Frontier](../README.md). Chat shell on top of the existing Frontier MCP server. Identity-only system prompt; all workflow behavior driven by the MCP server's tool descriptions, tool-response auto-injection, and skills.

## Setup

```bash
# 1. Start a local engine (ungated — no token) from the repo root:
MCP_TRANSPORT=sse python -m mcp_server.server   # serves http://localhost:8000/sse

# 2. Run the web app:
cd ui
cp .env.example .env.local         # add your ANTHROPIC_API_KEY
npm install
npm run dev                        # http://localhost:3000
```

The default `.env.example` uses the `anthropic-local` backend, which runs the agent loop in this app and talks to the local engine directly — **no public URL or token required**. Point elsewhere via `FRONTIER_MCP_URL` (full URL) or `FRONTIER_MCP_HOST` (host only — composes `https://$HOST/sse`); set `FRONTIER_MCP_TOKEN` if the target engine is gated.

## Stack

- **Next.js 15** (App Router, Node runtime for `/api/chat`)
- **React 19**, **Tailwind CSS**, **react-markdown** + `remark-gfm` for ASCII viz / table rendering
- **Anthropic SDK** (Messages API + MCP connector, `mcp-client-2025-11-20` beta)
- No DB; no per-user auth (optional shared-token gate on the engine); no AI SDK — straight SSE proxy from Anthropic streaming events to the client

## Pluggable agent runtime

[`lib/agent-runtime.ts`](lib/agent-runtime.ts) selects backend by `AGENT_BACKEND` env var:

| Value | Status | What it gets you |
|---|---|---|
| `messages-api` (prod default) | ✅ working | Messages API + server-side MCP connector — needs a public https engine |
| `anthropic-local` (local default) | ✅ working | Messages API + client-side MCP loop — works with a local or gated engine |
| `openai-compatible` | ✅ working | Any OpenAI-compatible provider + client-side MCP loop |
| `managed-agents` | 🚧 stub | Claude Managed Agents — memory, dreaming, telemetry, event SSE |
| `agent-sdk` | 🚧 stub | Claude Agent SDK — async workers |

Anthropic lock-in is bounded to this file. Swap cost: 3–5 days, mostly conversation-memory + telemetry reimplementation.

## Architecture notes

- **System prompt is identity-only** ([`lib/system-prompt.ts`](lib/system-prompt.ts)) — ~3 lines. **No skill content is duplicated here.** All workflow guidance flows from the MCP server. If you find yourself wanting to "fix" agent behavior by editing the system prompt, the fix actually belongs in `server.py` or a skill file in the engine.
- **Streaming is direct SSE** — no AI SDK on the server, no wire-format translation. Each `data: {...}` line is a raw Anthropic event the client renders incrementally.
- **Tool calls render inline** ([`components/ToolCallBlock.tsx`](components/ToolCallBlock.tsx)) — collapsed by default; click to expand input + result. Status dot is green/amber/red.
- **ASCII viz from the MCP server renders correctly** because `react-markdown` preserves monospace + whitespace in fenced code blocks. D3 charts swap in later once structured viz payloads land in `explorer.py`.
- **Sessions are ephemeral.** A random `problem_id` is created per chat session (until D.1 multi-tenancy + Clerk auth lands). Refreshing the page = new session.

## Deployment

Both services ship in the repo's [`render.yaml`](../render.yaml) — pushing to `main` (or pointing Render at your fork as a Blueprint, see the root [README](../README.md)) provisions the MCP engine and the web app together. The blueprint:

- **auto-generates one shared `FRONTIER_MCP_TOKEN`** (a Render env group) injected into both services, so the web app's connector calls carry the token the engine expects — no manual copying;
- **derives the engine URL** from the engine service's host via `fromService` (`FRONTIER_MCP_HOST`), so nothing is hardcoded;
- leaves only **`ANTHROPIC_API_KEY`** to set by hand (`sync: false`, so it stays out of source control).

```yaml
envVarGroups:
  - name: frontier-shared
    envVars:
      - key: FRONTIER_MCP_TOKEN
        generateValue: true            # shared by both services

services:
  - type: web
    name: frontier                     # MCP engine — gated by FRONTIER_MCP_TOKEN
    # ...
  - type: web
    name: frontier-web
    envVars:
      - fromGroup: frontier-shared      # sends the token via the MCP connector
      - key: FRONTIER_MCP_HOST
        fromService: { name: frontier, type: web, property: host }
      - key: ANTHROPIC_API_KEY
        sync: false                     # set in Render dashboard
      - key: AGENT_BACKEND
        value: messages-api
```

## Status

Phase 0.b MVP — pre-D.1. A single shared `FRONTIER_MCP_TOKEN` gates the engine, but there's no per-user identity yet: sessions are ephemeral and every browser shares one problem namespace (fine for a trusted closed beta; per-user `owner_id` scoping is the next step). Validates the chat UX + Anthropic Messages API + MCP connector path end-to-end before any heavier work.

# Frontier Web

Optional web UI for [Frontier](../README.md) — a thin chat shell over the Frontier MCP engine, for trying it without a coding-agent MCP client. No domain logic lives here; all workflow behavior comes from the engine's tools, `instructions`, auto-injected skills, and `viz_data` payloads.

## Run locally

```bash
# 1. Start a local engine (ungated — no token) from the repo root:
MCP_TRANSPORT=sse python -m mcp_server.server   # serves http://localhost:8000/sse

# 2. Run the web app:
cd ui
cp .env.example .env.local         # add your ANTHROPIC_API_KEY
npm install
npm run dev                        # http://localhost:3000
```

The default `.env.example` uses the `anthropic-local` backend — it runs the agent loop in this app against the local engine, so **no public URL or token is needed**. To point elsewhere, set `FRONTIER_MCP_URL` (or `FRONTIER_MCP_HOST`), plus `FRONTIER_MCP_TOKEN` if the target engine is gated. Backend choice is `AGENT_BACKEND` — see [`.env.example`](.env.example).

## Stack

Next.js 15 (App Router) · React 19 · Tailwind · react-markdown (prose + tables) · Anthropic SDK. Charts render client-side from the engine's `viz_data` (see [`../architecture.md`](../architecture.md) §5). No DB. Two independent gates: the engine's optional shared token (`FRONTIER_MCP_TOKEN`, app→engine) and the UI's own Basic-Auth password (`UI_ACCESS_PASSWORD` via [`middleware.ts`](middleware.ts)).

## Architecture & hosting

The design — pluggable agent runtime, thin system prompt (identity + engine `instructions` fetched and folded in), direct SSE streaming, `viz_data` chart rendering, ephemeral sessions — and the Render two-service + shared-token deploy model are documented in [`../architecture.md`](../architecture.md) §5. End-to-end deploy steps live in the root [README](../README.md).

A render-only route — `/render?problem_id=<id>` ([`app/api/render/route.ts`](app/api/render/route.ts)) — serves a problem's charts straight from engine state, no agent loop or API key involved; useful for demos, capture, and embedding. It sits behind the same Basic-Auth gate as the rest of the app.

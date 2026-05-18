# Frontier — Beta Distribution Architecture

> Design for Frontier's beta distribution surfaces. Builds on [`extensible-architecture.md`](extensible-architecture.md) (multi-client skill delivery + multi-tenancy planning) and operationalizes the [`Distribution & Access` section of roadmap.md](../../../Obsidian_Vault/projects/frontier/roadmap.md).
>
> **Cross-references:** [`architecture.md`](../../architecture.md) — system architecture, tool/skill reference | [`best-practices.md`](../../best-practices.md) — skill, prompt & MCP design guidelines | [`roadmap.md`](../../../Obsidian_Vault/projects/frontier/roadmap.md) — Phase 1–5 capability roadmap and Distribution & Access section (D.1–D.4)

---

## 1. Context & North Star

### What's already in place
- Frontier MCP server is live (`https://frontier-592q.onrender.com/sse`) with 4 tools (`model`, `solve`, `explore`, `get_skill`) and 4 skills, deployed on Render.
- Skills are delivered universally via the `get_skill` tool plus tool-response auto-injection at workflow transitions (see [architecture.md §2 Skill Auto-Injection](../../architecture.md)). The `extensible-architecture.md` Phase 1 (multi-client skill delivery) is shipped.
- Phase 1 capabilities (NSGA-II/III, scenarios, curation, marginal analysis, frontier shape, CVaR, redundancy) are complete and live-verified.
- No auth, no per-user scoping, no web surface. Engine is open and ephemeral by problem_id.

### North star
A user can reach Frontier via the surface that matches their intent and technical depth:

| Persona | Goal | Surface |
|---|---|---|
| Analyst / PM (no AI tooling) | Make a structured decision | **Simple web UI** at a public URL |
| Consumer Claude / ChatGPT user | Use Frontier inside their existing assistant | **Claude.ai Custom Connector** / **ChatGPT App** |
| Developer (Claude Code, Codex CLI, Cursor) | Drive Frontier from their coding agent | **Direct MCP** with copy-paste config |

### Twin goals (from roadmap)
1. Validate Frontier's actual Phase 1 TAM (analysts/PMs) without diluting "engine, not interface."
2. Decouple distribution from any single platform's user base.

### Constraint
**Never redo the core engine.** All four surface paths consume the same FastMCP server. State, skills, eval, and optimization rigor live in one place.

---

## 2. Principles

1. **One engine, multiple surfaces.** MCP server stays the canonical source of skills, state, and tools. Surfaces consume; they don't fork.
2. **MCP server drives behavior; surfaces are intentionally thin.** All workflow guidance — skill content, framing context, tool semantics, error correction — lives in the MCP server (tool descriptions, server instructions, tool-response auto-injection, `get_skill` fallback). Surfaces (web UI, consumer connectors, coding agents) are dumb consumers.
   - **The consumer connector path is the design target.** It's the lowest common denominator: no system-prompt control, no skill auto-loading, just tool calls and tool responses. If the agent can drive the full workflow from a Claude.ai Custom Connector / ChatGPT App with zero extra scaffolding, every other surface works strictly easier.
   - **No skill content is duplicated into any surface's system prompt.** Web UI system prompt is identity-only; behavior shaping happens server-side.
3. **Auth: bearer tokens first, OAuth later.** Bearer headers work on every MCP host today (Claude Code, Codex CLI, Cursor — including those without dynamic client registration). OAuth 2.1 layered on top later (when FastMCP + a hosted IdP makes Claude.ai's auto-OAuth flow possible).
4. **Pluggable agent runtime, vendor-neutral everywhere else.** The web UI's agent layer sits behind an adapter interface with three backends: Claude Managed Agents (default for beta — gets us memory, dreaming, telemetry, event SSE for free), Messages API + MCP connector (simplest fallback, zero feature dependencies), and Claude Agent SDK (local dev / future async workers). One env var (`AGENT_BACKEND`) swaps. Everything else — MCP server, skills, state, Postgres, coding-agent surface, consumer connectors, web UI shell + viz — stays vendor-neutral. Anthropic lock-in is bounded to the web-UI runtime and reversible in days.
5. **Distribution is share-a-link, not app-store.** No public directories exist for either Claude Custom Connectors or ChatGPT Apps as of mid-2026. Surface signup is a URL the user pastes into their settings — fine for targeted beta.

---

## 3. Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│ Surfaces                                                           │
│                                                                    │
│  Web UI            Claude.ai           ChatGPT          Coding     │
│  (analysts/PMs)    Custom Connector    App              agents     │
│  Next.js + Clerk   OAuth (auto)        OAuth (auto)     Bearer     │
│  on Render         (consumer)          (consumer)       (devs)     │
│       │                  │                 │              │        │
└───────┼──────────────────┼─────────────────┼──────────────┼────────┘
        │                  │                 │              │
        ▼                  │                 │              │
┌──────────────────────┐   │                 │              │
│ Pluggable Agent      │   │ (these surfaces call MCP directly       │
│ Runtime (web UI only)│   │  via the user's own client — no agent   │
│  AGENT_BACKEND ∈ {   │   │  runtime sits in front)                 │
│   managed-agents,    │   │                                         │
│   messages-api,      │   │                                         │
│   agent-sdk          │   │                                         │
│  } (one env var)     │   │                                         │
│                      │   │                                         │
│ default: managed-    │   │                                         │
│ agents (memory,      │   │                                         │
│ dreaming, telemetry, │   │                                         │
│ event SSE for free)  │   │                                         │
└──────────┬───────────┘   │                                         │
           │               │                                         │
           ▼               ▼                 ▼              ▼
┌────────────────────────────────────────────────────────────────────┐
│ Auth & Token Layer (Phase 1 = bearer; Phase 2 = OAuth front)       │
│  - Per-user bearer tokens minted by Clerk-backed Render route      │
│  - Phase 2: OAuth metadata endpoints (WorkOS / Clerk MCP-Auth)     │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│ Frontier MCP Server (FastMCP, Render, /mcp streamable HTTP)        │
│  - 4 tools, 4 skills, server-side auto-injection                   │
│  - owner_id scoping on Problem (D.1)                               │
│  - Token verification middleware                                   │
│  - Engine layer unchanged (optimizer, explorer, metrics, models)   │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│ Persistence (D.1)                                                  │
│  - PostgresStore (Render) — problems(id, owner_id, data jsonb, ...)│
│  - JsonFileStore retained for local dev                            │
└────────────────────────────────────────────────────────────────────┘
```

### Sharing across surfaces
- **State**: a problem created in any surface is reachable from any other (same `owner_id`, same engine).
- **Skills**: identical content delivered identically (tool-response injection).
- **Auth**: one user identity → one token → one set of problems regardless of where they're driving Frontier from.

---

## 4. Surfaces

### 4.1 Web UI — primary beta surface (D.2)

**Stack** (all current as of 2026):

| Layer | Choice | Why |
|---|---|---|
| Framework | Next.js 15 (App Router) on **Render** (web service) | Co-located with existing MCP server; no serverless function timeout cap (Render runs full Node processes — important for 10–30s `solve/run` calls); single `render.yaml` blueprint declares both services |
| Agent runtime | **Claude Managed Agents** (default) via pluggable adapter — fallback to Messages API + MCP connector or Agent SDK via `AGENT_BACKEND` env var | Managed Agents brings memory + dreaming + telemetry + event SSE for free during beta; adapter keeps lock-in reversible in days |
| LLM SDK (UI side) | **Vercel AI SDK 6** + `@ai-sdk/react` for `useChat` and typed tool parts | Runs anywhere; handles streaming, tool-call rendering, file attachments uniformly regardless of which agent backend is active |
| Chat UI | AI SDK 6 `useChat` + custom `tool-frontier_*` parts | ASCII viz renders cleanly in markdown; tool-call placeholders prevent UI freeze during long solves |
| Auth | **Clerk** (magic link + Google OAuth) | ~30 min to first login; prebuilt `<UserButton/>`; framework-agnostic |
| DB | **Render Postgres** (co-located with MCP server) | Same platform = simpler ops + lower latency from MCP to DB; ~$7/mo Starter |
| MCP transport | Streamable HTTP at `/mcp` | Hardened transport; SSE has had multiple 2025–2026 CVEs |

**Why not Claude Agent SDK for the web UI?** Vercel AI SDK is the match for Next.js (typed React hooks, edge-compatible streaming). Agent SDK is better-suited for server-side workers (e.g., long-running background optimization) — keep that option open for later.

**Key implementation note (skill delivery on this surface):** The Anthropic Messages API MCP connector does **not** pass MCP server `instructions` through to the model — only `tool_use` blocks. But this matters less than it sounds: the design target is the **consumer connector path** (claude.ai / ChatGPT App), which also has no system-prompt control. If the MCP server is sufficient there, it's sufficient here.

- Web UI system prompt is **identity-only** (~3 lines): no behavior shaping, no skill pointers, no workflow scaffolding. Matches what the consumer connector path gets (nothing Frontier-specific).
- All workflow guidance flows from the MCP server: tool descriptions, server instructions (where the host passes them), tool-response auto-injection, `get_skill` fallback.
- If something is missing from the consumer-path behavior, the fix lives in the MCP server (richer tool descriptions, first-call injection enrichment, better error messages) — never in the web UI system prompt.

**System prompt** (~3 lines, stored in `frontier-web/app/api/chat/system-prompt.ts`):
```
You are Frontier, an assistant for structured multi-objective decision making.
Use the available frontier tools to help users model decisions, run optimization,
and explore tradeoffs. Tool responses include workflow guidance — read and apply it.
```

That's it. Anything beyond this gets pushed to the MCP server so all surfaces benefit identically.

**Token flow:**
1. User signs in via Clerk → web app has `clerkUserId`.
2. On chat session start, web app calls `POST /api/frontier-token` (server-side route) → mints a short-lived (24h) JWT scoped to `owner_id = clerkUserId`.
3. Token attached as `Authorization: Bearer <jwt>` on every Messages API request via `mcp_servers[0].authorization_token`.
4. Frontier MCP middleware validates JWT, extracts `owner_id`, scopes all `model/list` / `model/get` / etc. queries.

**Onboarding UX:** blank chat with one-line prompt ("Describe a decision you're trying to make"). No tutorial. File drop accepts CSV/markdown for score tables. Curated set downloaded as `.md` or `.csv` from a chat affordance (renders `export_curated` payload as a download link).

### 4.2 Claude.ai Custom Connector — consumer surface

**What we ship:** nothing beyond an OAuth-protected MCP server (Phase 2). The Custom Connectors flow is fully GA on claude.ai for Pro/Max/Team/Enterprise — the user pastes a URL into Settings → Connectors, claude.ai runs the OAuth flow, and Frontier appears as a tool source in their chats.

**Setup the user does** (one-time):
1. Settings → Connectors → Add custom connector.
2. Paste `https://frontier-592q.onrender.com/mcp`.
3. claude.ai redirects to Frontier's OAuth (`/.well-known/oauth-protected-resource` → IdP) → user logs in → token issued → claude.ai stores it.
4. New conversations have `frontier` tools available.

**Distribution model:** share the URL via beta invite email or docs page. There is **no public Claude connector directory** as of mid-2026 — discovery is "share the link."

**Status:** blocked on Phase 2 OAuth (D.1.b below). Until OAuth lands, this surface is unavailable. Bearer tokens alone won't work — claude.ai's Custom Connector flow requires OAuth 2.1.

### 4.3 ChatGPT App — consumer surface

**What we ship:** the same OAuth-protected MCP server. ChatGPT renamed "connectors" to "Apps" in December 2025; the install path is identical in shape to claude.ai's.

**Setup the user does** (one-time):
1. Settings → Apps & Connectors → Add MCP server.
2. Paste the URL.
3. OAuth flow runs, app installs.

**Availability gotcha:** Business / Enterprise / Edu users get this by default. **Pro and Team users must enable Developer Mode** in settings first. Document this in setup docs.

**Distribution model:** share the URL. No GPT-Store-equivalent for MCP servers exists yet.

**Status:** same as Claude.ai — blocked on Phase 2 OAuth. Add to docs once D.1.b ships.

### 4.4 Coding agents — direct MCP (D.3)

For developers who already drive Claude Code, Codex CLI, Cursor, Claude Desktop, claude.ai with their own MCP setup, or Cowork. Same engine, same skills.

**One docs page** with copy-paste snippets per host. Bearer-token version (works everywhere now); OAuth version (when D.1.b ships).

**Bearer-token examples:**

```bash
# Claude Code
claude mcp add frontier --transport http \
  --url https://frontier-592q.onrender.com/mcp \
  --header "Authorization: Bearer $FRONTIER_TOKEN"

# Codex CLI (~/.codex/config.toml)
[mcp_servers.frontier]
url = "https://frontier-592q.onrender.com/mcp"
bearer_token_env_var = "FRONTIER_TOKEN"

# Cursor (~/.cursor/mcp.json)
{
  "mcpServers": {
    "frontier": {
      "url": "https://frontier-592q.onrender.com/mcp",
      "headers": { "Authorization": "Bearer ${env:FRONTIER_TOKEN}" }
    }
  }
}
```

**Token issuance:** users sign into the web app, click "Generate personal MCP token" on an account page, copy the token, paste into their host config. Same `POST /api/frontier-token` endpoint as the web app uses, just with a longer TTL (e.g. 90 days) and surfaced UI.

**Cursor caveat:** Cursor doesn't support Dynamic Client Registration today — bearer-token path is preferred even after D.1.b OAuth lands. OAuth on Cursor will need a static client ID workflow, which we'll add only if signal demands it.

---

## 5. Engine Changes (D.1 — Multi-Tenant Foundation)

### 5.1.a Persistent storage + per-user scoping

(Builds on [`extensible-architecture.md` Phase 2](extensible-architecture.md) — protocol is already designed.)

- **Add `owner_id: str` to `Problem` model** (`frontier/engine/models.py`).
- **Refactor `Store` into `StoreBackend` protocol** with `JsonFileStore` (dev/tests) and `PostgresStore` (production). Single `problems(id, owner_id, data jsonb, created_at, updated_at)` table on Render Postgres (co-located with the MCP web service). No ORM — round-trip via `model_dump_json` / `model_validate_json`.
- **Filter list/get/delete by `owner_id`.** A request without an `owner_id` (local dev) gets the global namespace; production always sets it from the validated token.
- **Migration script:** `frontier/scripts/migrate_jsonl_to_postgres.py` — reads `./data/*.json`, assigns to a default owner, inserts.

**Estimated scope:** ~150 lines + tests. Already partly designed in the prior plan.

### 5.1.b Token verification middleware

- **Phase 1 (bearer-only, ~1 wk):** FastMCP middleware that reads `Authorization: Bearer <jwt>`, verifies signature against a shared secret (env var), extracts `sub` as `owner_id`, attaches to request context. JWTs minted by the web app's Next.js route (`POST /api/frontier-token`) and by the account-page issuance UI for power users.
- **Phase 2 (OAuth 2.1 front, ~1 wk + IdP integration):** Add `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server` endpoints fronting FastMCP. Pair with **WorkOS AuthKit** or **Clerk MCP-Auth** as the IdP — both have FastMCP integration guides. Unlocks claude.ai Custom Connectors and ChatGPT Apps.

### 5.1.c Skill delivery — server-side, surface-agnostic

Server-side auto-injection in tool responses (already in `server.py`) works identically across surfaces:

| Surface | Server instructions on connect | Tool-response injection | `get_skill` tool |
|---|---|---|---|
| Web UI (Messages API + connector) | ❌ not passed through | ✅ works | ✅ works |
| Claude.ai Custom Connector | ✅ passed | ✅ works | ✅ works |
| ChatGPT App | ✅ passed | ✅ works | ✅ works |
| Claude Code / Desktop | ✅ passed | ✅ works | ✅ works |
| Codex CLI / Cursor | ✅ passed (host-dependent) | ✅ works | ✅ works |

**Design target: the workflow must be self-driving from MCP-server signals alone**, because the consumer-connector path has no system-prompt scaffolding and the Messages API path doesn't get server instructions. Tool descriptions, tool-response injection, and `get_skill` together must be sufficient.

**If the Phase 0.a spike (Section 7) shows tool-response injection is insufficient on its own:** the fix is to enrich the FIRST tool-call response with the framing context that currently lives in server instructions (condensed `problem_framing` + constraint schemas + scores schema). One-time per session, gated by problem state. This change lives in `server.py` and benefits all surfaces simultaneously. Estimated ~40 lines.

**Diagnostic principle:** if a surface needs special system-prompt help to drive the workflow, that's a signal the MCP server should be enriched — not the surface patched.

### 5.1.d Telemetry (D.4)

Per-user, per-stage tool-call logging in `metrics.py`. Skill-firing telemetry: which auto-inject triggers fire, which `get_skill` calls fire (signal that auto-injection missed the moment). `explore feedback` already records ratings — extend to capture surface (web vs MCP-direct).

---

## 6. Stack Decisions Summary

| Concern | Decision | Why this beats alternatives |
|---|---|---|
| Web framework | Next.js 15 on **Render** | Co-located with existing MCP server; no function timeout cap (full Node web service runs 30s `solve/run` cleanly); single `render.yaml` blueprint for both services |
| Agent runtime | **Claude Managed Agents** (default) behind a pluggable adapter; fallbacks: Messages API + MCP connector, Claude Agent SDK | Get memory + dreaming + telemetry + event SSE in beta for free; one env var to swap; lock-in bounded to web UI runtime only |
| UI streaming | Vercel AI SDK 6 (`useChat`, typed tool parts) | Backend-agnostic; runs on Render; handles tool-call rendering and file attachments |
| Auth (web) | Clerk | Fastest to first login; framework- and platform-agnostic; reassess at 5K MAU |
| Auth (MCP server) | Bearer JWT now → OAuth 2.1 later (WorkOS or Clerk MCP-Auth) | Bearer is universal today; OAuth unlocks Claude.ai/ChatGPT later |
| DB | **Render Postgres** (co-located) | Same platform as MCP and web app = simpler ops, lower latency |
| Hosting | **Render** (one platform for MCP + web UI + DB) | Already have account; saves a vendor; no Vercel function-timeout problem |
| MCP transport | Streamable HTTP at `/mcp` | Hardened; deprecate `/sse` per 2025–2026 spec |
| Skill delivery | Server-side tool-response injection (unchanged) | Universal; no surface duplication |
| Memory (cross-session) | Postgres (problems), ephemeral (chat) for now; managed memory later | Avoid building what Anthropic will offer |

---

## 7. Phased Implementation

Each phase is a coherent ship-able milestone. **Order is sequential** because each unlocks the next surface.

**Sequencing note:** the opportunity is reaching users *outside* coding agents — the web UI (analysts/PMs) and consumer connectors (Claude.ai / ChatGPT) are the two primary legs. Direct MCP for coding agents (D.3) is existing leverage — keep it as opt-in docs, not a milestone.

### Phase 0.a — Consumer-path + agent-runtime spike (~2–3 hours)
Goal: validate (1) the MCP server is self-driving with no system-prompt scaffolding (the consumer-connector design target) and (2) both candidate agent backends work against it, so the adapter choice is informed.

**0.a-i — Messages API + MCP connector (~1 hr).** Single Node or Python script: Anthropic Messages API with `mcp_servers: [Frontier URL]`, **no system prompt** (or identity-only, simulating the consumer connector reality). Test prompt: "Help me prioritize 5 product initiatives for next quarter, balancing engineering cost, customer impact, and strategic fit." Verify the agent drives `model/create` → `solve/run` → `explore/tradeoffs` using only tool descriptions + tool-response auto-injection + `get_skill`. Baseline.

**0.a-ii — Claude Managed Agents (~1–2 hrs).** Create a Managed Agent via API with Frontier MCP attached and the same identity-only configuration. Send the same test prompt. Capture: (a) does the workflow still self-drive correctly? (b) does conversation memory persist across sessions usefully? (c) what's the event stream / telemetry look like? (d) cost per session?

**Decision tree:**
- ✅ Both work, Managed Agents adds meaningful value → adapter defaults to `managed-agents` for Phase 0.b.
- ⚠️ Both work, Managed Agents adds little for the use case → default to `messages-api` (cheaper, fewer dependencies). Keep Managed Agents adapter for later experimentation.
- ❌ MCP server isn't self-driving on either path → fix in MCP server: enrich tool descriptions and/or auto-inject framing context on first call (see §5.1.c). Benefits all surfaces.

**Why both before anything else:** the choice of default backend shapes Phase 0.b's adapter implementation. Failure modes or feature surprises (memory quirks, telemetry surface, dreaming behavior) discovered in a script are 10× cheaper to address than after the chat shell is built. Either way, the MCP server is the constant — and proving it's self-driving from the consumer-path baseline is non-negotiable.

### Phase 0.b — Web UI demo (~3–5 days)
Goal: a sharable URL for live demos, no auth, ephemeral problems.

- Scaffold Next.js + AI SDK 6 (`useChat`, typed tool parts) on Render.
- **Pluggable agent runtime** in `lib/agent-runtime/`: adapters for `managed-agents` (default), `messages-api`, `agent-sdk`. Chosen via `AGENT_BACKEND` env var (~100 lines glue).
- Identity-only system prompt where the backend accepts one (Section 4.1) — most behavior shaping lives in the MCP server regardless of backend.
- Custom `tool-frontier_*` UI parts so optimization runs render with progress, not frozen UI.
- File drop for CSV/markdown score tables.
- Download affordance for `export_curated`.
- Deploy to Render as a web service alongside the existing MCP service in the same `render.yaml`.
- Random `problem_id` per browser session (until D.1 ships). Note: when `AGENT_BACKEND=managed-agents`, Anthropic's session/event store handles conversation continuity for free — but problem state still lives in Frontier MCP.

**Output:** `frontier-demo.onrender.com` (or custom subdomain) — sharable URL for targeted demos.

### Phase 1 — Multi-tenant engine (D.1, ~1 wk)
Goal: real per-user state, ready for non-demo beta.

- 1.a — Add `owner_id` to `Problem`, `PostgresStore`, migration script.
- 1.b — Bearer-token middleware on FastMCP.
- 1.c — `POST /api/frontier-token` route in web app (24h JWT, scoped to Clerk user).
- 1.d — Web app: replace ephemeral session with Clerk auth + token attach.
- 1.e — Verify skill auto-injection regression-free (test all four trigger points).

**Output:** beta-ready web app with persistent per-user problems.

### Phase 2 — Consumer integrations (~1 wk + IdP setup) **[promoted — opportunity leg 2]**
Goal: Frontier installable in claude.ai and ChatGPT — reaches the second slice of users outside coding agents.

- 2.a — Stand up OAuth 2.1 front for the MCP server (WorkOS AuthKit or Clerk MCP-Auth — decide before this phase).
- 2.b — Test claude.ai Custom Connector flow end-to-end.
- 2.c — Test ChatGPT App flow end-to-end (Pro Developer Mode + Business).
- 2.d — Update docs page with consumer install paths (share-the-URL pattern).

**Output:** three primary surfaces live (web UI + Claude.ai + ChatGPT). Phase 0.a's design-target validation pays off here directly.

### Phase 3 — Operations (D.4, parallel with Phases 1–2)
Goal: signal pipeline.

- 3.a — Per-user, per-stage tool-call logging (extend `metrics.py`).
- 3.b — Skill-firing telemetry (auto-inject triggers, `get_skill` calls).
- 3.c — `explore feedback` extended with `surface` field (web | claude-connector | chatgpt-app | mcp-direct).
- 3.d — Internal dashboard (e.g. simple `/admin` page reading from Postgres).

**Output:** signal to iterate skill content from real usage, not host-specific prompting variance.

### Phase 4 — Power-user opt-in (D.3, ~3 days) **[demoted — free leverage, not a milestone]**
Goal: developers can drive Frontier from their existing coding agent.

- 4.a — Account page: "Generate personal MCP token" button (90-day TTL).
- 4.b — Single docs page (`docs/connect-your-agent.md`): copy-paste snippets for Claude Code, Claude Desktop, Codex CLI, Cursor, Cowork — bearer-token form.
- 4.c — Don't surface in beta invites — offer 1:1 to power users who ask.

**Output:** developer surface live, free leverage given Phase 1.

**Total to "outside coding agents" beta (web UI + Claude.ai + ChatGPT):** ~3 weeks of focused work + IdP integration buffer.

---

## 8. Backend Swap-Ability (Reversibility Plan)

Managed Agents is the *default* beta backend — but the architecture treats it as one of three interchangeable agent runtimes behind the same adapter interface. The web UI, MCP server, state, skills, and all other surfaces are vendor-neutral. Swap cost stays bounded.

**When to swap away from Managed Agents:**
- Pricing changes that hurt unit economics
- Feature deprecation (e.g., memory or telemetry behavior changes in ways we depend on)
- Strategic shift toward platform-neutral distribution
- Multi-LLM future (route to non-Anthropic models for some users)

**What swapping changes:**
- `AGENT_BACKEND` env var flips to `messages-api` or `agent-sdk`.
- Conversation memory: lost (Anthropic-side) → must implement our own (Render Postgres `conversations(user_id, messages jsonb)` — ~50 lines).
- Telemetry: lost free SSE stream → wire our own via `metrics.py` server-side (already planned in D.4).
- Event/session history: lost server-side persistence → store in Postgres (~30 lines).

**What swapping doesn't change:**
- Frontier MCP server, tools, skills, optimizer, explorer, persistence.
- `owner_id` scoping, Clerk auth, web UI shell, viz components.
- All non-web surfaces (Claude.ai Custom Connector, ChatGPT App, coding agents).
- Skill delivery (tool-response injection is server-side and runtime-agnostic).

**Estimated swap cost:** 3–5 days of focused work (memory + telemetry reimplementation; UI shell unchanged because the adapter abstracts the backend).

**Phase 5 alignment** (`roadmap.md` Phase 5 — Persistent Decision Agent):
- 5.1 Session persistence and problem history → D.1 Postgres + `owner_id` (independent of agent runtime).
- 5.2 Organizational memory → Frontier-engine work; never provided by any agent runtime's generic memory.
- 5.3 Proactive gap-filling → uses 5.1/5.2 substrate; runtime-agnostic.
- Managed Agents conversation memory complements 5.1 *during the beta* (user-level continuity for free); when/if we swap away, we reimplement only the conversation-memory slice, not the Frontier-engine memory.

**Strategic note:** running on Managed Agents during beta is *itself* useful — it produces real signal on what generic agent memory and dreaming-style features add for decision-making workflows. That informs which Phase 5 features to invest in vs continue offloading.

---

## 9. Open Questions

1. **OAuth IdP choice (Phase 4).** WorkOS AuthKit vs Clerk MCP-Auth vs Scalekit — all have FastMCP guides. Decide closer to ship; not blocking Phase 0–3.
2. **Bearer token TTL for power users.** 90 days is pragmatic but weak; rotate via account-page UI on demand. Revisit after first incident (if any).
3. **Should the web app run a server-side Agent SDK loop for very long solves?** Render web services don't have function timeouts, so this is no longer a hosting constraint. But if `solve/run` in `mode="thorough"` ever exceeds the HTTP keep-alive comfort zone (~60s+), consider: (a) push to a Render background worker with status polling, (b) move to Claude Agent SDK on a small backend, (c) keep `mode="fast"` default and accept ceiling. Defer until signal.
4. **Cursor OAuth.** No DCR support today; bearer-only for now. Revisit if Cursor ships DCR.
5. **Memory scope at Phase 5.** Managed-agent memory handles "remember user prefers fast mode"; Frontier engine handles "remember this org's scoring rubric." Watch for boundary disputes as Phase 5 features come online.

---

## 10. References

### Internal
- [`architecture.md`](../../architecture.md) — system architecture, tools/skills, data flow
- [`best-practices.md`](../../best-practices.md) — skill, prompt & MCP design guidelines
- [`roadmap.md`](../../../Obsidian_Vault/projects/frontier/roadmap.md) — Distribution & Access section (D.1–D.4) and Phase 1–5 capabilities
- [`extensible-architecture.md`](extensible-architecture.md) — prior plan; this doc supersedes it for distribution and extends Phase 2 multi-tenancy

### External (research current as of mid-2026)
- [Anthropic MCP connector docs](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector)
- [Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview)
- [Claude Custom Connectors (consumer)](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)
- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Vercel AI SDK 6 release](https://vercel.com/blog/ai-sdk-6)
- [AI SDK MCP tools docs](https://ai-sdk.dev/docs/ai-sdk-core/mcp-tools)
- [AI SDK Anthropic provider](https://ai-sdk.dev/providers/ai-sdk-providers/anthropic)
- [OpenAI Codex MCP docs](https://developers.openai.com/codex/mcp)
- [ChatGPT MCP for developers](https://developers.openai.com/api/docs/mcp)
- [ChatGPT Developer Mode beta](https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta)
- [Cursor MCP docs](https://cursor.com/docs/mcp)
- [FastMCP × Anthropic integration](https://gofastmcp.com/integrations/anthropic)
- [FastMCP OAuth client](https://gofastmcp.com/clients/auth/oauth)
- [Securing FastMCP with Scalekit](https://www.scalekit.com/blog/securing-fastmcp-with-scalekit)
- [MCP Authorization spec (Nov 2025 rev)](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [Better Auth vs Clerk vs NextAuth (2026)](https://supastarter.dev/blog/better-auth-vs-nextauth-vs-clerk)
- [LogRocket Next.js auth comparison 2026](https://blog.logrocket.com/best-auth-library-nextjs-2026/)
- [Render MCP hosting guide](https://render.com/articles/building-and-hosting-mcp-servers-a-complete-guide)
- [Neon vs Supabase vs PlanetScale 2026](https://dev.to/whoffagents/neon-vs-supabase-vs-planetscale-managed-postgres-for-nextjs-in-2026-2el4)
- [Railway vs Render vs Fly.io 2026](https://devtoolpicks.com/blog/railway-vs-render-vs-fly-io-solo-developers-2026)

---

## Status

**Created:** 2026-05-07. **Status:** active design doc, not yet started.
**Supersedes:** `extensible-architecture.md` for distribution-layer concerns; that doc's Phase 2 multi-tenancy work folds into D.1 here.
**Next action:** review with product lead, then begin Phase 0 web UI demo (~3–5 days).

/**
 * Anthropic request-shaping for input-token cost: prompt caching + native context management.
 * Pure and dependency-free (no imports) so it can be unit-tested in isolation, like
 * compaction.ts. The adapters in agent-runtime.ts apply these to the request they send.
 */

// ─── prompt caching ─────────────────────────────────────────────────────────
// The single biggest cost lever. Without `cache_control`, every turn — and every server-side
// tool-call iteration in the connector loop — re-processes the full input at FULL price: the
// stable prefix (system prompt, the four tool definitions, and the injected skill bodies that
// ride in history — ~13.5k tokens for solution_interpreter alone) is paid for again and again.
// Caching marks that prefix so it's re-read at ~10% of input price. It KEEPS all content in
// context — skill bodies stay available to the model, just cheap to re-read — it removes
// nothing. Caching covers tools → system → messages up to each breakpoint; for an mcp_toolset
// the breakpoint lands on the toolset entry. Toggle off with AGENT_PROMPT_CACHE=off.
export const PROMPT_CACHE = (process.env.AGENT_PROMPT_CACHE ?? "on").toLowerCase() !== "off";

// Frozen so the shared reference can't be mutated in place into every breakpoint at once.
const CACHE_CONTROL = Object.freeze({ type: "ephemeral" as const });

// Block types that cannot carry cache_control (the API rejects a breakpoint on them).
const UNCACHEABLE_BLOCK_TYPES = new Set(["thinking", "redacted_thinking"]);

// System as a cacheable text block (the API accepts a string OR a block array).
export function cachedSystem(text: string, enabled: boolean = PROMPT_CACHE): unknown {
  return enabled ? [{ type: "text", text, cache_control: CACHE_CONTROL }] : text;
}

// Put a cache breakpoint on the last tool (for an mcp_toolset, the entry itself) so the whole
// tool-definition block is cached. Pure: shallow copy, original untouched.
export function cachedTools<T>(tools: T[], enabled: boolean = PROMPT_CACHE): T[] {
  if (!enabled || tools.length === 0) return tools;
  const out = tools.slice();
  out[out.length - 1] = { ...out[out.length - 1], cache_control: CACHE_CONTROL } as T;
  return out;
}

// Put a cache breakpoint on the last message's final content block, so the conversation prefix
// (prior turns, incl. injected skill bodies and old tool results) is cached and re-read cheaply
// on later turns / tool-call iterations. Pure: shallow copy, drops nothing. Skips the breakpoint
// when the final block can't carry one (e.g. a trailing thinking block) — system + tools stay
// cached regardless.
export function withCacheBreakpoint<T extends { role: string; content: unknown }>(
  messages: T[],
  enabled: boolean = PROMPT_CACHE,
): T[] {
  if (!enabled || messages.length === 0) return messages;
  const out = messages.slice();
  const last = out[out.length - 1];
  const blocks =
    typeof last.content === "string"
      ? [{ type: "text", text: last.content }]
      : Array.isArray(last.content)
        ? (last.content as Record<string, unknown>[]).slice()
        : null;
  if (!blocks || blocks.length === 0) return messages;
  const lastBlock = blocks[blocks.length - 1] as { type?: string };
  if (lastBlock && typeof lastBlock.type === "string" && UNCACHEABLE_BLOCK_TYPES.has(lastBlock.type)) {
    return messages;
  }
  blocks[blocks.length - 1] = { ...blocks[blocks.length - 1], cache_control: CACHE_CONTROL };
  out[out.length - 1] = { ...last, content: blocks } as T;
  return out;
}

// ─── native context management ──────────────────────────────────────────────
// Anthropic's server-side context management, layered on the Anthropic adapters so a long
// session is managed the way a coding-agent harness does. `clear_tool_uses` drops the oldest
// tool results — Frontier's large explore/solve JSON — with a placeholder; `compact` summarizes.
//
// Skill-content note: `exclude_tools: ["get_skill"]` keeps the *explicit* re-fetch path intact,
// but the *primary* skill delivery is auto-injection of full skill bodies INTO solve/explore/
// model tool results — those are NOT excluded, so a firing `clear_tool_uses` (or `compact`) can
// trim them on a long session. That's by design: the durable guidance index (system prompt) +
// get_skill re-fetch keep guidance recoverable, and prompt caching keeps the bodies present and
// cheap until they age out. So caching alone removes nothing; context management trims, and the
// re-fetch path is the safety net (not "never cleared").
export const CONTEXT_MGMT = process.env.AGENT_CONTEXT_MANAGEMENT ?? "clear_tool_uses";

export function contextManagement(
  mode: string = CONTEXT_MGMT,
): { beta: string; context_management: unknown } | null {
  if (mode === "clear_tool_uses") {
    return {
      beta: "context-management-2025-06-27",
      context_management: {
        edits: [{ type: "clear_tool_uses_20250919", exclude_tools: ["get_skill"] }],
      },
    };
  }
  if (mode === "compact") {
    // compact summarizes the whole conversation; it has no exclude_tools, so guidance is
    // condensed into the summary rather than protected verbatim — durable-index re-fetch applies.
    return {
      beta: "compact-2026-01-12",
      context_management: { edits: [{ type: "compact_20260112" }] },
    };
  }
  return null; // "off" or unrecognized → client-side applyCompaction only
}

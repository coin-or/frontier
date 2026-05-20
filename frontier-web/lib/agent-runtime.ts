/**
 * Pluggable agent runtime — single env var (`AGENT_BACKEND`) selects the adapter.
 *
 * Default: `messages-api` (Anthropic Messages API + MCP connector).
 * Fallbacks: `managed-agents` (Claude Managed Agents, stub), `agent-sdk` (stub).
 *
 * Per the design doc (§2 Principle 4), Anthropic lock-in is bounded to this
 * file. Swapping backends does not require changes to the chat shell, MCP
 * server, skills, or any other surface. Estimated swap cost: 3–5 days, mostly
 * memory/telemetry reimplementation.
 */

import Anthropic from "@anthropic-ai/sdk";
import { SYSTEM_PROMPT } from "./system-prompt";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string | unknown;
};

export type AgentRuntime = {
  stream: (messages: ChatMessage[]) => Promise<ReadableStream<Uint8Array>>;
};

const FRONTIER_MCP_URL =
  process.env.FRONTIER_MCP_URL ?? "https://frontier-592q.onrender.com/sse";
const MODEL = process.env.ANTHROPIC_MODEL ?? "claude-opus-4-7";

// ─── messages-api adapter (default) ─────────────────────────────────────────

const messagesApiAdapter: AgentRuntime = {
  async stream(messages) {
    const apiKey = process.env.ANTHROPIC_API_KEY || process.env.CLAUDE_API_KEY;
    if (!apiKey) throw new Error("ANTHROPIC_API_KEY (or CLAUDE_API_KEY) not set");
    const client = new Anthropic({ apiKey });
    const encoder = new TextEncoder();

    // Use the beta MCP-connector path. Anthropic runs the agent loop server-side,
    // including calling Frontier MCP tools and looping back with results.
    // Per mcp-client-2025-11-20 schema: mcp_servers defines connections,
    // tools array references them via mcp_toolset entries.
    // SDK 0.40.1 partially types these; cast as any to keep the surface clean.
    const params: any = {
      model: MODEL,
      max_tokens: 8000,
      system: SYSTEM_PROMPT,
      mcp_servers: [
        { type: "url", url: FRONTIER_MCP_URL, name: "frontier" },
      ],
      tools: [
        { type: "mcp_toolset", mcp_server_name: "frontier" },
      ],
      messages: messages as Anthropic.MessageParam[],
      betas: ["mcp-client-2025-11-20"],
    };
    const upstream = await client.beta.messages.stream(params);

    return new ReadableStream<Uint8Array>({
      async start(controller) {
        try {
          for await (const event of upstream) {
            const chunk = `data: ${JSON.stringify(event)}\n\n`;
            controller.enqueue(encoder.encode(chunk));
          }
          controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
          controller.close();
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: "error", message: msg })}\n\n`)
          );
          controller.close();
        }
      },
    });
  },
};

// ─── managed-agents adapter (stub) ──────────────────────────────────────────

const managedAgentsAdapter: AgentRuntime = {
  async stream(_messages) {
    throw new Error(
      "managed-agents adapter not implemented yet. " +
      "Set AGENT_BACKEND=messages-api or implement against " +
      "https://platform.claude.com/docs/en/managed-agents/overview"
    );
  },
};

// ─── agent-sdk adapter (stub) ───────────────────────────────────────────────

const agentSdkAdapter: AgentRuntime = {
  async stream(_messages) {
    throw new Error(
      "agent-sdk adapter not implemented yet. " +
      "Set AGENT_BACKEND=messages-api or implement against the Claude Agent SDK."
    );
  },
};

// ─── selector ───────────────────────────────────────────────────────────────

const adapters: Record<string, AgentRuntime> = {
  "messages-api": messagesApiAdapter,
  "managed-agents": managedAgentsAdapter,
  "agent-sdk": agentSdkAdapter,
};

const backend = process.env.AGENT_BACKEND ?? "messages-api";
export const agentRuntime: AgentRuntime = adapters[backend] ?? messagesApiAdapter;

/**
 * Chat endpoint — streams Anthropic events back to the client as SSE.
 *
 * Backend selected by `AGENT_BACKEND` env var (see lib/agent-runtime.ts).
 * No auth in this prototype; ephemeral sessions only. Adds Clerk + per-user
 * tokens in D.1 (design doc §5.1.b).
 */

import { agentRuntime, type ChatMessage } from "@/lib/agent-runtime";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const { messages } = (await req.json()) as { messages: ChatMessage[] };
    if (!Array.isArray(messages) || messages.length === 0) {
      return new Response(JSON.stringify({ error: "messages required" }), {
        status: 400,
        headers: { "content-type": "application/json" },
      });
    }

    const stream = await agentRuntime.stream(messages);

    return new Response(stream, {
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache, no-transform",
        connection: "keep-alive",
        "x-accel-buffering": "no",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { "content-type": "application/json" },
    });
  }
}

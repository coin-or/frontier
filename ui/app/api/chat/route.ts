/**
 * Chat endpoint — streams Anthropic events back to the client as SSE.
 *
 * Backend selected by `AGENT_BACKEND` env var (see lib/agent-runtime.ts).
 * Access is gated by the shared UI password (middleware.ts); a per-instance
 * rate limiter (lib/rate-limit.ts) caps the request rate as a floor against
 * runaway ANTHROPIC_API_KEY spend. Per-user tokens land in D.1 (design §5.1.b).
 */

import { agentRuntime, type ChatMessage } from "@/lib/agent-runtime";
import { chatRateLimiter, clientKey, tooManyRequests } from "@/lib/rate-limit";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const limit = chatRateLimiter.check(clientKey(req));
  if (!limit.ok) return tooManyRequests(limit);

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

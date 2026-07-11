/**
 * Pure helpers for the OpenAI Responses API wire (OPENAI_WIRE=responses).
 *
 * OpenAI's reasoning models (GPT-5.x) only support function tools WITH reasoning on
 * `/v1/responses` — `/v1/chat/completions` rejects the combination ("use /v1/responses
 * or set reasoning_effort to 'none'"). These helpers translate between the UI's
 * Anthropic-shaped chat blocks and the Responses wire; the streaming loop itself lives
 * in agent-runtime.ts. Kept pure (no env, no I/O) so `npm test` covers them directly.
 */
import type { ChatMessage } from "./agent-runtime";

export type ResponsesTool = {
  type: "function";
  name: string;
  description?: string;
  parameters: Record<string, unknown>;
};

// Input items: role messages, prior function calls, and their outputs.
export type ResponsesInputItem =
  | { role: "user"; content: Array<{ type: "input_text"; text: string }> }
  | { role: "assistant"; content: Array<{ type: "output_text"; text: string }> }
  | { type: "function_call"; call_id: string; name: string; arguments: string }
  | { type: "function_call_output"; call_id: string; output: string };

// MCP tool → Responses function tool (flat — no chat-style `function` wrapper).
export function buildResponsesTools(
  mcpTools: Array<{ name: string; description?: string; inputSchema?: Record<string, unknown> }>,
): ResponsesTool[] {
  return mcpTools.map((t) => ({
    type: "function",
    name: t.name,
    description: t.description,
    parameters: t.inputSchema ?? { type: "object", properties: {} },
  }));
}

function toolResultText(b: Record<string, unknown>): string {
  return Array.isArray(b.content)
    ? (b.content as Array<{ text?: string }>).map((c) => c.text ?? "").join("\n")
    : typeof b.content === "string"
      ? (b.content as string)
      : "";
}

/**
 * UI transcript → Responses `input` items. Mirrors translateMessagesToOpenAI's block
 * handling, with one wire-specific constraint honored by walking blocks IN ORDER: a
 * `function_call_output` must follow its `function_call`, so interleaved assistant turns
 * (text · tool_use · tool_result · text …) flush buffered text whenever a call boundary
 * is crossed instead of accumulating one big assistant message.
 */
export function translateMessagesToResponsesInput(messages: ChatMessage[]): ResponsesInputItem[] {
  const out: ResponsesInputItem[] = [];
  const pushText = (role: "user" | "assistant", text: string) => {
    if (!text) return;
    if (role === "user") out.push({ role, content: [{ type: "input_text", text }] });
    else out.push({ role, content: [{ type: "output_text", text }] });
  };
  for (const m of messages) {
    if (typeof m.content === "string") {
      pushText(m.role, m.content);
      continue;
    }
    const blocks = m.content as Array<Record<string, unknown>>;
    let textBuf = "";
    for (const b of blocks) {
      if (b.type === "text" && typeof b.text === "string") {
        textBuf += b.text;
        continue;
      }
      if (b.type === "mcp_tool_use") {
        pushText(m.role, textBuf);
        textBuf = "";
        out.push({
          type: "function_call",
          call_id: String(b.id ?? ""),
          name: String(b.name ?? ""),
          arguments: JSON.stringify(b.input ?? {}),
        });
        continue;
      }
      if (b.type === "mcp_tool_result") {
        pushText(m.role, textBuf);
        textBuf = "";
        out.push({
          type: "function_call_output",
          call_id: String(b.tool_use_id ?? ""),
          output: toolResultText(b),
        });
      }
    }
    pushText(m.role, textBuf);
  }
  return out;
}

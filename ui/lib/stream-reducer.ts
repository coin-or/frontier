/**
 * Pure stream-event → message-state reducer for the chat UI.
 *
 * Backends emit Anthropic-shaped SSE events (content_block_start/delta/stop).
 * This builds the rendered message history from them and produces the
 * Anthropic-shaped payload sent back on the next turn.
 *
 * Kept framework-free (no React/JSX) so it can be unit-tested in isolation —
 * the index-addressing contract below is subtle and worth pinning down.
 */

export type TextBlock = { type: "text"; text: string; index?: number };
export type ToolUseBlock = {
  type: "mcp_tool_use";
  id: string;
  name: string;
  server_name: string;
  input: Record<string, unknown>;
  inputJson: string; // internal accumulator (stripped on round-trip)
  index?: number; // server content-block index (internal; stripped on round-trip)
};
export type ToolResultContent = { type: "text"; text: string };
export type ToolResultBlock = {
  type: "mcp_tool_result";
  tool_use_id: string;
  content: ToolResultContent[]; // preserved as array for Anthropic round-trip
  is_error: boolean;
  index?: number; // server content-block index (internal; stripped on round-trip)
};
export type Block = TextBlock | ToolUseBlock | ToolResultBlock;

export type Message = { role: "user" | "assistant"; content: string | Block[] };

export type StreamEvent = { type?: string; [k: string]: unknown };

/**
 * Apply one stream event to the message list, returning a new list (or the same
 * reference when nothing changed). MUST be pure (no mutation): React 19
 * StrictMode double-invokes state updaters in dev, so in-place mutation would
 * duplicate effects.
 *
 * Blocks are addressed by the server-assigned content-block `index`, NEVER by
 * array position. The server's index space includes thinking blocks (which we
 * don't store), so it is sparse relative to our array. Matching on position
 * instead would misroute every text/input delta that follows a thinking block,
 * leaving empty text blocks — which the API then rejects on the next turn
 * ("text content blocks must be non-empty").
 */
export function applyEvent(prev: Message[], event: StreamEvent): Message[] {
  if (!prev.length) return prev;
  const lastIdx = prev.length - 1;
  const last = prev[lastIdx];
  if (last.role !== "assistant") return prev;

  const oldBlocks: Block[] = Array.isArray(last.content) ? (last.content as Block[]) : [];
  let blocks: Block[] = oldBlocks;

  // Update the block carrying `serverIndex`, preserving array identity when the
  // updater is a no-op (so the change-detection at the bottom can short-circuit).
  const updateByIndex = (serverIndex: number, fn: (b: Block) => Block) => {
    let changed = false;
    const mapped = blocks.map((b) => {
      if (b.index !== serverIndex) return b;
      const nb = fn(b);
      if (nb !== b) changed = true;
      return nb;
    });
    if (changed) blocks = mapped;
  };

  switch (event.type) {
    case "content_block_start": {
      const cb = (event as any).content_block;
      const index = (event as any).index as number;
      if (cb?.type === "text") {
        blocks = [...blocks, { type: "text", text: cb.text ?? "", index }];
      } else if (cb?.type === "mcp_tool_use") {
        blocks = [
          ...blocks,
          {
            type: "mcp_tool_use",
            id: cb.id,
            name: cb.name,
            server_name: cb.server_name ?? "frontier",
            input: cb.input ?? {},
            inputJson: "",
            index,
          },
        ];
      } else if (cb?.type === "mcp_tool_result") {
        // Normalize content to array-of-text-blocks shape (Anthropic round-trip requirement)
        let content: ToolResultContent[] = [];
        if (typeof cb.content === "string") {
          content = [{ type: "text", text: cb.content }];
        } else if (Array.isArray(cb.content)) {
          content = cb.content.map((c: any) => ({ type: "text", text: c?.text ?? "" }));
        }
        blocks = [
          ...blocks,
          { type: "mcp_tool_result", tool_use_id: cb.tool_use_id, content, is_error: cb.is_error ?? false, index },
        ];
      }
      // thinking (and any future block types) are not stored — they occupy a
      // server index but no slot here, which is exactly why we address by index.
      break;
    }
    case "content_block_delta": {
      const idx = (event as any).index as number;
      const delta = (event as any).delta;
      updateByIndex(idx, (target) => {
        if (delta?.type === "text_delta" && target.type === "text") {
          return { ...target, text: target.text + (delta.text ?? "") };
        }
        if (delta?.type === "input_json_delta" && target.type === "mcp_tool_use") {
          const inputJson = target.inputJson + (delta.partial_json ?? "");
          let input = target.input;
          try {
            input = JSON.parse(inputJson);
          } catch {
            /* still streaming partial JSON */
          }
          return { ...target, inputJson, input };
        }
        return target;
      });
      break;
    }
    case "content_block_stop": {
      const idx = (event as any).index as number;
      updateByIndex(idx, (target) => {
        if (target.type === "mcp_tool_use" && target.inputJson) {
          try {
            return { ...target, input: JSON.parse(target.inputJson) };
          } catch {
            return target;
          }
        }
        return target;
      });
      break;
    }
    case "error": {
      blocks = [...blocks, { type: "text", text: `\n\n_Error: ${(event as any).message ?? "unknown"}_` }];
      break;
    }
  }

  if (blocks === oldBlocks) return prev;

  const next = [...prev];
  next[lastIdx] = { ...last, content: blocks };
  return next;
}

export type ApiMessage = { role: "user" | "assistant"; content: string | Array<Record<string, unknown>> };

/**
 * Build the Anthropic-shaped payload for the next request: strip internal-only
 * fields (`inputJson`, `index`) and drop empty text blocks. The API rejects
 * text content blocks whose text is empty, so they must never be sent — even if
 * a model legitimately emits one, or a pre-fix session left one in history.
 */
export function toApiMessages(messages: Message[]): ApiMessage[] {
  return messages.map((m) => {
    if (typeof m.content === "string") return { role: m.role, content: m.content };
    const cleaned = (m.content as Block[])
      .filter((b) => !(b.type === "text" && b.text.trim() === ""))
      .map((b) => {
        if (b.type === "mcp_tool_use") {
          const { inputJson: _omitJson, index: _omitIdx, ...rest } = b;
          return rest as Record<string, unknown>;
        }
        const { index: _omitIdx, ...rest } = b as Block & { index?: number };
        return rest as Record<string, unknown>;
      });
    return { role: m.role, content: cleaned };
  });
}

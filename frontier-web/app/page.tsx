"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ToolCallBlock } from "@/components/ToolCallBlock";

type TextBlock = { type: "text"; text: string };
type ToolUseBlock = {
  type: "mcp_tool_use";
  id: string;
  name: string;
  input: Record<string, unknown>;
  inputJson: string;
};
type ToolResultBlock = {
  type: "mcp_tool_result";
  tool_use_id: string;
  content: string;
  is_error: boolean;
};
type Block = TextBlock | ToolUseBlock | ToolResultBlock;

type Message = { role: "user" | "assistant"; content: string | Block[] };

const STARTER_PROMPT =
  "Describe a decision you're trying to make — e.g., \"prioritize 3 of these 5 initiatives next quarter, balancing engineering cost, customer impact, and strategic fit.\"";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const trimmed = input.trim();
    if (!trimmed || streaming) return;
    setError(null);

    const userMsg: Message = { role: "user", content: trimmed };
    const assistantMsg: Message = { role: "assistant", content: [] };
    const next = [...messages, userMsg, assistantMsg];
    setMessages(next);
    setInput("");
    setStreaming(true);

    // Build Anthropic-shaped payload (strip our internal `inputJson` accumulator)
    const apiMessages = [...messages, userMsg].map((m) => {
      if (typeof m.content === "string") return { role: m.role, content: m.content };
      const cleaned = (m.content as Block[]).map((b) => {
        if (b.type === "mcp_tool_use") {
          const { inputJson: _omit, ...rest } = b;
          return rest;
        }
        return b;
      });
      return { role: m.role, content: cleaned };
    });

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages: apiMessages }),
      });

      if (!res.ok || !res.body) {
        const text = await res.text();
        throw new Error(text || `request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") continue;
          try {
            const event = JSON.parse(payload);
            setMessages((prev) => applyEvent(prev, event));
          } catch {
            /* swallow parse errors on partial chunks */
          }
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setStreaming(false);
    }
  }

  function reset() {
    setMessages([]);
    setError(null);
  }

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col">
      <header className="flex items-center justify-between border-b border-stone-200 px-6 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-base font-semibold text-stone-900">Frontier</h1>
          <span className="text-xs text-stone-500">
            structured multi-objective decision making
          </span>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={reset}
            className="text-xs text-stone-500 hover:text-stone-800"
          >
            new chat
          </button>
        )}
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="mx-auto mt-24 max-w-xl text-center text-sm text-stone-500">
            {STARTER_PROMPT}
          </div>
        )}

        {messages.map((m, i) => (
          <MessageView key={i} message={m} />
        ))}

        {error && (
          <div className="my-3 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700">
            error: {error}
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <footer className="border-t border-stone-200 px-6 py-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="message Frontier…"
            disabled={streaming}
            rows={1}
            className="min-h-[2.5rem] flex-1 resize-none rounded-md border border-stone-300 bg-white px-3 py-2 text-sm outline-none focus:border-stone-500 disabled:bg-stone-100"
          />
          <button
            type="button"
            onClick={send}
            disabled={streaming || !input.trim()}
            className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-400"
          >
            {streaming ? "…" : "send"}
          </button>
        </div>
        <div className="mt-1.5 text-[10px] text-stone-400">
          enter to send · shift-enter for newline · ephemeral session
        </div>
      </footer>
    </div>
  );
}

function MessageView({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const blocks: Block[] =
    typeof message.content === "string"
      ? [{ type: "text", text: message.content }]
      : (message.content as Block[]);

  // Pair tool_use with its tool_result (rendered together)
  const resultsByUseId: Record<string, ToolResultBlock> = {};
  for (const b of blocks) {
    if (b.type === "mcp_tool_result") resultsByUseId[b.tool_use_id] = b;
  }

  return (
    <div className={`mb-5 ${isUser ? "flex justify-end" : ""}`}>
      <div className={isUser ? "max-w-[80%] rounded-2xl bg-stone-900 px-4 py-2 text-sm text-white" : "prose w-full text-sm text-stone-800"}>
        {blocks.map((b, i) => {
          if (b.type === "text") {
            if (!b.text) return null;
            if (isUser) return <span key={i}>{b.text}</span>;
            return (
              <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>
                {b.text}
              </ReactMarkdown>
            );
          }
          if (b.type === "mcp_tool_use") {
            const result = resultsByUseId[b.id];
            return (
              <ToolCallBlock
                key={i}
                name={b.name}
                input={b.input}
                result={result?.content}
                isError={result?.is_error}
                pending={!result}
              />
            );
          }
          // tool_result is rendered inside its matching tool_use; skip standalone
          return null;
        })}
      </div>
    </div>
  );
}

// ─── stream event → message-state reducer ───────────────────────────────────

function applyEvent(prev: Message[], event: { type?: string; [k: string]: unknown }): Message[] {
  if (!prev.length) return prev;
  const lastIdx = prev.length - 1;
  const last = prev[lastIdx];
  if (last.role !== "assistant") return prev;

  const blocks: Block[] = Array.isArray(last.content) ? [...(last.content as Block[])] : [];

  switch (event.type) {
    case "content_block_start": {
      const cb = (event as any).content_block;
      if (cb?.type === "text") {
        blocks.push({ type: "text", text: cb.text ?? "" });
      } else if (cb?.type === "mcp_tool_use") {
        blocks.push({
          type: "mcp_tool_use",
          id: cb.id,
          name: cb.name,
          input: cb.input ?? {},
          inputJson: "",
        });
      } else if (cb?.type === "mcp_tool_result") {
        let content = "";
        if (typeof cb.content === "string") {
          content = cb.content;
        } else if (Array.isArray(cb.content)) {
          content = cb.content.map((c: any) => c?.text ?? "").join("\n");
        }
        blocks.push({
          type: "mcp_tool_result",
          tool_use_id: cb.tool_use_id,
          content,
          is_error: cb.is_error ?? false,
        });
      }
      break;
    }
    case "content_block_delta": {
      const idx = (event as any).index as number;
      const delta = (event as any).delta;
      const target = blocks[idx];
      if (!target) break;
      if (delta?.type === "text_delta" && target.type === "text") {
        target.text += delta.text ?? "";
      } else if (delta?.type === "input_json_delta" && target.type === "mcp_tool_use") {
        target.inputJson += delta.partial_json ?? "";
        try {
          target.input = JSON.parse(target.inputJson);
        } catch {
          /* still streaming */
        }
      }
      break;
    }
    case "content_block_stop": {
      const idx = (event as any).index as number;
      const target = blocks[idx];
      if (target?.type === "mcp_tool_use" && target.inputJson) {
        try {
          target.input = JSON.parse(target.inputJson);
        } catch {
          /* leave best-effort partial */
        }
      }
      break;
    }
    case "error": {
      blocks.push({ type: "text", text: `\n\n_Error: ${(event as any).message ?? "unknown"}_` });
      break;
    }
  }

  const next = [...prev];
  next[lastIdx] = { ...last, content: blocks };
  return next;
}

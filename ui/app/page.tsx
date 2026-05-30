"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { VizRenderer } from "@/components/Viz";
import { extractVizData } from "@/lib/viz-data";
import {
  applyEvent,
  toApiMessages,
  type Block,
  type Message,
  type ToolUseBlock,
  type ToolResultBlock,
} from "@/lib/stream-reducer";
import { ChatActionContext } from "@/lib/chat-action";

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

  // Track tools currently in flight on the last assistant message
  // (mcp_tool_use blocks without a matching mcp_tool_result). Drives the
  // active-tool indicator so parallel sequences don't look stalled.
  const pendingTools = useMemo(() => {
    if (!streaming || messages.length === 0) return [] as string[];
    const last = messages[messages.length - 1];
    if (last.role !== "assistant" || typeof last.content === "string") return [];
    const blocks = last.content as Block[];
    const resultIds = new Set<string>();
    for (const b of blocks) {
      if (b.type === "mcp_tool_result") resultIds.add(b.tool_use_id);
    }
    return blocks
      .filter((b): b is ToolUseBlock => b.type === "mcp_tool_use")
      .filter((b) => !resultIds.has(b.id))
      .map((b) => b.name);
  }, [messages, streaming]);

  async function sendText(raw: string) {
    const trimmed = raw.trim();
    if (!trimmed || streaming) return;
    setError(null);

    const userMsg: Message = { role: "user", content: trimmed };
    const assistantMsg: Message = { role: "assistant", content: [] };
    setMessages([...messages, userMsg, assistantMsg]);
    setStreaming(true);

    // Build the Anthropic-shaped payload (strips internal fields, drops empty text)
    const apiMessages = toApiMessages([...messages, userMsg]);

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

  function send() {
    if (streaming) return;
    const trimmed = input.trim();
    if (!trimmed) return;
    setInput("");
    sendText(trimmed);
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

        <ChatActionContext.Provider value={{ sendMessage: sendText, streaming }}>
          {messages.map((m, i) => (
            <MessageView key={i} message={m} />
          ))}
        </ChatActionContext.Provider>

        {error && (
          <div className="my-3 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700">
            error: {error}
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <footer className="border-t border-stone-200 px-6 py-3">
        {(streaming || pendingTools.length > 0) && (
          <div className="mb-2 flex items-center gap-2 text-xs text-stone-600">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
            {pendingTools.length === 0 ? (
              <span>thinking…</span>
            ) : (
              <span>
                running {pendingTools.length === 1 ? "1 tool" : `${pendingTools.length} tools`}:{" "}
                <span className="font-mono text-stone-700">{pendingTools.join(", ")}</span>
              </span>
            )}
          </div>
        )}
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

// The engine attaches ASCII visualizations (── Frontier Scatter ──, Parallel
// Coordinates …) to tool results for text/coding-agent surfaces; the model
// often echoes them as fenced code blocks. This surface renders D3 charts from
// the structured viz_data instead, so drop the redundant ASCII (identified by
// the box-drawing rules in its headers/axes). Other code blocks are kept.
function stripAsciiViz(md: string): string {
  return md.replace(/```[\s\S]*?```/g, (block) => (/─{3,}/.test(block) ? "" : block));
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
                {stripAsciiViz(b.text)}
              </ReactMarkdown>
            );
          }
          if (b.type === "mcp_tool_use") {
            // Don't render raw tool plumbing (input/result JSON) — the LLM's
            // prose carries the narrative. Surface only the rendered viz.
            const result = resultsByUseId[b.id];
            const resultText = result
              ? result.content.map((c) => c.text).join("\n")
              : undefined;
            const vizPayloads = resultText ? extractVizData(resultText) : [];
            if (vizPayloads.length === 0) return null;
            return (
              <div key={i}>
                {vizPayloads.map((vd, vi) => (
                  <VizRenderer key={vi} data={vd} />
                ))}
              </div>
            );
          }
          // tool_result is rendered inside its matching tool_use; skip standalone
          return null;
        })}
      </div>
    </div>
  );
}


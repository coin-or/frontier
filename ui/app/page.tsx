"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ToolCallBlock } from "@/components/ToolCallBlock";
import { VizRenderer } from "@/components/Viz";
import { extractVizData } from "@/lib/viz-data";

type TextBlock = { type: "text"; text: string };
type ToolUseBlock = {
  type: "mcp_tool_use";
  id: string;
  name: string;
  server_name: string;
  input: Record<string, unknown>;
  inputJson: string; // internal accumulator (stripped on round-trip)
};
type ToolResultContent = { type: "text"; text: string };
type ToolResultBlock = {
  type: "mcp_tool_result";
  tool_use_id: string;
  content: ToolResultContent[]; // preserved as array for Anthropic round-trip
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
            const resultText = result
              ? result.content.map((c) => c.text).join("\n")
              : undefined;
            const vizPayloads = resultText ? extractVizData(resultText) : [];
            return (
              <div key={i}>
                <ToolCallBlock
                  name={b.name}
                  input={b.input}
                  result={resultText}
                  isError={result?.is_error}
                  pending={!result}
                />
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

// ─── stream event → message-state reducer ───────────────────────────────────
// MUST be pure (no mutation). React 19 StrictMode double-invokes state-updater
// functions in dev; any in-place mutation here would duplicate effects.

function applyEvent(prev: Message[], event: { type?: string; [k: string]: unknown }): Message[] {
  if (!prev.length) return prev;
  const lastIdx = prev.length - 1;
  const last = prev[lastIdx];
  if (last.role !== "assistant") return prev;

  const oldBlocks: Block[] = Array.isArray(last.content) ? (last.content as Block[]) : [];
  let blocks: Block[] = oldBlocks;

  const replaceAt = (idx: number, fn: (b: Block) => Block) => {
    blocks = blocks.map((b, i) => (i === idx ? fn(b) : b));
  };

  switch (event.type) {
    case "content_block_start": {
      const cb = (event as any).content_block;
      if (cb?.type === "text") {
        blocks = [...blocks, { type: "text", text: cb.text ?? "" }];
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
          },
        ];
      } else if (cb?.type === "mcp_tool_result") {
        // Normalize content to array-of-text-blocks shape (Anthropic round-trip requirement)
        let content: ToolResultContent[] = [];
        if (typeof cb.content === "string") {
          content = [{ type: "text", text: cb.content }];
        } else if (Array.isArray(cb.content)) {
          content = cb.content.map((c: any) => ({
            type: "text",
            text: c?.text ?? "",
          }));
        }
        blocks = [
          ...blocks,
          {
            type: "mcp_tool_result",
            tool_use_id: cb.tool_use_id,
            content,
            is_error: cb.is_error ?? false,
          },
        ];
      }
      break;
    }
    case "content_block_delta": {
      const idx = (event as any).index as number;
      const delta = (event as any).delta;
      replaceAt(idx, (target) => {
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
      replaceAt(idx, (target) => {
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
      blocks = [
        ...blocks,
        { type: "text", text: `\n\n_Error: ${(event as any).message ?? "unknown"}_` },
      ];
      break;
    }
  }

  if (blocks === oldBlocks) return prev;

  const next = [...prev];
  next[lastIdx] = { ...last, content: blocks };
  return next;
}

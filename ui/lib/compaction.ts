/**
 * Token-budget-aware history compaction (v1 — no extra LLM call).
 *
 * The web UI resends the entire transcript on every turn and does no compaction of its
 * own, so a long session grows until it hits the model's context window and the request
 * hard-fails. This trims the transcript when (system + history) approaches a token budget,
 * PINNING the layers that carry durable value and dropping the stale middle behind a
 * breadcrumb:
 *
 *   pinned  — the system prompt (the durable guidance index; sent separately by the
 *             caller, counted here only against the budget), the first user turn (the
 *             original decision question — the session anchor), and the last K messages
 *             (the recent exchange);
 *   dropped — the older middle turns, replaced by ONE breadcrumb recording how many turns
 *             were elided and naming the active skill + its get_skill() re-fetch path, so
 *             methodology guidance that scrolled out of the middle stays recoverable.
 *
 * Why dropping whole turns is safe: in the UI message shape each assistant turn bundles
 * its own tool_use AND tool_result blocks, so a tool call is never separated from its
 * result by a turn-boundary drop. The breadcrumb is emitted as an assistant message and
 * the retained tail always begins on a user message, so the compacted history preserves
 * the user/assistant alternation the APIs require (first message user; roles alternate).
 *
 * This is the web-UI counterpart to the engine's durable index: the index keeps the
 * guidance MAP in the system prompt across compaction; this keeps long sessions from
 * dying at the context wall and leaves a breadcrumb back to the skills the index names.
 *
 * Pure and dependency-free (the only import is type-only, erased at runtime) so it can be
 * unit-tested in isolation, mirroring stream-reducer.ts.
 */
import type { ChatMessage } from "./agent-runtime";

// ~4 characters per token — a deliberately rough, tokenizer-free estimate. It only needs
// to be good enough to decide WHEN to compact; over-estimating just compacts a little early.
export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

function messageText(m: ChatMessage): string {
  return typeof m.content === "string" ? m.content : JSON.stringify(m.content);
}

// The engine embeds skill guidance in tool results as `_skill_guidance` (full body) or
// `guidance_pointer` (decision-step section pointer), each an object whose first key is
// the skill name. Match against the raw tool-result text (not the JSON-escaped envelope),
// so we can name the active skill in the breadcrumb for re-fetch.
const SKILL_RE = /"(?:_skill_guidance|guidance_pointer)"\s*:\s*\{[^{}]*?"skill"\s*:\s*"([a-z_]+)"/;

function toolResultTexts(m: ChatMessage): string[] {
  if (typeof m.content === "string") return [];
  const out: string[] = [];
  for (const b of m.content as Array<Record<string, unknown>>) {
    if (!b || b.type !== "mcp_tool_result") continue;
    const c = (b as { content?: unknown }).content;
    if (Array.isArray(c)) {
      for (const part of c) {
        const t = (part as { text?: unknown })?.text;
        if (typeof t === "string") out.push(t);
      }
    } else if (typeof c === "string") {
      out.push(c);
    }
  }
  return out;
}

function activeSkillIn(m: ChatMessage): string | null {
  for (const text of toolResultTexts(m)) {
    const match = SKILL_RE.exec(text);
    if (match) return match[1];
  }
  return null;
}

export type CompactionResult = {
  messages: ChatMessage[];
  compacted: boolean;
  dropped: number; // count of middle messages elided
};

/**
 * Trim `messages` to fit `budgetTokens` (input tokens available after reserving room for
 * the system prompt and the model's response). `keepRecent` is the number of trailing
 * messages to retain. Returns the original array reference untouched when no compaction is
 * needed, so callers can cheaply detect the no-op.
 */
export function compactHistory(
  messages: ChatMessage[],
  systemText: string,
  budgetTokens: number,
  keepRecent: number,
): CompactionResult {
  const used =
    estimateTokens(systemText) +
    messages.reduce((sum, m) => sum + estimateTokens(messageText(m)), 0);

  // Under budget, or too short for trimming to buy anything → leave it exactly as-is.
  if (used <= budgetTokens || messages.length <= keepRecent + 2) {
    return { messages, compacted: false, dropped: 0 };
  }

  const head = 0; // the first user turn — the decision anchor
  // Retain the last `keepRecent` messages, but back the cut up to a user message so the
  // breadcrumb→tail boundary lands on a user turn (keeps alternation; never orphans a
  // tool_result, though in the UI shape results are already turn-internal).
  let tailStart = Math.max(messages.length - keepRecent, head + 1);
  while (tailStart > head + 1 && messages[tailStart].role !== "user") tailStart--;

  const dropped = tailStart - (head + 1);
  if (dropped <= 0) return { messages, compacted: false, dropped: 0 };

  // Name the most-recent skill whose guidance is in the dropped span, so the breadcrumb can
  // point at the concrete re-fetch path (the durable index in the system prompt names the
  // same path; this makes it specific at the elision point).
  let activeSkill: string | null = null;
  for (let i = tailStart - 1; i > head && !activeSkill; i--) {
    activeSkill = activeSkillIn(messages[i]);
  }

  const breadcrumb: ChatMessage = {
    role: "assistant",
    content:
      `[Context note: ${dropped} earlier turn(s) from this session were omitted to fit the ` +
      `context window — the original request and the most recent exchanges are kept verbatim. ` +
      (activeSkill
        ? `Active workflow guidance was the ${activeSkill} skill; re-fetch it with ` +
          `get_skill('${activeSkill}') before relying on it. `
        : ``) +
      `The durable guidance map is still in your system prompt — re-fetch any phase's skill ` +
      `via get_skill(<name>) if it isn't in view.]`,
  };

  return {
    messages: [messages[head], breadcrumb, ...messages.slice(tailStart)],
    compacted: true,
    dropped,
  };
}

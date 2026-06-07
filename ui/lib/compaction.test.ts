/**
 * Unit tests for history compaction. Pure logic, so it runs with Node's built-in test
 * runner + TypeScript type-stripping — no extra dev dependencies:
 *
 *   node --test --experimental-strip-types lib/compaction.test.ts
 *
 * Excluded from the app tsconfig (the `.ts` import extension is for the Node runtime; the
 * app code imports extensionless). compaction.ts has only a type-only import, erased at
 * runtime, so this loads without the SDK / node_modules.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { compactHistory, estimateTokens } from "./compaction.ts";
import type { ChatMessage } from "./agent-runtime.ts";

const mkUser = (t: string): ChatMessage => ({ role: "user", content: t });
const mkAsst = (t: string): ChatMessage => ({ role: "assistant", content: t });

// An assistant turn that embedded an engine guidance_pointer in a tool result — the UI
// shape (tool_use + tool_result bundled in one assistant message).
const mkGuidanceTurn = (skill: string): ChatMessage => ({
  role: "assistant",
  content: [
    { type: "text", text: "looking at the frontier" },
    { type: "mcp_tool_use", id: "t1", name: "explore", server_name: "frontier", input: {} },
    {
      type: "mcp_tool_result",
      tool_use_id: "t1",
      content: [
        {
          type: "text",
          text: JSON.stringify({
            run_id: "r1",
            guidance_pointer: { skill, section: "Presentation Order", note: "n" },
          }),
        },
      ],
      is_error: false,
    },
    { type: "text", text: "here are the tradeoffs" },
  ],
});

// 11 messages, strictly alternating user/assistant, ending on a user turn (as the UI
// sends). The guidance turn sits at index 1 — inside the span that will be dropped.
const buildHistory = (): ChatMessage[] => [
  mkUser("original decision question"),
  mkGuidanceTurn("solution_interpreter"),
  mkUser("turn 2"),
  mkAsst("turn 3"),
  mkUser("turn 4"),
  mkAsst("turn 5"),
  mkUser("turn 6"),
  mkAsst("turn 7"),
  mkUser("turn 8"),
  mkAsst("turn 9"),
  mkUser("latest user turn"),
];

test("estimateTokens approximates ~4 chars/token", () => {
  assert.equal(estimateTokens(""), 0);
  assert.equal(estimateTokens("abcd"), 1);
  assert.equal(estimateTokens("abcde"), 2);
});

test("no-op when comfortably under budget (same array reference)", () => {
  const h = buildHistory();
  const r = compactHistory(h, "system", 1_000_000, 8);
  assert.equal(r.compacted, false);
  assert.equal(r.dropped, 0);
  assert.equal(r.messages, h); // untouched reference
});

test("no-op when too few messages to trim", () => {
  const h = [mkUser("a"), mkAsst("b"), mkUser("c")];
  const r = compactHistory(h, "system", 1, 8); // tiny budget but length <= keepRecent+2
  assert.equal(r.compacted, false);
  assert.equal(r.messages, h);
});

test("over budget: pins head + tail, drops middle, inserts a breadcrumb", () => {
  const h = buildHistory();
  const r = compactHistory(h, "system", 50, 4); // tiny budget forces compaction

  assert.equal(r.compacted, true);
  // keepRecent=4 → tail backs up to the nearest user message (index 6); head=0 kept;
  // indices 1..5 dropped (5 messages).
  assert.equal(r.dropped, 5);
  assert.equal(r.messages.length, 7); // head + breadcrumb + 5 tail

  // Head preserved verbatim (the decision anchor).
  assert.equal(r.messages[0], h[0]);
  // Breadcrumb is an assistant message naming the elision + the re-fetch path.
  assert.equal(r.messages[1].role, "assistant");
  const crumb = r.messages[1].content as string;
  assert.match(crumb, /omitted to fit/);
  assert.match(crumb, /get_skill\('solution_interpreter'\)/); // extracted from dropped tool result
  // Tail begins on a user message and runs to the latest turn.
  assert.equal(r.messages[2], h[6]);
  assert.equal(r.messages[r.messages.length - 1], h[10]);
});

test("compacted history preserves user/assistant alternation, starting with user", () => {
  const r = compactHistory(buildHistory(), "system", 50, 4);
  assert.equal(r.messages[0].role, "user");
  for (let i = 1; i < r.messages.length; i++) {
    assert.notEqual(r.messages[i].role, r.messages[i - 1].role, `roles must alternate at ${i}`);
  }
});

test("breadcrumb falls back to a generic re-fetch note when no skill is in the dropped span", () => {
  // All-text history (no embedded guidance), padded so it genuinely exceeds the budget →
  // it compacts, and the breadcrumb still points at get_skill(<name>).
  const pad = (s: string) => s.padEnd(60, ".");
  const h = [
    mkUser(pad("q")),
    mkAsst(pad("a1")), mkUser(pad("u2")), mkAsst(pad("a3")), mkUser(pad("u4")),
    mkAsst(pad("a5")), mkUser(pad("u6")), mkAsst(pad("a7")), mkUser(pad("u8")),
    mkAsst(pad("a9")), mkUser(pad("u10")),
  ];
  const r = compactHistory(h, "system", 50, 4);
  assert.equal(r.compacted, true);
  const crumb = r.messages[1].content as string;
  assert.match(crumb, /get_skill\(<name>\)/);
  assert.doesNotMatch(crumb, /Active workflow guidance was/);
});

test("degrades safely on bad tunables — env-sourced keepRecent/budget must never crash or corrupt", () => {
  const h = buildHistory();
  // keepRecent <= 0 (AGENT_KEEP_RECENT_MESSAGES=0) must not crash, and must clamp to a valid
  // structure rather than indexing past the end of the array.
  assert.doesNotThrow(() => compactHistory(h, "system", 50, 0));
  const zero = compactHistory(h, "system", 50, 0);
  assert.equal(zero.messages[0].role, "user");
  for (let i = 1; i < zero.messages.length; i++) {
    assert.notEqual(zero.messages[i].role, zero.messages[i - 1].role);
  }
  // Non-numeric keepRecent → default; must not duplicate the head or grow the transcript.
  const nan = compactHistory(h, "system", 50, NaN);
  assert.ok(Number.isFinite(nan.dropped));
  assert.ok(nan.messages.length <= h.length);
  // Non-finite budget (bad AGENT_CONTEXT_WINDOW) → no-op, not a NaN-driven mis-trim.
  const badBudget = compactHistory(h, "system", NaN, 4);
  assert.equal(badBudget.compacted, false);
  assert.equal(badBudget.messages, h);
  // First message not a user turn → bail rather than emit an assistant-led history.
  const assistantLed = [mkAsst("preamble"), ...h];
  const r = compactHistory(assistantLed, "system", 50, 4);
  assert.equal(r.compacted, false);
});

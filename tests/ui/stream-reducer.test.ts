/**
 * Regression test for the chat stream reducer.
 *
 * Run: node --experimental-strip-types --test tests/ui/stream-reducer.test.ts
 *
 * Pins the index-addressing contract: server content-block indices include
 * thinking blocks (which the UI does not store), so they are sparse relative to
 * the rendered block array. The reducer must address blocks by that server
 * index, never by array position — otherwise every text/input delta after a
 * thinking block is misrouted, leaving empty text blocks that the API rejects
 * on the next turn ("text content blocks must be non-empty").
 *
 * The event sequences below are captured verbatim from the real Anthropic
 * Messages API + MCP-connector stream (dev_temp/probe_connector_indices.mjs).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { applyEvent, toApiMessages, type Message, type StreamEvent } from "../../ui/lib/stream-reducer.ts";

// Seed state the way the UI does: a user turn + an empty assistant placeholder
// that streamed events accumulate into.
function seed(): Message[] {
  return [
    { role: "user", content: "pick 3 of 6 R&D projects" },
    { role: "assistant", content: [] },
  ];
}

function replay(events: StreamEvent[]): Message[] {
  return events.reduce((acc, ev) => applyEvent(acc, ev), seed());
}

function assistantBlocks(state: Message[]) {
  const last = state[state.length - 1];
  assert.equal(last.role, "assistant");
  assert.ok(Array.isArray(last.content));
  return last.content as Array<Record<string, any>>;
}

// Captured order: thinking@0, text@1, mcp_tool_use@2, mcp_tool_result@3,
// thinking@4, text@5 — the exact shape that triggered the production 400.
const THINKING_GAP: StreamEvent[] = [
  { type: "content_block_start", index: 0, content_block: { type: "thinking" } },
  { type: "content_block_delta", index: 0, delta: { type: "signature_delta", signature: "abc" } },
  { type: "content_block_stop", index: 0 },

  { type: "content_block_start", index: 1, content_block: { type: "text", text: "" } },
  { type: "content_block_delta", index: 1, delta: { type: "text_delta", text: "Here's how I'd " } },
  { type: "content_block_delta", index: 1, delta: { type: "text_delta", text: "frame this." } },
  { type: "content_block_stop", index: 1 },

  { type: "content_block_start", index: 2, content_block: { type: "mcp_tool_use", id: "tu_1", name: "get_skill", server_name: "frontier", input: {} } },
  { type: "content_block_delta", index: 2, delta: { type: "input_json_delta", partial_json: '{"skill_id":' } },
  { type: "content_block_delta", index: 2, delta: { type: "input_json_delta", partial_json: '"problem_framing"}' } },
  { type: "content_block_stop", index: 2 },

  { type: "content_block_start", index: 3, content_block: { type: "mcp_tool_result", tool_use_id: "tu_1", content: [{ type: "text", text: "PROBLEM FRAMING SKILL ..." }], is_error: false } },
  { type: "content_block_stop", index: 3 },

  { type: "content_block_start", index: 4, content_block: { type: "thinking" } },
  { type: "content_block_delta", index: 4, delta: { type: "signature_delta", signature: "def" } },
  { type: "content_block_stop", index: 4 },

  { type: "content_block_start", index: 5, content_block: { type: "text", text: "" } },
  { type: "content_block_delta", index: 5, delta: { type: "text_delta", text: "Framed as a selection problem." } },
  { type: "content_block_stop", index: 5 },
];

test("thinking gaps: text and tool input are captured (not dropped)", () => {
  const blocks = assistantBlocks(replay(THINKING_GAP));

  // thinking blocks are not stored → 4 surfaced blocks (text, tool_use, result, text)
  assert.equal(blocks.length, 4);

  assert.equal(blocks[0].type, "text");
  assert.equal(blocks[0].text, "Here's how I'd frame this.");

  assert.equal(blocks[1].type, "mcp_tool_use");
  assert.deepEqual(blocks[1].input, { skill_id: "problem_framing" });

  assert.equal(blocks[2].type, "mcp_tool_result");
  assert.equal(blocks[2].content[0].text, "PROBLEM FRAMING SKILL ...");

  assert.equal(blocks[3].type, "text");
  assert.equal(blocks[3].text, "Framed as a selection problem.");
});

test("thinking gaps: round-trip payload has no empty text blocks and no internal fields", () => {
  const state = replay(THINKING_GAP);
  const api = toApiMessages(state);
  const assistant = api[api.length - 1];
  const content = assistant.content as Array<Record<string, any>>;

  for (const b of content) {
    if (b.type === "text") assert.notEqual(b.text.trim(), "", "empty text block must not be sent");
    assert.equal("index" in b, false, "internal `index` must be stripped");
    assert.equal("inputJson" in b, false, "internal `inputJson` must be stripped");
  }
  // The two real text blocks survive; tool_use + result survive.
  assert.equal(content.filter((b) => b.type === "text").length, 2);
});

// Dense stream (adaptive thinking chose not to think): text@0, tool@1, result@2, text@3.
const NO_THINKING: StreamEvent[] = [
  { type: "content_block_start", index: 0, content_block: { type: "text", text: "" } },
  { type: "content_block_delta", index: 0, delta: { type: "text_delta", text: "On it." } },
  { type: "content_block_stop", index: 0 },
  { type: "content_block_start", index: 1, content_block: { type: "mcp_tool_use", id: "tu_2", name: "model", server_name: "frontier", input: {} } },
  { type: "content_block_delta", index: 1, delta: { type: "input_json_delta", partial_json: '{"action":"create"}' } },
  { type: "content_block_stop", index: 1 },
  { type: "content_block_start", index: 2, content_block: { type: "mcp_tool_result", tool_use_id: "tu_2", content: [{ type: "text", text: "created" }], is_error: false } },
  { type: "content_block_stop", index: 2 },
  { type: "content_block_start", index: 3, content_block: { type: "text", text: "" } },
  { type: "content_block_delta", index: 3, delta: { type: "text_delta", text: "Done." } },
  { type: "content_block_stop", index: 3 },
];

test("dense stream (no thinking) still reduces correctly", () => {
  const blocks = assistantBlocks(replay(NO_THINKING));
  assert.equal(blocks.length, 4);
  assert.equal(blocks[0].text, "On it.");
  assert.deepEqual(blocks[1].input, { action: "create" });
  assert.equal(blocks[2].content[0].text, "created");
  assert.equal(blocks[3].text, "Done.");
});

test("toApiMessages drops a genuinely-empty model text block", () => {
  // A model can emit a text block that never receives deltas even with correct
  // indexing; it must not reach the API.
  const events: StreamEvent[] = [
    { type: "content_block_start", index: 0, content_block: { type: "text", text: "" } },
    { type: "content_block_stop", index: 0 },
    { type: "content_block_start", index: 1, content_block: { type: "mcp_tool_use", id: "tu_3", name: "model", server_name: "frontier", input: {} } },
    { type: "content_block_delta", index: 1, delta: { type: "input_json_delta", partial_json: "{}" } },
    { type: "content_block_stop", index: 1 },
  ];
  const api = toApiMessages(replay(events));
  const content = (api[api.length - 1].content as Array<Record<string, any>>);
  assert.equal(content.some((b) => b.type === "text"), false, "empty text block dropped");
  assert.equal(content.length, 1);
  assert.equal(content[0].type, "mcp_tool_use");
});

test("string-content (user) messages pass through untouched", () => {
  const api = toApiMessages([{ role: "user", content: "explain the solutions" }]);
  assert.deepEqual(api, [{ role: "user", content: "explain the solutions" }]);
});

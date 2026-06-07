/**
 * Unit tests for the pure Anthropic request-shaping helpers (prompt caching + native context
 * management). Run with Node's built-in runner + type-stripping — no deps:
 *   node --test --experimental-strip-types lib/anthropic-request.test.ts
 * (the `npm test` script globs lib/*.test.ts). The functions take their enable/mode as explicit
 * args so both on and off paths are testable without env juggling.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  cachedSystem,
  cachedTools,
  withCacheBreakpoint,
  contextManagement,
} from "./anthropic-request.ts";

const CC = { type: "ephemeral" };

test("cachedSystem: block array with cache_control when on; plain string when off", () => {
  assert.deepEqual(cachedSystem("sys", true), [{ type: "text", text: "sys", cache_control: CC }]);
  assert.equal(cachedSystem("sys", false), "sys");
});

test("cachedTools: marks the last tool, leaves the rest, never mutates the input", () => {
  const tools = [{ name: "a" }, { name: "b" }];
  const out = cachedTools(tools, true);
  assert.deepEqual(out[1], { name: "b", cache_control: CC });
  assert.deepEqual(out[0], { name: "a" }); // earlier tool untouched
  assert.deepEqual(tools, [{ name: "a" }, { name: "b" }]); // original unmutated
  assert.equal(cachedTools(tools, false), tools); // off → same ref
  assert.deepEqual(cachedTools([], true), []); // empty → no crash
});

test("withCacheBreakpoint: marks last block of last message; string content → text block", () => {
  const msgs = [
    { role: "user", content: "hi" },
    { role: "assistant", content: [{ type: "text", text: "a" }, { type: "text", text: "b" }] },
    { role: "user", content: "again" },
  ];
  const out = withCacheBreakpoint(msgs, true);
  // last message's string content became a cache-marked text block
  assert.deepEqual(out[2], { role: "user", content: [{ type: "text", text: "again", cache_control: CC }] });
  // earlier messages untouched; original array + objects unmutated
  assert.equal(out[1], msgs[1]);
  assert.equal(msgs[2].content, "again");
});

test("withCacheBreakpoint: marks the final block of an array-content last message", () => {
  const msgs = [{ role: "assistant", content: [{ type: "text", text: "x" }, { type: "tool_use", id: "t" }] }];
  const out = withCacheBreakpoint(msgs, true);
  const blocks = out[0].content as any[];
  assert.equal(blocks[1].cache_control?.type, "ephemeral");
  assert.equal(blocks[0].cache_control, undefined); // only the last block
  // original objects not mutated
  assert.equal((msgs[0].content as any[])[1].cache_control, undefined);
});

test("withCacheBreakpoint: skips a trailing thinking block (API rejects cache_control there)", () => {
  const msgs = [{ role: "assistant", content: [{ type: "text", text: "x" }, { type: "thinking", thinking: "…" }] }];
  const out = withCacheBreakpoint(msgs, true);
  assert.equal(out, msgs); // returned unchanged — no breakpoint forced onto a thinking block
});

test("withCacheBreakpoint: no-ops when off or empty", () => {
  const msgs = [{ role: "user", content: "hi" }];
  assert.equal(withCacheBreakpoint(msgs, false), msgs);
  assert.equal(withCacheBreakpoint([], true).length, 0);
});

test("contextManagement: clear_tool_uses excludes get_skill; compact has its own beta; off → null", () => {
  const clear = contextManagement("clear_tool_uses")!;
  assert.equal(clear.beta, "context-management-2025-06-27");
  assert.deepEqual(clear.context_management, {
    edits: [{ type: "clear_tool_uses_20250919", exclude_tools: ["get_skill"] }],
  });
  const compact = contextManagement("compact")!;
  assert.equal(compact.beta, "compact-2026-01-12");
  assert.deepEqual(compact.context_management, { edits: [{ type: "compact_20260112" }] });
  assert.equal(contextManagement("off"), null);
  assert.equal(contextManagement("nonsense"), null);
});

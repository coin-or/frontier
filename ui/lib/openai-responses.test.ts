/**
 * Unit tests for the pure Responses-wire helpers (OPENAI_WIRE=responses). Run with
 * Node's built-in runner + type-stripping — no deps:
 *   node --test --experimental-strip-types lib/openai-responses.test.ts
 * (the `npm test` script globs lib/*.test.ts).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildResponsesTools, translateMessagesToResponsesInput } from "./openai-responses.ts";

test("buildResponsesTools: flat function tools, schema defaulted", () => {
  const tools = buildResponsesTools([
    { name: "model", description: "Build the model", inputSchema: { type: "object", properties: { action: {} } } },
    { name: "solve" },
  ]);
  assert.deepEqual(tools[0], {
    type: "function",
    name: "model",
    description: "Build the model",
    parameters: { type: "object", properties: { action: {} } },
  });
  // No nested `function` wrapper (that's the chat-completions shape).
  assert.equal((tools[0] as any).function, undefined);
  assert.deepEqual(tools[1].parameters, { type: "object", properties: {} });
});

test("translate: plain string turns become role messages with typed text parts", () => {
  const input = translateMessagesToResponsesInput([
    { role: "user", content: "hello" },
    { role: "assistant", content: "hi there" },
  ]);
  assert.deepEqual(input, [
    { role: "user", content: [{ type: "input_text", text: "hello" }] },
    { role: "assistant", content: [{ type: "output_text", text: "hi there" }] },
  ]);
});

test("translate: assistant tool_use + embedded result become call/output pairs in order", () => {
  const input = translateMessagesToResponsesInput([
    {
      role: "assistant",
      content: [
        { type: "text", text: "Let me check." },
        { type: "mcp_tool_use", id: "call_1", name: "solve", input: { action: "run" } },
        { type: "mcp_tool_result", tool_use_id: "call_1", content: [{ type: "text", text: "{\"ok\":true}" }] },
        { type: "text", text: "Done." },
      ],
    },
  ]);
  assert.deepEqual(input, [
    { role: "assistant", content: [{ type: "output_text", text: "Let me check." }] },
    { type: "function_call", call_id: "call_1", name: "solve", arguments: '{"action":"run"}' },
    { type: "function_call_output", call_id: "call_1", output: '{"ok":true}' },
    { role: "assistant", content: [{ type: "output_text", text: "Done." }] },
  ]);
});

test("translate: function_call_output always follows its function_call (wire ordering constraint)", () => {
  const input = translateMessagesToResponsesInput([
    {
      role: "assistant",
      content: [
        { type: "mcp_tool_use", id: "a", name: "model", input: {} },
        { type: "mcp_tool_result", tool_use_id: "a", content: "r1" },
        { type: "mcp_tool_use", id: "b", name: "explore", input: { action: "tradeoffs" } },
        { type: "mcp_tool_result", tool_use_id: "b", content: "r2" },
      ],
    },
  ]);
  const kinds = input.map((i: any) => i.type ?? i.role);
  assert.deepEqual(kinds, ["function_call", "function_call_output", "function_call", "function_call_output"]);
  assert.equal((input[1] as any).call_id, "a");
  assert.equal((input[3] as any).call_id, "b");
});

test("translate: user turn with round-tripped tool results splits text and outputs", () => {
  const input = translateMessagesToResponsesInput([
    {
      role: "user",
      content: [
        { type: "text", text: "and now?" },
        { type: "mcp_tool_result", tool_use_id: "c", content: [{ type: "text", text: "res" }] },
      ],
    },
  ]);
  assert.deepEqual(input[0], { role: "user", content: [{ type: "input_text", text: "and now?" }] });
  assert.deepEqual(input[1], { type: "function_call_output", call_id: "c", output: "res" });
});

test("translate: empty text buffers never emit empty message items", () => {
  const input = translateMessagesToResponsesInput([
    { role: "assistant", content: [{ type: "mcp_tool_use", id: "x", name: "solve", input: {} }] },
  ]);
  assert.equal(input.length, 1);
  assert.equal((input[0] as any).type, "function_call");
});

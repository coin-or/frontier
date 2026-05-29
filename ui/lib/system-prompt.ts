/**
 * Identity-only system prompt.
 *
 * Per the design doc (§2 Principle 2, §4.1), the MCP server drives behavior;
 * surfaces are intentionally thin consumers. NO skill content is duplicated
 * into this prompt — all workflow guidance flows from tool descriptions and
 * tool-response auto-injection in the Frontier MCP server.
 *
 * If something needs to change about agent behavior, fix it in the MCP server
 * (server.py / skills/*) — never patch this prompt.
 */
export const SYSTEM_PROMPT =
  "You are Frontier, an assistant for structured multi-objective decision making. " +
  "Use the available frontier tools to help users model decisions, run optimization, " +
  "and explore tradeoffs. Tool responses include workflow guidance — read and apply it.";

# ETF Portfolio Demo — Issues

**Run date:** 2026-04-12
**Problem:** ETF Portfolio Allocation (25 ETFs, 3 objectives, proportional)
**Problem ID:** ca897b3a-726e-4266-abd5-195eb48c07d9

---

## 1. `model create` silently drops objectives and options

**Severity:** High → **INVESTIGATED**
**Step:** Step 1 — Problem creation
**Root cause:** Python code is correct — `_model_create()` properly persists objectives/options (verified by unit test). The issue is at the MCP transport layer: the MCP client either didn't send the params or the response was truncated before reaching the agent.
**Status:** Code verified correct. The fact that `model update` works with the same code path confirms this is an MCP client/transport issue, not a server bug.
**Workaround:** Use `model update` to add objectives/options after create (works reliably).

---

## 2. Options require dict format `{"name": "X"}`, not strings

**Severity:** Low → **FIXED**
**Fix:** Added string shorthand support in both `_model_create` and `_model_update`. Options can now be passed as `["VOO", "VTV"]` or `[{"name": "VOO"}, {"name": "VTV"}]`.
**File:** `frontier/mcp_server/server.py`

---

## 3. No `_skill_guidance` auto-injection observed

**Severity:** High → **FIXED**
**Root cause:** The injection code works correctly — `_skill_guidance` IS added to result dicts (verified by unit test). However, the full skill files (7-28KB of markdown) were being injected as the `content` field, making responses so large that the MCP client/context compression stripped or truncated them.
**Fix:** Replaced full skill content injection with condensed key points (~300-400 chars) plus a reference to `get_skill()` for the full guide. Now `_skill_guidance` contains:
- `skill`: skill name
- `reason`: why it was injected
- `key_points`: 5 actionable bullet points (~300 chars)
- `full_skill`: reference to call `get_skill('name')` for complete guide
**File:** `frontier/mcp_server/server.py`
**Verified:** End-to-end test confirms all 3 phase transitions now inject guidance that fits in MCP responses.

---

## 4. Marginal analysis returns empty results

**Severity:** Medium → **FALSE ALARM**
**Root cause:** The marginal analysis works correctly and returned 165 rate segments per pair with knee detection. The demo script used wrong key names when extracting results:
- Used `segments` → actual key is `rates`
- Used `knees` (plural) → actual key is `knee` (singular)
**Data found:** 2 pairs analyzed (Return↔Vol r=-0.94, Return↔Yield r=-0.87), 165 segments each, knee at solution 31 with jump factors of 746.6x and 1030.3x.

---

## 5. Solver output exceeds token limits

**Severity:** Low (UX) — **NOT FIXED (by design)**
**Status:** With 166 solutions x 25 allocations, the raw solve output is inherently large (164K chars). The `explore` tools provide compact summaries (tradeoffs, compare, curate) that work well within MCP limits. Consider adding a `summary_only` flag to solve in a future iteration.

/**
 * Unit tests for extractVizData — the single parse point every rendered chart depends
 * on (chat surface and /api/render both route through it). Pure logic, so it runs with
 * Node's built-in test runner + TypeScript type-stripping:
 *
 *   node --test --experimental-strip-types lib/viz-data.test.ts
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { extractVizData } from "./viz-data.ts";

test("top-level viz_data is extracted", () => {
  const text = JSON.stringify({
    total_solutions: 3,
    viz_data: { type: "frontier_scatter", points: [], objectives: [] },
  });
  const out = extractVizData(text);
  assert.equal(out.length, 1);
  assert.equal(out[0].type, "frontier_scatter");
});

test("nested pairs[].viz_data are all extracted", () => {
  const text = JSON.stringify({
    pairs: [
      { objectives: ["A", "B"], viz_data: { type: "marginal_rates", rows: [] } },
      { objectives: ["A", "C"], viz_data: { type: "marginal_rates", rows: [] } },
      { objectives: ["B", "C"] }, // no viz_data — skipped, not crashed on
    ],
  });
  const out = extractVizData(text);
  assert.equal(out.length, 2);
  assert.ok(out.every((v) => v.type === "marginal_rates"));
});

test("non-JSON and shapeless payloads yield an empty list", () => {
  assert.deepEqual(extractVizData("plain prose, not JSON"), []);
  assert.deepEqual(extractVizData(JSON.stringify({ note: "no charts here" })), []);
  assert.deepEqual(extractVizData(JSON.stringify({ viz_data: { untyped: true } })), []);
});

test("scenario_summary carries the regret contract the panel renders", () => {
  const regret = {
    available: true,
    minimax_choice: { solution_id: 20, max_regret: 0.581 },
    per_solution: [
      {
        solution_id: 20,
        max_regret: 0.581,
        mean_regret: 0.581,
        by_scenario: { china: 0.581, surge: 1.0 },
        feasible_in_all: false,
        feasible_in_ranked: true,
      },
    ],
    per_solution_total: 40, // the compact slice hides 39 rows, not per_solution.length-1
    saturated: false,
    wipeout_scenarios: ["surge"],
    wipeout_note: "no base-frontier solution is feasible under: surge",
    survivors_by_scenario: { china: 21, surge: 0 },
  };
  const text = JSON.stringify({
    viz_data: {
      type: "scenario_summary",
      scenarios: ["china", "surge"],
      option_robustness: [],
      regret,
    },
  });
  const out = extractVizData(text);
  assert.equal(out.length, 1);
  const viz = out[0] as any;
  assert.equal(viz.type, "scenario_summary");
  assert.deepEqual(viz.regret.wipeout_scenarios, ["surge"]);
  assert.equal(viz.regret.per_solution_total, 40);
  assert.equal(viz.regret.per_solution[0].feasible_in_ranked, true);
  assert.equal(viz.regret.survivors_by_scenario.surge, 0);
});

/**
 * Types and extractor for the structured viz_data payloads that Frontier's
 * `explore/*` tools attach alongside ASCII visualizations.
 *
 * Engine source: `engine/explorer.py` `_viz_data_*` builders.
 * Hosts that can render charts (this web UI) consume viz_data; chat / coding-
 * agent surfaces ignore it and render the ASCII `visualization` field instead.
 */

export type ObjectiveMeta = {
  name: string;
  direction: "minimize" | "maximize";
  min: number;
  max: number;
};

export type ScatterPoint = {
  solution_id: number;
  values: Record<string, number>;
};

export type ScatterVizData = {
  type: "scatter";
  objectives: ObjectiveMeta[];
  points: ScatterPoint[];
  extremes: Record<string, { best_id: number; worst_id: number }>;
  balanced_id: number;
  inflection_ids: number[];
};

export type ParallelCoordsSeries = {
  id: number | string;
  label: string;
  values: Record<string, number>;
};

export type ParallelCoordsVizData = {
  type: "parallel_coords";
  axes: ObjectiveMeta[];
  series: ParallelCoordsSeries[];
};

export type MarginalRate = {
  from_id: number;
  to_id: number;
  rate: number;
  [k: string]: unknown;
};

export type MarginalRatesVizData = {
  type: "marginal_rates";
  from_objective: { name: string; direction: "minimize" | "maximize" };
  to_objective: { name: string; direction: "minimize" | "maximize" };
  rates: MarginalRate[];
  inflection: { solution_id: number; position: number; jump_factor: number } | null;
};

export type ScenarioSummaryVizData = {
  type: "scenario_summary";
  scenarios: string[];
  option_robustness: Array<Record<string, unknown>>;
  expected_values: Record<string, unknown>;
  scenario_risk: Record<string, unknown>;
};

export type VizData =
  | ScatterVizData
  | ParallelCoordsVizData
  | MarginalRatesVizData
  | ScenarioSummaryVizData;

/**
 * Walk a tool_result's text payload and pull out every viz_data block.
 * Handles:
 *   - top-level `viz_data` (tradeoffs, compare, compare_curated, scenario_results)
 *   - nested `pairs[].viz_data` (marginal_analysis returns multiple pairs)
 * Returns [] if not parseable JSON or no viz_data present.
 */
export function extractVizData(text: string): VizData[] {
  let parsed: any;
  try {
    parsed = JSON.parse(text);
  } catch {
    return [];
  }
  const out: VizData[] = [];
  if (parsed && typeof parsed === "object") {
    if (parsed.viz_data && parsed.viz_data.type) {
      out.push(parsed.viz_data as VizData);
    }
    if (Array.isArray(parsed.pairs)) {
      for (const p of parsed.pairs) {
        if (p && p.viz_data && p.viz_data.type) {
          out.push(p.viz_data as VizData);
        }
      }
    }
  }
  return out;
}

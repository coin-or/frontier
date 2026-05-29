"use client";

import type { VizData } from "@/lib/viz-data";
import { Scatter } from "./Scatter";
import { ParallelCoords } from "./ParallelCoords";
import { MarginalRates } from "./MarginalRates";
import { ScenarioSummary } from "./ScenarioSummary";

/**
 * Dispatcher: pick the right chart component for a viz_data payload.
 * Unknown types render nothing (silently — the ASCII fallback is still in the
 * tool_result text and remains visible inside the ToolCallBlock).
 */
export function VizRenderer({ data }: { data: VizData }) {
  switch (data.type) {
    case "scatter":
      return <Scatter data={data} />;
    case "parallel_coords":
      return <ParallelCoords data={data} />;
    case "marginal_rates":
      return <MarginalRates data={data} />;
    case "scenario_summary":
      return <ScenarioSummary data={data} />;
    default:
      return null;
  }
}

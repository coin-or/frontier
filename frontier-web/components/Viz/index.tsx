"use client";

import type { VizData } from "@/lib/viz-data";
import { Scatter } from "./Scatter";
import { ParallelCoords } from "./ParallelCoords";
import { MarginalRates } from "./MarginalRates";

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
      // not rendered as a chart for now — scenario_summary is more table-like.
      // The text payload + tool_result block already conveys the data; D3 view
      // can be added later if signal demands.
      return null;
    default:
      return null;
  }
}

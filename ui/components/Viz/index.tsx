"use client";

import type { VizData } from "@/lib/viz-data";
import { FrontierPlot } from "./FrontierPlot";
import { ParallelCoords } from "./ParallelCoords";
import { MarginalRates } from "./MarginalRates";
import { ScenarioSummary } from "./ScenarioSummary";

/**
 * Dispatcher: pick the right chart component for a viz_data payload.
 * Unknown types render nothing — the UI surfaces only the LLM's prose and
 * charts, not raw tool output, so there is no ASCII fallback to show.
 */
export function VizRenderer({ data }: { data: VizData }) {
  switch (data.type) {
    case "scatter":
      return <FrontierPlot data={data} />;
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

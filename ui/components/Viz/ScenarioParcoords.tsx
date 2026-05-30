"use client";

import dynamic from "next/dynamic";
import type { ScenarioParcoordsVizData } from "@/lib/viz-data";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const SCEN_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2"];

/**
 * Per-scenario Pareto frontiers overlaid as one parallel-coords plot, each line
 * colored by its scenario — shows how the achievable tradeoffs shift across futures.
 */
export function ScenarioParcoords({ data }: { data: ScenarioParcoordsVizData }) {
  const dimensions = data.axes.map((o) => ({
    label: `${o.name} ${o.direction === "maximize" ? "↑" : "↓"}`,
    range: [o.min, o.max],
    values: data.lines.map((l) => l.values[o.name] ?? 0),
  }));
  const maxIdx = Math.max(1, data.scenarios.length - 1);
  const colorscale = data.scenarios.map(
    (_, i) => [i / maxIdx, SCEN_COLORS[i % SCEN_COLORS.length]] as [number, string]
  );

  return (
    <div className="my-3 rounded border border-stone-200 bg-white p-3">
      <div className="mb-1 flex items-center justify-between text-[10px] text-stone-500">
        <span>
          per-scenario frontiers · {data.lines.length} solutions · {data.scenarios.length} scenarios
        </span>
        <div className="flex items-center gap-3">
          {data.scenarios.map((s, i) => (
            <span key={s} className="flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: SCEN_COLORS[i % SCEN_COLORS.length] }}
              />
              {s}
            </span>
          ))}
        </div>
      </div>
      <Plot
        data={
          [
            {
              type: "parcoords",
              labelfont: { size: 12 },
              dimensions,
              line: {
                color: data.lines.map((l) => l.scenario),
                colorscale,
                cmin: 0,
                cmax: maxIdx,
              },
            },
          ] as never
        }
        layout={
          {
            autosize: true,
            height: 380,
            margin: { l: 80, r: 60, t: 56, b: 20 },
            paper_bgcolor: "rgba(0,0,0,0)",
            font: { size: 11, color: "#292524" },
          } as never
        }
        config={{ displaylogo: false, responsive: true } as never}
        useResizeHandler
        style={{ width: "100%" }}
      />
      <div className="mt-1 text-[10px] text-stone-400">
        Each line is a Pareto-optimal solution under one scenario; drag an axis to brush.
      </div>
    </div>
  );
}

"use client";

import dynamic from "next/dynamic";
import type { CuratedScenarioPick, ScenarioParcoordsVizData } from "@/lib/viz-data";

// Plotly needs window/WebGL — load client-side only.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const SCEN_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2"];
const SHARED_COLOR = "#111827"; // invariant pick feasible across several scenarios (robust)
const NONE_COLOR = "#9ca3af"; // pick feasible in no scenario (base-only)

function fmtTick(v: number): string {
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (a >= 100) return v.toFixed(0);
  if (a >= 1) return v.toFixed(1);
  return v.toFixed(2);
}

/**
 * Per-scenario Pareto frontiers as a parallel-coordinates overlay.
 *
 * Built from plain scatter line traces (not Plotly's `parcoords`, which can't vary
 * width/opacity per line): one null-separated WebGL trace per scenario for the faint
 * field, and one bold SVG trace per curated pick on top. Picks are colored by the
 * scenario(s) they're feasible in — one scenario → that color, several (same profile)
 * → SHARED, none → grey; a pick that drifts across score-based scenarios draws one
 * bold line per scenario (the colored fan). Axes are drawn as shapes + annotations.
 * Fully data-driven — no per-problem assumptions.
 */
export function ScenarioParcoords({ data }: { data: ScenarioParcoordsVizData }) {
  const axes = data.axes;
  const n = axes.length;
  const lastName = axes[n - 1]?.name;
  const curated = data.curated ?? [];
  const hasPicks = curated.length > 0;

  const norm = (ai: number, v: number) => {
    const a = axes[ai];
    if (a.max === a.min) return 0.5;
    return Math.max(0, Math.min(1, (v - a.min) / (a.max - a.min)));
  };

  const invColor = (pres: number[]) =>
    pres.length === 0 ? NONE_COLOR : pres.length === 1 ? SCEN_COLORS[pres[0] % SCEN_COLORS.length] : SHARED_COLOR;

  const pickDrawn = (c: CuratedScenarioPick) =>
    c.lines.filter((l) => l.scenario < 0 || c.present.includes(l.scenario));

  const traces: Record<string, unknown>[] = [];

  // Faint field — one null-separated trace per scenario (WebGL, renders behind).
  const fieldOpacity = hasPicks ? 0.16 : 0.5;
  data.scenarios.forEach((_, si) => {
    const xs: (number | null)[] = [];
    const ys: (number | null)[] = [];
    data.lines
      .filter((l) => l.scenario === si)
      .forEach((l) => {
        axes.forEach((a, i) => {
          xs.push(i);
          ys.push(norm(i, l.values[a.name] ?? a.min));
        });
        xs.push(null);
        ys.push(null);
      });
    if (xs.length) {
      traces.push({
        type: "scattergl",
        mode: "lines",
        x: xs,
        y: ys,
        line: { color: SCEN_COLORS[si % SCEN_COLORS.length], width: 1 },
        opacity: fieldOpacity,
        hoverinfo: "skip",
        showlegend: false,
      });
    }
  });

  // Bold curated picks — one SVG trace per drawn line (renders in front of WebGL).
  curated.forEach((c) => {
    pickDrawn(c).forEach((l) => {
      const color = l.scenario >= 0 ? SCEN_COLORS[l.scenario % SCEN_COLORS.length] : invColor(c.present);
      traces.push({
        type: "scatter",
        mode: "lines",
        x: axes.map((_, i) => i),
        y: axes.map((a, i) => norm(i, l.values[a.name] ?? a.min)),
        line: { color, width: 2.6, dash: c.present.length === 0 ? "dot" : "solid", shape: "linear" },
        opacity: 0.95,
        text: axes.map((a) => `${a.name}: ${fmtTick(l.values[a.name] ?? 0)}`),
        hovertemplate: `<b>${c.name}</b><br>%{text}<extra></extra>`,
        showlegend: false,
      });
    });
  });

  // Axes as vertical shapes.
  const shapes = axes.map((_, i) => ({
    type: "line",
    xref: "x",
    yref: "y",
    x0: i,
    x1: i,
    y0: 0,
    y1: 1,
    line: { color: "#e7e5e4", width: 1 },
  }));

  // Annotations: axis name / direction / min+max ticks.
  const annotations: Record<string, unknown>[] = [];
  axes.forEach((a, i) => {
    annotations.push({ x: i, y: 1.13, xref: "x", yref: "y", text: `<b>${a.name}</b>`, showarrow: false, font: { size: 11, color: "#44403c" } });
    annotations.push({ x: i, y: 1.07, xref: "x", yref: "y", text: a.direction === "maximize" ? "↑ max" : "↓ min", showarrow: false, font: { size: 9, color: "#78716c" } });
    annotations.push({ x: i, y: 1.0, yshift: 7, xref: "x", yref: "y", text: fmtTick(a.max), showarrow: false, font: { size: 8, color: "#a8a29e" } });
    annotations.push({ x: i, y: 0, yshift: -8, xref: "x", yref: "y", text: fmtTick(a.min), showarrow: false, font: { size: 8, color: "#a8a29e" } });
  });

  // Pick labels at the right edge, spaced so they don't overlap.
  const pickLabels = curated
    .map((c) => {
      const ys = pickDrawn(c).map((l) => norm(n - 1, l.values[lastName] ?? axes[n - 1].min));
      const y = ys.length ? ys.reduce((s, v) => s + v, 0) / ys.length : 0.5;
      return { name: c.name, color: c.invariant ? invColor(c.present) : SHARED_COLOR, y };
    })
    .sort((a, b) => a.y - b.y);
  const gap = 0.07;
  for (let i = 1; i < pickLabels.length; i++) {
    if (pickLabels[i].y < pickLabels[i - 1].y + gap) pickLabels[i].y = pickLabels[i - 1].y + gap;
  }
  pickLabels.forEach((p) =>
    annotations.push({
      x: n - 1,
      y: p.y,
      xref: "x",
      yref: "y",
      xshift: 8,
      text: p.name,
      showarrow: false,
      xanchor: "left",
      font: { size: 10, color: p.color },
    })
  );

  return (
    <div data-viz="scenario-parcoords" className="my-3 rounded border border-stone-200 bg-white p-3">
      <div className="mb-1 flex items-center justify-between text-[10px] text-stone-500">
        <span>
          per-scenario frontiers · {data.lines.length} solutions · {data.scenarios.length} scenarios
          {hasPicks ? ` · ${curated.length} curated` : ""}
        </span>
        <div className="flex items-center gap-3">
          {data.scenarios.map((s, i) => (
            <span key={s} className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: SCEN_COLORS[i % SCEN_COLORS.length] }} />
              {s}
            </span>
          ))}
        </div>
      </div>

      <Plot
        data={traces as never}
        layout={
          {
            autosize: true,
            height: 380,
            margin: { l: 26, r: hasPicks ? 112 : 26, t: 34, b: 22 },
            xaxis: { range: [-0.4, n - 1 + 0.4], showgrid: false, zeroline: false, showticklabels: false, fixedrange: true },
            yaxis: { range: [-0.14, 1.22], showgrid: false, zeroline: false, showticklabels: false, fixedrange: true },
            shapes,
            annotations,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { size: 11, color: "#292524" },
            showlegend: false,
            hovermode: "closest",
          } as never
        }
        config={{ displaylogo: false, responsive: true, displayModeBar: false } as never}
        useResizeHandler
        style={{ width: "100%" }}
      />

      <div className="mt-1 text-[10px] text-stone-400">
        Faint lines: each scenario&apos;s Pareto frontier.
        {hasPicks
          ? " Bold lines: curated picks, colored by the scenario(s) they're feasible in — grey = none, black = robust across several, or one bold line per scenario when a pick shifts."
          : " Each line is a Pareto-optimal solution under one scenario."}
      </div>
    </div>
  );
}

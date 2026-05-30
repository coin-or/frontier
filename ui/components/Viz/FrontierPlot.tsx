"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { ScatterVizData, ScatterPoint } from "@/lib/viz-data";
import { useChatAction } from "@/lib/chat-action";

// Plotly needs window/WebGL — load client-side only.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const ROLE_COLOR = {
  balanced: "#a855f7",
  inflection: "#f59e0b",
  extreme: "#ef4444",
  other: "#78716c",
} as const;
type Role = keyof typeof ROLE_COLOR;

const SELECTED_COLOR = "#111827";

type Selected = { id: number; name: string | null; values: Record<string, number> } | null;
type Effective = "scatter2d" | "scatter3d" | "parcoords";

/**
 * Frontier solutions, rendered by dimensionality:
 *   2 objectives  → 2D scatter (WebGL, zoom + click-select)
 *   3 objectives  → 3D scatter (orbit/rotate, zoom, click-select)
 *   ≥4 objectives → parallel coordinates (axis brushing)
 * A toggle lets the user force parallel coordinates at any dimensionality (≤3),
 * since PC is often the most interpretable multi-objective view. Points are
 * role-colored (balanced / inflection / extreme / other); clicking a scatter
 * point reads out its id + curated name.
 */
function inRanges(v: number, cr: number[] | number[][] | undefined): boolean {
  if (!cr || cr.length === 0) return true;
  const ranges = (Array.isArray(cr[0]) ? cr : [cr]) as number[][];
  return ranges.some((r) => v >= Math.min(r[0], r[1]) && v <= Math.max(r[0], r[1]));
}

export function FrontierPlot({ data }: { data: ScatterVizData }) {
  const [selected, setSelected] = useState<Selected>(null);
  const [brushIds, setBrushIds] = useState<number[]>([]);
  const chat = useChatAction();
  const objs = data.objectives;
  const nObj = objs.length;

  const canScatter = nObj <= 3;
  const [mode, setMode] = useState<"scatter" | "parcoords">("scatter");
  const effective: Effective =
    !canScatter || mode === "parcoords"
      ? "parcoords"
      : nObj <= 2
        ? "scatter2d"
        : "scatter3d";

  const roleOf = useMemo(() => {
    const extremeIds = new Set<number>();
    for (const o of objs) {
      const e = data.extremes[o.name];
      if (e) {
        extremeIds.add(e.best_id);
        extremeIds.add(e.worst_id);
      }
    }
    const inflSet = new Set(data.inflection_ids);
    return (id: number): Role =>
      id === data.balanced_id
        ? "balanced"
        : inflSet.has(id)
          ? "inflection"
          : extremeIds.has(id)
            ? "extreme"
            : "other";
  }, [data, objs]);

  const nameOf = (p: ScatterPoint) => p.name ?? null;

  const { plotData, layout } = useMemo(() => {
    const is3d = effective === "scatter3d";
    const colors = data.points.map((p) =>
      p.solution_id === selected?.id ? SELECTED_COLOR : ROLE_COLOR[roleOf(p.solution_id)]
    );
    const sizes = data.points.map((p) => {
      const big = roleOf(p.solution_id) !== "other";
      if (p.solution_id === selected?.id) return is3d ? 7 : 16;
      return is3d ? (big ? 4.5 : 3) : big ? 11 : 7;
    });
    const customdata = data.points.map((p) => [p.solution_id, nameOf(p) ?? "—"]);

    if (effective === "scatter2d") {
      const yName = objs[1]?.name ?? objs[0].name;
      return {
        plotData: [
          {
            type: "scattergl",
            mode: "markers",
            x: data.points.map((p) => p.values[objs[0].name]),
            y: data.points.map((p) => p.values[yName]),
            customdata,
            marker: { color: colors, size: sizes, line: { width: 0.5, color: "#ffffff" } },
            hovertemplate:
              `#%{customdata[0]} %{customdata[1]}<br>` +
              `${objs[0].name}: %{x:.2f}<br>${yName}: %{y:.2f}<extra></extra>`,
          },
        ],
        layout: {
          xaxis: { title: { text: `${objs[0].name} (${objs[0].direction})` } },
          yaxis: { title: { text: `${yName} (${objs[1]?.direction ?? objs[0].direction})` } },
          margin: { l: 60, r: 20, t: 10, b: 50 },
          dragmode: "zoom",
          hovermode: "closest",
        },
      };
    }

    if (effective === "scatter3d") {
      return {
        plotData: [
          {
            type: "scatter3d",
            mode: "markers",
            x: data.points.map((p) => p.values[objs[0].name]),
            y: data.points.map((p) => p.values[objs[1].name]),
            z: data.points.map((p) => p.values[objs[2].name]),
            customdata,
            marker: { color: colors, size: sizes, line: { width: 0 } },
            hovertemplate:
              `#%{customdata[0]} %{customdata[1]}<br>` +
              `${objs[0].name}: %{x:.2f}<br>${objs[1].name}: %{y:.2f}<br>${objs[2].name}: %{z:.2f}<extra></extra>`,
          },
        ],
        layout: {
          scene: {
            xaxis: { title: { text: objs[0].name } },
            yaxis: { title: { text: objs[1].name } },
            zaxis: { title: { text: objs[2].name } },
          },
          margin: { l: 0, r: 0, t: 0, b: 0 },
        },
      };
    }

    // parallel coordinates (role-colored lines, axis brushing) — any nObj ≥ 2
    const roleRank: Record<Role, number> = { other: 0, extreme: 1, inflection: 2, balanced: 3 };
    return {
      plotData: [
        {
          type: "parcoords",
          labelfont: { size: 12 },
          dimensions: objs.map((o) => ({
            label: `${o.name} ${o.direction === "maximize" ? "↑" : "↓"}`,
            range: [o.min, o.max],
            values: data.points.map((p) => p.values[o.name]),
          })),
          line: {
            color: data.points.map((p) => roleRank[roleOf(p.solution_id)]),
            colorscale: [
              [0, ROLE_COLOR.other],
              [0.33, ROLE_COLOR.extreme],
              [0.66, ROLE_COLOR.inflection],
              [1, ROLE_COLOR.balanced],
            ],
          },
        },
      ],
      layout: { margin: { l: 80, r: 60, t: 56, b: 20 } },
    };
  }, [data, objs, effective, roleOf, selected]);

  function onClick(e: { points?: Array<{ customdata?: [number, string] }> }) {
    const pt = e?.points?.[0];
    if (!pt?.customdata) return;
    const id = Number(pt.customdata[0]);
    const rawName = pt.customdata[1];
    const found = data.points.find((p) => p.solution_id === id);
    setSelected({
      id,
      name: rawName && rawName !== "—" ? String(rawName) : null,
      values: found ? { ...found.values } : {},
    });
  }

  // Parallel-coords selection is brushing: read the per-axis constraint ranges
  // and keep the solutions inside all of them (for the "curate selected" action).
  function onUpdate(figure: {
    data?: Array<{ dimensions?: Array<{ constraintrange?: number[] | number[][] }> }>;
  }) {
    if (effective !== "parcoords") return;
    const dims = figure?.data?.[0]?.dimensions;
    if (!dims) return;
    const next = dims.some((d) => d?.constraintrange)
      ? data.points
          .filter((p) => objs.every((o, i) => inRanges(p.values[o.name], dims[i]?.constraintrange)))
          .map((p) => p.solution_id)
      : [];
    const same = next.length === brushIds.length && next.every((v, i) => v === brushIds[i]);
    if (!same) setBrushIds(next);
  }

  const kind =
    effective === "scatter2d"
      ? "2D scatter"
      : effective === "scatter3d"
        ? "3D scatter"
        : "parallel coordinates";

  return (
    <div className="my-3 rounded border border-stone-200 bg-white p-3">
      <div className="mb-1 flex items-center justify-between text-[10px] text-stone-500">
        <span>
          {kind} · {data.points.length} solutions · {nObj} objectives
        </span>
        <div className="flex items-center gap-3">
          {canScatter && <Toggle mode={mode} setMode={setMode} nObj={nObj} />}
          <Legend />
        </div>
      </div>
      <Plot
        data={plotData as never}
        layout={
          {
            autosize: true,
            height: effective === "scatter3d" ? 460 : 380,
            showlegend: false,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { size: 11, color: "#292524" },
            ...layout,
          } as never
        }
        config={
          {
            displaylogo: false,
            responsive: true,
            modeBarButtonsToRemove: ["lasso2d", "select2d"],
          } as never
        }
        useResizeHandler
        style={{ width: "100%" }}
        onClick={onClick as never}
        onUpdate={onUpdate as never}
      />
      {selected && effective !== "parcoords" && (
        <div className="mt-1 flex items-center gap-2 text-[11px] text-stone-700">
          <span>
            <span className="font-semibold">
              Selected #{selected.id}
              {selected.name ? ` · ${selected.name}` : ""}
            </span>
            {" — "}
            {objs.map((o) => `${o.name} ${selected.values[o.name]?.toFixed(2) ?? "—"}`).join(" · ")}
          </span>
          {chat && (
            <button
              type="button"
              disabled={chat.streaming}
              onClick={() =>
                chat.sendMessage(
                  selected.name
                    ? `Remove the curated solution "${selected.name}" (#${selected.id}) from curation.`
                    : `Curate solution #${selected.id}.`
                )
              }
              className="shrink-0 rounded bg-stone-800 px-1.5 py-0.5 text-[10px] text-white hover:bg-stone-700 disabled:bg-stone-300"
            >
              {selected.name ? "− Uncurate" : "+ Curate"}
            </button>
          )}
        </div>
      )}
      {effective === "parcoords" && (
        <div className="mt-1 flex items-center gap-2 text-[10px] text-stone-400">
          <span>Drag along an axis to brush; double-click to clear.</span>
          {chat && brushIds.length > 0 && (
            <button
              type="button"
              disabled={chat.streaming}
              onClick={() =>
                chat.sendMessage(
                  `Curate the ${brushIds.length} brushed solution${brushIds.length > 1 ? "s" : ""}: ` +
                    brushIds
                      .slice(0, 12)
                      .map((id) => `#${id}`)
                      .join(", ") +
                    (brushIds.length > 12 ? `, and ${brushIds.length - 12} more` : "") +
                    "."
                )
              }
              className="shrink-0 rounded bg-stone-800 px-1.5 py-0.5 text-[10px] text-white hover:bg-stone-700 disabled:bg-stone-300"
            >
              + Curate selected ({brushIds.length})
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function Toggle({
  mode,
  setMode,
  nObj,
}: {
  mode: "scatter" | "parcoords";
  setMode: (m: "scatter" | "parcoords") => void;
  nObj: number;
}) {
  const scatterLabel = nObj <= 2 ? "2D" : "3D";
  const btn = (m: "scatter" | "parcoords", label: string) => (
    <button
      type="button"
      onClick={() => setMode(m)}
      className={`rounded px-1.5 py-0.5 ${
        mode === m ? "bg-stone-800 text-white" : "bg-stone-100 text-stone-600 hover:bg-stone-200"
      }`}
    >
      {label}
    </button>
  );
  return (
    <div className="flex items-center gap-1 text-[10px]">
      {btn("scatter", scatterLabel)}
      {btn("parcoords", "‖ PC")}
    </div>
  );
}

function Legend() {
  const items: Array<[Role, string]> = [
    ["balanced", "balanced"],
    ["inflection", "inflection"],
    ["extreme", "extreme"],
    ["other", "other"],
  ];
  return (
    <div className="flex items-center gap-3 text-[10px] text-stone-600">
      {items.map(([role, label]) => (
        <span key={role} className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: ROLE_COLOR[role] }}
          />
          {label}
        </span>
      ))}
    </div>
  );
}

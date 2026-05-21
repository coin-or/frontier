"use client";

import { useMemo, useState } from "react";
import * as d3 from "d3";
import type { ScatterVizData } from "@/lib/viz-data";

const MARGIN = { top: 16, right: 24, bottom: 50, left: 70 };
const W = 600;
const H = 380;

type Props = { data: ScatterVizData };

export function Scatter({ data }: Props) {
  const [hover, setHover] = useState<{
    sid: number;
    x: number;
    y: number;
    values: Record<string, number>;
  } | null>(null);

  // Pick the two most-conflicting objectives if available; otherwise first two.
  // For ≥2 objectives we just use the first pair — frontier-shape data lives
  // server-side; doing fancy pair selection client-side is out of scope.
  const xObj = data.objectives[0];
  const yObj = data.objectives[1];

  const { xScale, yScale, ticksX, ticksY } = useMemo(() => {
    const innerW = W - MARGIN.left - MARGIN.right;
    const innerH = H - MARGIN.top - MARGIN.bottom;
    const x = d3
      .scaleLinear()
      .domain([xObj?.min ?? 0, xObj?.max ?? 1])
      .range([0, innerW])
      .nice();
    const y = d3
      .scaleLinear()
      .domain([yObj?.min ?? 0, yObj?.max ?? 1])
      .range([innerH, 0])
      .nice();
    return {
      xScale: x,
      yScale: y,
      ticksX: x.ticks(6),
      ticksY: y.ticks(6),
    };
  }, [xObj, yObj]);

  if (!xObj || !yObj) {
    return (
      <div className="my-3 rounded border border-stone-200 bg-stone-50 p-3 text-xs text-stone-500">
        Need at least 2 objectives to render a scatter — only {data.objectives.length} present.
      </div>
    );
  }

  const innerW = W - MARGIN.left - MARGIN.right;
  const innerH = H - MARGIN.top - MARGIN.bottom;

  // Annotate points by role
  const extremeIds = new Set<number>();
  for (const o of [xObj.name, yObj.name]) {
    const e = data.extremes[o];
    if (e) {
      extremeIds.add(e.best_id);
      extremeIds.add(e.worst_id);
    }
  }
  const inflectionSet = new Set(data.inflection_ids);

  function colorOf(id: number): string {
    if (id === data.balanced_id) return "#a855f7"; // purple — balanced
    if (inflectionSet.has(id)) return "#f59e0b"; // amber — inflection
    if (extremeIds.has(id)) return "#ef4444"; // red — extreme
    return "#78716c"; // stone — regular
  }

  function radiusOf(id: number): number {
    if (id === data.balanced_id) return 7;
    if (inflectionSet.has(id) || extremeIds.has(id)) return 6;
    return 4.5;
  }

  return (
    <div className="my-3 rounded border border-stone-200 bg-white p-3">
      <div className="mb-1 flex items-center justify-between text-[10px] text-stone-500">
        <span>scatter · {data.points.length} solutions</span>
        <Legend />
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
          <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
            {/* axes */}
            <line x1={0} y1={innerH} x2={innerW} y2={innerH} stroke="#a8a29e" />
            <line x1={0} y1={0} x2={0} y2={innerH} stroke="#a8a29e" />
            {ticksX.map((t) => (
              <g key={`tx-${t}`} transform={`translate(${xScale(t)},${innerH})`}>
                <line y2={5} stroke="#a8a29e" />
                <text y={18} fontSize={10} textAnchor="middle" fill="#57534e">
                  {t}
                </text>
              </g>
            ))}
            {ticksY.map((t) => (
              <g key={`ty-${t}`} transform={`translate(0,${yScale(t)})`}>
                <line x2={-5} stroke="#a8a29e" />
                <text x={-9} y={3} fontSize={10} textAnchor="end" fill="#57534e">
                  {t}
                </text>
              </g>
            ))}
            {/* axis labels */}
            <text
              x={innerW / 2}
              y={innerH + 40}
              fontSize={11}
              textAnchor="middle"
              fill="#292524"
            >
              {xObj.name} ({xObj.direction})
            </text>
            <text
              transform={`translate(-52,${innerH / 2}) rotate(-90)`}
              fontSize={11}
              textAnchor="middle"
              fill="#292524"
            >
              {yObj.name} ({yObj.direction})
            </text>
            {/* points */}
            {data.points.map((p) => (
              <circle
                key={p.solution_id}
                cx={xScale(p.values[xObj.name] ?? 0)}
                cy={yScale(p.values[yObj.name] ?? 0)}
                r={radiusOf(p.solution_id)}
                fill={colorOf(p.solution_id)}
                opacity={0.85}
                onMouseEnter={(e) => {
                  const target = e.currentTarget;
                  const rect = target.getBoundingClientRect();
                  const parent = target.ownerSVGElement?.parentElement?.getBoundingClientRect();
                  setHover({
                    sid: p.solution_id,
                    x: rect.left + rect.width / 2 - (parent?.left ?? 0),
                    y: rect.top - (parent?.top ?? 0),
                    values: p.values,
                  });
                }}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: "pointer" }}
              />
            ))}
          </g>
        </svg>
        {hover && (
          <div
            className="pointer-events-none absolute z-10 rounded border border-stone-300 bg-white px-2 py-1 text-xs shadow"
            style={{ left: hover.x + 8, top: hover.y - 6, transform: "translateY(-100%)" }}
          >
            <div className="font-semibold">Solution {hover.sid}</div>
            {data.objectives.map((o) => (
              <div key={o.name} className="text-[10px] text-stone-600">
                {o.name}: {hover.values[o.name]?.toFixed(2) ?? "—"}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3 text-[10px] text-stone-600">
      <span className="flex items-center gap-1">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: "#a855f7" }}
        />
        balanced
      </span>
      <span className="flex items-center gap-1">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: "#f59e0b" }}
        />
        inflection
      </span>
      <span className="flex items-center gap-1">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: "#ef4444" }}
        />
        extreme
      </span>
      <span className="flex items-center gap-1">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: "#78716c" }}
        />
        other
      </span>
    </div>
  );
}

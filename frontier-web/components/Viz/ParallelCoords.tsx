"use client";

import { useMemo, useState } from "react";
import * as d3 from "d3";
import type { ParallelCoordsVizData } from "@/lib/viz-data";

const MARGIN = { top: 24, right: 60, bottom: 30, left: 60 };
const W = 680;
const H = 360;

const SERIES_COLORS = [
  "#0ea5e9",
  "#a855f7",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#84cc16",
  "#ec4899",
];

type Props = { data: ParallelCoordsVizData };

export function ParallelCoords({ data }: Props) {
  const [highlight, setHighlight] = useState<number | string | null>(null);

  const innerW = W - MARGIN.left - MARGIN.right;
  const innerH = H - MARGIN.top - MARGIN.bottom;

  const scales = useMemo(() => {
    return data.axes.map((a) =>
      d3.scaleLinear().domain([a.min, a.max]).range([innerH, 0]).nice()
    );
  }, [data.axes, innerH]);

  const xPositions = useMemo(() => {
    if (data.axes.length === 1) return [innerW / 2];
    const step = innerW / (data.axes.length - 1);
    return data.axes.map((_, i) => i * step);
  }, [data.axes.length, innerW]);

  if (data.axes.length === 0 || data.series.length === 0) {
    return (
      <div className="my-3 rounded border border-stone-200 bg-stone-50 p-3 text-xs text-stone-500">
        No axes or series available.
      </div>
    );
  }

  return (
    <div className="my-3 rounded border border-stone-200 bg-white p-3">
      <div className="mb-2 flex items-center justify-between text-[10px] text-stone-500">
        <span>
          parallel coordinates · {data.series.length} solutions ·{" "}
          {data.axes.length} axes
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {/* axes */}
          {data.axes.map((a, i) => {
            const x = xPositions[i];
            const scale = scales[i];
            const ticks = scale.ticks(5);
            return (
              <g key={a.name} transform={`translate(${x},0)`}>
                <line y1={0} y2={innerH} stroke="#a8a29e" />
                {ticks.map((t) => (
                  <g key={`${a.name}-t-${t}`} transform={`translate(0,${scale(t)})`}>
                    <line x2={-4} stroke="#a8a29e" />
                    <text
                      x={-7}
                      y={3}
                      fontSize={9}
                      textAnchor="end"
                      fill="#57534e"
                    >
                      {Number.isInteger(t) ? t : t.toFixed(2)}
                    </text>
                  </g>
                ))}
                <text
                  y={-10}
                  fontSize={11}
                  textAnchor="middle"
                  fill="#292524"
                >
                  {a.name}
                </text>
                <text
                  y={-22}
                  fontSize={9}
                  textAnchor="middle"
                  fill="#78716c"
                >
                  ({a.direction})
                </text>
              </g>
            );
          })}
          {/* series polylines */}
          {data.series.map((s, idx) => {
            const points = data.axes.map((a, i) =>
              [xPositions[i], scales[i](s.values[a.name] ?? 0)].join(",")
            );
            const isHi = highlight === s.id;
            const isMuted = highlight !== null && !isHi;
            return (
              <g key={String(s.id)}>
                <polyline
                  points={points.join(" ")}
                  fill="none"
                  stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
                  strokeWidth={isHi ? 2.5 : 1.5}
                  opacity={isMuted ? 0.2 : 0.85}
                  onMouseEnter={() => setHighlight(s.id)}
                  onMouseLeave={() => setHighlight(null)}
                  style={{ cursor: "pointer" }}
                />
              </g>
            );
          })}
        </g>
      </svg>
      {/* legend */}
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-stone-700">
        {data.series.map((s, idx) => (
          <span
            key={String(s.id)}
            onMouseEnter={() => setHighlight(s.id)}
            onMouseLeave={() => setHighlight(null)}
            className="flex cursor-pointer items-center gap-1"
            style={{
              opacity:
                highlight !== null && highlight !== s.id ? 0.4 : 1,
            }}
          >
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: SERIES_COLORS[idx % SERIES_COLORS.length] }}
            />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

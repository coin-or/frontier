"use client";

import { useMemo } from "react";
import * as d3 from "d3";
import type { MarginalRatesVizData } from "@/lib/viz-data";

const MARGIN = { top: 16, right: 16, bottom: 44, left: 56 };
const W = 600;
const ROW_H = 18;

type Props = { data: MarginalRatesVizData };

export function MarginalRates({ data }: Props) {
  const innerW = W - MARGIN.left - MARGIN.right;
  const totalH = MARGIN.top + MARGIN.bottom + data.rates.length * ROW_H;

  const xScale = useMemo(() => {
    const maxRate = Math.max(0.0001, ...data.rates.map((r) => Math.abs(r.rate)));
    return d3.scaleLinear().domain([0, maxRate]).range([0, innerW]).nice();
  }, [data.rates, innerW]);

  if (data.rates.length === 0) {
    return (
      <div className="my-3 rounded border border-stone-200 bg-stone-50 p-3 text-xs text-stone-500">
        No marginal rates to plot.
      </div>
    );
  }

  const inflectionPos = data.inflection?.position ?? -1;
  const ticks = xScale.ticks(5);

  return (
    <div className="my-3 rounded border border-stone-200 bg-white p-3">
      <div className="mb-1 text-[10px] text-stone-500">
        marginal rates · {data.from_objective.name} → {data.to_objective.name} ·{" "}
        {data.rates.length} transitions
        {data.inflection && (
          <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-amber-800">
            inflection at #{data.inflection.position} · jump ×
            {data.inflection.jump_factor.toFixed(1)}
          </span>
        )}
      </div>
      <svg viewBox={`0 0 ${W} ${totalH}`} className="w-full">
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {/* x ticks (top) */}
          <line x1={0} y1={0} x2={innerW} y2={0} stroke="#a8a29e" />
          {ticks.map((t) => (
            <g key={`tx-${t}`} transform={`translate(${xScale(t)},0)`}>
              <line y2={-4} stroke="#a8a29e" />
              <text y={-7} fontSize={9} textAnchor="middle" fill="#57534e">
                {Number.isInteger(t) ? t : t.toFixed(2)}
              </text>
            </g>
          ))}
          {/* bars per rate */}
          {data.rates.map((r, i) => {
            const y = i * ROW_H + 4;
            const isInf = i === inflectionPos;
            const w = xScale(Math.abs(r.rate));
            return (
              <g key={`${r.from_id}-${r.to_id}`}>
                <text
                  x={-6}
                  y={y + ROW_H / 2}
                  fontSize={9}
                  textAnchor="end"
                  fill={isInf ? "#b45309" : "#57534e"}
                  dominantBaseline="middle"
                  fontWeight={isInf ? 600 : 400}
                >
                  #{r.from_id}→#{r.to_id}
                </text>
                <rect
                  x={0}
                  y={y}
                  width={w}
                  height={ROW_H - 6}
                  fill={isInf ? "#f59e0b" : "#0ea5e9"}
                  opacity={0.85}
                />
                <text
                  x={w + 4}
                  y={y + ROW_H / 2}
                  fontSize={9}
                  fill="#292524"
                  dominantBaseline="middle"
                >
                  {r.rate.toFixed(3)}
                </text>
              </g>
            );
          })}
          {/* axis label */}
          <text
            x={innerW / 2}
            y={data.rates.length * ROW_H + 24}
            fontSize={10}
            textAnchor="middle"
            fill="#292524"
          >
            cost per unit {data.from_objective.name} → {data.to_objective.name}
          </text>
        </g>
      </svg>
    </div>
  );
}

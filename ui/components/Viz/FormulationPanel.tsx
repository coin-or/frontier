"use client";

import type { FormulationVizData } from "@/lib/viz-data";

/**
 * Structured formulation overview — the typed problem (objectives, constraints,
 * scenarios) the engine holds, rendered as a card. The "messy inputs → structured
 * problem" output.
 */
export function FormulationPanel({ data }: { data: FormulationVizData }) {
  return (
    <div data-viz="formulation" className="my-3 rounded border border-stone-200 bg-white p-3 text-sm">
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <span className="font-semibold text-stone-900">{data.name || "Problem"}</span>
        <span className="text-[10px] text-stone-500">
          {data.domain} · {data.approach} · {data.options_count} options
          {data.scores_complete < 1 ? ` · scores ${Math.round(data.scores_complete * 100)}%` : ""}
        </span>
      </div>

      <div className="mb-2">
        <div className="mb-1 text-[10px] uppercase tracking-wide text-stone-400">Objectives</div>
        <table className="w-full text-xs">
          <tbody>
            {data.objectives.map((o) => (
              <tr key={o.name} className="border-t border-stone-100">
                <td className="py-0.5 pr-2 font-medium text-stone-800">
                  {o.name}
                  {o.unit ? <span className="ml-1 font-normal text-stone-500">({o.unit})</span> : null}
                </td>
                <td className="py-0.5 pr-2 text-stone-600">
                  {o.direction === "maximize" ? "max ↑" : "min ↓"}
                </td>
                <td className="py-0.5 text-stone-500">{o.aggregation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.constraints.length > 0 && (
        <div className="mb-2">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-stone-400">Constraints</div>
          <ul className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-stone-700">
            {data.constraints.map((c, i) => (
              <li key={i} className="rounded bg-stone-100 px-1.5 py-0.5">
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.scenarios.length > 0 && (
        <div>
          <div className="mb-1 text-[10px] uppercase tracking-wide text-stone-400">Scenarios</div>
          <div className="flex flex-wrap gap-2 text-xs">
            {data.scenarios.map((s) => (
              <span
                key={s}
                className="rounded-full border border-stone-200 px-2 py-0.5 text-stone-700"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import type { ScenarioSummaryVizData } from "@/lib/viz-data";

type OptionRobustness = {
  option: string;
  tier?: "core" | "common" | "marginal";
  avg_frequency?: number;
  avg_weight?: number;
};

type ScenarioRiskEntry = {
  expected?: number;
  worst_case?: number;
  best_case?: number;
  range?: [number, number];
  [k: string]: unknown; // accommodates dynamic cvar_<α%> key
};

const TIER_STYLES: Record<string, string> = {
  core: "bg-emerald-100 text-emerald-800 border-emerald-300",
  common: "bg-sky-100 text-sky-800 border-sky-300",
  marginal: "bg-stone-100 text-stone-600 border-stone-300",
};

export function ScenarioSummary({ data }: { data: ScenarioSummaryVizData }) {
  const options = (data.option_robustness ?? []) as OptionRobustness[];
  const risks = (data.scenario_risk ?? {}) as Record<string, ScenarioRiskEntry>;
  const expected = (data.expected_values ?? {}) as Record<string, number>;
  const scenarios = data.scenarios ?? [];

  // Group options by tier for visual hierarchy
  const byTier: Record<string, OptionRobustness[]> = {
    core: [],
    common: [],
    marginal: [],
  };
  for (const opt of options) {
    const t = opt.tier ?? "marginal";
    (byTier[t] ?? byTier.marginal).push(opt);
  }

  return (
    <div className="my-3 rounded border border-stone-200 bg-white p-3 text-sm">
      <div className="mb-2 flex items-center justify-between text-[10px] text-stone-500">
        <span>
          scenario summary · {scenarios.length} scenarios
          {options.length > 0 && ` · ${options.length} options classified`}
        </span>
      </div>

      {scenarios.length > 0 && (
        <div className="mb-3 text-xs">
          <span className="text-stone-500">scenarios:</span>{" "}
          <span className="font-mono text-stone-700">{scenarios.join(", ")}</span>
        </div>
      )}

      {/* Option robustness by tier */}
      {options.length > 0 && (
        <div className="mb-3">
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-stone-600">
            Option robustness
          </div>
          <div className="space-y-1.5">
            {(["core", "common", "marginal"] as const).map((tier) =>
              byTier[tier].length === 0 ? null : (
                <div key={tier} className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase ${TIER_STYLES[tier]}`}
                  >
                    {tier}
                  </span>
                  {byTier[tier].map((o) => (
                    <span
                      key={o.option}
                      className="rounded bg-stone-50 px-1.5 py-0.5 text-xs text-stone-700"
                      title={
                        o.avg_frequency !== undefined
                          ? `freq: ${(o.avg_frequency * 100).toFixed(0)}%${
                              o.avg_weight !== undefined
                                ? `, weight: ${o.avg_weight.toFixed(2)}`
                                : ""
                            }`
                          : undefined
                      }
                    >
                      {o.option}
                      {o.avg_frequency !== undefined && (
                        <span className="ml-1 text-[10px] text-stone-400">
                          {(o.avg_frequency * 100).toFixed(0)}%
                        </span>
                      )}
                    </span>
                  ))}
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Scenario risk table */}
      {Object.keys(risks).length > 0 && (
        <div>
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-stone-600">
            Scenario risk per objective
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <thead className="text-stone-500">
                <tr>
                  <th className="border-b border-stone-200 px-2 py-1 text-left font-normal">
                    objective
                  </th>
                  <th className="border-b border-stone-200 px-2 py-1 text-right font-normal">
                    expected
                  </th>
                  <th className="border-b border-stone-200 px-2 py-1 text-right font-normal">
                    worst
                  </th>
                  <th className="border-b border-stone-200 px-2 py-1 text-right font-normal">
                    best
                  </th>
                  <th className="border-b border-stone-200 px-2 py-1 text-right font-normal">
                    CVaR
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(risks).map(([obj, r]) => {
                  const cvarKey = Object.keys(r).find((k) => k.startsWith("cvar_"));
                  const cvarVal = cvarKey ? (r[cvarKey] as number | null) : null;
                  return (
                    <tr key={obj} className="hover:bg-stone-50">
                      <td className="border-b border-stone-100 px-2 py-1 font-mono text-stone-700">
                        {obj}
                      </td>
                      <td className="border-b border-stone-100 px-2 py-1 text-right font-mono text-stone-800">
                        {fmt(r.expected ?? expected[obj])}
                      </td>
                      <td className="border-b border-stone-100 px-2 py-1 text-right font-mono text-red-700">
                        {fmt(r.worst_case)}
                      </td>
                      <td className="border-b border-stone-100 px-2 py-1 text-right font-mono text-emerald-700">
                        {fmt(r.best_case)}
                      </td>
                      <td className="border-b border-stone-100 px-2 py-1 text-right font-mono text-amber-700">
                        {fmt(cvarVal)}
                        {cvarKey && (
                          <span className="ml-1 text-[9px] text-stone-400">
                            {cvarKey.replace("cvar_", "")}%
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toString();
    return v.toFixed(2);
  }
  return String(v);
}

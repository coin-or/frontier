"use client";

import { useState } from "react";

type Props = {
  name: string;
  input: unknown;
  result?: string;
  isError?: boolean;
  pending?: boolean;
};

export function ToolCallBlock({ name, input, result, isError, pending }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="my-2 rounded-md border border-stone-300 bg-stone-50 text-xs">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left font-mono text-stone-700 hover:bg-stone-100"
      >
        <span className="flex items-center gap-2">
          <span className="inline-flex h-1.5 w-1.5 rounded-full" style={{
            background: isError ? "#dc2626" : pending ? "#f59e0b" : "#16a34a",
          }} />
          <span className="font-semibold">{name}</span>
          {pending && <span className="text-stone-400">running…</span>}
        </span>
        <span className="text-stone-400">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="border-t border-stone-200 px-3 py-2">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-stone-500">input</div>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[11px] text-stone-700">
            {JSON.stringify(input, null, 2)}
          </pre>
          {result !== undefined && (
            <>
              <div className="mb-1 mt-2 text-[10px] uppercase tracking-wide text-stone-500">
                result {isError ? "(error)" : ""}
              </div>
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] text-stone-700">
                {result}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}

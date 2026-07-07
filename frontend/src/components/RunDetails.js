import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Badge, statusTone } from "./Ui";

export function RunRow({ run }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-slate-200 rounded-lg mb-2 bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-50"
      >
        {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        <span className="font-medium text-sm text-slate-800 flex-1 truncate">
          {run.agent_name}
        </span>
        <Badge tone={statusTone(run.status)}>{run.status}</Badge>
        <span className="text-xs text-slate-400 hidden sm:block">
          {run.started_at?.slice(0, 19).replace("T", " ")}
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-slate-100">
          {run.summary && (
            <div className="mt-3 text-sm text-slate-700 whitespace-pre-wrap bg-slate-50 rounded-lg p-3">
              {run.summary}
            </div>
          )}
          {(run.steps || []).length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1.5">
                Tool calls ({run.steps.length})
              </p>
              {run.steps.map((s, i) => (
                <div key={i} className="text-xs font-mono bg-slate-900 text-slate-100 rounded-md p-2.5 mb-1.5 overflow-x-auto">
                  <span className={s.is_error ? "text-red-400" : "text-emerald-400"}>
                    {s.tool}
                  </span>
                  <span className="text-slate-400"> ← {JSON.stringify(s.input)}</span>
                  <div className="text-slate-300 mt-1 truncate">
                    → {JSON.stringify(s.result)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

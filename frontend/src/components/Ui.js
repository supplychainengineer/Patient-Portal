import React from "react";
import { X } from "lucide-react";

export function Card({ title, action, children, className = "" }) {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
          <h3 className="font-semibold text-slate-800">{title}</h3>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function Button({ children, variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-brand-700 hover:bg-brand-800 text-white",
    secondary: "bg-white hover:bg-slate-50 text-slate-700 border border-slate-300",
    danger: "bg-white hover:bg-red-50 text-red-600 border border-red-200",
  };
  return (
    <button
      className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium
        transition disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Badge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-red-700",
    teal: "bg-brand-100 text-brand-800",
    blue: "bg-blue-100 text-blue-700",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function statusTone(status) {
  return {
    completed: "green", sent: "green", running: "blue", dry_run: "amber",
    failed: "red", new: "teal", onboarded: "green", active: "blue",
  }[status] || "slate";
}

export function Field({ label, children, hint }) {
  return (
    <label className="block mb-3">
      <span className="block text-sm font-medium text-slate-700 mb-1">{label}</span>
      {children}
      {hint && <span className="block text-xs text-slate-500 mt-1">{hint}</span>}
    </label>
  );
}

export const inputCls =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none " +
  "focus:ring-2 focus:ring-brand-500 focus:border-brand-500";

export function Modal({ title, onClose, children, wide }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
         onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`bg-white rounded-xl shadow-xl w-full ${wide ? "max-w-3xl" : "max-w-lg"}
                       max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
          <h3 className="font-semibold text-slate-800">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function Empty({ children }) {
  return <p className="text-sm text-slate-500 py-6 text-center">{children}</p>;
}

export function Notice({ tone = "info", children }) {
  const tones = {
    info: "bg-blue-50 text-blue-800 border-blue-200",
    warn: "bg-amber-50 text-amber-800 border-amber-200",
    ok: "bg-emerald-50 text-emerald-800 border-emerald-200",
    error: "bg-red-50 text-red-800 border-red-200",
  };
  return <div className={`rounded-lg border px-4 py-3 text-sm ${tones[tone]}`}>{children}</div>;
}

import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  Bot, FileText, Inbox, LayoutDashboard, Mail, Settings, Users,
} from "lucide-react";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/patients", label: "Patients", icon: Users },
  { to: "/agents", label: "Agents", icon: Bot },
  { to: "/forms", label: "Forms & Documents", icon: FileText },
  { to: "/templates", label: "Email Templates", icon: Mail },
  { to: "/outbox", label: "Outbox", icon: Inbox },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 bg-brand-900 text-white flex flex-col">
        <div className="px-5 py-5 border-b border-white/10">
          <h1 className="font-bold text-lg leading-tight">Patient Portal</h1>
          <p className="text-xs text-brand-100/70 mt-0.5">Agentic automation</p>
        </div>
        <nav className="flex-1 py-3">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm transition ${
                  isActive
                    ? "bg-white/10 text-white font-medium border-r-2 border-brand-500"
                    : "text-brand-100/70 hover:text-white hover:bg-white/5"
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 text-[11px] text-brand-100/50 border-t border-white/10">
          6 agents · powered by Claude
        </div>
      </aside>
      <main className="flex-1 min-w-0 p-8 max-w-6xl">
        <Outlet />
      </main>
    </div>
  );
}

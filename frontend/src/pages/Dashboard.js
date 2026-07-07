import React, { useEffect, useState } from "react";
import { Bot, FileText, Mail, Users, Wallet } from "lucide-react";
import { api } from "../api";
import { RunRow } from "../components/RunDetails";
import { Card, Empty, Notice } from "../components/Ui";

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex items-center gap-4">
      <div className="w-10 h-10 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center">
        <Icon size={19} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800 leading-none">{value}</p>
        <p className="text-xs text-slate-500 mt-1">{label}</p>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/dashboard")
      .then((r) => setData(r.data))
      .catch(() => setError("Backend unreachable or MongoDB not connected — see Settings."));
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-800 mb-1">Dashboard</h2>
      <p className="text-sm text-slate-500 mb-6">
        Your agent team at a glance.
      </p>
      {error && <Notice tone="warn">{error}</Notice>}
      {data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
            <Stat icon={Users} label="Patients" value={data.patients} />
            <Stat icon={Bot} label="Agent runs" value={data.agent_runs} />
            <Stat icon={Mail} label="Emails" value={data.emails} />
            <Stat icon={FileText} label="Documents" value={data.documents} />
            <Stat icon={Wallet} label={`Pending dues (${data.pending_dues_count})`}
                  value={Number(data.pending_dues_total).toLocaleString()} />
          </div>
          <Card title="Recent agent activity">
            {data.recent_runs.length === 0 ? (
              <Empty>No agent runs yet — trigger one from the Agents page.</Empty>
            ) : (
              data.recent_runs.map((run) => <RunRow key={run.id} run={run} />)
            )}
          </Card>
        </>
      )}
    </div>
  );
}

import React, { useCallback, useEffect, useState } from "react";
import { Bot, Play } from "lucide-react";
import { api, errMessage } from "../api";
import { RunRow } from "../components/RunDetails";
import {
  Badge, Button, Card, Empty, Field, inputCls, Modal, Notice,
} from "../components/Ui";

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [patients, setPatients] = useState([]);
  const [runs, setRuns] = useState([]);
  const [running, setRunning] = useState(null); // agent being configured
  const [values, setValues] = useState({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  const load = useCallback(() => {
    api.get("/agents").then((r) => setAgents(r.data)).catch(() => {});
    api.get("/patients").then((r) => setPatients(r.data)).catch(() => {});
    api.get("/agents/runs").then((r) => setRuns(r.data)).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const openRun = (agent) => {
    setValues({});
    setNotice(null);
    setRunning(agent);
  };

  const trigger = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const payload = {};
      for (const f of running.input_fields) {
        const v = values[f.name];
        if (v === undefined || v === "") continue;
        payload[f.name] = f.type === "number" ? Number(v) : v;
      }
      const r = await api.post(`/agents/${running.key}/run`, { payload });
      setNotice({
        tone: r.data.status === "completed" ? "ok" : "error",
        text: `${r.data.agent_name}: ${r.data.status}. ${r.data.summary?.slice(0, 400) || ""}`,
      });
      setRunning(null);
      load();
    } catch (e) {
      setNotice({ tone: "error", text: errMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  const renderField = (f) => {
    const v = values[f.name] ?? (f.type === "patients" ? [] : "");
    const set = (val) => setValues({ ...values, [f.name]: val });
    if (f.type === "textarea")
      return <textarea className={inputCls} rows={3} value={v} onChange={(e) => set(e.target.value)} />;
    if (f.type === "select")
      return (
        <select className={inputCls} value={v} onChange={(e) => set(e.target.value)}>
          <option value="">— choose —</option>
          {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      );
    if (f.type === "patient")
      return (
        <select className={inputCls} value={v} onChange={(e) => set(e.target.value)}>
          <option value="">— choose patient —</option>
          {patients.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.email})</option>)}
        </select>
      );
    if (f.type === "patients")
      return (
        <select multiple className={`${inputCls} h-28`} value={v}
                onChange={(e) => set([...e.target.selectedOptions].map((o) => o.value))}>
          {patients.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.email})</option>)}
        </select>
      );
    return (
      <input className={inputCls} value={v}
             type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
             onChange={(e) => set(e.target.value)} />
    );
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-800 mb-1">Agents</h2>
      <p className="text-sm text-slate-500 mb-6">
        Each workflow is owned by a dedicated agent. Trigger one manually here
        — it decides which tools to use and reports back what it did.
      </p>

      {notice && <div className="mb-4"><Notice tone={notice.tone}>{notice.text}</Notice></div>}

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        {agents.map((a) => (
          <Card key={a.key} className="flex flex-col">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center shrink-0">
                <Bot size={17} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-slate-800">{a.name}</h3>
                <p className="text-sm text-slate-500 mt-0.5">{a.description}</p>
                <div className="flex flex-wrap gap-1 mt-2.5">
                  {a.tools.map((t) => <Badge key={t}>{t}</Badge>)}
                </div>
              </div>
            </div>
            <div className="mt-4">
              <Button onClick={() => openRun(a)}>
                <Play size={14} /> Run
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <Card title="Run history">
        {runs.length === 0 ? (
          <Empty>No runs yet.</Empty>
        ) : (
          runs.map((run) => <RunRow key={run.id} run={run} />)
        )}
      </Card>

      {running && (
        <Modal title={`Run ${running.name}`} onClose={() => setRunning(null)}>
          {running.input_fields.map((f) => (
            <Field key={f.name} label={`${f.label}${f.optional ? " (optional)" : ""}`}>
              {renderField(f)}
            </Field>
          ))}
          <Button onClick={trigger} disabled={busy}>
            {busy ? "Agent running — this can take a minute..." : "Start agent"}
          </Button>
        </Modal>
      )}
    </div>
  );
}

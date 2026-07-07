import React, { useCallback, useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import { api, downloadUrl, errMessage } from "../api";
import {
  Badge, Button, Card, Empty, Field, inputCls, Notice,
} from "../components/Ui";

const FORM_CONFIG = {
  financial_acknowledgement: {
    title: "Financial Acknowledgement Form",
    blurb: "Fill in the financial responsibility details — the agent generates the official form PDF and emails it to the patient for signature.",
    fields: [
      { name: "service_description", label: "Service / treatment" },
      { name: "total_charges", label: "Total charges", type: "number" },
      { name: "payment_terms", label: "Payment terms", type: "textarea" },
      { name: "insurance_details", label: "Insurance details", optional: true },
      { name: "effective_date", label: "Effective date", type: "date" },
    ],
  },
  financial_resolution: {
    title: "Financial Resolution Form",
    blurb: "Record the agreed resolution of an outstanding balance — the agent generates the resolution form PDF and emails it to the patient.",
    fields: [
      { name: "original_balance", label: "Original outstanding balance", type: "number" },
      { name: "resolution_type", label: "Resolution type", placeholder: "settlement / payment plan / write-off" },
      { name: "settlement_amount", label: "Agreed amount", type: "number" },
      { name: "payment_schedule", label: "Payment schedule", type: "textarea" },
      { name: "conditions", label: "Conditions", type: "textarea", optional: true },
    ],
  },
};

export default function Forms() {
  const [tab, setTab] = useState("financial_acknowledgement");
  const [patients, setPatients] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [values, setValues] = useState({ patient_id: "" });
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  const load = useCallback(() => {
    api.get("/patients").then((r) => setPatients(r.data)).catch(() => {});
    api.get("/documents").then((r) => setDocuments(r.data)).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const config = FORM_CONFIG[tab];

  const generate = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const payload = { patient_id: values.patient_id };
      for (const f of config.fields) {
        const v = values[f.name];
        if (v !== undefined && v !== "")
          payload[f.name] = f.type === "number" ? Number(v) : v;
      }
      const r = await api.post(`/agents/${tab}/run`, { payload });
      setNotice({
        tone: r.data.status === "completed" ? "ok" : "error",
        text: `${r.data.agent_name}: ${r.data.status}. ${r.data.summary?.slice(0, 400) || ""}`,
      });
      setValues({ patient_id: "" });
      load();
    } catch (e) {
      setNotice({ tone: "error", text: errMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-800 mb-1">Forms & Documents</h2>
      <p className="text-sm text-slate-500 mb-6">
        Fill in the data — the matching form agent generates the PDF and sends it.
      </p>

      <div className="flex gap-2 mb-4">
        {Object.entries(FORM_CONFIG).map(([key, cfg]) => (
          <button key={key} onClick={() => { setTab(key); setNotice(null); }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                    tab === key ? "bg-brand-700 text-white" : "bg-white border border-slate-300 text-slate-600 hover:bg-slate-50"
                  }`}>
            {cfg.title}
          </button>
        ))}
      </div>

      {notice && <div className="mb-4"><Notice tone={notice.tone}>{notice.text}</Notice></div>}

      <div className="grid lg:grid-cols-2 gap-6">
        <Card title={config.title}>
          <p className="text-sm text-slate-500 mb-4">{config.blurb}</p>
          <Field label="Patient">
            <select className={inputCls} value={values.patient_id || ""}
                    onChange={(e) => setValues({ ...values, patient_id: e.target.value })}>
              <option value="">— choose patient —</option>
              {patients.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.email})</option>)}
            </select>
          </Field>
          {config.fields.map((f) => (
            <Field key={f.name} label={`${f.label}${f.optional ? " (optional)" : ""}`}>
              {f.type === "textarea" ? (
                <textarea className={inputCls} rows={3} value={values[f.name] || ""}
                          onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} />
              ) : (
                <input className={inputCls} placeholder={f.placeholder || ""}
                       type={f.type || "text"} value={values[f.name] || ""}
                       onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} />
              )}
            </Field>
          ))}
          <Button onClick={generate} disabled={busy || !values.patient_id}>
            {busy ? "Agent running..." : "Generate & send form"}
          </Button>
        </Card>

        <Card title="Generated documents">
          {documents.length === 0 ? (
            <Empty>No documents yet.</Empty>
          ) : (
            documents.map((d) => (
              <div key={d.id} className="flex items-center gap-3 py-2.5 border-b border-slate-50 last:border-0">
                <FileText size={16} className="text-brand-700 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{d.title}</p>
                  <p className="text-xs text-slate-400">
                    {d.created_at?.slice(0, 19).replace("T", " ")}
                  </p>
                </div>
                <Badge tone={d.kind === "receipt" ? "teal" : "blue"}>{d.kind}</Badge>
                <a href={downloadUrl(d.id)} className="text-brand-700 hover:bg-brand-50 rounded-md p-1.5"
                   title="Download PDF">
                  <Download size={15} />
                </a>
              </div>
            ))
          )}
        </Card>
      </div>
    </div>
  );
}

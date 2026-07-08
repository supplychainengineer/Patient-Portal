import React, { useEffect, useRef, useState } from "react";
import { Save, Upload, Wand2 } from "lucide-react";
import { api, errMessage } from "../api";
import { Button, Card, Field, inputCls, Modal, Notice } from "../components/Ui";

export default function Templates() {
  const [templates, setTemplates] = useState([]);
  const [active, setActive] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);
  const [builder, setBuilder] = useState(null); // {files: File[], instructions}

  const importHtml = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setActive({ ...active, html_body: String(reader.result) });
      setNotice({
        tone: "ok",
        text: `Imported ${file.name} (${Math.round(file.size / 1024)} KB). ` +
              "Review the preview below, then hit Save template. " +
              "Tip: swap dynamic spots (patient name, fees, dates) for {{placeholders}} " +
              "so the agent can personalize each send.",
      });
    };
    reader.readAsText(file);
    event.target.value = "";
  };

  useEffect(() => {
    api.get("/templates").then((r) => {
      setTemplates(r.data);
      setActive(r.data[0] || null);
    }).catch(() => {});
  }, []);

  const buildFromExamples = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const form = new FormData();
      builder.files.forEach((f) => form.append("files", f));
      form.append("instructions", builder.instructions || "");
      const r = await api.post(`/templates/${active.key}/build-from-examples`, form,
                               { timeout: 600000 });
      setActive(r.data);
      setTemplates(templates.map((t) => (t.key === r.data.key ? r.data : t)));
      setBuilder(null);
      setNotice({ tone: "ok",
                  text: "Template built from your examples — review the preview below, tweak if needed, then Save." });
    } catch (e) {
      setNotice({ tone: "error", text: errMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    setNotice(null);
    try {
      await api.put(`/templates/${active.key}`, {
        subject: active.subject,
        html_body: active.html_body,
      });
      setTemplates(templates.map((t) => (t.key === active.key ? active : t)));
      setNotice({ tone: "ok", text: "Template saved. Agents will use it on their next run." });
    } catch (e) {
      setNotice({ tone: "error", text: errMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-800 mb-1">Email Templates</h2>
      <p className="text-sm text-slate-500 mb-6">
        Agents fill the <code className="bg-slate-100 px-1 rounded">{"{{placeholders}}"}</code> automatically.
        Build your onboarding template here — the Onboarding Agent sends it verbatim.
      </p>

      {notice && <div className="mb-4"><Notice tone={notice.tone}>{notice.text}</Notice></div>}

      <div className="grid lg:grid-cols-[220px,1fr] gap-6">
        <div className="space-y-1.5">
          {templates.map((t) => (
            <button key={t.key} onClick={() => { setActive(t); setNotice(null); }}
                    className={`w-full text-left px-4 py-2.5 rounded-lg text-sm transition ${
                      active?.key === t.key
                        ? "bg-brand-700 text-white font-medium"
                        : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
                    }`}>
              {t.name}
            </button>
          ))}
        </div>

        {active && (
          <Card title={active.name}>
            <Field label="Subject">
              <input className={inputCls} value={active.subject}
                     onChange={(e) => setActive({ ...active, subject: e.target.value })} />
            </Field>
            <Field label="HTML body"
                   hint={"Placeholders: {{patient_name}}, {{clinic_name}}, {{clinic_phone}}, {{clinic_email}}, {{amount_paid}}, {{balance_due}}, {{form_name}} — plus for onboarding: " +
                         "{{treatment_plan}}, {{estimated_duration}}, {{total_contract_fee}}, {{down_payment}}, {{remaining_balance}}, {{monthly_amount}}, {{num_payments}}, {{first_due_date}}, {{payment_method}}, {{final_payment}}"}>
              <textarea className={`${inputCls} font-mono text-xs`} rows={14}
                        value={active.html_body}
                        onChange={(e) => setActive({ ...active, html_body: e.target.value })} />
            </Field>
            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                <Button onClick={save} disabled={busy}>
                  <Save size={14} /> {busy ? "Saving..." : "Save template"}
                </Button>
                <Button variant="secondary" onClick={() => fileInput.current?.click()}>
                  <Upload size={14} /> Import HTML file
                </Button>
                <Button variant="secondary"
                        onClick={() => setBuilder({ files: [], instructions: "" })}>
                  <Wand2 size={14} /> Build from examples
                </Button>
                <input ref={fileInput} type="file" accept=".html,.htm,text/html"
                       className="hidden" onChange={importHtml} />
              </div>
              <span className="text-xs text-slate-400">key: {active.key}</span>
            </div>
            <div className="mt-5 border-t border-slate-100 pt-4">
              <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Preview</p>
              <div className="border border-slate-200 rounded-lg p-4 text-sm"
                   dangerouslySetInnerHTML={{ __html: active.html_body }} />
            </div>
          </Card>
        )}
      </div>

      {builder && active && (
        <Modal title={`Build "${active.name}" from examples`} onClose={() => setBuilder(null)}>
          <Notice tone="info">
            Upload examples of this communication — HTML files, screenshots
            (PNG/JPG), PDFs or text. The Template Builder agent studies them,
            reproduces the design and inserts the right placeholders. The
            result lands in the editor for you to review and tweak.
          </Notice>
          <div className="mt-4">
            <Field label="Example files (up to 6)">
              <input type="file" multiple
                     accept=".html,.htm,.txt,.md,.png,.jpg,.jpeg,.gif,.webp,.pdf"
                     className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg
                                file:border-0 file:bg-brand-50 file:px-3 file:py-2
                                file:text-brand-800 file:font-medium hover:file:bg-brand-100"
                     onChange={(e) => setBuilder({ ...builder, files: [...e.target.files] })} />
            </Field>
            {builder.files.length > 0 && (
              <p className="text-xs text-slate-500 -mt-1 mb-3">
                {builder.files.map((f) => f.name).join(", ")}
              </p>
            )}
            <Field label="Instructions (optional)"
                   hint="e.g. 'Use the first file for layout and the PDF for wording' or 'Keep the payment table exactly as shown'">
              <textarea className={inputCls} rows={3} value={builder.instructions}
                        onChange={(e) => setBuilder({ ...builder, instructions: e.target.value })} />
            </Field>
            <Button onClick={buildFromExamples} disabled={busy || builder.files.length === 0}>
              <Wand2 size={14} />
              {busy ? "Agent is studying your examples..." : "Build template"}
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}

import React, { useCallback, useEffect, useState } from "react";
import { FileSignature, Plus, Receipt, RefreshCw, Send, Trash2 } from "lucide-react";
import { api, errMessage } from "../api";
import {
  Badge, Button, Card, Empty, Field, inputCls, Modal, Notice, statusTone,
} from "../components/Ui";

const emptyPatient = { name: "", email: "", phone: "", balance_due: 0, notes: "" };

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [modal, setModal] = useState(null); // 'add' | 'receipt' | 'zoho' | 'contract'
  const [form, setForm] = useState(emptyPatient);
  const [receipt, setReceipt] = useState({ amount_paid: "", payment_method: "", payment_date: "", description: "" });
  const [zoho, setZoho] = useState({ worksheet_name: "", name_column: "Name", email_column: "Email", balance_column: "" });
  const [contract, setContract] = useState({ patient: null, contract_amount: "", notes: "" });
  const [onboardData, setOnboardData] = useState({ patient: null });
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  const load = useCallback(() => {
    api.get("/patients").then((r) => setPatients(r.data)).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const toggle = (id) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const run = async (fn, okMessage) => {
    setBusy(true);
    setNotice(null);
    try {
      const result = await fn();
      setNotice({ tone: "ok", text: okMessage(result) });
      setModal(null);
      load();
    } catch (e) {
      setNotice({ tone: "error", text: errMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  const addPatient = () =>
    run(async () => (await api.post("/patients", { ...form, balance_due: Number(form.balance_due) || 0 })).data,
        (p) => `Added ${p.name}.`);

  const sendReceipts = () =>
    run(async () => {
      const payload = {
        patient_ids: [...selected],
        amount_paid: Number(receipt.amount_paid),
        payment_method: receipt.payment_method,
        payment_date: receipt.payment_date,
        description: receipt.description,
      };
      return (await api.post("/agents/receipt/run", { payload })).data;
    }, (r) => `Receipt Agent finished (${r.status}). ${r.summary?.slice(0, 200) || ""}`);

  const syncZoho = () =>
    run(async () => (await api.post("/patients/sync-zoho", zoho)).data,
        (r) => `Zoho sync: ${r.created} created, ${r.updated} updated, ${r.skipped} skipped.`);

  const onboard = () =>
    run(async () => {
      const { patient, ...fields } = onboardData;
      const body = {};
      for (const [k, v] of Object.entries(fields)) {
        if (v === "" || v === undefined) continue;
        body[k] = ["total_contract_fee", "down_payment", "monthly_amount", "num_payments"]
          .includes(k) ? Number(v) : v;
      }
      return (await api.post(`/patients/${patient.id}/onboard`, body)).data;
    }, (r) => `Onboarding Agent finished (${r.status}). ${r.summary?.slice(0, 200) || ""}`);

  const contractSigned = () =>
    run(async () => (await api.post(`/patients/${contract.patient.id}/contract-signed`, {
      contract_amount: contract.contract_amount ? Number(contract.contract_amount) : null,
      notes: contract.notes,
    })).data,
        (r) => `Contract receipt sent (${r.status}). ${r.summary?.slice(0, 200) || ""}`);

  const remove = async (p) => {
    if (!window.confirm(`Delete patient ${p.name}?`)) return;
    await api.delete(`/patients/${p.id}`);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-1">Patients</h2>
          <p className="text-sm text-slate-500">
            Select patients, then send receipts with one click. Onboarding and
            contract actions run the Onboarding Agent.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setModal("zoho")}>
            <RefreshCw size={15} /> Sync from Zoho
          </Button>
          <Button onClick={() => { setForm(emptyPatient); setModal("add"); }}>
            <Plus size={15} /> Add patient
          </Button>
        </div>
      </div>

      {notice && <div className="mb-4"><Notice tone={notice.tone}>{notice.text}</Notice></div>}

      {selected.size > 0 && (
        <div className="mb-4 flex items-center gap-3 bg-brand-50 border border-brand-100 rounded-lg px-4 py-2.5">
          <span className="text-sm text-brand-900 font-medium">{selected.size} selected</span>
          <Button onClick={() => setModal("receipt")}>
            <Receipt size={15} /> Send receipts
          </Button>
        </div>
      )}

      <Card>
        {patients.length === 0 ? (
          <Empty>No patients yet. Add one or sync from your Zoho sheet.</Empty>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 uppercase border-b border-slate-100">
                <th className="py-2 pr-2 w-8"></th>
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4 text-right">Balance due</th>
                <th className="py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50/60">
                  <td className="py-2.5 pr-2">
                    <input type="checkbox" checked={selected.has(p.id)}
                           onChange={() => toggle(p.id)}
                           className="accent-brand-700" />
                  </td>
                  <td className="py-2.5 pr-4 font-medium text-slate-800">{p.name}</td>
                  <td className="py-2.5 pr-4 text-slate-600">{p.email}</td>
                  <td className="py-2.5 pr-4"><Badge tone={statusTone(p.status)}>{p.status}</Badge></td>
                  <td className={`py-2.5 pr-4 text-right font-medium ${p.balance_due > 0 ? "text-amber-700" : "text-slate-500"}`}>
                    {Number(p.balance_due || 0).toLocaleString()}
                  </td>
                  <td className="py-2.5 text-right whitespace-nowrap">
                    <button title="Send onboarding welcome email" disabled={busy}
                            onClick={() => { setOnboardData({ patient: p }); setModal("onboard"); }}
                            className="text-brand-700 hover:bg-brand-50 rounded-md p-1.5">
                      <Send size={15} />
                    </button>
                    <button title="Contract signed → send receipt" disabled={busy}
                            onClick={() => { setContract({ patient: p, contract_amount: "", notes: "" }); setModal("contract"); }}
                            className="text-brand-700 hover:bg-brand-50 rounded-md p-1.5">
                      <FileSignature size={15} />
                    </button>
                    <button title="Delete" onClick={() => remove(p)}
                            className="text-red-500 hover:bg-red-50 rounded-md p-1.5">
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {modal === "add" && (
        <Modal title="Add patient" onClose={() => setModal(null)}>
          <Field label="Full name">
            <input className={inputCls} value={form.name}
                   onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="Email">
            <input className={inputCls} type="email" value={form.email}
                   onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
          <Field label="Phone">
            <input className={inputCls} value={form.phone}
                   onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </Field>
          <Field label="Balance due">
            <input className={inputCls} type="number" value={form.balance_due}
                   onChange={(e) => setForm({ ...form, balance_due: e.target.value })} />
          </Field>
          <Button onClick={addPatient} disabled={busy || !form.name || !form.email}>
            {busy ? "Saving..." : "Save patient"}
          </Button>
        </Modal>
      )}

      {modal === "receipt" && (
        <Modal title={`Send receipts to ${selected.size} patient(s)`} onClose={() => setModal(null)}>
          <Notice tone="info">
            The Receipt Agent will generate a PDF receipt per patient and email
            it using your receipt template.
          </Notice>
          <div className="mt-4">
            <Field label="Amount paid (per patient)">
              <input className={inputCls} type="number" value={receipt.amount_paid}
                     onChange={(e) => setReceipt({ ...receipt, amount_paid: e.target.value })} />
            </Field>
            <Field label="Payment description">
              <input className={inputCls} placeholder="e.g. Consultation fee"
                     value={receipt.description}
                     onChange={(e) => setReceipt({ ...receipt, description: e.target.value })} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Payment method">
                <input className={inputCls} placeholder="card / cash / transfer"
                       value={receipt.payment_method}
                       onChange={(e) => setReceipt({ ...receipt, payment_method: e.target.value })} />
              </Field>
              <Field label="Payment date">
                <input className={inputCls} type="date" value={receipt.payment_date}
                       onChange={(e) => setReceipt({ ...receipt, payment_date: e.target.value })} />
              </Field>
            </div>
            <Button onClick={sendReceipts} disabled={busy || !receipt.amount_paid}>
              {busy ? "Agent running..." : "Run Receipt Agent"}
            </Button>
          </div>
        </Modal>
      )}

      {modal === "zoho" && (
        <Modal title="Sync patients from Zoho sheet" onClose={() => setModal(null)}>
          <Notice tone="info">
            Imports rows from a worksheet of your assigned Zoho sheet, matching
            existing patients by email. Configure the connection in Settings first.
          </Notice>
          <div className="mt-4">
            <Field label="Worksheet name">
              <input className={inputCls} placeholder="e.g. Patients"
                     value={zoho.worksheet_name}
                     onChange={(e) => setZoho({ ...zoho, worksheet_name: e.target.value })} />
            </Field>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Name column">
                <input className={inputCls} value={zoho.name_column}
                       onChange={(e) => setZoho({ ...zoho, name_column: e.target.value })} />
              </Field>
              <Field label="Email column">
                <input className={inputCls} value={zoho.email_column}
                       onChange={(e) => setZoho({ ...zoho, email_column: e.target.value })} />
              </Field>
              <Field label="Balance column" hint="optional">
                <input className={inputCls} value={zoho.balance_column}
                       onChange={(e) => setZoho({ ...zoho, balance_column: e.target.value })} />
              </Field>
            </div>
            <Button onClick={syncZoho} disabled={busy || !zoho.worksheet_name}>
              {busy ? "Syncing..." : "Sync now"}
            </Button>
          </div>
        </Modal>
      )}

      {modal === "onboard" && onboardData.patient && (
        <Modal title={`Onboarding welcome — ${onboardData.patient.name}`} onClose={() => setModal(null)} wide>
          <Notice tone="info">
            The Onboarding Agent sends your welcome template and fills in the
            treatment &amp; payment details below. Anything left blank appears
            as “—” in the email — exactly like your template's empty states.
          </Notice>
          <div className="mt-4 grid grid-cols-2 gap-x-4">
            <Field label="Treatment plan">
              <input className={inputCls} placeholder="e.g. Invisalign Comprehensive"
                     value={onboardData.treatment_plan || ""}
                     onChange={(e) => setOnboardData({ ...onboardData, treatment_plan: e.target.value })} />
            </Field>
            <Field label="Estimated duration">
              <input className={inputCls} placeholder="e.g. 18 months"
                     value={onboardData.estimated_duration || ""}
                     onChange={(e) => setOnboardData({ ...onboardData, estimated_duration: e.target.value })} />
            </Field>
            <Field label="Total contract fee">
              <input className={inputCls} type="number" value={onboardData.total_contract_fee || ""}
                     onChange={(e) => setOnboardData({ ...onboardData, total_contract_fee: e.target.value })} />
            </Field>
            <Field label="Down payment received">
              <input className={inputCls} type="number" value={onboardData.down_payment || ""}
                     onChange={(e) => setOnboardData({ ...onboardData, down_payment: e.target.value })} />
            </Field>
            <Field label="Monthly payment">
              <input className={inputCls} type="number" value={onboardData.monthly_amount || ""}
                     onChange={(e) => setOnboardData({ ...onboardData, monthly_amount: e.target.value })} />
            </Field>
            <Field label="Number of monthly payments">
              <input className={inputCls} type="number" value={onboardData.num_payments || ""}
                     onChange={(e) => setOnboardData({ ...onboardData, num_payments: e.target.value })} />
            </Field>
            <Field label="First payment due">
              <input className={inputCls} type="date" value={onboardData.first_due_date || ""}
                     onChange={(e) => setOnboardData({ ...onboardData, first_due_date: e.target.value })} />
            </Field>
            <Field label="Payment method">
              <input className={inputCls} placeholder="e.g. Card autopay"
                     value={onboardData.payment_method || ""}
                     onChange={(e) => setOnboardData({ ...onboardData, payment_method: e.target.value })} />
            </Field>
          </div>
          <Button onClick={onboard} disabled={busy}>
            {busy ? "Agent running..." : "Send welcome email"}
          </Button>
        </Modal>
      )}

      {modal === "contract" && contract.patient && (
        <Modal title={`Contract signed — ${contract.patient.name}`} onClose={() => setModal(null)}>
          <Notice tone="info">
            The Onboarding Agent will generate a receipt for the contract payment
            and email it to the patient.
          </Notice>
          <div className="mt-4">
            <Field label="Contract payment amount" hint="Leave empty for a confirmation receipt with no payment">
              <input className={inputCls} type="number" value={contract.contract_amount}
                     onChange={(e) => setContract({ ...contract, contract_amount: e.target.value })} />
            </Field>
            <Field label="Notes">
              <input className={inputCls} value={contract.notes}
                     onChange={(e) => setContract({ ...contract, notes: e.target.value })} />
            </Field>
            <Button onClick={contractSigned} disabled={busy}>
              {busy ? "Agent running..." : "Send contract receipt"}
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}

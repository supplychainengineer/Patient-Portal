import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Badge, Card, Empty, Modal, Notice, statusTone } from "../components/Ui";

export default function Outbox() {
  const [emails, setEmails] = useState([]);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api.get("/emails").then((r) => setEmails(r.data)).catch(() => {});
  }, []);

  const dryCount = emails.filter((e) => e.status === "dry_run").length;

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-800 mb-1">Outbox</h2>
      <p className="text-sm text-slate-500 mb-6">
        Every email the agents produce, sent or captured.
      </p>

      {dryCount > 0 && (
        <div className="mb-4">
          <Notice tone="warn">
            {dryCount} email(s) were captured in dry-run mode and NOT delivered.
            Connect SMTP and set <code>EMAIL_DRY_RUN=false</code> to send for real (see Settings).
          </Notice>
        </div>
      )}

      <Card>
        {emails.length === 0 ? (
          <Empty>No emails yet — run an agent.</Empty>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 uppercase border-b border-slate-100">
                <th className="py-2 pr-4">To</th>
                <th className="py-2 pr-4">Subject</th>
                <th className="py-2 pr-4">Agent</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {emails.map((e) => (
                <tr key={e.id} onClick={() => setOpen(e)}
                    className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer">
                  <td className="py-2.5 pr-4 text-slate-700">{e.to}</td>
                  <td className="py-2.5 pr-4 font-medium text-slate-800 max-w-xs truncate">{e.subject}</td>
                  <td className="py-2.5 pr-4 text-slate-500">{e.agent_key || "—"}</td>
                  <td className="py-2.5 pr-4"><Badge tone={statusTone(e.status)}>{e.status}</Badge></td>
                  <td className="py-2.5 text-slate-400 text-xs">
                    {e.created_at?.slice(0, 19).replace("T", " ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {open && (
        <Modal title={open.subject} onClose={() => setOpen(null)} wide>
          <p className="text-sm text-slate-500 mb-1">To: {open.to}</p>
          {open.attachments?.length > 0 && (
            <p className="text-sm text-slate-500 mb-1">Attachments: {open.attachments.join(", ")}</p>
          )}
          {open.detail && <p className="text-xs text-amber-700 mb-3">{open.detail}</p>}
          <div className="border border-slate-200 rounded-lg p-4 text-sm"
               dangerouslySetInnerHTML={{ __html: open.html_body }} />
        </Modal>
      )}
    </div>
  );
}

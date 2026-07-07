import React, { useEffect, useState } from "react";
import { CheckCircle2, PlugZap, XCircle } from "lucide-react";
import { api } from "../api";
import { Button, Card, Notice } from "../components/Ui";

const GUIDES = {
  mongodb: {
    name: "MongoDB",
    steps: ["Set MONGO_URL and DB_NAME in backend/.env", "Restart the backend"],
  },
  anthropic: {
    name: "Anthropic (agent brain)",
    steps: [
      "Create an API key at platform.claude.com",
      "Set ANTHROPIC_API_KEY in backend/.env",
      "Restart the backend — all 6 agents come online",
    ],
  },
  zoho_sheets: {
    name: "Zoho Sheets",
    steps: [
      "Create a Self Client at api-console.zoho.com",
      "Generate a grant code with scope ZohoSheet.dataAPI.READ",
      "Exchange it for a refresh token (curl command in the README)",
      "Set ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN and ZOHO_SHEET_RESOURCE_ID in backend/.env",
    ],
  },
  email: {
    name: "Email (SMTP)",
    steps: [
      "Set SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD in backend/.env (Zoho Mail: smtp.zoho.com:587)",
      "Keep EMAIL_DRY_RUN=true while testing — emails land in the Outbox",
      "Set EMAIL_DRY_RUN=false to deliver for real",
    ],
  },
};

export default function Settings() {
  const [status, setStatus] = useState(null);
  const [zohoTest, setZohoTest] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/settings/connections")
      .then((r) => setStatus(r.data))
      .catch(() => setError("Backend unreachable — start it with: uvicorn server:app --port 8001"));
  }, []);

  const testZoho = async () => {
    setZohoTest({ loading: true });
    try {
      const r = await api.post("/settings/test-zoho");
      setZohoTest(r.data);
    } catch (e) {
      setZohoTest({ ok: false, error: String(e) });
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-800 mb-1">Settings & Connections</h2>
      <p className="text-sm text-slate-500 mb-6">
        The portal is fully built — these are the only places where you connect
        your own accounts. Everything is configured in <code className="bg-slate-100 px-1 rounded">backend/.env</code>.
      </p>

      {error && <Notice tone="error">{error}</Notice>}

      {status && (
        <div className="grid md:grid-cols-2 gap-4">
          {Object.entries(GUIDES).map(([key, guide]) => {
            const s = status[key] || {};
            return (
              <Card key={key}>
                <div className="flex items-start gap-3">
                  {s.configured ? (
                    <CheckCircle2 className="text-emerald-500 shrink-0 mt-0.5" size={20} />
                  ) : (
                    <XCircle className="text-amber-500 shrink-0 mt-0.5" size={20} />
                  )}
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-800">{guide.name}</h3>
                    <p className="text-sm text-slate-500 mt-0.5">{s.detail}</p>
                    {!s.configured && (
                      <ol className="mt-3 space-y-1.5 text-sm text-slate-600 list-decimal list-inside">
                        {guide.steps.map((step, i) => <li key={i}>{step}</li>)}
                      </ol>
                    )}
                    {key === "email" && s.configured && s.dry_run && (
                      <p className="text-xs text-amber-700 mt-2">
                        SMTP is set but dry-run is still ON — flip EMAIL_DRY_RUN=false when ready.
                      </p>
                    )}
                    {key === "zoho_sheets" && s.configured && (
                      <div className="mt-3">
                        <Button variant="secondary" onClick={testZoho}>
                          <PlugZap size={14} /> Test connection
                        </Button>
                        {zohoTest && !zohoTest.loading && (
                          <p className={`text-xs mt-2 ${zohoTest.ok ? "text-emerald-600" : "text-red-600"}`}>
                            {zohoTest.ok
                              ? `Connected. Worksheets: ${(zohoTest.worksheets || []).join(", ")}`
                              : zohoTest.error}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

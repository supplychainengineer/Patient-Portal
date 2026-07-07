# Patient Portal — Agentic Automation

A patient portal where six Claude-powered agents do the busywork: receipts,
Zoho-sheet-driven emails, dues follow-ups, financial forms and onboarding.
The system is fully built — the only things left for you are the **connections**
(your Anthropic key, Zoho OAuth, SMTP), all listed on the Settings page.

## The agent team

| Agent | What it does | Triggered from |
|---|---|---|
| **Receipt Agent** | Generates a payment receipt PDF per selected patient and emails it (receipt attached) | Patients page → select → "Send receipts", or Agents page |
| **Zoho Sheet Email Agent** | Reads your assigned Zoho sheet and emails people using row data as context, following your instruction | Agents page |
| **Dues Follow-up Agent** | Finds pending dues (portal balances and/or a Zoho worksheet) and sends polite reminders | Agents page |
| **Financial Acknowledgement Form Agent** | Turns filled-in data into the official acknowledgement form PDF and emails it for signature | Forms page |
| **Financial Resolution Form Agent** | Same for resolution of outstanding balances (settlements, payment plans) | Forms page |
| **Onboarding Agent** | Sends your onboarding email template to new patients; when a contract is signed, generates and emails a receipt | Patients page row actions |

Every run is logged step-by-step (each tool call and result) — expand any run
on the Dashboard or Agents page to audit exactly what an agent did. All email
is captured in the **Outbox** and, until you flip `EMAIL_DRY_RUN=false`,
nothing is actually delivered — safe by default.

## Architecture

```
frontend/  React + Tailwind UI (Dashboard, Patients, Agents, Forms, Templates, Outbox, Settings)
backend/   FastAPI
  agents/        the agentic core
    base.py        Claude tool-use loop with per-step run logging
    tools.py       the tool belt (patients, Zoho, email, PDFs, templates)
    registry.py    the six agent definitions (system prompt + tools each)
  integrations/  zoho.py (Sheets API, OAuth refresh) · mailer.py (SMTP + dry-run outbox)
  services/      pdf.py (receipts & forms, reportlab) · templates.py (editable email templates)
  routers/       REST API: /api/patients, /api/agents, /api/templates, /api/emails,
                 /api/documents, /api/dashboard, /api/settings
```

Data lives in MongoDB (`patients`, `agent_runs`, `emails`, `documents`,
`templates`); generated PDFs in `backend/storage/`.

## Run it

### Backend
```bash
cd backend
cp .env.example .env        # fill in what you have — it runs fine before connecting anything
pip install -r requirements.txt
uvicorn server:app --reload --port 8001
```

### Frontend
```bash
cd frontend
cp .env.example .env        # REACT_APP_BACKEND_URL=http://localhost:8001
npm install                 # or yarn
npm start
```

## Connect your accounts (the only manual part)

All of this happens in `backend/.env` — the **Settings page** shows live
status for each connection.

1. **MongoDB** — `MONGO_URL`, `DB_NAME`.
2. **Anthropic** (the agents' brain) — create a key at
   [platform.claude.com](https://platform.claude.com) and set `ANTHROPIC_API_KEY`.
3. **Zoho Sheets** —
   1. Create a *Self Client* at [api-console.zoho.com](https://api-console.zoho.com).
   2. Generate a grant code with scope `ZohoSheet.dataAPI.READ`.
   3. Exchange it for a refresh token:
      ```bash
      curl -X POST "https://accounts.zoho.com/oauth/v2/token" \
        -d "code=GRANT_CODE" -d "client_id=CLIENT_ID" \
        -d "client_secret=CLIENT_SECRET" -d "grant_type=authorization_code"
      ```
   4. Set `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN` and
      `ZOHO_SHEET_RESOURCE_ID` (the id in your sheet's URL:
      `https://sheet.zoho.com/sheet/open/<resource_id>`).
   5. Non-US Zoho DC? Also change `ZOHO_ACCOUNTS_BASE` / `ZOHO_SHEET_API_BASE`
      (e.g. `.zoho.in`, `.zoho.eu`).
4. **Email (SMTP)** — works with Zoho Mail (`smtp.zoho.com:587`), Gmail, SES…
   Set `SMTP_HOST/PORT/USER/PASSWORD`. Keep `EMAIL_DRY_RUN=true` while testing
   (emails land in the Outbox), then flip to `false` to send for real.

## Build your onboarding template

Templates page → *New Patient Onboarding*. The Onboarding Agent sends it
verbatim, filling `{{patient_name}}`, `{{clinic_name}}`, `{{clinic_phone}}`,
`{{clinic_email}}`. The other templates (receipt, dues follow-up, form
delivery) are editable the same way.

## API quick reference

- `POST /api/agents/{key}/run` — trigger any agent (`receipt`, `zoho_context`,
  `dues_followup`, `financial_acknowledgement`, `financial_resolution`, `onboarding`)
- `GET /api/agents/runs` — full audit trail
- `POST /api/patients/{id}/onboard` · `POST /api/patients/{id}/contract-signed`
- `POST /api/patients/sync-zoho` — import patients from a Zoho worksheet
- `GET /api/settings/connections` — connection health

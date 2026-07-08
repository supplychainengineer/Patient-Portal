"""The tool belt agents work with. Each tool is a plain function plus a JSON
schema; the agent loop in base.py executes them and feeds results back to
Claude. Run-scoped context (run_id, agent_key) is injected by the loop."""
import json
from datetime import datetime, timezone

import config
from database import db
from integrations import mailer, zoho
from services import pdf, templates


def _tool(name, description, properties, required, fn):
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
        "fn": fn,
    }


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

def _list_patients(ctx, status: str = None):
    query = {"status": status} if status else {}
    docs = list(db.patients.find(query, {"_id": 0}).limit(500))
    return {"count": len(docs), "patients": docs}


def _get_patient(ctx, patient_id: str):
    doc = db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not doc:
        return {"error": f"No patient found with id {patient_id}"}
    return doc


def _update_patient(ctx, patient_id: str, fields: dict):
    allowed = {"status", "balance_due", "onboarded_at", "contract_signed_at", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return {"error": f"No updatable fields provided. Allowed: {sorted(allowed)}"}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = db.patients.update_one({"id": patient_id}, {"$set": updates})
    return {"updated": result.modified_count == 1, "fields": updates}


# ---------------------------------------------------------------------------
# Zoho Sheets
# ---------------------------------------------------------------------------

def _list_worksheets(ctx):
    try:
        return {"worksheets": zoho.list_worksheets()}
    except zoho.ZohoNotConnectedError as exc:
        return {"error": str(exc)}


def _fetch_zoho_sheet(ctx, worksheet_name: str, count: int = 200):
    try:
        records = zoho.fetch_records(worksheet_name, count=count)
        return {"worksheet": worksheet_name, "row_count": len(records), "rows": records}
    except zoho.ZohoNotConnectedError as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Templates & email
# ---------------------------------------------------------------------------

def _get_email_template(ctx, key: str):
    tpl = templates.get_template(key)
    if not tpl:
        available = [t["key"] for t in db.templates.find({}, {"key": 1})]
        return {"error": f"Template '{key}' not found. Available: {available}"}
    return tpl


def _send_email(ctx, to_email: str, subject: str, html_body: str,
                document_ids: list = None, patient_id: str = None):
    attachment_paths = []
    for doc_id in document_ids or []:
        doc = db.documents.find_one({"id": doc_id})
        if not doc:
            return {"error": f"Document {doc_id} not found — generate it first."}
        attachment_paths.append(doc["path"])
    return mailer.send_email(
        to_email, subject, html_body, attachment_paths,
        agent_key=ctx.get("agent_key"), run_id=ctx.get("run_id"), patient_id=patient_id,
    )


# ---------------------------------------------------------------------------
# Documents (receipts and forms)
# ---------------------------------------------------------------------------

def _generate_receipt(ctx, patient_name: str, amount_paid: float, items: list = None,
                      payment_method: str = "", payment_date: str = "",
                      balance_due: float = 0.0, notes: str = "", patient_id: str = None,
                      extra: dict = None):
    doc = pdf.generate_receipt(
        patient_name=patient_name, items=items or [], amount_paid=amount_paid,
        payment_method=payment_method, payment_date=payment_date,
        balance_due=balance_due, notes=notes, patient_id=patient_id,
        run_id=ctx.get("run_id"), extra=extra or {},
    )
    return {"document_id": doc["id"], "receipt_no": doc["meta"]["receipt_no"],
            "filename": doc["filename"]}


def _generate_form(ctx, form_type: str, patient_name: str, fields: dict,
                   patient_id: str = None):
    try:
        doc = pdf.generate_form(form_type, patient_name, fields,
                                patient_id=patient_id, run_id=ctx.get("run_id"))
    except ValueError as exc:
        return {"error": str(exc)}
    return {"document_id": doc["id"], "form_no": doc["meta"]["form_no"],
            "filename": doc["filename"]}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

LIST_PATIENTS = _tool(
    "list_patients",
    "List patients in the portal database. Optionally filter by status "
    "(new, active, onboarded, inactive).",
    {"status": {"type": "string", "description": "Optional status filter"}},
    [], _list_patients)

GET_PATIENT = _tool(
    "get_patient",
    "Fetch a single patient's full record (name, email, balance_due, status, ...) by id.",
    {"patient_id": {"type": "string"}},
    ["patient_id"], _get_patient)

UPDATE_PATIENT = _tool(
    "update_patient",
    "Update a patient record. Use after completing an action, e.g. set status "
    "to 'onboarded' after a welcome email, adjust balance_due after a payment.",
    {"patient_id": {"type": "string"},
     "fields": {"type": "object",
                "description": "Fields to set: status, balance_due, onboarded_at, "
                               "contract_signed_at, notes"}},
    ["patient_id", "fields"], _update_patient)

LIST_WORKSHEETS = _tool(
    "list_zoho_worksheets",
    "List the worksheet (tab) names available in the connected Zoho sheet.",
    {}, [], _list_worksheets)

FETCH_ZOHO_SHEET = _tool(
    "fetch_zoho_sheet",
    "Fetch rows from a worksheet in the assigned Zoho sheet. Returns each row "
    "as a JSON object keyed by the sheet's column headers.",
    {"worksheet_name": {"type": "string"},
     "count": {"type": "integer", "description": "Max rows to fetch (default 200)"}},
    ["worksheet_name"], _fetch_zoho_sheet)

GET_EMAIL_TEMPLATE = _tool(
    "get_email_template",
    "Fetch an email template by key (onboarding, receipt_email, dues_followup, "
    "form_delivery). Returns subject and html_body with {{placeholder}} variables "
    "for you to fill in before sending.",
    {"key": {"type": "string"}},
    ["key"], _get_email_template)

SEND_EMAIL = _tool(
    "send_email",
    "Send an HTML email, optionally attaching previously generated documents "
    "(receipts/forms) by document_id. In dry-run mode the email is captured in "
    "the Outbox instead of being delivered — report the returned status honestly.",
    {"to_email": {"type": "string"},
     "subject": {"type": "string"},
     "html_body": {"type": "string"},
     "document_ids": {"type": "array", "items": {"type": "string"},
                      "description": "Optional document ids to attach as PDFs"},
     "patient_id": {"type": "string", "description": "Optional patient id for the log"}},
    ["to_email", "subject", "html_body"], _send_email)

GENERATE_RECEIPT = _tool(
    "generate_receipt_pdf",
    "Generate a payment receipt PDF for a patient using the practice's receipt "
    "document template (FSA/HSA receipt). Returns a document_id that can be "
    "attached to an email with send_email. Pass every detail you know — "
    "missing values render as an em dash.",
    {"patient_name": {"type": "string"},
     "amount_paid": {"type": "number", "description": "Total amount paid"},
     "items": {"type": "array", "items": {"type": "object"},
               "description": "Payment history rows: [{description, date, amount}] "
                              "— e.g. {description: 'Orthodontic Treatment', "
                              "date: '01/20/2026', amount: 723.00}"},
     "payment_method": {"type": "string"},
     "payment_date": {"type": "string"},
     "balance_due": {"type": "number"},
     "notes": {"type": "string"},
     "patient_id": {"type": "string"},
     "extra": {"type": "object",
               "description": "Receipt-template fields when known: "
                              "service_description, contract_date, appliance_placed, "
                              "responsible_party, patient_address, payment_type "
                              "('Partial' or 'Full')"}},
    ["patient_name", "amount_paid"], _generate_receipt)

GENERATE_FORM = _tool(
    "generate_form_pdf",
    "Generate a financial form PDF. form_type is 'financial_acknowledgement' or "
    "'financial_resolution'. fields is a flat object of the form's data — pass "
    "the input field names verbatim as keys (e.g. service_description, "
    "total_charges, payment_terms) so they map onto the practice's form "
    "template placeholders. Format money values with $ and separators. "
    "Returns a document_id for emailing.",
    {"form_type": {"type": "string",
                   "enum": ["financial_acknowledgement", "financial_resolution"]},
     "patient_name": {"type": "string"},
     "fields": {"type": "object"},
     "patient_id": {"type": "string"}},
    ["form_type", "patient_name", "fields"], _generate_form)


def clinic_context() -> str:
    """Shared practice facts injected into every agent's system prompt."""
    return (f"Practice details — name: {config.CLINIC_NAME}; address: {config.CLINIC_ADDRESS}; "
            f"phone: {config.CLINIC_PHONE}; email: {config.CLINIC_EMAIL}. "
            f"Email mode: {'DRY RUN (emails are captured in the Outbox, not delivered)' if config.EMAIL_DRY_RUN else 'LIVE'}.")


def serialize(tool: dict) -> dict:
    return {k: tool[k] for k in ("name", "description", "input_schema")}

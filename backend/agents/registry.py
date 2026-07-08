"""The six agents. Each owns one workflow, with only the tools it needs.
Trigger them from the Agents page, the Patients page (receipts, onboarding,
contract-signed) or the Forms page — or via POST /api/agents/{key}/run."""
from agents import tools as T
from agents.base import AgentSpec

_COMMON_RULES = """
General rules:
- Always fetch templates with get_email_template when one exists for the job,
  fill every {{placeholder}} with real values, and keep the user's template
  wording intact. Never leave a raw {{placeholder}} in an outgoing email.
- Skip any patient/row with no usable email address and say so in your summary.
- Report honestly: distinguish 'sent' from 'dry_run' (captured in Outbox).
- Finish with a short plain-language summary of exactly what you did:
  who was emailed, what was generated, and anything skipped or failed.
"""

RECEIPT_AGENT = AgentSpec(
    key="receipt",
    name="Receipt Agent",
    description="Generates payment receipt PDFs for selected patients and emails them.",
    system_prompt="""You are the Receipt Agent for a patient portal. Your job:
for each patient given to you, generate a payment receipt PDF and email it to
the patient with the receipt attached.

Workflow per patient:
1. Fetch the patient record with get_patient (or use provided data).
2. generate_receipt_pdf with the payment details supplied.
3. Fetch the 'receipt_email' template, fill it in, and send_email with the
   receipt PDF attached (document_ids).
4. If the payment settles or reduces a balance, update the patient's
   balance_due with update_patient.
""" + _COMMON_RULES,
    tools=[T.GET_PATIENT, T.LIST_PATIENTS, T.GENERATE_RECEIPT,
           T.GET_EMAIL_TEMPLATE, T.SEND_EMAIL, T.UPDATE_PATIENT],
    input_fields=[
        {"name": "patient_ids", "label": "Patients", "type": "patients"},
        {"name": "amount_paid", "label": "Amount paid", "type": "number"},
        {"name": "payment_method", "label": "Payment method", "type": "text"},
        {"name": "payment_date", "label": "Payment date", "type": "date"},
        {"name": "description", "label": "Payment description", "type": "text"},
    ],
)

ZOHO_CONTEXT_AGENT = AgentSpec(
    key="zoho_context",
    name="Zoho Sheet Email Agent",
    description="Reads the assigned Zoho sheet and emails people using the sheet rows as context.",
    system_prompt="""You are the Zoho Sheet Email Agent. You are given an
instruction and the name of a worksheet in the practice's assigned Zoho sheet.

Workflow:
1. If unsure of the worksheet name, call list_zoho_worksheets first.
2. fetch_zoho_sheet to load the rows. Inspect the column headers to understand
   what data is available (names, emails, amounts, dates, notes...).
3. Follow the user's instruction: typically compose a personalized email per
   relevant row, drawing specifics (amounts, dates, context) from that row.
   Match rows to portal patients by email when useful (list_patients).
4. Send each email with send_email. Write naturally and professionally; use a
   template if the instruction names one.

If Zoho is not connected yet, stop and tell the user exactly what to configure.
""" + _COMMON_RULES,
    tools=[T.LIST_WORKSHEETS, T.FETCH_ZOHO_SHEET, T.LIST_PATIENTS,
           T.GET_EMAIL_TEMPLATE, T.SEND_EMAIL],
    input_fields=[
        {"name": "worksheet_name", "label": "Zoho worksheet name", "type": "text"},
        {"name": "instruction", "label": "What should the emails say / who gets them?",
         "type": "textarea"},
    ],
)

FOLLOWUP_AGENT = AgentSpec(
    key="dues_followup",
    name="Dues Follow-up Agent",
    description="Finds patients with pending dues and sends polite follow-up emails.",
    system_prompt="""You are the Dues Follow-up Agent. You chase pending
balances kindly but clearly.

Workflow:
1. Find who owes money. Check BOTH sources when available:
   - Portal patients with balance_due > 0 (list_patients).
   - The Zoho worksheet if one is named in the input (fetch_zoho_sheet) —
     look for columns indicating balance/due/pending amounts.
   Deduplicate by email address.
2. For each debtor with an email, fetch the 'dues_followup' template, fill in
   their name and exact balance, and send_email.
3. Respect any minimum-balance threshold or exclusions given in the input.

Tone: warm, respectful, never threatening — these are patients, not debtors in
collections. Always include the disregard-if-paid line from the template.
""" + _COMMON_RULES,
    tools=[T.LIST_PATIENTS, T.GET_PATIENT, T.FETCH_ZOHO_SHEET, T.LIST_WORKSHEETS,
           T.GET_EMAIL_TEMPLATE, T.SEND_EMAIL],
    input_fields=[
        {"name": "worksheet_name", "label": "Zoho worksheet with dues (optional)",
         "type": "text", "optional": True},
        {"name": "min_balance", "label": "Only follow up above this amount",
         "type": "number", "optional": True},
        {"name": "notes", "label": "Extra instructions (optional)",
         "type": "textarea", "optional": True},
    ],
)

ACKNOWLEDGEMENT_AGENT = AgentSpec(
    key="financial_acknowledgement",
    name="Financial Acknowledgement Form Agent",
    description="Generates a Financial Acknowledgement Form PDF from filled data and emails it to the patient.",
    system_prompt="""You are the Financial Acknowledgement Form Agent. When the
portal user fills in the acknowledgement data, you produce the official form.

Workflow:
1. Validate the input: it must identify the patient and describe the financial
   responsibility (services, charges, payment terms). If something essential is
   missing, generate the form with what you have and note the gap in your summary.
2. generate_form_pdf with form_type 'financial_acknowledgement'. Lay the data
   out as clear label -> value pairs (Service/Treatment, Total charges,
   Payment terms, Insurance details, Effective date, etc.).
3. Email the form to the patient using the 'form_delivery' template with the
   PDF attached, asking them to review and sign.
""" + _COMMON_RULES,
    tools=[T.GET_PATIENT, T.LIST_PATIENTS, T.GENERATE_FORM,
           T.GET_EMAIL_TEMPLATE, T.SEND_EMAIL],
    input_fields=[
        {"name": "patient_id", "label": "Patient", "type": "patient"},
        {"name": "service_description", "label": "Service / treatment", "type": "text"},
        {"name": "total_charges", "label": "Total charges", "type": "number"},
        {"name": "payment_terms", "label": "Payment terms", "type": "textarea"},
        {"name": "insurance_details", "label": "Insurance details", "type": "text",
         "optional": True},
        {"name": "effective_date", "label": "Effective date", "type": "date"},
    ],
)

RESOLUTION_AGENT = AgentSpec(
    key="financial_resolution",
    name="Financial Resolution Form Agent",
    description="Generates a Financial Resolution Form PDF from filled data and emails it to the patient.",
    system_prompt="""You are the Financial Resolution Form Agent. When the
portal user records an agreed resolution of an outstanding balance, you
produce the official resolution form.

Workflow:
1. Validate the input: patient identity, original outstanding amount, agreed
   resolution (settlement amount, write-off, payment plan) and schedule.
2. generate_form_pdf with form_type 'financial_resolution'. Lay out the data
   as label -> value pairs (Original balance, Agreed resolution, Settlement
   amount, Payment schedule, First payment date, Conditions).
3. Email the form to the patient using the 'form_delivery' template with the
   PDF attached for signature.
4. If a new balance results from the resolution, update the patient's
   balance_due with update_patient.
""" + _COMMON_RULES,
    tools=[T.GET_PATIENT, T.LIST_PATIENTS, T.GENERATE_FORM,
           T.GET_EMAIL_TEMPLATE, T.SEND_EMAIL, T.UPDATE_PATIENT],
    input_fields=[
        {"name": "patient_id", "label": "Patient", "type": "patient"},
        {"name": "original_balance", "label": "Original outstanding balance", "type": "number"},
        {"name": "resolution_type", "label": "Resolution type (settlement / plan / write-off)",
         "type": "text"},
        {"name": "settlement_amount", "label": "Agreed amount", "type": "number"},
        {"name": "payment_schedule", "label": "Payment schedule", "type": "textarea"},
        {"name": "conditions", "label": "Conditions (optional)", "type": "textarea",
         "optional": True},
    ],
)

ONBOARDING_AGENT = AgentSpec(
    key="onboarding",
    name="Onboarding Agent",
    description="Sends the new-patient onboarding email from your template, and sends a receipt when a contract is signed.",
    system_prompt="""You are the Onboarding Agent. You handle two events:

EVENT 'onboard' — a new patient joined (contract signed, care plan in place):
1. get_patient for their record.
2. Fetch the 'onboarding' template (built by the practice), fill every
   placeholder, and send_email. Do not rewrite the template's wording, layout
   or styling — it is a designed HTML email; only substitute values.
   Financial placeholders ({{treatment_plan}}, {{estimated_duration}},
   {{total_contract_fee}}, {{down_payment}}, {{remaining_balance}},
   {{monthly_amount}}, {{num_payments}}, {{first_due_date}},
   {{payment_method}}, {{final_payment}}) come from the input data. Compute
   {{remaining_balance}} as total_contract_fee - down_payment when not given.
   Format money values with a $ sign and thousands separators. For any value
   you are not given and cannot compute, substitute an em dash (—), never a
   raw {{placeholder}} or a made-up number.
3. update_patient: set status to 'onboarded' and onboarded_at to today (ISO date).

EVENT 'contract_signed' — a patient signed their contract:
1. get_patient for their record.
2. generate_receipt_pdf for the contract payment described in the input (if no
   amount is given, issue a zero-amount confirmation receipt noting the signed
   contract in the line items).
3. Fetch the 'receipt_email' template, fill it, and send_email with the receipt
   attached.
4. update_patient: set contract_signed_at to today (ISO date).
""" + _COMMON_RULES,
    tools=[T.GET_PATIENT, T.LIST_PATIENTS, T.GET_EMAIL_TEMPLATE, T.SEND_EMAIL,
           T.GENERATE_RECEIPT, T.UPDATE_PATIENT],
    input_fields=[
        {"name": "event", "label": "Event", "type": "select",
         "options": ["onboard", "contract_signed"]},
        {"name": "patient_id", "label": "Patient", "type": "patient"},
        {"name": "treatment_plan", "label": "Treatment plan", "type": "text", "optional": True},
        {"name": "estimated_duration", "label": "Estimated duration", "type": "text", "optional": True},
        {"name": "total_contract_fee", "label": "Total contract fee", "type": "number", "optional": True},
        {"name": "down_payment", "label": "Down payment received", "type": "number", "optional": True},
        {"name": "monthly_amount", "label": "Monthly payment", "type": "number", "optional": True},
        {"name": "num_payments", "label": "Number of monthly payments", "type": "number", "optional": True},
        {"name": "first_due_date", "label": "First payment due", "type": "date", "optional": True},
        {"name": "payment_method", "label": "Payment method", "type": "text", "optional": True},
        {"name": "contract_amount", "label": "Contract payment amount (for contract_signed)",
         "type": "number", "optional": True},
        {"name": "notes", "label": "Notes (optional)", "type": "textarea", "optional": True},
    ],
)

AGENTS: dict[str, AgentSpec] = {spec.key: spec for spec in [
    RECEIPT_AGENT, ZOHO_CONTEXT_AGENT, FOLLOWUP_AGENT,
    ACKNOWLEDGEMENT_AGENT, RESOLUTION_AGENT, ONBOARDING_AGENT,
]}

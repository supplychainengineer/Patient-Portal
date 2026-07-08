"""Email templates, editable from the Templates page. Placeholders use
{{variable}} syntax; agents fill them from patient/sheet context. The
`onboarding` template is intentionally a scaffold — replace it with the
template you're building."""
from datetime import datetime, timezone

from database import db

DEFAULT_TEMPLATES = [
    {
        "key": "onboarding",
        "name": "New Patient Onboarding",
        "subject": "Welcome to {{clinic_name}}, {{patient_name}}!",
        "html_body": (
            "<p>Hi {{patient_name}},</p>"
            "<p><em>[YOUR ONBOARDING TEMPLATE GOES HERE — use the \"Import HTML "
            "file\" button on the Templates page to load your designed email "
            "(e.g. asana_ortho_welcome.html), or paste the HTML into the editor. "
            "Put {{placeholders}} wherever the agent should substitute values: "
            "{{patient_name}}, {{clinic_name}}, {{clinic_phone}}, {{clinic_email}}, "
            "{{treatment_plan}}, {{estimated_duration}}, {{total_contract_fee}}, "
            "{{down_payment}}, {{remaining_balance}}, {{monthly_amount}}, "
            "{{num_payments}}, {{first_due_date}}, {{payment_method}}, "
            "{{final_payment}}. Values the agent isn't given render as an em "
            "dash (—).]</em></p>"
            "<p>Welcome aboard!<br/>{{clinic_name}}</p>"
        ),
    },
    {
        "key": "receipt_email",
        "name": "Receipt Delivery Email",
        "subject": "Your payment receipt from {{clinic_name}}",
        "html_body": (
            "<p>Dear {{patient_name}},</p>"
            "<p>Thank you for your payment of <b>{{amount_paid}}</b>. "
            "Your receipt is attached to this email for your records.</p>"
            "<p>Warm regards,<br/>{{clinic_name}}</p>"
        ),
    },
    {
        "key": "dues_followup",
        "name": "Pending Dues Follow-up",
        "subject": "Friendly reminder: pending balance at {{clinic_name}}",
        "html_body": (
            "<p>Dear {{patient_name}},</p>"
            "<p>This is a friendly reminder that your account shows a pending "
            "balance of <b>{{balance_due}}</b>. You can settle it at your next "
            "visit or contact us at {{clinic_phone}} to arrange payment.</p>"
            "<p>If you have already made this payment, please disregard this "
            "message.</p><p>Thank you,<br/>{{clinic_name}}</p>"
        ),
    },
    {
        "key": "form_delivery",
        "name": "Financial Form Delivery",
        "subject": "{{form_name}} from {{clinic_name}}",
        "html_body": (
            "<p>Dear {{patient_name}},</p>"
            "<p>Please find your <b>{{form_name}}</b> attached. Kindly review, "
            "sign and return it at your earliest convenience.</p>"
            "<p>Thank you,<br/>{{clinic_name}}</p>"
        ),
    },
]


def _form_document(title: str, intro: str, rows: list[tuple[str, str]]) -> str:
    """Default HTML layout for a form *document* (rendered to the PDF).
    Replace it wholesale via 'Import HTML file' on the Templates page —
    keep layout table-based with inline styles (the PDF renderer does not
    support flexbox/grid)."""
    row_html = "".join(
        f'<tr><td style="background:#f0fdfa;border:1px solid #d6d3cb;padding:8px 10px;'
        f'font-weight:bold;width:38%;">{label}</td>'
        f'<td style="border:1px solid #d6d3cb;padding:8px 10px;">{{{{{key}}}}}</td></tr>'
        for label, key in rows
    )
    return f"""<html><body style="font-family:Helvetica,Arial,sans-serif;color:#1f2937;font-size:11pt;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="border-bottom:3px solid #0f766e;padding-bottom:10px;">
    <span style="font-size:20pt;font-weight:bold;">{{{{clinic_name}}}}</span><br/>
    <span style="font-size:9pt;color:#555;">{{{{clinic_address}}}} · {{{{clinic_phone}}}} · {{{{clinic_email}}}}</span>
  </td></tr>
</table>
<h2 style="font-size:13pt;letter-spacing:2px;color:#0f766e;margin:18px 0 2px 0;">{title}</h2>
<p style="font-size:9pt;color:#555;margin:0 0 14px 0;">Document #: {{{{form_no}}}} &nbsp;|&nbsp; Date: {{{{date}}}}</p>
<p><b>Patient:</b> {{{{patient_name}}}}</p>
<p style="margin:10px 0 16px 0;">{intro}</p>
<table width="100%" cellpadding="0" cellspacing="0" style="font-size:10.5pt;">{row_html}</table>
<br/><br/><br/>
<table width="100%" cellpadding="0" cellspacing="0" style="font-size:9pt;color:#555;">
  <tr>
    <td width="45%" style="border-top:1px solid #333;padding-top:4px;">Patient signature</td>
    <td width="10%"></td>
    <td width="45%" style="border-top:1px solid #333;padding-top:4px;">Date</td>
  </tr>
  <tr><td colspan="3" style="height:36px;"></td></tr>
  <tr>
    <td style="border-top:1px solid #333;padding-top:4px;">Practice representative</td>
    <td></td>
    <td style="border-top:1px solid #333;padding-top:4px;">Date</td>
  </tr>
</table>
</body></html>"""


# The FSA/HSA receipt document, recreated from the practice's own receipt PDF
# (ReceiptAO2026070108). {{items_rows}} is replaced with the payment-history
# rows; every other {{placeholder}} is filled from the receipt data and the
# clinic settings. Logo/signature load from backend/assets/.
RECEIPT_DOCUMENT_HTML = """<html>
<head><style>@page { size: letter; margin: 0; }</style></head>
<body style="font-family:Helvetica,Arial,sans-serif;color:#1f2937;font-size:10pt;margin:0;">

<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#12332a;">
  <tr>
    <td style="padding:10px 24px;" width="140">
      <img src="{{assets_dir}}/asana_logo.png" width="117" height="44"/>
    </td>
    <td style="padding:10px 10px;color:#ffffff;font-size:14pt;font-weight:bold;">
      {{clinic_legal_name}}
    </td>
    <td style="padding:10px 24px;text-align:right;color:#cfe3d8;">
      <span style="font-size:8pt;letter-spacing:2px;font-weight:bold;">FSA / HSA RECEIPT</span><br/>
      <span style="font-size:9pt;">{{receipt_no}}</span>
    </td>
  </tr>
</table>
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="height:4px;background-color:#4b7f5f;font-size:1pt;">&nbsp;</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px;">
  <tr>
    <td style="padding:0 24px;color:#8aa39a;font-size:8pt;letter-spacing:2px;font-weight:bold;">DATE</td>
    <td style="padding:0 24px;text-align:right;font-weight:bold;font-size:11pt;">{{date}}</td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:10px;">
  <tr>
    <td width="50%" style="padding:0 12px 0 24px;border-top:1px solid #e5e7e3;">
      <p style="color:#8aa39a;font-size:8pt;letter-spacing:2px;font-weight:bold;margin:8px 0 3px 0;">PRACTICE INFORMATION</p>
      <p style="font-weight:bold;margin:0 0 3px 0;">{{clinic_legal_name}}</p>
      <p style="margin:0 0 3px 0;color:#374151;">{{clinic_address}}</p>
      <p style="margin:0;color:#374151;">TIN: &nbsp;{{clinic_tin}}</p>
    </td>
    <td width="50%" style="padding:0 24px 0 12px;border-top:1px solid #e5e7e3;">
      <p style="color:#8aa39a;font-size:8pt;letter-spacing:2px;font-weight:bold;margin:8px 0 3px 0;">PATIENT INFORMATION</p>
      <p style="font-weight:bold;margin:0 0 3px 0;">{{patient_name}}</p>
      <p style="margin:0 0 3px 0;color:#374151;">{{patient_address}}</p>
      <p style="margin:0;color:#374151;">Responsible Party: &nbsp;{{responsible_party}}</p>
    </td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">
  <tr><td colspan="3" style="padding:8px 24px 3px 24px;border-top:1px solid #e5e7e3;color:#8aa39a;font-size:8pt;letter-spacing:2px;font-weight:bold;">SERVICE DETAILS</td></tr>
  <tr>
    <td style="padding:2px 12px 0 24px;color:#8aa39a;font-size:8.5pt;">Service Description</td>
    <td style="padding:2px 12px 0 12px;color:#8aa39a;font-size:8.5pt;">Contract Date</td>
    <td style="padding:2px 24px 0 12px;color:#8aa39a;font-size:8.5pt;">Appliance Placed</td>
  </tr>
  <tr>
    <td style="padding:2px 12px 0 24px;font-weight:bold;">{{service_description}}</td>
    <td style="padding:2px 12px 0 12px;font-weight:bold;">{{contract_date}}</td>
    <td style="padding:2px 24px 0 12px;font-weight:bold;">{{appliance_placed}}</td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">
  <tr><td style="padding:8px 24px 3px 24px;border-top:1px solid #e5e7e3;color:#8aa39a;font-size:8pt;letter-spacing:2px;font-weight:bold;">PAYMENT DETAILS</td></tr>
  <tr><td style="padding:2px 24px 6px 24px;">This confirms that {{payment_type}} payment has been received for the qualified orthodontic services rendered to {{patient_name}}.</td></tr>
</table>

<table width="92%" align="center" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7e3;">
  <tr style="background-color:#f3f5f4;">
    <td style="padding:6px 12px;color:#5b7f75;font-size:8pt;letter-spacing:1px;font-weight:bold;">DESCRIPTION</td>
    <td style="padding:6px 12px;color:#5b7f75;font-size:8pt;letter-spacing:1px;font-weight:bold;">DATE OF PAYMENT</td>
    <td style="padding:6px 12px;color:#5b7f75;font-size:8pt;letter-spacing:1px;font-weight:bold;text-align:right;">AMOUNT PAID</td>
  </tr>
  {{items_rows}}
  <tr style="background-color:#eef2ef;">
    <td colspan="2" style="padding:8px 12px;font-weight:bold;">TOTAL AMOUNT PAID</td>
    <td style="padding:8px 12px;font-weight:bold;text-align:right;font-size:11pt;">{{total_amount_paid}}</td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">
  <tr><td style="padding:8px 24px 3px 24px;border-top:1px solid #e5e7e3;color:#8aa39a;font-size:8pt;letter-spacing:2px;font-weight:bold;">CERTIFICATION</td></tr>
  <tr><td style="padding:2px 24px 0 24px;">I certify that the services listed above were provided on the date specified and that the payment covers the {{payment_type}} treatment fee.</td></tr>
  <tr><td style="padding:6px 24px 0 24px;font-style:italic;color:#4b5563;font-size:9pt;">While services were initially rendered under Laurie M Estes DDS Inc., the practice has since transitioned to Dr. Nourah Abdul Kader DDS, MS, Inc. DBA Asana Ortho. This patient continued treatment under new ownership.</td></tr>
  <tr><td style="padding:8px 24px 0 24px;font-style:italic;">Sincerely,</td></tr>
  <tr><td style="padding:4px 24px 0 24px;"><img src="{{assets_dir}}/signature.png" width="74" height="48"/></td></tr>
  <tr><td style="padding:4px 24px 0 24px;font-weight:bold;">Dr. Nourah Abdul Kader, DMD, MS</td></tr>
  <tr><td style="padding:2px 24px 0 24px;color:#5b7f75;font-size:9pt;">Founder and Orthodontist</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#12332a;margin-top:8px;">
  <tr>
    <td style="padding:10px 24px;color:#cfe3d8;font-size:8.5pt;">{{clinic_address}}</td>
    <td style="padding:10px 24px;text-align:right;color:#cfe3d8;font-size:8.5pt;">T: {{clinic_phone}} &nbsp;|&nbsp; F: {{clinic_fax}} &nbsp;|&nbsp; {{clinic_website}}</td>
  </tr>
</table>

</body></html>"""

DEFAULT_TEMPLATES += [
    {
        "key": "receipt_document",
        "name": "Payment Receipt (document)",
        "subject": "FSA / HSA RECEIPT",
        "html_body": RECEIPT_DOCUMENT_HTML,
    },
    {
        "key": "financial_acknowledgement_form",
        "name": "Financial Acknowledgement Form (document)",
        "subject": "FINANCIAL ACKNOWLEDGEMENT FORM",  # used as the document title
        "html_body": _form_document(
            "FINANCIAL ACKNOWLEDGEMENT FORM",
            "I, the undersigned, acknowledge my financial responsibility for "
            "services rendered by the practice as detailed below. I understand "
            "and accept the charges, payment terms and policies described in "
            "this document.",
            [("Service / Treatment", "service_description"),
             ("Total Charges", "total_charges"),
             ("Payment Terms", "payment_terms"),
             ("Insurance Details", "insurance_details"),
             ("Effective Date", "effective_date")],
        ),
    },
    {
        "key": "financial_resolution_form",
        "name": "Financial Resolution Form (document)",
        "subject": "FINANCIAL RESOLUTION FORM",
        "html_body": _form_document(
            "FINANCIAL RESOLUTION FORM",
            "This document records the mutually agreed resolution of the "
            "outstanding financial balance detailed below, including the agreed "
            "settlement terms and payment schedule.",
            [("Original Outstanding Balance", "original_balance"),
             ("Resolution Type", "resolution_type"),
             ("Agreed Amount", "settlement_amount"),
             ("Payment Schedule", "payment_schedule"),
             ("Conditions", "conditions")],
        ),
    },
]


def seed_templates():
    for tpl in DEFAULT_TEMPLATES:
        if not db.templates.find_one({"key": tpl["key"]}):
            db.templates.insert_one({**tpl, "updated_at": datetime.now(timezone.utc).isoformat()})


def get_template(key: str) -> dict | None:
    doc = db.templates.find_one({"key": key}, {"_id": 0})
    return doc

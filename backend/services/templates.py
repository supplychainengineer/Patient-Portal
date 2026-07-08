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


def seed_templates():
    for tpl in DEFAULT_TEMPLATES:
        if not db.templates.find_one({"key": tpl["key"]}):
            db.templates.insert_one({**tpl, "updated_at": datetime.now(timezone.utc).isoformat()})


def get_template(key: str) -> dict | None:
    doc = db.templates.find_one({"key": key}, {"_id": 0})
    return doc

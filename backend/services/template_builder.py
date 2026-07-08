"""Template Builder — turns example files (HTML, screenshots, PDFs, text)
into a ready-to-use template for a given template key.

Claude studies the examples (using vision for images / document reading for
PDFs), reproduces the design as clean HTML, and inserts the {{placeholders}}
the target template supports. The result is saved to the templates collection
where it can be reviewed, tweaked and used by the agents.
"""
import base64
import json
import uuid
from datetime import datetime, timezone

import anthropic

import config
from database import db

# What the agents can substitute per template key (documented on the UI too).
COMMON_PLACEHOLDERS = ["patient_name", "clinic_name", "clinic_address",
                       "clinic_phone", "clinic_email"]
KEY_PLACEHOLDERS = {
    "onboarding": ["treatment_plan", "estimated_duration", "total_contract_fee",
                   "down_payment", "remaining_balance", "monthly_amount",
                   "num_payments", "first_due_date", "payment_method",
                   "final_payment"],
    "receipt_email": ["amount_paid", "balance_due"],
    "dues_followup": ["balance_due"],
    "form_delivery": ["form_name"],
    "receipt_document": ["receipt_no", "date", "patient_address",
                         "responsible_party", "service_description",
                         "contract_date", "appliance_placed", "payment_type",
                         "items_rows", "total_amount_paid", "amount_paid",
                         "balance_due", "payment_method", "payment_date",
                         "clinic_legal_name", "clinic_tin", "clinic_fax",
                         "clinic_website", "assets_dir"],
    "financial_acknowledgement_form": ["service_description", "total_charges",
                                       "payment_terms", "insurance_details",
                                       "effective_date", "form_no", "date"],
    "financial_resolution_form": ["original_balance", "resolution_type",
                                  "settlement_amount", "payment_schedule",
                                  "conditions", "form_no", "date"],
}

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_TEXT_SUFFIXES = (".html", ".htm", ".txt", ".css", ".md")

MAX_FILES = 6
MAX_FILE_BYTES = 8 * 1024 * 1024


class TemplateBuilderError(Exception):
    pass


def _example_block(filename: str, data: bytes, content_type: str):
    content_type = (content_type or "").lower()
    if content_type in _IMAGE_TYPES:
        return {"type": "image",
                "source": {"type": "base64", "media_type": content_type,
                           "data": base64.standard_b64encode(data).decode()}}
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        return {"type": "document",
                "source": {"type": "base64", "media_type": "application/pdf",
                           "data": base64.standard_b64encode(data).decode()}}
    if filename.lower().endswith(_TEXT_SUFFIXES) or content_type.startswith("text/"):
        text = data.decode("utf-8", errors="replace")
        return {"type": "text",
                "text": f"--- EXAMPLE FILE: {filename} ---\n{text}\n--- END OF {filename} ---"}
    raise TemplateBuilderError(
        f"Unsupported example file '{filename}' ({content_type or 'unknown type'}). "
        "Use HTML, TXT, PNG, JPG, GIF, WEBP or PDF.")


def _system_prompt(key: str, template_name: str) -> str:
    placeholders = COMMON_PLACEHOLDERS + KEY_PLACEHOLDERS.get(key, [])
    is_form_doc = key.endswith("_form")
    medium_rules = (
        "The template is rendered to a PDF DOCUMENT with xhtml2pdf, so: use "
        "table-based layout with inline styles only; no flexbox, no grid, no "
        "external CSS or fonts, no JavaScript; keep it printable on US Letter."
        if is_form_doc else
        "The template is sent as an HTML EMAIL, so: use email-safe HTML — "
        "table-based layout, inline styles, no JavaScript, no external "
        "stylesheets; images only via absolute hosted https URLs (keep any "
        "image URLs found in the examples; if an example references a local "
        "file path, replace it with a clearly marked comment like "
        "<!-- TODO: host this image and set src -->)."
    )
    return f"""You are an expert HTML template developer for a patient portal.
You will be shown one or more EXAMPLE files (HTML source, screenshots, PDFs or
text) of the practice's designed communications. Build the '{template_name}'
template from them.

Rules:
- Reproduce the examples' visual design, structure, branding, colors,
  typography and wording as faithfully as the medium allows. Do not invent a
  new design; you are converting their design into a reusable template.
- {medium_rules}
- Replace every patient-specific or transaction-specific value in the examples
  (names, amounts, dates, plan details) with the matching placeholder from
  this list, written exactly as {{{{placeholder}}}}:
  {', '.join(placeholders)}.
  Values that have no matching placeholder stay as literal text.
- Where the examples show intentionally blank values (like "$—" or "—"),
  still use the matching placeholder — the system renders missing data as an
  em dash automatically.
- If the template has repeating line-item/payment-history rows and
  'items_rows' is in the placeholder list, put a single {{{{items_rows}}}} where
  the <tr> rows belong — the system injects the rows there. Local images can
  be referenced as {{{{assets_dir}}}}/filename.png when that placeholder is
  available (document templates only).
- Also write a fitting email subject line (for form documents, the subject
  field is used as the document title).
Return the finished template only — no explanations."""


def build_from_examples(key: str, files: list, instructions: str = "") -> dict:
    """files: list of (filename, data_bytes, content_type). Saves and returns
    the updated template."""
    if not config.ANTHROPIC_API_KEY:
        raise TemplateBuilderError(
            "The Template Builder needs the Anthropic connection: set "
            "ANTHROPIC_API_KEY in backend/.env (see the Settings page).")
    tpl = db.templates.find_one({"key": key}, {"_id": 0})
    if not tpl:
        raise TemplateBuilderError(f"Unknown template key '{key}'.")
    if not files:
        raise TemplateBuilderError("Upload at least one example file.")
    if len(files) > MAX_FILES:
        raise TemplateBuilderError(f"Too many files — maximum {MAX_FILES}.")

    content = []
    for filename, data, content_type in files:
        if len(data) > MAX_FILE_BYTES:
            raise TemplateBuilderError(f"'{filename}' is too large (max 8 MB).")
        content.append(_example_block(filename, data, content_type))
    task = "Build the template from these examples."
    if instructions.strip():
        task += f"\n\nAdditional instructions from the practice:\n{instructions.strip()}"
    content.append({"type": "text", "text": task})

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    schema = {
        "type": "object",
        "properties": {
            "subject": {"type": "string",
                        "description": "Email subject line (or document title for form documents)"},
            "html_body": {"type": "string", "description": "The complete template HTML"},
        },
        "required": ["subject", "html_body"],
        "additionalProperties": False,
    }
    with client.messages.stream(
        model=config.AGENT_MODEL,
        max_tokens=64000,
        thinking={"type": "adaptive"},
        system=_system_prompt(key, tpl["name"]),
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise TemplateBuilderError("The model declined to process these examples.")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        raise TemplateBuilderError("Template generation returned malformed output — try again.")

    now = datetime.now(timezone.utc).isoformat()
    db.templates.update_one({"key": key}, {"$set": {
        "subject": result["subject"], "html_body": result["html_body"],
        "updated_at": now, "built_from_examples": [f[0] for f in files],
    }})
    db.agent_runs.insert_one({
        "id": str(uuid.uuid4()), "agent_key": "template_builder",
        "agent_name": "Template Builder", "status": "completed",
        "task": f"Build '{tpl['name']}' template from {len(files)} example file(s)",
        "payload": {"template_key": key, "examples": [f[0] for f in files],
                    "instructions": instructions},
        "steps": [], "summary": f"Rebuilt template '{key}' from examples: "
                                f"{', '.join(f[0] for f in files)}.",
        "started_at": now, "finished_at": now, "triggered_by": "templates_page",
    })
    return db.templates.find_one({"key": key}, {"_id": 0})

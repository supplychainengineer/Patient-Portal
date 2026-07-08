"""PDF generation for receipts and financial forms.
Each generated document is stored under backend/storage and indexed in the
`documents` collection so the UI can list and download it.

Forms are template-driven: if a document template exists in the `templates`
collection (keys `financial_acknowledgement_form` / `financial_resolution_form`
— editable and importable on the Templates page), its HTML is filled with the
form data and rendered to PDF. Otherwise a built-in reportlab layout is used."""
import logging
import re
import uuid
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

import config
from database import db

_styles = getSampleStyleSheet()
_title = ParagraphStyle("DocTitle", parent=_styles["Title"], fontSize=18, spaceAfter=4)
_muted = ParagraphStyle("Muted", parent=_styles["Normal"], textColor=colors.HexColor("#555555"), fontSize=9)
_body = _styles["Normal"]
_h2 = ParagraphStyle("H2", parent=_styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)


def _header(elements, doc_title: str, doc_number: str):
    elements.append(Paragraph(config.CLINIC_NAME, _title))
    elements.append(Paragraph(
        f"{config.CLINIC_ADDRESS} · {config.CLINIC_PHONE} · {config.CLINIC_EMAIL}", _muted))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#0f766e"), thickness=2))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(doc_title, _h2))
    elements.append(Paragraph(
        f"Document #: {doc_number} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}", _muted))
    elements.append(Spacer(1, 12))


def _register(kind: str, title: str, path, patient_id=None, patient_name=None,
              run_id=None, meta=None) -> dict:
    doc = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "title": title,
        "filename": path.name,
        "path": str(path),
        "patient_id": patient_id,
        "patient_name": patient_name,
        "run_id": run_id,
        "meta": meta or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db.documents.insert_one(dict(doc))
    return doc


def _next_receipt_no() -> str:
    """Sequential per-month numbering matching the practice's format,
    e.g. AO-202607-0108."""
    ym = datetime.now().strftime("%Y%m")
    seq = db.documents.count_documents(
        {"kind": "receipt", "meta.receipt_no": {"$regex": f"-{ym}-"}}) + 1
    return f"{config.RECEIPT_PREFIX}-{ym}-{seq:04d}"


def _items_rows_html(items: list) -> str:
    """Payment-history rows injected at {{items_rows}} in the receipt
    template: {description, date, amount} per row."""
    cell = "padding:5px 12px;border-bottom:1px solid #e5e7e3;font-size:10pt;"
    rows = []
    for item in items:
        rows.append(
            f'<tr><td style="{cell}">{item.get("description", "Payment")}</td>'
            f'<td style="{cell}">{item.get("date", "") or "—"}</td>'
            f'<td style="{cell}text-align:right;">{_money(item.get("amount", 0))}</td></tr>')
    return "".join(rows)


def generate_receipt(patient_name: str, items: list, amount_paid: float,
                     payment_method: str = "", payment_date: str = "",
                     balance_due: float = 0.0, notes: str = "",
                     patient_id: str = None, run_id: str = None,
                     extra: dict | None = None) -> dict:
    """items: list of {description, amount, date?}. extra: additional values
    for the receipt template (service_description, contract_date,
    appliance_placed, responsible_party, patient_address, payment_type...)."""
    receipt_no = _next_receipt_no()
    path = config.STORAGE_DIR / f"{receipt_no}.pdf"

    receipt_items = items or [{"description": "Payment received",
                               "date": payment_date, "amount": amount_paid}]
    context = {
        "receipt_no": receipt_no,
        "patient_name": patient_name,
        "responsible_party": (extra or {}).get("responsible_party") or patient_name,
        "payment_type": (extra or {}).get("payment_type") or "Partial",
        "items_rows": _items_rows_html(receipt_items),
        "total_amount_paid": _money(amount_paid),
        "amount_paid": _money(amount_paid),
        "balance_due": _money(balance_due),
        "payment_method": payment_method,
        "payment_date": payment_date,
        "notes": notes,
        **{k: v for k, v in (extra or {}).items() if v not in (None, "")},
    }
    if _render_template_pdf("receipt_document", context, path):
        return _register("receipt", f"Receipt {receipt_no} — {patient_name}", path,
                         patient_id=patient_id, patient_name=patient_name,
                         run_id=run_id,
                         meta={"receipt_no": receipt_no, "amount_paid": amount_paid,
                               "balance_due": balance_due,
                               "rendered_from": "receipt_document template"})
    pdf = SimpleDocTemplate(str(path), pagesize=LETTER,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    el = []
    _header(el, "PAYMENT RECEIPT", receipt_no)
    el.append(Paragraph(f"<b>Received from:</b> {patient_name}", _body))
    if payment_date:
        el.append(Paragraph(f"<b>Payment date:</b> {payment_date}", _body))
    if payment_method:
        el.append(Paragraph(f"<b>Payment method:</b> {payment_method}", _body))
    el.append(Spacer(1, 12))

    rows = [["Description", "Amount"]]
    for item in items or [{"description": "Payment received", "amount": amount_paid}]:
        rows.append([item.get("description", ""), f"{float(item.get('amount', 0)):,.2f}"])
    rows.append(["Amount paid", f"{float(amount_paid):,.2f}"])
    rows.append(["Balance due", f"{float(balance_due):,.2f}"])

    table = Table(rows, colWidths=[4.7 * inch, 1.8 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -3), [colors.white, colors.HexColor("#f0fdfa")]),
        ("BACKGROUND", (0, -2), (-1, -2), colors.HexColor("#ecfdf5")),
    ]))
    el.append(table)
    if notes:
        el.append(Spacer(1, 12))
        el.append(Paragraph(f"<b>Notes:</b> {notes}", _body))
    el.append(Spacer(1, 24))
    el.append(Paragraph("Thank you for your payment.", _muted))
    pdf.build(el)

    return _register("receipt", f"Receipt {receipt_no} — {patient_name}", path,
                     patient_id=patient_id, patient_name=patient_name, run_id=run_id,
                     meta={"receipt_no": receipt_no, "amount_paid": amount_paid,
                           "balance_due": balance_due})


FORM_TITLES = {
    "financial_acknowledgement": "FINANCIAL ACKNOWLEDGEMENT FORM",
    "financial_resolution": "FINANCIAL RESOLUTION FORM",
}

FORM_INTROS = {
    "financial_acknowledgement": (
        "I, the undersigned, acknowledge my financial responsibility for services "
        "rendered by the practice as detailed below. I understand and accept the "
        "charges, payment terms and policies described in this document."),
    "financial_resolution": (
        "This document records the mutually agreed resolution of the outstanding "
        "financial balance detailed below, including the agreed settlement terms "
        "and payment schedule."),
}


logger = logging.getLogger("patient-portal.pdf")

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_ ]+)\s*\}\}")


def _fill_placeholders(html: str, context: dict) -> str:
    """Deterministically substitute {{placeholders}}; unknown ones become an
    em dash so a designed form never ships with raw template syntax."""
    normalized = {str(k).strip().lower().replace(" ", "_"): str(v)
                  for k, v in context.items() if v not in (None, "")}

    def sub(match):
        key = match.group(1).strip().lower().replace(" ", "_")
        return normalized.get(key, "—")

    return _PLACEHOLDER.sub(sub, html)


def _clinic_context() -> dict:
    return {
        "clinic_name": config.CLINIC_NAME,
        "clinic_legal_name": config.CLINIC_LEGAL_NAME,
        "clinic_address": config.CLINIC_ADDRESS,
        "clinic_phone": config.CLINIC_PHONE,
        "clinic_fax": config.CLINIC_FAX,
        "clinic_email": config.CLINIC_EMAIL,
        "clinic_website": config.CLINIC_WEBSITE,
        "clinic_tin": config.CLINIC_TIN,
        "assets_dir": str(config.ASSETS_DIR),
        "date": datetime.now(timezone.utc).strftime("%m/%d/%Y"),
    }


def _render_template_pdf(template_key: str, context: dict, path) -> bool:
    """Render a document template from the templates collection to PDF.
    Returns False when no template exists or rendering fails (callers fall
    back to the built-in reportlab layout)."""
    tpl = db.templates.find_one({"key": template_key}, {"_id": 0})
    if not tpl or not tpl.get("html_body"):
        return False
    try:
        from xhtml2pdf import pisa
    except ImportError:
        logger.warning("xhtml2pdf not installed — using built-in layout.")
        return False

    html = _fill_placeholders(tpl["html_body"], {**_clinic_context(), **context})
    try:
        with open(path, "wb") as fh:
            result = pisa.CreatePDF(html, dest=fh)
        if result.err:
            raise RuntimeError(f"{result.err} rendering error(s)")
        return True
    except Exception as exc:
        logger.warning("Document template %s failed to render (%s) — using "
                       "built-in layout.", template_key, exc)
        path.unlink(missing_ok=True)
        return False


def _money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value or "—")


def generate_form(form_type: str, patient_name: str, fields: dict,
                  patient_id: str = None, run_id: str = None) -> dict:
    """fields: flat dict of the form's input values, keyed by field name
    (e.g. service_description, total_charges)."""
    if form_type not in FORM_TITLES:
        raise ValueError(f"Unknown form type: {form_type}")
    form_no = f"{'FAF' if form_type == 'financial_acknowledgement' else 'FRF'}-" \
              f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    path = config.STORAGE_DIR / f"{form_no}.pdf"

    form_context = {**fields, "patient_name": patient_name, "form_no": form_no}
    if _render_template_pdf(f"{form_type}_form", form_context, path):
        return _register(form_type,
                         f"{FORM_TITLES[form_type].title()} {form_no} — {patient_name}",
                         path, patient_id=patient_id, patient_name=patient_name,
                         run_id=run_id,
                         meta={"form_no": form_no, "fields": fields,
                               "rendered_from": f"{form_type}_form template"})
    pdf = SimpleDocTemplate(str(path), pagesize=LETTER,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    el = []
    _header(el, FORM_TITLES[form_type], form_no)
    el.append(Paragraph(f"<b>Patient:</b> {patient_name}", _body))
    el.append(Spacer(1, 8))
    el.append(Paragraph(FORM_INTROS[form_type], _body))
    el.append(Spacer(1, 12))

    rows = [[Paragraph(f"<b>{str(label).replace('_', ' ').title()}</b>", _body),
             Paragraph(str(value), _body)]
            for label, value in fields.items() if value not in (None, "")]
    if rows:
        table = Table(rows, colWidths=[2.4 * inch, 4.1 * inch])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0fdfa")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        el.append(table)

    el.append(Spacer(1, 40))
    sig = Table([["_________________________", "_________________________"],
                 ["Patient signature", "Date"],
                 ["", ""],
                 ["_________________________", "_________________________"],
                 ["Practice representative", "Date"]],
                colWidths=[3.2 * inch, 3.2 * inch])
    sig.setStyle(TableStyle([("FONTSIZE", (0, 1), (-1, 1), 8),
                             ("FONTSIZE", (0, 4), (-1, 4), 8),
                             ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#555555")),
                             ("TEXTCOLOR", (0, 4), (-1, 4), colors.HexColor("#555555"))]))
    el.append(sig)
    pdf.build(el)

    return _register(form_type, f"{FORM_TITLES[form_type].title()} {form_no} — {patient_name}",
                     path, patient_id=patient_id, patient_name=patient_name, run_id=run_id,
                     meta={"form_no": form_no, "fields": fields})

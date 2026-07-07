"""PDF generation for receipts and financial forms (reportlab).
Each generated document is stored under backend/storage and indexed in the
`documents` collection so the UI can list and download it."""
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


def generate_receipt(patient_name: str, items: list, amount_paid: float,
                     payment_method: str = "", payment_date: str = "",
                     balance_due: float = 0.0, notes: str = "",
                     patient_id: str = None, run_id: str = None) -> dict:
    """items: list of {description, amount}."""
    receipt_no = f"RCPT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    path = config.STORAGE_DIR / f"{receipt_no}.pdf"
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


def generate_form(form_type: str, patient_name: str, fields: dict,
                  patient_id: str = None, run_id: str = None) -> dict:
    """fields: ordered dict of label -> value collected from the portal form."""
    if form_type not in FORM_TITLES:
        raise ValueError(f"Unknown form type: {form_type}")
    form_no = f"{'FAF' if form_type == 'financial_acknowledgement' else 'FRF'}-" \
              f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    path = config.STORAGE_DIR / f"{form_no}.pdf"
    pdf = SimpleDocTemplate(str(path), pagesize=LETTER,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    el = []
    _header(el, FORM_TITLES[form_type], form_no)
    el.append(Paragraph(f"<b>Patient:</b> {patient_name}", _body))
    el.append(Spacer(1, 8))
    el.append(Paragraph(FORM_INTROS[form_type], _body))
    el.append(Spacer(1, 12))

    rows = [[Paragraph(f"<b>{label}</b>", _body), Paragraph(str(value), _body)]
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
